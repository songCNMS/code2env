from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from code2env.rollout_export import (
    ConversationSchemaError,
    MERGED_JSONL_NAME,
    compute_qualified,
    has_submit_answer,
    iter_jsonl,
    load_conversation,
    validate_conversation,
    write_conversation,
)


def _sample_conversation(env_id: str = "code2env.sample.deadbeef.v1") -> dict:
    """A minimal but contract-complete qualified RolloutResult."""

    return {
        "env_id": env_id,
        "model": "kimi",
        "endpoint_source": "endpoints.txt",
        "started_at": "2026-06-14T00:00:00Z",
        "finished_at": "2026-06-14T00:00:03Z",
        "messages": [
            {"role": "system", "content": "You are solving a code2env task."},
            {"role": "user", "content": "Run the entrypoint and submit the answer."},
            {
                "role": "assistant",
                "content": "",
                "tool_call": {"tool": "call_entrypoint", "arguments": {"args": ["ada"], "kwargs": {}}},
            },
            {"role": "tool", "name": "call_entrypoint", "content": "{\"ok\": true, \"value\": \"Ada\"}"},
            {
                "role": "assistant",
                "content": "",
                "tool_call": {"tool": "submit_answer", "arguments": {"answer": {"value": "Ada"}}},
            },
            {"role": "tool", "name": "submit_answer", "content": "{\"ok\": true}"},
        ],
        "steps": [
            {
                "step": 1,
                "action": {"type": "tool_call", "tool": "call_entrypoint", "arguments": {"args": ["ada"], "kwargs": {}}},
                "tool_result": {"ok": True, "value": "Ada"},
                "reward": 0.2,
                "parse_error": None,
            },
            {
                "step": 2,
                "action": {"type": "tool_call", "tool": "submit_answer", "arguments": {"answer": {"value": "Ada"}}},
                "tool_result": {"ok": True},
                "reward": 0.8,
                "parse_error": None,
            },
        ],
        "final": {
            "submitted_answer": {"value": "Ada"},
            "correct": True,
            "score": 1.0,
            "score_breakdown": {"total": 1.0, "dimensions": {}},
            "steps": 2,
        },
        "num_tool_call_rounds": 2,
        "qualified": True,
        "termination_reason": "submitted",
        "retries": 0,
        "errors": [],
    }


class ValidateConversationTest(unittest.TestCase):
    def test_valid_sample_passes(self) -> None:
        obj = _sample_conversation()
        self.assertIs(validate_conversation(obj), obj)
        self.assertTrue(has_submit_answer(obj))
        self.assertTrue(compute_qualified(obj))

    def test_missing_field_raises(self) -> None:
        obj = _sample_conversation()
        del obj["final"]
        with self.assertRaises(ConversationSchemaError):
            validate_conversation(obj)

    def test_wrong_type_raises(self) -> None:
        obj = _sample_conversation()
        obj["num_tool_call_rounds"] = "2"
        with self.assertRaises(ConversationSchemaError):
            validate_conversation(obj)

    def test_bad_role_raises(self) -> None:
        obj = _sample_conversation()
        obj["messages"][0]["role"] = "narrator"
        with self.assertRaises(ConversationSchemaError):
            validate_conversation(obj)

    def test_qualified_inconsistent_raises(self) -> None:
        # qualified=True but only one round and no submit -> contract violation.
        obj = _sample_conversation()
        obj["num_tool_call_rounds"] = 1
        obj["messages"] = obj["messages"][:2]
        obj["steps"] = obj["steps"][:1]
        obj["qualified"] = True
        with self.assertRaises(ConversationSchemaError):
            validate_conversation(obj)

    def test_unqualified_sample_is_consistent(self) -> None:
        obj = _sample_conversation()
        obj["num_tool_call_rounds"] = 1
        obj["messages"] = [m for m in obj["messages"] if (m.get("tool_call") or {}).get("tool") != "submit_answer"]
        obj["steps"] = [s for s in obj["steps"] if s["action"].get("tool") != "submit_answer"]
        obj["final"]["correct"] = False
        obj["final"]["score"] = 0.2
        obj["termination_reason"] = "max_steps"
        obj["qualified"] = False
        self.assertFalse(has_submit_answer(obj))
        self.assertIs(validate_conversation(obj), obj)


class WriteAndLoadTest(unittest.TestCase):
    def test_write_creates_per_env_json_and_merged_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "rollouts"  # not pre-created -> must auto-mkdir
            obj = _sample_conversation()
            path = write_conversation(obj, out_dir)

            self.assertTrue(path.exists())
            self.assertEqual(path.name, "code2env.sample.deadbeef.v1.json")
            self.assertEqual(load_conversation(path), obj)

            merged = out_dir / MERGED_JSONL_NAME
            self.assertTrue(merged.exists())
            records = list(iter_jsonl(merged))
            self.assertEqual(records, [obj])

    def test_round_trip_equivalence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            obj = _sample_conversation()
            original = copy.deepcopy(obj)
            path = write_conversation(obj, temp_dir)
            self.assertEqual(load_conversation(path), original)

    def test_merged_jsonl_appends_multiple_envs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = _sample_conversation("env.one.v1")
            second = _sample_conversation("env.two.v1")
            write_conversation(first, temp_dir)
            write_conversation(second, temp_dir)

            merged = Path(temp_dir) / MERGED_JSONL_NAME
            env_ids = [record["env_id"] for record in iter_jsonl(merged)]
            self.assertEqual(env_ids, ["env.one.v1", "env.two.v1"])
            # Each per-env file is independently loadable.
            self.assertTrue((Path(temp_dir) / "env.one.v1.json").exists())
            self.assertTrue((Path(temp_dir) / "env.two.v1.json").exists())

    def test_write_rejects_bad_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bad = _sample_conversation()
            bad["final"]["correct"] = "yes"  # wrong type
            with self.assertRaises(ConversationSchemaError):
                write_conversation(bad, temp_dir)
            # Nothing should have been written.
            self.assertEqual(list(Path(temp_dir).iterdir()), [])

    def test_env_id_is_sanitised_for_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            obj = _sample_conversation("pkg/mod:func v1")
            path = write_conversation(obj, temp_dir)
            self.assertEqual(path.name, "pkg_mod_func_v1.json")
            # Content keeps the original env_id untouched.
            self.assertEqual(load_conversation(path)["env_id"], "pkg/mod:func v1")

    def test_atomic_write_leaves_no_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_conversation(_sample_conversation(), temp_dir)
            names = sorted(p.name for p in Path(temp_dir).iterdir())
            self.assertEqual(names, ["code2env.sample.deadbeef.v1.json", MERGED_JSONL_NAME])

    def test_iter_jsonl_skips_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            merged = Path(temp_dir) / MERGED_JSONL_NAME
            merged.write_text(json.dumps(_sample_conversation()) + "\n\n", encoding="utf-8")
            self.assertEqual(len(list(iter_jsonl(merged))), 1)


if __name__ == "__main__":
    unittest.main()
