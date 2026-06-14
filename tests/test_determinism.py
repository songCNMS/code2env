from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code2env.batch import generate_batch
from code2env.determinism import classify_determinism, is_usable
from code2env.ingest import ingest_repo
from code2env.spec import draft_env_spec


def _val(value) -> dict:
    return {"ok": True, "value": {"kind": "json", "value": value}}


def _repr(text: str) -> dict:
    return {"ok": True, "value": {"kind": "repr", "type": "object", "repr": text}}


class ClassifyDeterminismTest(unittest.TestCase):
    def test_plain_value_is_deterministic(self) -> None:
        self.assertEqual(classify_determinism(_val(42), [_val(42), _val(42)]), "deterministic")

    def test_object_repr_flagged_standalone(self) -> None:
        # Default object repr with a live address: flagged on a single run.
        self.assertEqual(
            classify_determinism(_repr("<object object at 0x7f12ab34cd56>")),
            "nondeterministic:object_repr",
        )

    def test_hashlib_style_repr_flagged(self) -> None:
        self.assertEqual(
            classify_determinism(_repr("<sha1 _hashlib.HASH object at 0x7f8a1b2c3d4e>")),
            "nondeterministic:object_repr",
        )

    # --- Anti over-flag: legitimate, *stable* hex/path returns must NOT be flagged ---

    def test_stable_bare_hex_is_deterministic(self) -> None:
        golden = _val("0xdeadbeef")
        self.assertEqual(
            classify_determinism(golden, [golden, golden]), "deterministic"
        )

    def test_stable_abs_path_is_deterministic(self) -> None:
        golden = _val("/home/user/output.txt")
        self.assertEqual(
            classify_determinism(golden, [golden, golden]), "deterministic"
        )

    def test_stable_hex_without_repeats_is_deterministic(self) -> None:
        # No repeat evidence and no object-repr → trust it (don't over-prune).
        self.assertEqual(classify_determinism(_val("0xcafebabe1234")), "deterministic")

    # --- Corroborated nondeterminism via repeat mismatch ---

    def test_unstable_value_is_unstable_across_runs(self) -> None:
        self.assertEqual(
            classify_determinism(_val(1), [_val(2), _val(3)]),
            "nondeterministic:unstable_across_runs",
        )

    def test_unstable_abs_path_refines_reason(self) -> None:
        self.assertEqual(
            classify_determinism(_val("/home/a/1.txt"), [_val("/home/b/2.txt")]),
            "nondeterministic:abs_path",
        )

    def test_unstable_bare_hex_refines_to_memory_addr(self) -> None:
        self.assertEqual(
            classify_determinism(_val("0xaaaaaa"), [_val("0xbbbbbb")]),
            "nondeterministic:memory_addr",
        )

    def test_is_usable(self) -> None:
        self.assertTrue(is_usable("real_value", "deterministic"))
        self.assertFalse(is_usable("real_value", "nondeterministic:object_repr"))
        self.assertFalse(is_usable("weak_oracle:golden_exception:X", "deterministic"))
        self.assertFalse(is_usable("real_value", None))


class DraftDeterminismTest(unittest.TestCase):
    def _draft(self, source: str, symbol: str, **kwargs):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text(source, encoding="utf-8")
            return draft_env_spec(ingest_repo(str(repo)), symbol=symbol, **kwargs)

    def test_deterministic_function(self) -> None:
        spec = self._draft("def double(x: int):\n    return x * 2\n", "m:double", fixture={"args": [3]})
        self.assertEqual(spec.provenance["golden_status"], "real_value")
        self.assertEqual(spec.provenance["determinism"], "deterministic")

    def test_object_return_is_object_repr(self) -> None:
        spec = self._draft("def make():\n    return object()\n", "m:make")
        self.assertEqual(spec.provenance["golden_status"], "real_value")
        self.assertEqual(spec.provenance["determinism"], "nondeterministic:object_repr")

    def test_random_return_is_unstable(self) -> None:
        spec = self._draft(
            "import random\n\ndef roll():\n    return random.random()\n",
            "m:roll",
            determinism_runs=3,
        )
        self.assertEqual(spec.provenance["determinism"], "nondeterministic:unstable_across_runs")

    def test_legit_path_return_not_flagged(self) -> None:
        # Returns a constant absolute path: stable across runs → deterministic.
        spec = self._draft(
            'def where():\n    return "/home/project/data.txt"\n',
            "m:where",
            determinism_runs=3,
        )
        self.assertEqual(spec.provenance["determinism"], "deterministic")

    def test_legit_hex_return_not_flagged(self) -> None:
        spec = self._draft(
            'def color():\n    return "0xdeadbeef"\n', "m:color", determinism_runs=3
        )
        self.assertEqual(spec.provenance["determinism"], "deterministic")

    def test_weak_oracle_determinism_is_null(self) -> None:
        spec = self._draft(
            "def f(x: int):\n    import totally_missing_xyz\n    return totally_missing_xyz.g(x)\n",
            "m:f",
            fixture={"args": [1]},
        )
        self.assertTrue(spec.provenance["golden_status"].startswith("weak_oracle:"))
        self.assertIsNone(spec.provenance["determinism"])


class BatchDeterminismTest(unittest.TestCase):
    def test_manifest_usable_and_nondeterministic_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text(
                "def good(x: int):\n    return x + 1\n\n"
                "def obj():\n    return object()\n",
                encoding="utf-8",
            )
            manifest = generate_batch(
                [str(repo)],
                output_dir=Path(temp_dir) / "out",
                target_count=100,
                determinism_runs=2,
                generated_at="2026-06-14T00:00:00Z",
            )
            determinism = {
                env["symbol"].split(":")[-1]: env["determinism"] for env in manifest["envs"]
            }
            self.assertEqual(determinism["good"], "deterministic")
            self.assertEqual(determinism["obj"], "nondeterministic:object_repr")
            self.assertEqual(manifest["summary"]["usable"], 1)
            self.assertEqual(manifest["summary"]["nondeterministic"], 1)
            self.assertEqual(manifest["summary"]["by_repo"][str(repo)]["usable"], 1)
            self.assertEqual(manifest["summary"]["by_repo"][str(repo)]["nondeterministic"], 1)


if __name__ == "__main__":
    unittest.main()
