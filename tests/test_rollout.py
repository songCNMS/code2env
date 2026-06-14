from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.jsonio import write_json
from code2env.llm import assistant_message_from_response
from code2env.rollout import (
    MockChatLLM,
    RolloutActionError,
    ScriptedSolveChat,
    parse_action_from_message,
    run_rollout,
)
from code2env.runtime import Code2Env
from code2env.spec import draft_env_spec


SAMPLE = """
def clean_text(value):
    return " ".join(value.strip().split())


def normalize_name(name, shout=False):
    \"\"\"Normalize a human name for display.\"\"\"
    cleaned = clean_text(name)
    if shout:
        return cleaned.upper()
    return cleaned.title()
"""


def _build_env(temp_dir: Path) -> Code2Env:
    repo = temp_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "sample.py").write_text(SAMPLE.lstrip(), encoding="utf-8")
    snapshot = ingest_repo(str(repo))
    spec = draft_env_spec(
        snapshot,
        symbol="sample:normalize_name",
        fixture={"args": ["  ada   lovelace "], "kwargs": {"shout": True}},
    )
    spec_path = temp_dir / "env_spec.json"
    write_json(spec_path, spec.to_dict())
    package_root = build_env_package(spec_path, temp_dir / "generated")
    return Code2Env(package_root / "env_spec.json")


class ParseActionTest(unittest.TestCase):
    def test_parses_plain_tool_arguments(self) -> None:
        action = parse_action_from_message({"content": '{"tool": "inspect_task", "arguments": {}}'})
        self.assertEqual(action, {"type": "tool_call", "tool": "inspect_task", "arguments": {}})

    def test_parses_type_tool_call_and_name_args_aliases(self) -> None:
        a1 = parse_action_from_message({"content": '{"type":"tool_call","tool":"call_entrypoint","arguments":{"args":[]}}'})
        self.assertEqual(a1["tool"], "call_entrypoint")
        a2 = parse_action_from_message({"content": '{"name":"submit_answer","args":{"answer":1}}'})
        self.assertEqual(a2, {"type": "tool_call", "tool": "submit_answer", "arguments": {"answer": 1}})

    def test_parses_fenced_json(self) -> None:
        action = parse_action_from_message({"content": '```json\n{"tool":"inspect_state","arguments":{}}\n```'})
        self.assertEqual(action["tool"], "inspect_state")

    def test_parses_native_tool_calls(self) -> None:
        message = {
            "content": "",
            "tool_calls": [{"function": {"name": "call_entrypoint", "arguments": '{"args": [1]}'}}],
        }
        action = parse_action_from_message(message)
        self.assertEqual(action, {"type": "tool_call", "tool": "call_entrypoint", "arguments": {"args": [1]}})

    def test_malformed_content_raises(self) -> None:
        with self.assertRaises(RolloutActionError):
            parse_action_from_message({"content": "I will call inspect_task now."})
        with self.assertRaises(RolloutActionError):
            parse_action_from_message({"content": '{"arguments": {}}'})  # missing tool

    def test_non_object_arguments_rejected(self) -> None:
        with self.assertRaises(RolloutActionError):
            parse_action_from_message({"content": '{"tool":"x","arguments":[1,2]}'})


class AssistantMessageExtractionTest(unittest.TestCase):
    def test_empty_content_with_tool_calls(self) -> None:
        payload = {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [{"id": "1"}]}}]}
        message = assistant_message_from_response(payload)
        self.assertEqual(message["content"], "")
        self.assertEqual(message["tool_calls"], [{"id": "1"}])

    def test_reads_text_content(self) -> None:
        payload = {"choices": [{"message": {"role": "assistant", "content": "hello"}}]}
        self.assertEqual(assistant_message_from_response(payload)["content"], "hello")


class RolloutLoopTest(unittest.TestCase):
    def test_scripted_solver_is_qualified_and_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            result = run_rollout(env, ScriptedSolveChat(env), primary_source="mock", max_rounds=8)
            self.assertEqual(result["endpoint_source"], "mock")
            self.assertEqual(result["num_tool_call_rounds"], 2)
            self.assertTrue(result["qualified"])
            self.assertEqual(result["termination_reason"], "submitted")
            self.assertTrue(result["final"]["correct"])
            self.assertEqual(result["final"]["score"], 1.0)
            self.assertIn("score_breakdown", result["final"])
            # Steps carry action + tool_result + reward; messages include tool role entries.
            self.assertEqual(len(result["steps"]), 2)
            self.assertEqual(result["steps"][0]["action"]["tool"], "call_entrypoint")
            self.assertTrue(any(m["role"] == "tool" for m in result["messages"]))
            self.assertTrue(any(m.get("tool_call") for m in result["messages"]))

    def test_mock_json_actions_drive_two_rounds_even_when_wrong(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            scripted = [
                {"tool": "call_entrypoint", "arguments": {}},
                {"tool": "submit_answer", "arguments": {"answer": {"wrong": True}}},
            ]
            result = run_rollout(env, MockChatLLM(scripted), max_rounds=8)
            self.assertEqual(result["num_tool_call_rounds"], 2)
            self.assertTrue(result["qualified"])  # >=2 rounds + submit
            self.assertEqual(result["termination_reason"], "submitted")
            self.assertFalse(result["final"]["correct"])

    def test_parse_error_is_corrected_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            scripted = [
                "this is not json",  # round 1 attempt 1 -> parse error, corrected
                {"tool": "call_entrypoint", "arguments": {}},  # round 1 attempt 2
                {"tool": "submit_answer", "arguments": {"answer": {"x": 1}}},  # round 2
            ]
            result = run_rollout(env, MockChatLLM(scripted), max_rounds=8, max_parse_retries=2)
            self.assertEqual(result["num_tool_call_rounds"], 2)
            self.assertIsNotNone(result["steps"][0]["parse_error"])
            self.assertGreaterEqual(result["retries"], 1)
            self.assertTrue(any(m.get("parse_error") for m in result["messages"]))

    def test_driver_max_rounds_stops_without_submit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            scripted = [{"tool": "inspect_state", "arguments": {}} for _ in range(10)]
            result = run_rollout(env, MockChatLLM(scripted), max_rounds=2)
            self.assertEqual(result["num_tool_call_rounds"], 2)
            self.assertFalse(result["qualified"])
            self.assertEqual(result["termination_reason"], "step_budget_exhausted")

    def test_env_step_budget_terminates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            env.max_steps = 3
            scripted = [{"tool": "inspect_state", "arguments": {}} for _ in range(10)]
            result = run_rollout(env, MockChatLLM(scripted), max_rounds=20)
            self.assertEqual(result["termination_reason"], "step_budget_exhausted")
            self.assertEqual(result["num_tool_call_rounds"], 3)

    def test_all_endpoints_failing_terminates_with_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            broken = MockChatLLM([], fail_times=99)
            result = run_rollout(env, broken, max_rounds=4, max_llm_retries=1)
            self.assertEqual(result["termination_reason"], "error")
            self.assertEqual(result["num_tool_call_rounds"], 0)
            self.assertTrue(result["errors"])

    def test_fallback_endpoint_is_used_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            primary = MockChatLLM([], fail_times=99)  # always fails
            fallback = ScriptedSolveChat(env)
            result = run_rollout(
                env,
                primary,
                fallback_llm=fallback,
                primary_source="gpt-5.5",
                fallback_source="mock-solver",
                max_rounds=8,
                max_llm_retries=1,
            )
            self.assertEqual(result["endpoint_source"], "fallback:mock-solver")
            self.assertTrue(result["qualified"])
            self.assertTrue(result["final"]["correct"])
            self.assertGreaterEqual(result["retries"], 2)  # primary retried before fallback


if __name__ == "__main__":
    unittest.main()
