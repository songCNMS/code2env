"""D2 LLM rollout driver — multi-round tool-calling agent loop over Code2Env.

The driver feeds the env observation and the available tool schemas to an
OpenAI-compatible chat model, asks it to emit a JSON ``tool_call`` action, parses
that action (native ``tool_calls`` or JSON-in-content), runs ``Code2Env.step``,
and loops until the agent calls ``submit_answer`` or the step budget is exhausted.
It adds bounded retries, format correction, and multi-endpoint fallback.

This module only *validates* rollouts; it does not train. The returned
``RolloutResult`` dict follows the contract shared with w3/w4 (do not rename
fields): see ``run_rollout``.
"""

from __future__ import annotations

import copy
import datetime
import ast
import json
from pathlib import Path
from typing import Any, Protocol

from code2env.llm import parse_llm_json
from code2env.rich_fixtures import fixture_component_descriptor
from code2env.runtime import Code2Env
from code2env.spec import source_root_for_spec

TRACE_MODE_DEFAULT = "default"
TRACE_MODE_SUBFUNCTIONS = "subfunctions"
TRACE_MODES = {TRACE_MODE_DEFAULT, TRACE_MODE_SUBFUNCTIONS}
CALL_ENTRYPOINT_TOOL = "call_entrypoint"
CALL_HELPER_TOOL = "call_helper"
SUBMIT_ANSWER_TOOL = "submit_answer"
HELPER_TOOL_PREFIX = "call_"


class ChatLLM(Protocol):
    model_name: str

    def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        ...


class RolloutActionError(ValueError):
    """Raised when an assistant message cannot be parsed into a tool_call action."""


class MockChatLLM:
    """Deterministic chat model for tests and offline dry runs.

    Each ``chat`` call pops the next scripted item and returns it as an assistant
    message. Items may be:

    - a dict action ``{"tool": ..., "arguments": {...}}`` -> serialized to JSON content
    - a raw string -> returned verbatim as content (use to inject malformed output)
    - ``{"__content__": "..."}`` -> returned verbatim (explicit raw content)
    """

    def __init__(self, scripted: list[Any], *, model_name: str = "mock-chat", fail_times: int = 0):
        self._queue: list[Any] = list(scripted)
        self.model_name = model_name
        self.calls = 0
        self._fail_times = fail_times

    def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        self.calls += 1
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("mock chat transport failure")
        if not self._queue:
            # Exhausted scripts default to a harmless no-op so loops terminate on budget.
            content = json.dumps({"tool": "inspect_state", "arguments": {}})
        else:
            item = self._queue.pop(0)
            if isinstance(item, str):
                content = item
            elif isinstance(item, dict) and "__content__" in item:
                content = str(item["__content__"])
            else:
                content = json.dumps(item)
        return {"role": "assistant", "content": content, "tool_calls": None}


class ScriptedSolveChat:
    """Adaptive offline solver mock: run the entrypoint, then submit its result.

    Reads the live env (``last_tool_result``) so it submits the correct answer
    without any network — used for the ``rollout`` CLI mock mode and integration
    tests. Produces a 2-round, qualified, correct rollout.
    """

    model_name = "mock-solver"

    def __init__(self, env: Code2Env):
        self.env = env
        self.calls = 0

    def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            action = {"tool": "call_entrypoint", "arguments": {}}
        else:
            answer = self.env.state.get("last_tool_result")
            action = {"tool": "submit_answer", "arguments": {"answer": answer}}
        return {"role": "assistant", "content": json.dumps(action), "tool_calls": None}


class ScriptedTraceSolveChat:
    """Offline solver mock for subfunction trace mode.

    It calls required semantic helper tools in the extracted order, then runs the
    entrypoint with fixture fallback, then submits the entrypoint result. This is
    intentionally deterministic so CLI mock runs can produce trace-mode evidence
    without using an endpoint.
    """

    model_name = "mock-trace-solver"

    def __init__(self, env: Code2Env):
        self.env = env
        self.calls = 0
        self._required_helpers = list(build_subfunction_trace_plan(env)["required_helper_tools"])

    def chat(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        self.calls += 1
        helper_index = self.calls - 1
        if helper_index < len(self._required_helpers):
            action = {"tool": self._required_helpers[helper_index], "arguments": {}}
        elif helper_index == len(self._required_helpers):
            action = {"tool": CALL_ENTRYPOINT_TOOL, "arguments": {}}
        else:
            answer = self.env.state.get("last_tool_result")
            action = {"tool": SUBMIT_ANSWER_TOOL, "arguments": {"answer": answer}}
        return {"role": "assistant", "content": json.dumps(action), "tool_calls": None}


# Guidance that prevents the "executed but mismatched golden" false negative
# (root cause B): the agent must NOT fabricate call_entrypoint arguments — the
# runtime falls back to the pinned spec.fixture when args/kwargs are omitted, and
# the golden answer is graded against that exact fixture.
CALL_ENTRYPOINT_FIXTURE_GUIDANCE = (
    "IMPORTANT — call_entrypoint arguments: do NOT invent, guess, or re-type any "
    'argument values. Call it with empty arguments ({"tool": "call_entrypoint", '
    '"arguments": {}}); the environment automatically runs the entrypoint with its '
    "provided fixture, and the submitted answer is graded by exact match against that "
    "exact fixture. Supplying your own args/kwargs will mismatch the golden answer even "
    "if the call succeeds. The same applies to dedicated call_<helper> tools — omit "
    "args/kwargs unless the task explicitly tells you to vary them."
)


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def build_tool_descriptions(env: Code2Env) -> list[dict[str, Any]]:
    """Describe the env's tools (name/description/input_schema) for the prompt."""
    descriptions: list[dict[str, Any]] = []
    for tool in env.spec.tools:
        descriptions.append(
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
        )
    return descriptions


def build_subfunction_trace_plan(env: Code2Env) -> dict[str, Any]:
    """Extract the helper sequence for trace mode from EnvSpec tool provenance.

    The plan prefers dedicated semantic tools (``call_<helper>`` backed by a
    concrete function) and orders them by the entrypoint's decomposed step
    callees. Helpers that are known by provenance but not available as direct
    semantic tools are recorded as skipped with reasons instead of being routed
    through the generic ``call_helper`` wrapper.
    """

    semantic_tools = _semantic_helper_tools(env)
    helper_candidates = _helper_candidates(env)
    side_effect_helpers = _side_effect_helpers(env)

    required: list[str] = []
    seen_helpers: set[str] = set()
    skipped: list[dict[str, str]] = []
    skipped_helpers: set[str] = set()

    def add_required(helper: str) -> None:
        if helper in seen_helpers:
            return
        tool_name = semantic_tools.get(helper)
        if tool_name is None:
            return
        required.append(tool_name)
        seen_helpers.add(helper)

    def add_skipped(helper: str, reason: str) -> None:
        if helper in seen_helpers or helper in skipped_helpers:
            return
        skipped.append({"helper": helper, "tool": f"{HELPER_TOOL_PREFIX}{helper}", "reason": reason})
        skipped_helpers.add(helper)

    for callee in _entrypoint_step_callees(env):
        if callee in semantic_tools:
            add_required(callee)
        elif callee in side_effect_helpers:
            add_skipped(callee, "side_effect_helper_not_exposed")
        elif callee in helper_candidates:
            add_skipped(callee, "direct_semantic_tool_unavailable")

    # Legacy or hand-authored specs may expose semantic helper tools without the
    # entrypoint step decomposition. Keep those useful tools in spec order.
    for helper in semantic_tools:
        add_required(helper)

    for helper in helper_candidates:
        if helper not in semantic_tools:
            reason = "side_effect_helper_not_exposed" if helper in side_effect_helpers else "direct_semantic_tool_unavailable"
            add_skipped(helper, reason)
    for helper in side_effect_helpers:
        if helper not in semantic_tools:
            add_skipped(helper, "side_effect_helper_not_exposed")

    return {
        "trace_mode": TRACE_MODE_SUBFUNCTIONS,
        "required_helper_tools": required,
        "skipped_helpers": skipped,
    }


def build_subfunction_trace_system_prompt(
    env: Code2Env,
    tools: list[dict[str, Any]],
    trace_plan: dict[str, Any] | None = None,
) -> str:
    """Build the trace-mode prompt while preserving the default tool protocol."""

    plan = trace_plan or build_subfunction_trace_plan(env)
    required = list(plan.get("required_helper_tools", []))
    if required:
        order = "\n".join(f"{index}. {tool}" for index, tool in enumerate(required, start=1))
        helper_instruction = (
            "Required helper tool order:\n"
            f"{order}\n"
            "Do not call call_entrypoint first. Call the required helper tools in exactly this order before "
            "calling call_entrypoint."
        )
    else:
        helper_instruction = (
            "No direct semantic helper tools are required for this environment. In trace mode, proceed to "
            "call_entrypoint, then submit_answer."
        )

    skipped = plan.get("skipped_helpers") or []
    skipped_block = ""
    if skipped:
        skipped_block = (
            "\nSkipped or unavailable helpers, with reasons:\n"
            f"{json.dumps(skipped, ensure_ascii=False, indent=2)}"
        )

    return (
        f"{build_system_prompt(env, tools)}\n\n"
        "SUBFUNCTION TRACE MODE:\n"
        "This rollout is collecting a decomposed helper trajectory, not only a black-box answer.\n"
        f"{helper_instruction}\n"
        "Call each helper with empty arguments unless the task explicitly requires different arguments; the "
        "runtime will use helper defaults where available. After the helper sequence, call call_entrypoint with "
        "empty arguments so it uses the provided fixture. Then call submit_answer with the exact result from "
        "call_entrypoint. Do not submit a helper result as the final answer."
        f"{skipped_block}"
    )


def build_subfunction_trace_metadata(trace_plan: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute machine-checkable trace metadata from completed rollout steps."""

    required = list(trace_plan.get("required_helper_tools", []))
    observed = [
        step.get("action", {}).get("tool")
        for step in steps
        if isinstance(step.get("action"), dict) and isinstance(step.get("action", {}).get("tool"), str)
    ]
    entrypoint_index = _first_index(observed, CALL_ENTRYPOINT_TOOL)
    helper_search_limit = entrypoint_index if entrypoint_index is not None else len(observed)

    positions: list[int] = []
    missing: list[str] = []
    helper_results: list[dict[str, Any]] = []
    cursor = 0
    for helper_tool in required:
        found = _find_from(observed, helper_tool, cursor, helper_search_limit)
        if found is None:
            missing.append(helper_tool)
            helper_results.append(
                {
                    "tool": helper_tool,
                    "called": False,
                    "success": False,
                    "argument_status": "not_called",
                    "step": None,
                    "error_type": None,
                    "error_message": None,
                }
            )
            continue
        positions.append(found)
        helper_results.append(_helper_call_result(helper_tool, found, steps[found]))
        cursor = found + 1

    helper_trace_complete = not missing
    if required:
        entrypoint_after_helpers = entrypoint_index is not None and helper_trace_complete and all(
            position < entrypoint_index for position in positions
        )
    else:
        entrypoint_after_helpers = entrypoint_index is not None
    helper_calls_successful = all(item["success"] for item in helper_results) if required else True
    helper_trace_valid = helper_trace_complete and entrypoint_after_helpers and helper_calls_successful

    return {
        "trace_mode": trace_plan.get("trace_mode", TRACE_MODE_SUBFUNCTIONS),
        "required_helper_tools": required,
        "observed_tools": observed,
        "helper_trace_complete": helper_trace_complete,
        "helper_calls_successful": helper_calls_successful,
        "helper_trace_valid": helper_trace_valid,
        "helper_call_results": helper_results,
        "failed_helper_tools": [item["tool"] for item in helper_results if not item["success"]],
        "entrypoint_after_helpers": entrypoint_after_helpers,
        "skipped_helpers": list(trace_plan.get("skipped_helpers", [])),
        "missing_helper_tools": missing,
    }


def _helper_call_result(tool_name: str, step_index: int, step: dict[str, Any]) -> dict[str, Any]:
    tool_result = step.get("tool_result")
    success = isinstance(tool_result, dict) and tool_result.get("ok") is True
    error_type = tool_result.get("error_type") if isinstance(tool_result, dict) else None
    error_message = tool_result.get("error_message") if isinstance(tool_result, dict) else None
    argument_provenance = (
        step.get("argument_provenance") if isinstance(step.get("argument_provenance"), dict) else None
    )
    argument_source = (
        argument_provenance.get("source")
        if isinstance(argument_provenance, dict) and isinstance(argument_provenance.get("source"), str)
        else "model_supplied"
    )
    return {
        "tool": tool_name,
        "called": True,
        "success": success,
        "argument_status": _helper_argument_status(step, tool_result, success),
        "argument_source": argument_source,
        "argument_provenance": copy.deepcopy(argument_provenance),
        "step": step.get("step", step_index + 1),
        "error_type": error_type if isinstance(error_type, str) else None,
        "error_message": error_message if isinstance(error_message, str) else None,
    }


def _helper_argument_status(step: dict[str, Any], tool_result: Any, success: bool) -> str:
    if success:
        return "ok"
    action = step.get("action") if isinstance(step.get("action"), dict) else {}
    arguments = action.get("arguments", {}) if isinstance(action, dict) else {}
    error_type = tool_result.get("error_type") if isinstance(tool_result, dict) else None
    error_message = tool_result.get("error_message") if isinstance(tool_result, dict) else ""
    if (
        error_type == "TypeError"
        and isinstance(arguments, dict)
        and not arguments
        and isinstance(error_message, str)
        and "missing" in error_message
        and "argument" in error_message
    ):
        return "argument_unavailable"
    return "call_failed"


def _source_tool_return_metadata(steps: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        action = step.get("action") if isinstance(step.get("action"), dict) else {}
        tool_name = action.get("tool") if isinstance(action, dict) else None
        if not isinstance(tool_name, str) or not _is_source_tool(tool_name):
            continue
        tool_result = step.get("tool_result")
        ok = isinstance(tool_result, dict) and tool_result.get("ok") is True
        item = {
            "tool": tool_name,
            "step": step.get("step", index + 1),
            "ok": ok,
        }
        if isinstance(tool_result, dict) and not ok:
            error_type = tool_result.get("error_type")
            error_message = tool_result.get("error_message")
            item["error_type"] = error_type if isinstance(error_type, str) else None
            item["error_message"] = error_message if isinstance(error_message, str) else None
        results.append(item)
    return {
        "source_tool_return_results": results,
        "all_source_tool_returns_ok": bool(results) and all(item["ok"] for item in results),
    }


def _is_source_tool(tool_name: str) -> bool:
    if tool_name in {CALL_ENTRYPOINT_TOOL, CALL_HELPER_TOOL}:
        return True
    return tool_name.startswith(HELPER_TOOL_PREFIX)


def _semantic_helper_tools(env: Code2Env) -> dict[str, str]:
    helpers: dict[str, str] = {}
    for tool in env.spec.tools:
        if tool.name in {CALL_ENTRYPOINT_TOOL, CALL_HELPER_TOOL, SUBMIT_ANSWER_TOOL}:
            continue
        if not tool.name.startswith(HELPER_TOOL_PREFIX):
            continue
        provenance = tool.provenance or {}
        backing = provenance.get("backing", {}) if isinstance(provenance.get("backing"), dict) else {}
        if provenance.get("kind") != "wrapper" or backing.get("kind") != "function":
            continue
        symbol = backing.get("symbol")
        helper = _helper_name_from_symbol(symbol) if isinstance(symbol, str) else tool.name.removeprefix(HELPER_TOOL_PREFIX)
        helpers[helper] = tool.name
    return helpers


def _entrypoint_step_callees(env: Code2Env) -> list[str]:
    entrypoint = _tool_by_name(env, CALL_ENTRYPOINT_TOOL)
    if entrypoint is None:
        return []
    steps = entrypoint.provenance.get("steps", [])
    if not isinstance(steps, list):
        return []
    callees: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        for callee in step.get("callees", []) or []:
            if isinstance(callee, str):
                callees.append(callee)
    return callees


def _tool_by_name(env: Code2Env, name: str):
    for tool in env.spec.tools:
        if tool.name == name:
            return tool
    return None


def _helper_candidates(env: Code2Env) -> list[str]:
    raw = env.spec.provenance.get("helper_candidates", [])
    return [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []


def _side_effect_helpers(env: Code2Env) -> list[str]:
    entrypoint = _tool_by_name(env, CALL_ENTRYPOINT_TOOL)
    if entrypoint is None:
        return []
    raw = entrypoint.provenance.get("sandboxed_side_effect_helpers", [])
    return [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []


def _helper_name_from_symbol(symbol: str) -> str:
    return symbol.rsplit(":", 1)[-1].split(".")[-1]


def _first_index(items: list[str], needle: str) -> int | None:
    for index, item in enumerate(items):
        if item == needle:
            return index
    return None


def _find_from(items: list[str], needle: str, start: int, stop: int) -> int | None:
    for index in range(start, stop):
        if items[index] == needle:
            return index
    return None


def build_system_prompt(env: Code2Env, tools: list[dict[str, Any]]) -> str:
    tool_lines = []
    for tool in tools:
        schema = json.dumps(tool.get("input_schema", {}), ensure_ascii=False)
        tool_lines.append(f"- {tool['name']}: {tool['description']} | input_schema: {schema}")
    tools_block = "\n".join(tool_lines)
    return (
        "You are an agent solving a task by calling tools in a sandboxed runtime. "
        "On every turn reply with EXACTLY ONE JSON object and nothing else, of the form "
        '{"tool": "<tool_name>", "arguments": {<json arguments>}}. '
        "Do not wrap it in prose or markdown fences. Inspect the task, run the entrypoint "
        "or helper tools to obtain the result, then call submit_answer with the final answer. "
        "Call submit_answer once you are confident.\n\n"
        f"{CALL_ENTRYPOINT_FIXTURE_GUIDANCE}\n\n"
        f"Available tools:\n{tools_block}"
    )


def build_initial_user_message(observation: dict[str, Any], fixture: dict[str, Any] | None = None) -> str:
    task = observation.get("task", {})
    fixture_block = ""
    if fixture is not None:
        fixture_block = (
            "Provided fixture (call_entrypoint already uses this automatically — "
            "do NOT pass these values yourself):\n"
            f"{json.dumps(fixture, ensure_ascii=False, indent=2)}\n\n"
        )
    return (
        "Task:\n"
        f"{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
        f"{fixture_block}"
        "Initial observation:\n"
        f"{json.dumps({k: v for k, v in observation.items() if k != 'task'}, ensure_ascii=False, indent=2)}\n\n"
        'Respond with one JSON tool_call, e.g. {"tool": "inspect_task", "arguments": {}}.'
    )


def parse_action_from_message(message: dict[str, Any]) -> dict[str, Any]:
    """Parse an assistant message into a Code2Env action.

    Supports native OpenAI ``tool_calls`` and JSON-in-content (via parse_llm_json).
    Raises RolloutActionError on malformed output.
    """
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        function = (tool_calls[0] or {}).get("function", {}) or {}
        name = function.get("name")
        raw_args = function.get("arguments", "{}")
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
        except (ValueError, TypeError) as exc:
            raise RolloutActionError(f"could not parse tool_call arguments: {exc}") from exc
        if not name:
            raise RolloutActionError("native tool_call missing function name")
        return _normalize_action(name, arguments)

    content = message.get("content") or ""
    try:
        obj = parse_llm_json(content)
    except ValueError as exc:
        raise RolloutActionError(f"assistant content is not a JSON object: {exc}") from exc

    if obj.get("type") == "tool_call" and isinstance(obj.get("tool"), str):
        return _normalize_action(obj["tool"], obj.get("arguments", {}))
    tool = obj.get("tool") or obj.get("name")
    arguments = obj.get("arguments")
    if arguments is None:
        arguments = obj.get("args", {})
    if not tool:
        raise RolloutActionError("JSON action missing 'tool' field")
    return _normalize_action(str(tool), arguments)


def _normalize_action(tool: str, arguments: Any) -> dict[str, Any]:
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise RolloutActionError("action 'arguments' must be a JSON object")
    return {"type": "tool_call", "tool": str(tool), "arguments": arguments}


def synthesize_trace_helper_arguments(
    env: Code2Env,
    trace_plan: dict[str, Any],
    action: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Fill dedicated trace helper args from the pinned fixture when safe.

    The LLM-visible protocol still asks models to omit helper args unless they
    know what they are doing. In trace mode this adapter can provide deterministic
    args for required helper parameters, and it records provenance so exported
    rollouts can distinguish synthesized values from model-supplied values.
    """

    tool_name = action.get("tool")
    required_tools = list(trace_plan.get("required_helper_tools", []))
    if not isinstance(tool_name, str) or tool_name not in required_tools:
        return action, None

    arguments = action.get("arguments", {})
    if not isinstance(arguments, dict):
        return action, None

    args = arguments.get("args", [])
    kwargs = arguments.get("kwargs", {})
    extra_keys = set(arguments) - {"args", "kwargs"}
    if (isinstance(args, list) and args) or (isinstance(kwargs, dict) and kwargs) or extra_keys:
        return action, _argument_provenance(tool_name, "model_supplied")

    helper_index = required_tools.index(tool_name)
    payload, provenance = _synthesize_helper_payload(env, tool_name, helper_index)
    if payload is None:
        return action, provenance

    rewritten = copy.deepcopy(action)
    rewritten["arguments"] = payload
    return rewritten, provenance


def _synthesize_helper_payload(
    env: Code2Env,
    tool_name: str,
    helper_index: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    symbol = env.semantic_tools.get(tool_name)
    if symbol is None:
        return None, _argument_provenance(
            tool_name,
            "unavailable",
            reason="semantic_helper_symbol_unavailable",
        )
    helper_signature = _function_signature(env, symbol)
    if helper_signature is None:
        return None, _argument_provenance(
            tool_name,
            "unavailable",
            reason=f"helper_signature_unavailable:{symbol}",
        )

    required_positional = list(helper_signature["required_positional"])
    required_kwonly = list(helper_signature["required_kwonly"])
    if not required_positional and not required_kwonly:
        return None, None

    fixture = env.spec.fixture if isinstance(env.spec.fixture, dict) else {}
    fixture_args = fixture.get("args", [])
    fixture_kwargs = fixture.get("kwargs", {})
    fixture_args = fixture_args if isinstance(fixture_args, list) else []
    fixture_kwargs = fixture_kwargs if isinstance(fixture_kwargs, dict) else {}
    entrypoint_signature = _function_signature(env, env.spec.source["entrypoint"])
    entrypoint_positional = (
        list(entrypoint_signature["positional"]) if entrypoint_signature is not None else []
    )

    synthesized_args: list[Any] = []
    arg_records: list[dict[str, Any]] = []
    for param in required_positional:
        found, value, record = _fixture_value_for_param(
            param,
            fixture_args,
            fixture_kwargs,
            entrypoint_positional,
        )
        if not found and len(required_positional) == 1 and not required_kwonly:
            found, value, record = _fixture_value_for_helper_index(
                helper_index,
                fixture_args,
                param,
            )
        if not found:
            return None, _argument_provenance(
                tool_name,
                "unavailable",
                reason=f"fixture_mapping_unavailable:{param}",
            )
        synthesized_args.append(value)
        arg_records.append(record)

    synthesized_kwargs: dict[str, Any] = {}
    kwarg_records: list[dict[str, Any]] = []
    for param in required_kwonly:
        found, value, record = _fixture_value_for_param(
            param,
            fixture_args,
            fixture_kwargs,
            entrypoint_positional,
        )
        if not found:
            return None, _argument_provenance(
                tool_name,
                "unavailable",
                reason=f"fixture_mapping_unavailable:{param}",
            )
        synthesized_kwargs[param] = value
        kwarg_records.append(record)

    provenance = _argument_provenance(
        tool_name,
        "synthesized",
        args=arg_records,
        kwargs=kwarg_records,
    )
    return {"args": synthesized_args, "kwargs": synthesized_kwargs}, provenance


def _argument_provenance(
    tool_name: str,
    source: str,
    *,
    reason: str | None = None,
    args: list[dict[str, Any]] | None = None,
    kwargs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "tool": tool_name,
        "source": source,
        "reason": reason,
        "args": args or [],
        "kwargs": kwargs or [],
    }


def _fixture_value_for_param(
    param: str,
    fixture_args: list[Any],
    fixture_kwargs: dict[str, Any],
    entrypoint_positional: list[str],
) -> tuple[bool, Any, dict[str, Any]]:
    if param in fixture_kwargs:
        return True, fixture_kwargs[param], {
            "param": param,
            "strategy": "fixture_kwarg",
            "fixture_path": f"fixture.kwargs.{param}",
        }
    if param in entrypoint_positional:
        index = entrypoint_positional.index(param)
        if index < len(fixture_args):
            return True, fixture_args[index], {
                "param": param,
                "strategy": "entrypoint_param",
                "fixture_path": f"fixture.args[{index}]",
            }
    return False, None, {}


def _fixture_value_for_helper_index(
    helper_index: int,
    fixture_args: list[Any],
    param: str,
) -> tuple[bool, Any, dict[str, Any]]:
    if len(fixture_args) > 1 and helper_index < len(fixture_args):
        return True, fixture_args[helper_index], {
            "param": param,
            "strategy": "helper_index_arg",
            "fixture_path": f"fixture.args[{helper_index}]",
        }
    if len(fixture_args) != 1:
        return False, None, {}

    found, value, component_path = fixture_component_descriptor(fixture_args[0], helper_index)
    if not found:
        return False, None, {}
    path = _join_fixture_component_path("fixture.args[0]", component_path)
    return True, value, {
        "param": param,
        "strategy": "fixture_sequence_component",
        "fixture_path": path,
    }


def _join_fixture_component_path(base: str, component_path: str | None) -> str:
    if not component_path:
        return base
    if component_path.startswith("["):
        return f"{base}{component_path}"
    return f"{base}.{component_path}"


def _function_signature(env: Code2Env, symbol: str) -> dict[str, list[str]] | None:
    if ":" not in symbol:
        return None
    module_name, qualname = symbol.split(":", 1)
    source_root = source_root_for_spec(env.spec, env.package_root)
    module_path = _module_path(source_root, module_name)
    if module_path is None:
        return None
    try:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None
    node = _find_function_node(tree, qualname)
    if node is None:
        return None

    args = node.args
    positional = [arg.arg for arg in list(args.posonlyargs) + list(args.args)]
    required_positional = (
        positional[: len(positional) - len(args.defaults)] if args.defaults else positional
    )
    required_kwonly = [
        arg.arg for arg, default in zip(args.kwonlyargs, args.kw_defaults) if default is None
    ]
    return {
        "positional": positional,
        "required_positional": required_positional,
        "required_kwonly": required_kwonly,
    }


def _module_path(source_root: Path, module_name: str) -> Path | None:
    relative = Path(*module_name.split("."))
    py_path = source_root / relative.with_suffix(".py")
    if py_path.exists():
        return py_path
    package_init = source_root / relative / "__init__.py"
    if package_init.exists():
        return package_init
    return None


def _find_function_node(
    tree: ast.Module,
    qualname: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    target = qualname.split(".")
    found: ast.FunctionDef | ast.AsyncFunctionDef | None = None

    def visit_body(body: list[ast.stmt], prefix: list[str]) -> None:
        nonlocal found
        if found is not None:
            return
        for child in body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                current = prefix + [child.name]
                if current == target:
                    found = child
                    return
                visit_body(child.body, current)
            elif isinstance(child, ast.ClassDef):
                visit_body(child.body, prefix + [child.name])

    visit_body(tree.body, [])
    return found


class _FallbackChat:
    """Wraps a primary chat model with an optional fallback and per-call retries."""

    def __init__(
        self,
        primary: ChatLLM,
        *,
        fallback: ChatLLM | None = None,
        primary_source: str,
        fallback_source: str | None = None,
        max_retries: int = 1,
    ):
        self.primary = primary
        self.fallback = fallback
        self.primary_source = primary_source
        self.fallback_source = fallback_source
        self.max_retries = max_retries
        self.retries = 0
        self.used_fallback = False
        self.errors: list[str] = []

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                self.retries += 1
            try:
                return self.primary.chat(messages, tools=tools)
            except Exception as exc:  # noqa: BLE001 - transport errors trigger retry/fallback.
                last_exc = exc
                self.errors.append(f"primary({self.primary_source}) attempt {attempt}: {exc}")
        if self.fallback is not None:
            for attempt in range(self.max_retries + 1):
                if attempt > 0:
                    self.retries += 1
                try:
                    message = self.fallback.chat(messages, tools=tools)
                    self.used_fallback = True
                    return message
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    self.errors.append(f"fallback({self.fallback_source}) attempt {attempt}: {exc}")
        raise RuntimeError(f"all chat endpoints failed: {last_exc}")

    def endpoint_source(self) -> str:
        if self.used_fallback and self.fallback_source is not None:
            return f"fallback:{self.fallback_source}"
        return self.primary_source


def run_rollout(
    env: Code2Env,
    llm: ChatLLM,
    *,
    fallback_llm: ChatLLM | None = None,
    primary_source: str | None = None,
    fallback_source: str | None = None,
    max_rounds: int = 8,
    max_parse_retries: int = 2,
    max_llm_retries: int = 1,
    system_prompt: str | None = None,
    trace_mode: str = TRACE_MODE_DEFAULT,
    seed: int | None = 0,
) -> dict[str, Any]:
    """Drive a multi-round tool-calling rollout and return a RolloutResult dict.

    Contract (field names are shared with w3/w4 — do not rename):
    ``{env_id, model, endpoint_source, started_at, finished_at, messages, steps,
    final, num_tool_call_rounds, qualified, termination_reason, retries, errors}``.

    - ``endpoint_source`` is ``"mock"`` for a MockChatLLM primary, the primary
      model name when no fallback fired, or ``"fallback:<model>"`` when it did.
    - ``qualified`` is True iff there were >=2 tool_call rounds and submit_answer ran.
    - ``termination_reason`` is one of ``submitted | step_budget_exhausted | error``.
    """
    if trace_mode not in TRACE_MODES:
        raise ValueError(f"unknown trace_mode: {trace_mode}")
    if primary_source is None:
        primary_source = "mock" if isinstance(llm, MockChatLLM) else getattr(llm, "model_name", "primary")
    if fallback_source is None and fallback_llm is not None:
        fallback_source = getattr(fallback_llm, "model_name", "fallback")

    caller = _FallbackChat(
        llm,
        fallback=fallback_llm,
        primary_source=primary_source,
        fallback_source=fallback_source,
        max_retries=max_llm_retries,
    )

    started_at = _now_iso()
    observation = env.reset(seed=seed)
    tools = build_tool_descriptions(env)
    trace_plan = build_subfunction_trace_plan(env) if trace_mode == TRACE_MODE_SUBFUNCTIONS else None
    if system_prompt is not None:
        system_content = system_prompt
    elif trace_plan is not None:
        system_content = build_subfunction_trace_system_prompt(env, tools, trace_plan)
    else:
        system_content = build_system_prompt(env, tools)
    user_content = build_initial_user_message(observation, env.spec.fixture)

    api_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    transcript: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    steps: list[dict[str, Any]] = []
    errors: list[str] = []
    num_tool_call_rounds = 0
    saw_submit = False
    termination_reason = "step_budget_exhausted"

    parse_retries_total = 0
    rounds = 0
    while not env.done and rounds < max_rounds:
        action, parse_error, parse_retries = _obtain_action(
            caller, api_messages, transcript, tools, max_parse_retries, errors
        )
        parse_retries_total += parse_retries
        if action is None:
            termination_reason = "error"
            break

        argument_provenance: dict[str, Any] | None = None
        if trace_plan is not None:
            action, argument_provenance = synthesize_trace_helper_arguments(env, trace_plan, action)

        observation, reward, done, info = env.step(action)
        rounds += 1
        num_tool_call_rounds += 1
        tool_result = copy.deepcopy(env.state.get("last_tool_result"))
        step_record = {
            "step": env.state.get("step", rounds),
            "action": action,
            "tool_result": tool_result,
            "reward": reward,
            "parse_error": parse_error,
        }
        if argument_provenance is not None:
            step_record["argument_provenance"] = argument_provenance
        steps.append(step_record)
        tool_content = json.dumps(tool_result, ensure_ascii=False, default=str)
        transcript.append({"role": "tool", "name": action["tool"], "content": tool_content})
        api_messages.append(
            {"role": "user", "content": f"TOOL_RESULT[{action['tool']}]:\n{tool_content}"}
        )

        if action["tool"] == "submit_answer":
            saw_submit = True
        if done:
            break

    evaluation = env.evaluate()
    if saw_submit:
        termination_reason = "submitted"
    elif termination_reason != "error":
        termination_reason = "step_budget_exhausted"

    finished_at = _now_iso()
    errors.extend(caller.errors)

    result = {
        "env_id": env.spec.id,
        "model": getattr(llm, "model_name", primary_source),
        "endpoint_source": caller.endpoint_source(),
        "started_at": started_at,
        "finished_at": finished_at,
        "messages": transcript,
        "steps": steps,
        "final": {
            "submitted_answer": evaluation.get("submitted_answer"),
            "correct": evaluation.get("correct"),
            "score": evaluation.get("score"),
            "score_breakdown": evaluation.get("score_breakdown"),
            "steps": evaluation.get("steps"),
        },
        "num_tool_call_rounds": num_tool_call_rounds,
        "qualified": num_tool_call_rounds >= 2 and saw_submit,
        "termination_reason": termination_reason,
        "retries": caller.retries + parse_retries_total,
        "errors": errors,
    }
    if trace_plan is not None:
        trace_metadata = build_subfunction_trace_metadata(trace_plan, steps)
        trace_metadata.update(_source_tool_return_metadata(steps))
        result["subfunction_trace"] = trace_metadata
    return result


def _obtain_action(
    caller: _FallbackChat,
    api_messages: list[dict[str, Any]],
    transcript: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_parse_retries: int,
    errors: list[str],
) -> tuple[dict[str, Any] | None, str | None, int]:
    """Generate and parse one action, retrying on malformed output.

    Returns (action, parse_error, parse_retries). action is None when generation
    fails or output stays malformed after retries; parse_error records the first
    parse failure that was eventually corrected (or the final failure);
    parse_retries is how many corrective re-generations this round consumed.
    """
    # Tools are described in the system prompt (JSON-in-content protocol), so the
    # chat payload must NOT carry an OpenAI native `tools` field — gateways reject a
    # non-function-shaped tools array. ``tools`` is kept for prompt building only.
    first_parse_error: str | None = None
    parse_retries = 0
    for attempt in range(max_parse_retries + 1):
        try:
            message = caller.generate(api_messages, None)
        except Exception as exc:  # noqa: BLE001 - all endpoints failed.
            errors.append(f"generation failed: {exc}")
            return None, first_parse_error, parse_retries

        content = message.get("content") or ""
        try:
            action = parse_action_from_message(message)
        except RolloutActionError as exc:
            if first_parse_error is None:
                first_parse_error = str(exc)
            parse_retries += 1
            transcript.append(
                {"role": "assistant", "content": content, "parse_error": str(exc)}
            )
            api_messages.append({"role": "assistant", "content": content})
            api_messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous response was not a valid tool_call. "
                        'Reply with ONLY a JSON object: {"tool": "<tool_name>", "arguments": {}}. '
                        f"Parse error: {exc}"
                    ),
                }
            )
            continue

        transcript.append(
            {
                "role": "assistant",
                "content": content,
                "tool_call": {"tool": action["tool"], "arguments": action["arguments"]},
            }
        )
        api_messages.append({"role": "assistant", "content": content})
        return action, first_parse_error, parse_retries

    return None, first_parse_error, parse_retries
