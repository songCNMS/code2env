from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from code2env.batch import _disqualify, generate_batch, synthesize_fixture
from code2env.indexer import find_candidate, index_repo
from code2env.ingest import ingest_repo


def _func(source: str) -> ast.FunctionDef:
    return next(
        node
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


SAMPLE_REPO = """
def add(a: int, b: int) -> int:
    \"\"\"Add two ints.\"\"\"
    if a > b:
        return a + b
    return b + a


def greet(name: str = "world") -> str:
    \"\"\"Greet someone.\"\"\"
    parts = name.split()
    return "hi " + " ".join(parts)


def make_list(n: int) -> list:
    \"\"\"Build a list.\"\"\"
    out = []
    for i in range(n):
        out.append(i)
    return out


def writes(path: str):
    \"\"\"Has a side effect.\"\"\"
    open(path, "w")
    return path


def untyped(x):
    return x


class Holder:
    def method(self, x: int):
        return x
"""


class FixtureSynthesisTest(unittest.TestCase):
    def test_empty_signature_when_no_required_params(self) -> None:
        fixture = synthesize_fixture(_func("def f():\n    return 1\n"))
        self.assertTrue(fixture["ok"])
        self.assertEqual(fixture["strategy"], "empty_signature")
        self.assertEqual(fixture["value"], {"args": [], "kwargs": {}})

    def test_all_defaulted_params_use_empty_signature(self) -> None:
        fixture = synthesize_fixture(_func("def f(a=1, b='x'):\n    return a\n"))
        self.assertEqual(fixture["strategy"], "empty_signature")
        self.assertEqual(fixture["value"], {"args": [], "kwargs": {}})

    def test_typed_scalar_and_container_params(self) -> None:
        fixture = synthesize_fixture(
            _func("def f(a: int, b: str, c: list, d: dict, e: bool):\n    return a\n")
        )
        self.assertTrue(fixture["ok"])
        self.assertEqual(fixture["strategy"], "typed_signature")
        self.assertEqual(fixture["value"]["args"], [1, "x", [], {}, False])

    def test_typed_generic_subscript_params(self) -> None:
        fixture = synthesize_fixture(
            _func("def f(a: 'list[int]', b: 'dict[str, int]'):\n    return a\n")
        )
        # Subscripted generics resolve to their base container.
        self.assertEqual(fixture["value"]["args"], [[], {}])

    def test_optional_param_synthesises_null(self) -> None:
        fixture = synthesize_fixture(_func("def f(a: 'Optional[int]'):\n    return a\n"))
        self.assertEqual(fixture["value"]["args"], [None])

    def test_required_keyword_only_param(self) -> None:
        fixture = synthesize_fixture(_func("def f(*, a: int):\n    return a\n"))
        self.assertEqual(fixture["value"], {"args": [], "kwargs": {"a": 1}})

    def test_varargs_and_kwargs_are_optional(self) -> None:
        fixture = synthesize_fixture(_func("def f(*args, **kwargs):\n    return 1\n"))
        self.assertEqual(fixture["strategy"], "empty_signature")

    def test_untyped_required_param_is_not_synthesisable(self) -> None:
        fixture = synthesize_fixture(_func("def f(a):\n    return a\n"))
        self.assertFalse(fixture["ok"])
        self.assertEqual(fixture["reason"], "untyped_required_param:a")

    def test_unsupported_typed_param_is_not_synthesisable(self) -> None:
        fixture = synthesize_fixture(_func("def f(a: bytes):\n    return a\n"))
        self.assertFalse(fixture["ok"])
        self.assertEqual(fixture["reason"], "unsupported_param_type:a:bytes")

    def test_missing_function_node(self) -> None:
        fixture = synthesize_fixture(None)
        self.assertFalse(fixture["ok"])
        self.assertEqual(fixture["reason"], "function_node_not_found")


class BatchPipelineTest(unittest.TestCase):
    def _write_repo(self, root: Path) -> Path:
        root.mkdir(parents=True)
        (root / "m.py").write_text(SAMPLE_REPO, encoding="utf-8")
        return root

    def test_small_batch_closed_loop_and_manifest_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._write_repo(Path(temp_dir) / "lib")
            output_dir = Path(temp_dir) / "out"
            manifest = generate_batch(
                [str(repo)],
                output_dir=output_dir,
                target_count=100,
                generated_at="2026-06-13T00:00:00Z",
            )

            # Manifest top-level contract.
            self.assertEqual(
                set(manifest.keys()),
                {"generated_at", "repos", "summary", "repo_deps", "envs", "skipped"},
            )
            self.assertEqual(manifest["repos"], [str(repo)])
            self.assertTrue((output_dir / "manifest.json").exists())

            summary = manifest["summary"]
            self.assertEqual(
                set(summary.keys()),
                {
                    "candidates_scanned",
                    "draft_ok",
                    "build_ok",
                    "smoke_ok",
                    "skipped_no_fixture",
                    "real_value",
                    "weak_oracle",
                    "by_repo",
                },
            )
            # add / greet / make_list build and smoke; writes / untyped / method skipped.
            self.assertEqual(summary["build_ok"], 3)
            self.assertEqual(summary["draft_ok"], 3)
            self.assertEqual(summary["smoke_ok"], 3)
            self.assertEqual(summary["skipped_no_fixture"], 3)
            # No third-party deps in the synthetic repo → all golden answers are real.
            self.assertEqual(summary["real_value"], 3)
            self.assertEqual(summary["weak_oracle"], 0)
            self.assertEqual(
                summary["by_repo"][str(repo)],
                {"build_ok": 3, "smoke_ok": 3, "real_value": 3, "weak_oracle": 0, "deps_status": "no_deps"},
            )
            # repo_deps records per-repo dependency provenance.
            self.assertEqual(manifest["repo_deps"][str(repo)]["deps_status"], "no_deps")

            # Skip reasons.
            reasons = {entry["reason"] for entry in manifest["skipped"]}
            self.assertEqual(
                reasons, {"possible_side_effect", "untyped_required_param:x", "not_module_level"}
            )
            for entry in manifest["skipped"]:
                self.assertEqual(set(entry.keys()), {"symbol", "repo", "reason"})

            # Env record contract + on-disk artifacts.
            required_env_keys = {
                "env_id",
                "repo",
                "symbol",
                "file",
                "line_start",
                "line_end",
                "fixture",
                "draft_ok",
                "build_ok",
                "smoke_ok",
                "smoke_fail_reason",
                "golden_status",
                "deps_status",
                "deps_installed",
                "spec_path",
                "package_path",
            }
            for env in manifest["envs"]:
                self.assertEqual(set(env.keys()), required_env_keys)
                self.assertEqual(
                    set(env["fixture"].keys()), {"ok", "strategy", "value", "reason"}
                )
                self.assertEqual(set(env["fixture"]["value"].keys()), {"args", "kwargs"})
                self.assertEqual(env["golden_status"], "real_value")
                self.assertEqual(env["deps_status"], "no_deps")
                self.assertTrue(Path(env["spec_path"]).exists())
                self.assertTrue((Path(env["package_path"]) / "env_spec.json").exists())

    def test_target_count_caps_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._write_repo(Path(temp_dir) / "lib")
            manifest = generate_batch(
                [str(repo)],
                output_dir=Path(temp_dir) / "out",
                target_count=1,
                generated_at="2026-06-13T00:00:00Z",
            )
            self.assertEqual(manifest["summary"]["build_ok"], 1)

    def test_side_effect_candidate_skipped_by_default_but_allowed_via_flag(self) -> None:
        # Tested at the disqualify layer so the side-effecting function is never
        # executed (the golden-answer subprocess does not sandbox file writes).
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._write_repo(Path(temp_dir) / "lib")
            candidates = index_repo(ingest_repo(str(repo)))
            writes = find_candidate(candidates, "m:writes")
            self.assertEqual(
                _disqualify(writes, include_side_effects=False), "possible_side_effect"
            )
            self.assertIsNone(_disqualify(writes, include_side_effects=True))


if __name__ == "__main__":
    unittest.main()
