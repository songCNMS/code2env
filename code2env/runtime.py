from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from code2env.executor import run_symbol_subprocess
from code2env.jsonio import read_json
from code2env.models import EnvSpec
from code2env.spec import source_root_for_spec


# Fallback reward weights, mirroring spec.draft_env_spec defaults. Used when a
# spec does not declare reward.weights so older packages keep scoring sensibly.
DEFAULT_REWARD_WEIGHTS: dict[str, float] = {
    "schema_validity": 0.05,
    "process_progress": 0.20,
    "final_correctness": 0.65,
    "efficiency": 0.05,
    "safety": 0.05,
}

# Five reward dimensions, in display order.
REWARD_DIMENSIONS: tuple[str, ...] = (
    "schema_validity",
    "process_progress",
    "final_correctness",
    "efficiency",
    "safety",
)

# Tool-result error signatures that indicate a sandbox enforcement fired
# (the agent / source attempted a forbidden operation).
_SAFETY_ERROR_SIGNATURES: tuple[str, ...] = (
    "network access is disabled",
    "subprocess execution is disabled",
)
_SAFETY_ERROR_TYPES: frozenset[str] = frozenset({"TimeoutExpired"})

# Tools that gather information / execute the pinned source. Reaching them is
# what process_progress measures. Named semantic helper tools (call_<helper>,
# resolved per-spec into self.semantic_tools) also count as executing source.
_EXPLORE_TOOLS: frozenset[str] = frozenset(
    {"inspect_task", "inspect_state", "call_entrypoint", "call_helper"}
)
_EXECUTE_TOOLS: frozenset[str] = frozenset({"call_entrypoint", "call_helper"})


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _accepted_answer_forms(golden: Any) -> list[Any]:
    """The exact submitted shapes that count as correct for a given golden answer.

    The golden answer for a deterministic success is the executor's two-layer
    envelope ``{"ok": True, "value": {"kind": "json", "value": X}}``. We peel
    *exactly those two known layers* (and only when both are present) to recover
    the canonical inner value ``X``, then accept three concrete shapes:

    - ``X`` — the bare inner value,
    - ``{"kind": "json", "value": X}`` — the serialization shell,
    - the full envelope (``== golden``).

    Comparison is exact equality against this fixed set — we never greedily peel
    the *submitted* value. That matters when the target function itself returns a
    wrapper-shaped dict (e.g. ``{"ok": True, "value": 5}`` or
    ``{"kind": "json", "value": 7}``): ``X`` keeps that shape, so an agent that
    submits a bare inner value is correctly judged INCORRECT instead of colliding.

    Any other golden shape — error envelopes (``{"ok": False, ...}``) or non-JSON
    ``{"kind": "repr", ...}`` payloads — requires an exact match against golden.
    """
    if isinstance(golden, dict) and golden.get("ok") is True and "value" in golden:
        shell = golden["value"]
        if isinstance(shell, dict) and shell.get("kind") == "json" and "value" in shell:
            inner = shell["value"]
            return [inner, {"kind": "json", "value": inner}, golden]
    return [golden]


def _answers_equal(submitted: Any, golden: Any) -> bool:
    """True iff the submitted answer exactly matches one accepted shape of golden."""
    return any(submitted == form for form in _accepted_answer_forms(golden))


class Code2Env:
    """Tool-call runtime for generated Code2Env packages.

    Scoring is multi-dimensional (PRD 7.7 / F7): every episode accumulates raw
    signals for schema_validity, process_progress, final_correctness, efficiency
    and safety. ``evaluate`` returns the weighted, explainable ``score_breakdown``
    (the offline *evaluation score*), while ``step`` returns a dense, per-step
    *training reward* (potential-based shaping over the same breakdown). The two
    are intentionally separate: training consumes the step rewards, offline
    analysis consumes the breakdown.
    """

    def __init__(self, spec: EnvSpec | str | Path, *, package_root: str | Path | None = None):
        if isinstance(spec, EnvSpec):
            self.spec = spec
            self.package_root = Path(package_root).resolve() if package_root else None
        else:
            spec_path = Path(spec).resolve()
            self.spec = EnvSpec.from_dict(read_json(spec_path))
            self.package_root = Path(package_root).resolve() if package_root else spec_path.parent
        self.max_steps = int(self.spec.runtime.get("max_steps", 8))
        self.timeout_seconds = float(self.spec.runtime.get("timeout_seconds", 3))
        self.allowed_tools = {tool.name for tool in self.spec.tools}
        self.allowed_helpers = set(self.spec.provenance.get("helper_candidates", []))
        self.weights = self._resolve_weights()
        # Named semantic helper tools (call_<helper>) map to their backing symbol via
        # the ToolSpec provenance written by the extractor.
        self.semantic_tools = {
            tool.name: tool.provenance["backing"]["symbol"]
            for tool in self.spec.tools
            if tool.provenance.get("kind") == "wrapper"
            and tool.provenance.get("backing", {}).get("kind") == "function"
            and isinstance(tool.provenance.get("backing", {}).get("symbol"), str)
        }
        self.trajectory: list[dict[str, Any]] = []
        self.state: dict[str, Any] = {}
        self.done = False
        self._reward_state: dict[str, Any] = {}

    def reset(self, seed: int | None = None, task_id: str | None = None) -> dict[str, Any]:
        self.trajectory = []
        self.done = False
        self._reward_state = {
            "tool_steps": 0,        # number of step() tool-call attempts
            "valid_steps": 0,       # well-formed actions that dispatched without raising
            "schema_errors": 0,     # actions rejected by schema/parse
            "error_calls": 0,       # steps whose tool result was not ok
            "duplicate_calls": 0,   # repeated identical well-formed calls
            "safety_violations": 0, # sandbox enforcements that fired
            "explored": False,      # ran any info-gathering / source tool
            "executed_source": False,  # successfully ran call_entrypoint/call_helper
            "submitted": False,
            "submitted_after_progress": False,
            "budget_exhausted": False,
            "final_correct": False,
            "call_signatures": set(),
        }
        self.state = {
            "seed": seed,
            "task_id": task_id or self.spec.id,
            "step": 0,
            "phase": "ready",
            "last_tool_result": None,
            "submitted_answer": None,
            "score": 0.0,
            "score_breakdown": self._compute_breakdown(),
        }
        self.state["score"] = self.state["score_breakdown"]["total"]
        if self.spec.golden_answer is None:
            self.spec.golden_answer = self._call_source(
                self.spec.source["entrypoint"],
                self.spec.fixture["args"],
                self.spec.fixture["kwargs"],
            )
        return self._observation()

    def step(self, action: dict[str, Any]) -> tuple[dict[str, Any], float, bool, dict[str, Any]]:
        if self.done:
            return self._observation(), 0.0, True, {"error": "episode_already_done"}
        self.state["step"] += 1
        prev_total = self.state["score_breakdown"]["total"]
        rs = self._reward_state
        rs["tool_steps"] += 1
        info: dict[str, Any] = {"tool": None}

        schema_valid = True
        tool_name: str | None = None
        arguments: dict[str, Any] = {}
        try:
            tool_name, arguments = self._parse_action(action)
            info["tool"] = tool_name
            result = self._dispatch(tool_name, arguments)
        except Exception as exc:  # noqa: BLE001 - agent errors become environment observations.
            schema_valid = False
            tool_name = action.get("tool") if isinstance(action, dict) else None
            result = {"ok": False, "error_type": type(exc).__name__, "error_message": str(exc)}

        self._accumulate(schema_valid, tool_name, arguments, result)
        self.state["last_tool_result"] = result

        done_now = False
        if schema_valid and tool_name == "submit_answer" and result.get("done"):
            rs["submitted"] = True
            rs["final_correct"] = bool(result.get("correct"))
            if rs["explored"] or rs["executed_source"]:
                rs["submitted_after_progress"] = True
            done_now = True

        if done_now:
            self.done = True
        elif self.state["step"] >= self.max_steps:
            self.done = True
            rs["budget_exhausted"] = True
            result = {**result, "done": True, "termination_reason": "step_budget_exhausted"}

        breakdown = self._compute_breakdown()
        self.state["score_breakdown"] = breakdown
        self.state["score"] = breakdown["total"]
        # Dense training reward: potential-based shaping over the weighted total,
        # so the sum of per-step rewards telescopes to the final evaluation score.
        reward = breakdown["total"] - prev_total

        event = {
            "step": self.state["step"],
            "action": copy.deepcopy(action),
            "result": copy.deepcopy(result),
            "reward": reward,
            "done": self.done,
        }
        self.trajectory.append(event)
        info["trajectory_length"] = len(self.trajectory)
        info["score_breakdown"] = breakdown
        return self._observation(), reward, self.done, info

    def evaluate(self) -> dict[str, Any]:
        submitted = self.state.get("submitted_answer")
        correct = _answers_equal(submitted, self.spec.golden_answer)
        breakdown = self._compute_breakdown()
        return {
            "score": breakdown["total"],
            "correct": correct,
            "final_correctness": breakdown["dimensions"]["final_correctness"]["raw"],
            "submitted_answer": submitted,
            "golden_answer": self.spec.golden_answer,
            "steps": self.state.get("step", 0),
            "score_breakdown": breakdown,
            "trajectory": copy.deepcopy(self.trajectory),
        }

    def close(self) -> None:
        self.done = True

    def scripted_smoke(self) -> dict[str, Any]:
        self.reset(seed=0)
        _, reward_call, _, _ = self.step(
            {
                "type": "tool_call",
                "tool": "call_entrypoint",
                "arguments": self.spec.fixture,
            }
        )
        answer = self.state["last_tool_result"]
        _, reward_submit, done, _ = self.step(
            {
                "type": "tool_call",
                "tool": "submit_answer",
                "arguments": {"answer": answer},
            }
        )
        return {
            "ok": done and self.evaluate()["correct"],
            "reward": reward_call + reward_submit,
            "evaluation": self.evaluate(),
        }

    # ------------------------------------------------------------------
    # Reward computation
    # ------------------------------------------------------------------
    def _resolve_weights(self) -> dict[str, float]:
        weights = dict(DEFAULT_REWARD_WEIGHTS)
        reward = self.spec.reward if isinstance(self.spec.reward, dict) else {}
        declared = reward.get("weights")
        if isinstance(declared, dict):
            for dim in REWARD_DIMENSIONS:
                value = declared.get(dim)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    weights[dim] = float(value)
        return weights

    def _accumulate(
        self,
        schema_valid: bool,
        tool_name: str | None,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        rs = self._reward_state
        if schema_valid:
            rs["valid_steps"] += 1
        else:
            rs["schema_errors"] += 1

        if not result.get("ok"):
            rs["error_calls"] += 1
        if self._is_safety_violation(result):
            rs["safety_violations"] += 1

        if schema_valid and tool_name is not None:
            signature = self._action_signature(tool_name, arguments)
            if signature in rs["call_signatures"]:
                rs["duplicate_calls"] += 1
            else:
                rs["call_signatures"].add(signature)

        if schema_valid and result.get("ok"):
            is_semantic_helper = tool_name in self.semantic_tools
            if tool_name in _EXPLORE_TOOLS or is_semantic_helper:
                rs["explored"] = True
            if tool_name in _EXECUTE_TOOLS or is_semantic_helper:
                rs["executed_source"] = True

    @staticmethod
    def _action_signature(tool_name: str, arguments: dict[str, Any]) -> str:
        try:
            args_repr = json.dumps(arguments, sort_keys=True, default=repr)
        except (TypeError, ValueError):
            args_repr = repr(arguments)
        return f"{tool_name}:{args_repr}"

    @staticmethod
    def _is_safety_violation(result: dict[str, Any]) -> bool:
        if result.get("ok"):
            return False
        if result.get("error_type") in _SAFETY_ERROR_TYPES:
            return True
        message = str(result.get("error_message", ""))
        return any(signature in message for signature in _SAFETY_ERROR_SIGNATURES)

    def _compute_breakdown(self) -> dict[str, Any]:
        rs = self._reward_state or {}
        tool_steps = int(rs.get("tool_steps", 0))
        max_steps = max(1, self.max_steps)

        # schema_validity: fraction of actions that were well-formed and parseable.
        valid_steps = int(rs.get("valid_steps", 0))
        if tool_steps == 0:
            schema_raw = 1.0
            schema_detail = "no actions taken yet"
        else:
            schema_raw = valid_steps / tool_steps
            schema_detail = f"{valid_steps}/{tool_steps} actions well-formed"

        # process_progress: staged invariants (explore -> execute source -> submit after progress).
        milestones = [
            bool(rs.get("explored")),
            bool(rs.get("executed_source")),
            bool(rs.get("submitted_after_progress")),
        ]
        reached = sum(1 for hit in milestones if hit)
        process_raw = reached / len(milestones)
        process_detail = (
            f"{reached}/{len(milestones)} milestones "
            f"(explore={milestones[0]}, execute_source={milestones[1]}, submit_after_progress={milestones[2]})"
        )

        # final_correctness: exact-match against the pinned golden answer.
        final_raw = 1.0 if rs.get("final_correct") else 0.0
        final_detail = "submitted answer matches golden" if final_raw else "no correct submission"

        # efficiency: penalize invalid/error calls, repeats and exhausting the budget without submitting.
        error_calls = int(rs.get("error_calls", 0))
        duplicate_calls = int(rs.get("duplicate_calls", 0))
        waste = error_calls + duplicate_calls
        penalty = waste / max_steps
        if rs.get("budget_exhausted") and not rs.get("submitted"):
            penalty += 0.5
        efficiency_raw = _clamp_unit(1.0 - penalty)
        efficiency_detail = (
            f"{error_calls} error + {duplicate_calls} duplicate call(s)"
            + (" + budget exhausted w/o submit" if rs.get("budget_exhausted") and not rs.get("submitted") else "")
        )

        # safety: sandbox enforcements (network/subprocess/timeout) tank the dimension.
        violations = int(rs.get("safety_violations", 0))
        safety_raw = _clamp_unit(1.0 - violations)
        safety_detail = "no sandbox violations" if violations == 0 else f"{violations} sandbox violation(s)"

        raws = {
            "schema_validity": (schema_raw, schema_detail),
            "process_progress": (process_raw, process_detail),
            "final_correctness": (final_raw, final_detail),
            "efficiency": (efficiency_raw, efficiency_detail),
            "safety": (safety_raw, safety_detail),
        }

        dimensions: dict[str, Any] = {}
        total = 0.0
        for dim in REWARD_DIMENSIONS:
            raw, detail = raws[dim]
            weight = float(self.weights.get(dim, 0.0))
            weighted = raw * weight
            total += weighted
            dimensions[dim] = {
                "raw": round(raw, 6),
                "weight": weight,
                "weighted": round(weighted, 6),
                "detail": detail,
            }

        return {
            "dimensions": dimensions,
            "total": round(_clamp_unit(total), 6),
            # Flat aliases kept for backward compatibility with earlier consumers.
            "final_correctness": dimensions["final_correctness"]["raw"],
            "exact_match": bool(rs.get("final_correct")),
        }

    # ------------------------------------------------------------------
    # Observation / dispatch
    # ------------------------------------------------------------------
    def _observation(self) -> dict[str, Any]:
        return {
            "task": self.spec.task,
            "state": copy.deepcopy(self.state),
            "available_tools": sorted(self.allowed_tools),
            "budget": {"remaining_steps": max(0, self.max_steps - int(self.state.get("step", 0)))},
        }

    def _parse_action(self, action: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if action.get("type") != "tool_call":
            raise ValueError("action.type must be 'tool_call'")
        tool_name = action.get("tool")
        if tool_name not in self.allowed_tools:
            raise ValueError(f"unknown tool: {tool_name}")
        arguments = action.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("action.arguments must be an object")
        return str(tool_name), arguments

    def _dispatch(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "inspect_task":
            return {
                "ok": True,
                "task": self.spec.task,
                "fixture": self.spec.fixture,
                "source": self.spec.source,
                "helpers": sorted(self.allowed_helpers),
                "golden_answer_available": self.spec.golden_answer is not None,
            }
        if tool_name == "inspect_state":
            return {
                "ok": True,
                "state": copy.deepcopy(self.state),
                "available_tools": sorted(self.allowed_tools),
                "helpers": sorted(self.allowed_helpers),
                "budget": {"remaining_steps": max(0, self.max_steps - int(self.state.get("step", 0)))},
            }
        if tool_name == "call_entrypoint":
            payload = {
                "args": arguments.get("args", self.spec.fixture.get("args", [])),
                "kwargs": arguments.get("kwargs", self.spec.fixture.get("kwargs", {})),
            }
            return self._call_source(self.spec.source["entrypoint"], payload["args"], payload["kwargs"])
        if tool_name in self.semantic_tools:
            return self._call_source(
                self.semantic_tools[tool_name],
                list(arguments.get("args", [])),
                dict(arguments.get("kwargs", {})),
            )
        if tool_name == "call_helper":
            helper = arguments.get("helper")
            if helper not in self.allowed_helpers:
                raise ValueError(f"helper is not allowed: {helper}")
            module = self.spec.source["entrypoint"].split(":", 1)[0]
            return self._call_source(
                f"{module}:{helper}",
                list(arguments.get("args", [])),
                dict(arguments.get("kwargs", {})),
            )
        if tool_name == "submit_answer":
            answer = arguments.get("answer")
            self.state["submitted_answer"] = copy.deepcopy(answer)
            correct = _answers_equal(answer, self.spec.golden_answer)
            return {
                "ok": True,
                "done": True,
                "correct": correct,
                "final_correctness": 1.0 if correct else 0.0,
                "exact_match": correct,
            }
        raise ValueError(f"unimplemented tool: {tool_name}")

    def _call_source(self, symbol: str, args: list[Any], kwargs: dict[str, Any]) -> dict[str, Any]:
        source_root = source_root_for_spec(self.spec, self.package_root)
        sandbox = self.spec.runtime.get("sandbox", {})
        return run_symbol_subprocess(
            source_root,
            symbol,
            args,
            kwargs,
            timeout_seconds=self.timeout_seconds,
            disable_network=sandbox.get("network") is False,
            disable_subprocess=sandbox.get("subprocess") in {False, "disabled"},
            python_executable=self._python_executable,
        )

    @property
    def _python_executable(self) -> str | None:
        """Repo venv interpreter from the spec (task030), if it still exists.

        Falls back to the default interpreter when the recorded venv path is absent
        (e.g. the package was moved to another machine), so rollouts never hard-fail
        on a missing cache directory.
        """

        python = self.spec.runtime.get("python_executable")
        if python and Path(python).exists():
            return str(python)
        return None
