from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.jsonio import write_json
from code2env.runtime import Code2Env, _answers_equal, _normalize_answer_envelope
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


GOLDEN = {"ok": True, "value": {"kind": "json", "value": "ADA LOVELACE"}}


class NormalizeEnvelopeTest(unittest.TestCase):
    def test_peels_tool_and_json_layers_to_inner_value(self) -> None:
        self.assertEqual(_normalize_answer_envelope(GOLDEN), "ADA LOVELACE")
        self.assertEqual(_normalize_answer_envelope({"kind": "json", "value": "ADA LOVELACE"}), "ADA LOVELACE")
        self.assertEqual(_normalize_answer_envelope("ADA LOVELACE"), "ADA LOVELACE")

    def test_inner_data_structure_is_preserved(self) -> None:
        env = {"ok": True, "value": {"kind": "json", "value": {"a": [1, 2], "b": {"c": 3}}}}
        self.assertEqual(_normalize_answer_envelope(env), {"a": [1, 2], "b": {"c": 3}})

    def test_error_envelope_is_not_peeled(self) -> None:
        err = {"ok": False, "error_type": "ValueError", "error_message": "boom"}
        self.assertEqual(_normalize_answer_envelope(err), err)

    def test_repr_shell_is_kept(self) -> None:
        wrapped = {"ok": True, "value": {"kind": "repr", "type": "set", "repr": "{1, 2}"}}
        self.assertEqual(_normalize_answer_envelope(wrapped), {"kind": "repr", "type": "set", "repr": "{1, 2}"})

    def test_guard_against_pathological_nesting(self) -> None:
        node: dict = {}
        node["ok"] = True
        node["value"] = node  # self-referential
        # Should not infinite-loop; returns something within the guard budget.
        _normalize_answer_envelope(node)


class AnswersEqualTest(unittest.TestCase):
    def test_all_envelope_shapes_of_same_value_match_golden(self) -> None:
        for submitted in (GOLDEN, {"kind": "json", "value": "ADA LOVELACE"}, "ADA LOVELACE"):
            self.assertTrue(_answers_equal(submitted, GOLDEN), submitted)

    def test_different_underlying_value_does_not_match(self) -> None:
        self.assertFalse(_answers_equal("GRACE HOPPER", GOLDEN))
        self.assertFalse(_answers_equal({"kind": "json", "value": "GRACE HOPPER"}, GOLDEN))

    def test_error_golden_only_matches_same_error(self) -> None:
        err = {"ok": False, "error_type": "ValueError", "error_message": "boom"}
        self.assertTrue(_answers_equal(err, err))
        self.assertFalse(_answers_equal("boom", err))
        self.assertFalse(_answers_equal({"kind": "json", "value": "boom"}, err))

    def test_none_submission_never_matches(self) -> None:
        self.assertFalse(_answers_equal(None, GOLDEN))


class RuntimeEnvelopeIntegrationTest(unittest.TestCase):
    def _golden(self, env: Code2Env) -> object:
        env.reset()
        return env.spec.golden_answer

    def test_submitting_inner_value_is_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            env.reset()
            _, _, done, _ = env.step(
                {"type": "tool_call", "tool": "submit_answer", "arguments": {"answer": "ADA LOVELACE"}}
            )
            self.assertTrue(done)
            self.assertTrue(env.evaluate()["correct"])

    def test_submitting_json_shell_is_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            env.reset()
            env.step(
                {
                    "type": "tool_call",
                    "tool": "submit_answer",
                    "arguments": {"answer": {"kind": "json", "value": "ADA LOVELACE"}},
                }
            )
            self.assertTrue(env.evaluate()["correct"])

    def test_submitting_full_envelope_still_correct(self) -> None:
        # scripted_smoke submits the full last_tool_result; must remain correct.
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            result = env.scripted_smoke()
            self.assertTrue(result["ok"])
            self.assertEqual(result["evaluation"]["score"], 1.0)

    def test_wrong_value_is_incorrect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            env.reset()
            env.step(
                {"type": "tool_call", "tool": "submit_answer", "arguments": {"answer": "WRONG NAME"}}
            )
            self.assertFalse(env.evaluate()["correct"])


if __name__ == "__main__":
    unittest.main()
