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
import json
from typing import Any, Protocol

from code2env.llm import parse_llm_json
from code2env.runtime import Code2Env


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
    system_content = system_prompt or build_system_prompt(env, tools)
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

        observation, reward, done, info = env.step(action)
        rounds += 1
        num_tool_call_rounds += 1
        tool_result = copy.deepcopy(env.state.get("last_tool_result"))
        steps.append(
            {
                "step": env.state.get("step", rounds),
                "action": action,
                "tool_result": tool_result,
                "reward": reward,
                "parse_error": parse_error,
            }
        )
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

    return {
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
