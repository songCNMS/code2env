from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.jsonio import write_json
from code2env.runtime import Code2Env, _accepted_answer_forms, _answers_equal
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


def _envelope(inner: object) -> dict:
    """Build the executor's two-layer success envelope around a serialized inner value."""
    return {"ok": True, "value": {"kind": "json", "value": inner}}


GOLDEN = _envelope("ADA LOVELACE")


class AcceptedFormsTest(unittest.TestCase):
    def test_standard_golden_yields_three_accepted_shapes(self) -> None:
        forms = _accepted_answer_forms(GOLDEN)
        self.assertEqual(
            forms,
            ["ADA LOVELACE", {"kind": "json", "value": "ADA LOVELACE"}, GOLDEN],
        )

    def test_error_envelope_requires_exact_match(self) -> None:
        err = {"ok": False, "error_type": "ValueError", "error_message": "boom"}
        self.assertEqual(_accepted_answer_forms(err), [err])

    def test_repr_payload_requires_exact_match(self) -> None:
        wrapped = {"ok": True, "value": {"kind": "repr", "type": "set", "repr": "{1, 2}"}}
        self.assertEqual(_accepted_answer_forms(wrapped), [wrapped])


class AnswersEqualTest(unittest.TestCase):
    def test_all_three_shapes_of_same_value_match(self) -> None:
        for submitted in ("ADA LOVELACE", {"kind": "json", "value": "ADA LOVELACE"}, GOLDEN):
            self.assertTrue(_answers_equal(submitted, GOLDEN), submitted)

    def test_different_underlying_value_does_not_match(self) -> None:
        self.assertFalse(_answers_equal("GRACE HOPPER", GOLDEN))
        self.assertFalse(_answers_equal({"kind": "json", "value": "GRACE HOPPER"}, GOLDEN))

    def test_inner_data_structure_shapes(self) -> None:
        golden = _envelope({"a": [1, 2], "b": {"c": 3}})
        self.assertTrue(_answers_equal({"a": [1, 2], "b": {"c": 3}}, golden))
        self.assertTrue(_answers_equal({"kind": "json", "value": {"a": [1, 2], "b": {"c": 3}}}, golden))
        self.assertFalse(_answers_equal({"a": [1, 2], "b": {"c": 4}}, golden))

    def test_error_golden_only_matches_same_error(self) -> None:
        err = {"ok": False, "error_type": "ValueError", "error_message": "boom"}
        self.assertTrue(_answers_equal(err, err))
        self.assertFalse(_answers_equal("boom", err))
        self.assertFalse(_answers_equal({"kind": "json", "value": "boom"}, err))

    def test_none_submission_never_matches(self) -> None:
        self.assertFalse(_answers_equal(None, GOLDEN))

    # --- regression: the false positive REQUEST_CHANGES was about (root cause: collision) ---
    def test_function_returning_ok_value_dict_rejects_bare_inner(self) -> None:
        # Target function legitimately returns {"ok": True, "value": 5}.
        golden = _envelope({"ok": True, "value": 5})
        # Correct submissions:
        self.assertTrue(_answers_equal({"ok": True, "value": 5}, golden))            # bare inner X
        self.assertTrue(_answers_equal({"kind": "json", "value": {"ok": True, "value": 5}}, golden))  # shell
        self.assertTrue(_answers_equal(golden, golden))                              # full envelope
        # The collision that must NOT be accepted: submitting the over-peeled inner value.
        self.assertFalse(_answers_equal(5, golden))

    def test_function_returning_json_shaped_dict_rejects_bare_inner(self) -> None:
        # Target function legitimately returns {"kind": "json", "value": 7}.
        golden = _envelope({"kind": "json", "value": 7})
        self.assertTrue(_answers_equal({"kind": "json", "value": 7}, golden))  # bare inner X
        self.assertFalse(_answers_equal(7, golden))                            # over-peeled -> incorrect


class RuntimeEnvelopeIntegrationTest(unittest.TestCase):
    def _submit(self, env: Code2Env, answer: object) -> bool:
        env.reset()
        env.step({"type": "tool_call", "tool": "submit_answer", "arguments": {"answer": answer}})
        return env.evaluate()["correct"]

    def test_inner_value_json_shell_and_full_envelope_all_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            self.assertTrue(self._submit(env, "ADA LOVELACE"))
            self.assertTrue(self._submit(env, {"kind": "json", "value": "ADA LOVELACE"}))
            self.assertTrue(self._submit(env, {"ok": True, "value": {"kind": "json", "value": "ADA LOVELACE"}}))

    def test_wrong_value_is_incorrect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            self.assertFalse(self._submit(env, "WRONG NAME"))

    def test_scripted_smoke_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = _build_env(Path(temp))
            result = env.scripted_smoke()
            self.assertTrue(result["ok"])
            self.assertEqual(result["evaluation"]["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
