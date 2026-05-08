from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.indexer import index_repo
from code2env.jsonio import write_json
from code2env.materialize import materialize_env_spec
from code2env.runtime import Code2Env
from code2env.spec import draft_env_spec


class Code2EnvMvpTest(unittest.TestCase):
    def test_scan_draft_build_and_smoke_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._create_sample_repo(Path(temp_dir) / "repo")
            snapshot = ingest_repo(str(repo))
            candidates = index_repo(snapshot)
            symbols = [candidate.symbol for candidate in candidates]
            self.assertIn("sample:normalize_name", symbols)

            spec = draft_env_spec(
                snapshot,
                symbol="sample:normalize_name",
                fixture={"args": ["  ada   lovelace "], "kwargs": {"shout": True}},
            )
            self.assertEqual(spec.golden_answer, {"ok": True, "value": {"kind": "json", "value": "ADA LOVELACE"}})

            spec_path = Path(temp_dir) / "env_spec.json"
            write_json(spec_path, spec.to_dict())
            package_root = build_env_package(spec_path, Path(temp_dir) / "generated")
            self.assertTrue((package_root / "source" / "sample.py").exists())

            env = Code2Env(package_root / "env_spec.json")
            env.reset()
            _, _, _, _ = env.step(
                {
                    "type": "tool_call",
                    "tool": "call_helper",
                    "arguments": {"helper": "clean_text", "args": ["  ada   lovelace "], "kwargs": {}},
                }
            )
            self.assertEqual(
                env.state["last_tool_result"],
                {"ok": True, "value": {"kind": "json", "value": "ada lovelace"}},
            )
            result = env.scripted_smoke()
            self.assertTrue(result["ok"])
            self.assertEqual(result["evaluation"]["score"], 1.0)

    def test_cli_scan_draft_build_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._create_sample_repo(Path(temp_dir) / "repo")
            spec_path = Path(temp_dir) / "spec.json"
            output_dir = Path(temp_dir) / "out"

            scan = self._run_cli(["scan", str(repo), "--top-k", "3", "--json"])
            scan_payload = json.loads(scan.stdout)
            self.assertEqual(scan_payload["candidates"][0]["symbol"], "sample:normalize_name")

            self._run_cli(
                [
                    "draft",
                    str(repo),
                    "--symbol",
                    "sample:normalize_name",
                    "--fixture-json",
                    '{"args": [" grace hopper "], "kwargs": {}}',
                    "--output",
                    str(spec_path),
                ]
            )
            build = self._run_cli(["build", str(spec_path), "--output-dir", str(output_dir)])
            package_root = Path(build.stdout.strip())
            smoke = self._run_cli(["smoke", str(package_root), "--json"])
            self.assertTrue(json.loads(smoke.stdout)["ok"])

    def test_src_layout_package_imports_work_after_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            package = repo / "src" / "pkg"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "ops.py").write_text(
                """
def double(value):
    return value * 2
""".lstrip(),
                encoding="utf-8",
            )

            snapshot = ingest_repo(str(repo))
            spec = draft_env_spec(snapshot, symbol="pkg.ops:double", fixture={"args": [21]})
            spec_path = Path(temp_dir) / "spec.json"
            write_json(spec_path, spec.to_dict())
            package_root = build_env_package(spec_path, Path(temp_dir) / "generated")
            self.assertTrue(Code2Env(package_root / "env_spec.json").scripted_smoke()["ok"])

    def test_materialize_env_spec_then_build_and_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._create_sample_repo(Path(temp_dir) / "repo")
            snapshot = ingest_repo(str(repo))
            draft = draft_env_spec(snapshot, symbol="sample:normalize_name", compute_golden=False)
            draft_path = Path(temp_dir) / "draft.json"
            materialized_path = Path(temp_dir) / "materialized.json"
            write_json(draft_path, draft.to_dict())

            summary = materialize_env_spec(
                draft_path,
                output_path=materialized_path,
                fixture={"args": [" ada lovelace "], "kwargs": {"shout": True}},
            )
            self.assertEqual(
                summary["golden_answer"],
                {"ok": True, "value": {"kind": "json", "value": "ADA LOVELACE"}},
            )
            package_root = build_env_package(materialized_path, Path(temp_dir) / "generated")
            self.assertTrue(Code2Env(package_root / "env_spec.json").scripted_smoke()["ok"])

    def test_nested_functions_are_not_exported_as_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "nested.py").write_text(
                """
def outer(value):
    def inner(item):
        return item + 1
    return inner(value)
""".lstrip(),
                encoding="utf-8",
            )
            candidates = index_repo(ingest_repo(str(repo)))
            self.assertEqual([candidate.symbol for candidate in candidates], ["nested:outer"])

    def test_runtime_blocks_network_socket(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "net_sample.py").write_text(
                """
def tries_network():
    import socket
    socket.socket()
    return "unexpected"
""".lstrip(),
                encoding="utf-8",
            )

            snapshot = ingest_repo(str(repo))
            spec = draft_env_spec(snapshot, symbol="net_sample:tries_network", compute_golden=False)
            spec_path = Path(temp_dir) / "spec.json"
            write_json(spec_path, spec.to_dict())
            package_root = build_env_package(spec_path, Path(temp_dir) / "generated")
            env = Code2Env(package_root / "env_spec.json")
            env.reset()
            env.step({"type": "tool_call", "tool": "call_entrypoint", "arguments": {}})
            result = env.state["last_tool_result"]
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_type"], "RuntimeError")
            self.assertIn("network access is disabled", result["error_message"])

    def _run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-m", "code2env", *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            self.fail(f"CLI failed: {result.args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def _create_sample_repo(self, path: Path) -> Path:
        path.mkdir(parents=True)
        (path / "sample.py").write_text(
            """
def clean_text(value):
    return " ".join(value.strip().split())


def normalize_name(name, shout=False):
    \"\"\"Normalize a human name for display.\"\"\"
    cleaned = clean_text(name)
    if shout:
        return cleaned.upper()
    return cleaned.title()
""".lstrip(),
            encoding="utf-8",
        )
        return path


if __name__ == "__main__":
    unittest.main()
