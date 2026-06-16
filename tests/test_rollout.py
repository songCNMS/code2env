from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.jsonio import write_json
from code2env.llm import assistant_message_from_response
from code2env.rich_fixtures import DESCRIPTOR_KEY, numpy_array_descriptor
from code2env.rollout import (
    CALL_ENTRYPOINT_FIXTURE_GUIDANCE,
    MockChatLLM,
    RolloutActionError,
    ScriptedSolveChat,
    ScriptedTraceSolveChat,
    build_initial_user_message,
    build_subfunction_trace_metadata,
    build_subfunction_trace_plan,
    build_subfunction_trace_system_prompt,
    build_system_prompt,
    build_tool_descriptions,
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


TRACE_SAMPLE = """
def split_words(text=None):
    return (text or "ada lovelace").split()


def join_words(text=None):
    return "-".join(split_words(text))


def format_bundle(text=None):
    words = split_words(text)
    slug = join_words(text)
    return {"words": words, "slug": slug}
"""


TYPED_TRACE_SAMPLE = """
def rotation_x(theta):
    return {"axis": "x", "value": round(float(theta) + 1.0, 6)}


def rotation_y(theta):
    return {"axis": "y", "value": round(float(theta) + 2.0, 6)}


def rotation_z(theta):
    return {"axis": "z", "value": round(float(theta) + 3.0, 6)}


def rotation(angles):
    x = rotation_x(angles[0])
    y = rotation_y(angles[1])
    z = rotation_z(angles[2])
    return {
        "axes": [x["axis"], y["axis"], z["axis"]],
        "total": round(x["value"] + y["value"] + z["value"], 6),
}
"""


UNMAPPABLE_TRACE_SAMPLE = """
def helper_needs_payload(payload):
    return payload["name"].upper()


def format_unmappable(name):
    return {"display": helper_needs_payload({"name": name})}
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


def _build_trace_env(temp_dir: Path) -> Code2Env:
    repo = temp_dir / "trace_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "trace_sample.py").write_text(TRACE_SAMPLE.lstrip(), encoding="utf-8")
    snapshot = ingest_repo(str(repo))
    spec = draft_env_spec(
        snapshot,
        symbol="trace_sample:format_bundle",
        fixture={"args": ["ada lovelace"], "kwargs": {}},
    )
    spec_path = temp_dir / "trace_env_spec.json"
    write_json(spec_path, spec.to_dict())
    package_root = build_env_package(spec_path, temp_dir / "trace_generated")
    return Code2Env(package_root / "env_spec.json")


def _build_typed_trace_env(temp_dir: Path) -> Code2Env:
    repo = temp_dir / "typed_trace_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "typed_trace_sample.py").write_text(TYPED_TRACE_SAMPLE.lstrip(), encoding="utf-8")
    snapshot = ingest_repo(str(repo))
    spec = draft_env_spec(
        snapshot,
        symbol="typed_trace_sample:rotation",
        fixture={
            "args": [numpy_array_descriptor([0.1, 0.2, 0.3], dtype="float64")],
            "kwargs": {},
        },
    )
    spec_path = temp_dir / "typed_trace_env_spec.json"
    write_json(spec_path, spec.to_dict())
    package_root = build_env_package(spec_path, temp_dir / "typed_trace_generated")
    return Code2Env(package_root / "env_spec.json")


def _build_unmappable_trace_env(temp_dir: Path) -> Code2Env:
    repo = temp_dir / "unmappable_trace_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "unmappable_trace_sample.py").write_text(
        UNMAPPABLE_TRACE_SAMPLE.lstrip(),
        encoding="utf-8",
    )
    snapshot = ingest_repo(str(repo))
    spec = draft_env_spec(
        snapshot,
        symbol="unmappable_trace_sample:format_unmappable",
        fixture={"args": ["ada"], "kwargs": {}},
    )
    spec_path = temp_dir / "unmappable_trace_env_spec.json"
    write_json(spec_path, spec.to_dict())
    package_root = build_env_package(spec_path, temp_dir / "unmappable_trace_generated")
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


class SubfunctionTraceModeTest(unittest.TestCase):
    def test_extracts_helper_sequence_from_entrypoint_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_trace_env(Path(temp))
            plan = build_subfunction_trace_plan(env)
            # Tool declaration order is alphabetical for equal helper step counts;
            # trace mode must recover the entrypoint's actual callee order.
            self.assertEqual(plan["required_helper_tools"], ["call_split_words", "call_join_words"])
            self.assertEqual(plan["skipped_helpers"], [])

    def test_trace_prompt_requires_helpers_before_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_trace_env(Path(temp))
            plan = build_subfunction_trace_plan(env)
            prompt = build_subfunction_trace_system_prompt(env, build_tool_descriptions(env), plan)

            self.assertIn("SUBFUNCTION TRACE MODE", prompt)
            self.assertIn("Do not call call_entrypoint first", prompt)
            self.assertLess(prompt.index("1. call_split_words"), prompt.index("2. call_join_words"))
            self.assertIn("Then call submit_answer", prompt)

    def test_trace_metadata_detects_complete_and_incomplete_sequences(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_trace_env(Path(temp))
            plan = build_subfunction_trace_plan(env)
            complete = build_subfunction_trace_metadata(
                plan,
                [
                    {"step": 1, "action": {"tool": "call_split_words", "arguments": {}}, "tool_result": {"ok": True}},
                    {"step": 2, "action": {"tool": "call_join_words", "arguments": {}}, "tool_result": {"ok": True}},
                    {"action": {"tool": "call_entrypoint"}},
                    {"action": {"tool": "submit_answer"}},
                ],
            )
            self.assertTrue(complete["helper_trace_complete"])
            self.assertTrue(complete["helper_calls_successful"])
            self.assertTrue(complete["helper_trace_valid"])
            self.assertTrue(complete["entrypoint_after_helpers"])
            self.assertEqual(complete["observed_tools"], ["call_split_words", "call_join_words", "call_entrypoint", "submit_answer"])
            self.assertEqual(
                [item["argument_status"] for item in complete["helper_call_results"]],
                ["ok", "ok"],
            )

            incomplete = build_subfunction_trace_metadata(
                plan,
                [
                    {"action": {"tool": "call_entrypoint"}},
                    {"action": {"tool": "call_split_words"}},
                    {"action": {"tool": "submit_answer"}},
                ],
            )
            self.assertFalse(incomplete["helper_trace_complete"])
            self.assertFalse(incomplete["helper_calls_successful"])
            self.assertFalse(incomplete["helper_trace_valid"])
            self.assertFalse(incomplete["entrypoint_after_helpers"])
            self.assertEqual(incomplete["missing_helper_tools"], ["call_split_words", "call_join_words"])
            self.assertEqual(incomplete["helper_call_results"][0]["argument_status"], "not_called")

    def test_trace_metadata_exposes_failed_helper_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_trace_env(Path(temp))
            plan = build_subfunction_trace_plan(env)
            trace = build_subfunction_trace_metadata(
                plan,
                [
                    {
                        "step": 1,
                        "action": {"tool": "call_split_words", "arguments": {}},
                        "tool_result": {
                            "ok": False,
                            "error_type": "TypeError",
                            "error_message": "split_words() missing 1 required positional argument: 'text'",
                        },
                    },
                    {
                        "step": 2,
                        "action": {"tool": "call_join_words", "arguments": {}},
                        "tool_result": {"ok": True},
                    },
                    {"step": 3, "action": {"tool": "call_entrypoint", "arguments": {}}, "tool_result": {"ok": True}},
                ],
            )

            self.assertTrue(trace["helper_trace_complete"])
            self.assertTrue(trace["entrypoint_after_helpers"])
            self.assertFalse(trace["helper_calls_successful"])
            self.assertFalse(trace["helper_trace_valid"])
            self.assertEqual(trace["failed_helper_tools"], ["call_split_words"])
            first = trace["helper_call_results"][0]
            self.assertEqual(first["tool"], "call_split_words")
            self.assertFalse(first["success"])
            self.assertEqual(first["argument_status"], "argument_unavailable")
            self.assertEqual(first["error_type"], "TypeError")

    def test_trace_mock_rollout_calls_helpers_then_entrypoint_then_submit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_trace_env(Path(temp))
            result = run_rollout(
                env,
                ScriptedTraceSolveChat(env),
                primary_source="mock",
                max_rounds=8,
                trace_mode="subfunctions",
            )

            trace = result["subfunction_trace"]
            self.assertEqual(
                [step["action"]["tool"] for step in result["steps"]],
                ["call_split_words", "call_join_words", "call_entrypoint", "submit_answer"],
            )
            self.assertEqual(trace["required_helper_tools"], ["call_split_words", "call_join_words"])
            self.assertTrue(trace["helper_trace_complete"])
            self.assertTrue(trace["helper_calls_successful"])
            self.assertTrue(trace["helper_trace_valid"])
            self.assertTrue(trace["entrypoint_after_helpers"])
            self.assertTrue(result["qualified"])
            self.assertTrue(result["final"]["correct"])

    def test_trace_plan_skips_unmappable_helper_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_unmappable_trace_env(Path(temp))
            plan = build_subfunction_trace_plan(env)

            self.assertEqual(plan["required_helper_tools"], [])
            self.assertEqual(
                plan["skipped_helpers"],
                [
                    {
                        "helper": "helper_needs_payload",
                        "tool": "call_helper_needs_payload",
                        "reason": "argument_unavailable:payload",
                    }
                ],
            )
            self.assertEqual(plan["dedicated_semantic_helper_count"], 1)
            self.assertEqual(plan["executable_required_helper_count"], 0)
            self.assertEqual(
                plan["skipped_helper_count_by_reason"],
                {"argument_unavailable": 1},
            )

            result = run_rollout(
                env,
                ScriptedTraceSolveChat(env),
                primary_source="mock",
                max_rounds=8,
                trace_mode="subfunctions",
            )
            self.assertEqual(
                [step["action"]["tool"] for step in result["steps"]],
                ["call_entrypoint", "submit_answer"],
            )
            trace = result["subfunction_trace"]
            self.assertTrue(trace["helper_trace_complete"])
            self.assertTrue(trace["helper_calls_successful"])
            self.assertTrue(trace["helper_trace_valid"])
            self.assertEqual(trace["executable_required_helper_count"], 0)
            self.assertEqual(
                trace["skipped_helper_count_by_reason"],
                {"argument_unavailable": 1},
            )

    def test_trace_rollout_synthesizes_typed_fixture_helper_args(self) -> None:
        if importlib.util.find_spec("numpy") is None:
            self.skipTest("numpy is not installed")
        with tempfile.TemporaryDirectory() as temp:
            env = _build_typed_trace_env(Path(temp))
            result = run_rollout(
                env,
                ScriptedTraceSolveChat(env),
                primary_source="mock",
                max_rounds=8,
                trace_mode="subfunctions",
            )

            helper_steps = result["steps"][:3]
            self.assertEqual(
                [step["action"]["tool"] for step in helper_steps],
                ["call_rotation_x", "call_rotation_y", "call_rotation_z"],
            )
            for index, step in enumerate(helper_steps):
                provenance = step["argument_provenance"]
                self.assertEqual(provenance["source"], "synthesized")
                self.assertEqual(provenance["args"][0]["strategy"], "fixture_sequence_component")
                self.assertEqual(provenance["args"][0]["fixture_path"], f"fixture.args[0].data[{index}]")
                arg = step["action"]["arguments"]["args"][0]
                self.assertEqual(arg[DESCRIPTOR_KEY], "numpy.ndarray")
                self.assertTrue(step["tool_result"]["ok"])

            trace = result["subfunction_trace"]
            self.assertTrue(trace["helper_trace_complete"])
            self.assertTrue(trace["helper_calls_successful"])
            self.assertTrue(trace["helper_trace_valid"])
            self.assertTrue(trace["all_source_tool_returns_ok"])
            self.assertTrue(result["qualified"])
            self.assertTrue(result["final"]["correct"])
            self.assertEqual(
                [item["argument_source"] for item in trace["helper_call_results"]],
                ["synthesized", "synthesized", "synthesized"],
            )

    def test_default_rollout_does_not_synthesize_typed_helper_args(self) -> None:
        if importlib.util.find_spec("numpy") is None:
            self.skipTest("numpy is not installed")
        with tempfile.TemporaryDirectory() as temp:
            env = _build_typed_trace_env(Path(temp))
            result = run_rollout(env, ScriptedSolveChat(env), primary_source="mock", max_rounds=8)

            self.assertNotIn("subfunction_trace", result)
            self.assertEqual(
                [step["action"]["tool"] for step in result["steps"]],
                ["call_entrypoint", "submit_answer"],
            )
            self.assertNotIn("argument_provenance", result["steps"][0])

    def test_default_mode_remains_black_box_without_trace_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_trace_env(Path(temp))
            result = run_rollout(env, ScriptedSolveChat(env), primary_source="mock", max_rounds=8)
            self.assertNotIn("subfunction_trace", result)
            self.assertEqual([step["action"]["tool"] for step in result["steps"]], ["call_entrypoint", "submit_answer"])
            self.assertNotIn("SUBFUNCTION TRACE MODE", result["messages"][0]["content"])


class PromptFixtureGuidanceTest(unittest.TestCase):
    def test_system_prompt_contains_fixture_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            prompt = build_system_prompt(env, build_tool_descriptions(env))
            self.assertIn(CALL_ENTRYPOINT_FIXTURE_GUIDANCE, prompt)
            # Key instruction phrases the agent must see.
            self.assertIn("do NOT invent", prompt)
            self.assertIn("empty arguments", prompt)

    def test_user_message_echoes_fixture(self) -> None:
        observation = {"task": {"title": "t"}, "budget": {"remaining_steps": 8}}
        fixture = {"args": ["  ada   lovelace "], "kwargs": {"shout": True}}
        message = build_initial_user_message(observation, fixture)
        self.assertIn("Provided fixture", message)
        self.assertIn("ada   lovelace", message)
        self.assertIn("do NOT pass these values yourself", message)
        # Without a fixture the block is omitted.
        self.assertNotIn("Provided fixture", build_initial_user_message(observation))

    def test_empty_args_call_entrypoint_uses_fixture_and_stays_qualified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            # ScriptedSolveChat calls call_entrypoint with empty arguments {}.
            result = run_rollout(env, ScriptedSolveChat(env), primary_source="mock", max_rounds=8)
            self.assertEqual(result["steps"][0]["action"]["tool"], "call_entrypoint")
            self.assertEqual(result["steps"][0]["action"]["arguments"], {})
            self.assertTrue(result["steps"][0]["tool_result"]["ok"])  # fixture fallback ran
            self.assertTrue(result["qualified"])
            self.assertTrue(result["final"]["correct"])
            # The fed system/user prompts carry the guidance + fixture echo.
            self.assertIn(CALL_ENTRYPOINT_FIXTURE_GUIDANCE, result["messages"][0]["content"])
            self.assertIn("Provided fixture", result["messages"][1]["content"])

    def test_fabricated_args_mismatch_is_the_failure_mode_being_prevented(self) -> None:
        # Documents root cause B: supplying own args runs fine but mismatches golden.
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            llm = MockChatLLM([
                {"tool": "call_entrypoint", "arguments": {"args": ["someone else"], "kwargs": {}}},
                {"tool": "submit_answer", "arguments": {"answer": {"ok": True, "value": {"kind": "json", "value": "Someone Else"}}}},
            ])
            result = run_rollout(env, llm, max_rounds=8)
            self.assertTrue(result["qualified"])
            self.assertFalse(result["final"]["correct"])  # mismatched golden -> false negative


if __name__ == "__main__":
    unittest.main()
