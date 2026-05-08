from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from code2env.executor import run_symbol_subprocess
from code2env.jsonio import read_json
from code2env.models import EnvSpec
from code2env.spec import source_root_for_spec


class Code2Env:
    """Tool-call runtime for generated Code2Env packages."""

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
        self.trajectory: list[dict[str, Any]] = []
        self.state: dict[str, Any] = {}
        self.done = False

    def reset(self, seed: int | None = None, task_id: str | None = None) -> dict[str, Any]:
        self.trajectory = []
        self.done = False
        self.state = {
            "seed": seed,
            "task_id": task_id or self.spec.id,
            "step": 0,
            "phase": "ready",
            "last_tool_result": None,
            "submitted_answer": None,
            "score": 0.0,
        }
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
        reward = 0.0
        info: dict[str, Any] = {"tool": None}

        try:
            tool_name, arguments = self._parse_action(action)
            info["tool"] = tool_name
            result = self._dispatch(tool_name, arguments)
            reward += 0.05
        except Exception as exc:  # noqa: BLE001 - agent errors become environment observations.
            result = {"ok": False, "error_type": type(exc).__name__, "error_message": str(exc)}
            reward -= 0.05

        self.state["last_tool_result"] = result
        if result.get("done"):
            self.done = True
            reward += float(result.get("reward", 0.0))
            self.state["score"] = max(0.0, min(1.0, reward))
        elif self.state["step"] >= self.max_steps:
            self.done = True
            result = {**result, "done": True, "termination_reason": "step_budget_exhausted"}

        event = {
            "step": self.state["step"],
            "action": copy.deepcopy(action),
            "result": copy.deepcopy(result),
            "reward": reward,
            "done": self.done,
        }
        self.trajectory.append(event)
        info["trajectory_length"] = len(self.trajectory)
        return self._observation(), reward, self.done, info

    def evaluate(self) -> dict[str, Any]:
        submitted = self.state.get("submitted_answer")
        correct = submitted == self.spec.golden_answer
        return {
            "score": 1.0 if correct else 0.0,
            "correct": correct,
            "submitted_answer": submitted,
            "golden_answer": self.spec.golden_answer,
            "steps": self.state.get("step", 0),
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
        if tool_name == "call_entrypoint":
            payload = {
                "args": arguments.get("args", self.spec.fixture.get("args", [])),
                "kwargs": arguments.get("kwargs", self.spec.fixture.get("kwargs", {})),
            }
            return self._call_source(self.spec.source["entrypoint"], payload["args"], payload["kwargs"])
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
            correct = answer == self.spec.golden_answer
            return {
                "ok": True,
                "done": True,
                "correct": correct,
                "reward": 1.0 if correct else 0.0,
                "score_breakdown": {
                    "final_correctness": 1.0 if correct else 0.0,
                    "exact_match": correct,
                },
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
        )
