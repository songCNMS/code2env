from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from code2env.batch import generate_batch
from code2env.builder import build_env_package
from code2env.envdeps import (
    _create_venv,
    golden_status_for,
    prepare_repo_env,
    requirements_from_snapshot,
)
from code2env.executor import run_symbol_subprocess
from code2env.ingest import ingest_repo
from code2env.jsonio import read_json, write_json
from code2env.materialize import materialize_env_spec
from code2env.runtime import Code2Env
from code2env.spec import draft_env_spec


class RequirementsParsingTest(unittest.TestCase):
    def test_requirements_txt_and_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            (repo / "requirements.txt").write_text(
                "# comment\nwerkzeug>=2.0\nclick  # cli\n-e .\n\nitsdangerous; python_version>='3'\n",
                encoding="utf-8",
            )
            (repo / "pyproject.toml").write_text(
                '[project]\nname = "x"\ndependencies = ["jinja2>=3", "markupsafe"]\n',
                encoding="utf-8",
            )
            snapshot = ingest_repo(str(repo))
            requirements = requirements_from_snapshot(snapshot)
            self.assertIn("werkzeug>=2.0", requirements)
            self.assertIn("click", requirements)
            self.assertIn("itsdangerous", requirements)
            self.assertIn("jinja2>=3", requirements)
            self.assertIn("markupsafe", requirements)
            # Editlines / comments / markers are stripped.
            self.assertNotIn("-e .", requirements)


class PrepareRepoEnvTest(unittest.TestCase):
    def _repo_with_requirements(self, root: Path, requirements: str) -> Path:
        root.mkdir(parents=True)
        (root / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (root / "requirements.txt").write_text(requirements, encoding="utf-8")
        return root

    def test_no_deps_uses_base_python_without_venv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            result = prepare_repo_env(ingest_repo(str(repo)))
            self.assertEqual(result["deps_status"], "no_deps")
            self.assertEqual(result["python"], sys.executable)
            self.assertIsNone(result["venv_dir"])

    def test_all_deps_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo_with_requirements(Path(temp_dir) / "repo", "werkzeug\nclick\n")
            built: list[Path] = []

            def fake_builder(venv_dir: Path, base_python: str) -> str:
                built.append(venv_dir)
                return base_python  # reuse current interpreter; no real venv

            def fake_installer(venv_python: str, requirement: str):
                return True, ""

            result = prepare_repo_env(
                ingest_repo(str(repo)),
                cache_dir=Path(temp_dir) / "venvs",
                venv_builder=fake_builder,
                installer=fake_installer,
            )
            self.assertEqual(result["deps_status"], "installed")
            self.assertEqual(result["installed"], ["werkzeug", "click"])
            self.assertEqual(result["failed"], [])
            self.assertEqual(len(built), 1)

    def test_uninstallable_dep_is_skipped_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo_with_requirements(Path(temp_dir) / "repo", "good\nbroken\n")

            def fake_builder(venv_dir: Path, base_python: str) -> str:
                return base_python

            def fake_installer(venv_python: str, requirement: str):
                if requirement == "broken":
                    return False, "No matching distribution found for broken"
                return True, ""

            result = prepare_repo_env(
                ingest_repo(str(repo)),
                cache_dir=Path(temp_dir) / "venvs",
                venv_builder=fake_builder,
                installer=fake_installer,
            )
            self.assertEqual(result["deps_status"], "partial")
            self.assertEqual(result["installed"], ["good"])
            self.assertEqual(len(result["failed"]), 1)
            self.assertEqual(result["failed"][0]["package"], "broken")
            self.assertIn("broken", result["failed"][0]["reason"])

    def test_install_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo_with_requirements(Path(temp_dir) / "repo", "werkzeug\n")
            result = prepare_repo_env(ingest_repo(str(repo)), install=False)
            self.assertEqual(result["deps_status"], "skipped")
            self.assertEqual(result["python"], sys.executable)


def _venv_runner(*, fail_venv: bool, fail_uv: bool):
    """Fake subprocess runner: routes stdlib-venv vs uv-venv by '--seed' in cmd."""

    calls: list[list[str]] = []

    def runner(cmd, **kwargs):
        calls.append(list(cmd))
        is_uv = "--seed" in cmd
        if (is_uv and fail_uv) or (not is_uv and fail_venv):
            raise subprocess.CalledProcessError(1, cmd, stderr="boom")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return runner, calls


class CreateVenvUvFallbackTest(unittest.TestCase):
    def test_stdlib_venv_used_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner, calls = _venv_runner(fail_venv=False, fail_uv=False)
            python = _create_venv(
                Path(temp_dir) / "v", sys.executable, runner=runner, which=lambda _: None
            )
            self.assertTrue(python.endswith("/bin/python"))
            # Only the stdlib venv command runs; uv is never consulted.
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1:3], ["-m", "venv"])

    def test_uv_fallback_when_stdlib_venv_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner, calls = _venv_runner(fail_venv=True, fail_uv=False)
            python = _create_venv(
                Path(temp_dir) / "v",
                sys.executable,
                runner=runner,
                which=lambda name: "/usr/bin/uv" if name == "uv" else None,
            )
            self.assertTrue(python.endswith("/bin/python"))
            # Stdlib venv attempted first, then uv venv --seed.
            self.assertEqual(len(calls), 2)
            self.assertIn("--seed", calls[1])
            self.assertEqual(calls[1][0], "/usr/bin/uv")

    def test_venv_failed_when_stdlib_fails_and_uv_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner, _ = _venv_runner(fail_venv=True, fail_uv=False)
            with self.assertRaises(subprocess.CalledProcessError):
                _create_venv(
                    Path(temp_dir) / "v", sys.executable, runner=runner, which=lambda _: None
                )

    def test_venv_failed_when_both_stdlib_and_uv_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runner, calls = _venv_runner(fail_venv=True, fail_uv=True)
            with self.assertRaises(subprocess.CalledProcessError):
                _create_venv(
                    Path(temp_dir) / "v",
                    sys.executable,
                    runner=runner,
                    which=lambda name: "/usr/bin/uv",
                )
            self.assertEqual(len(calls), 2)

    def test_prepare_repo_env_succeeds_via_uv_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            (repo / "requirements.txt").write_text("werkzeug\n", encoding="utf-8")
            runner, _ = _venv_runner(fail_venv=True, fail_uv=False)

            def builder(venv_dir: Path, base_python: str) -> str:
                return _create_venv(
                    venv_dir,
                    base_python,
                    runner=runner,
                    which=lambda name: "/usr/bin/uv",
                )

            result = prepare_repo_env(
                ingest_repo(str(repo)),
                cache_dir=Path(temp_dir) / "venvs",
                venv_builder=builder,
                installer=lambda py, req: (True, ""),
            )
            self.assertEqual(result["deps_status"], "installed")
            self.assertEqual(result["installed"], ["werkzeug"])

    def test_prepare_repo_env_venv_failed_when_no_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            (repo / "requirements.txt").write_text("werkzeug\n", encoding="utf-8")
            runner, _ = _venv_runner(fail_venv=True, fail_uv=False)

            def builder(venv_dir: Path, base_python: str) -> str:
                return _create_venv(
                    venv_dir, base_python, runner=runner, which=lambda _: None
                )

            result = prepare_repo_env(
                ingest_repo(str(repo)),
                cache_dir=Path(temp_dir) / "venvs",
                venv_builder=builder,
            )
            self.assertEqual(result["deps_status"], "venv_failed")
            self.assertEqual(result["python"], sys.executable)
            self.assertIn("venv_create_failed", result["reason"])


class GoldenStatusTest(unittest.TestCase):
    def test_classification(self) -> None:
        self.assertEqual(golden_status_for({"ok": True, "value": {}}), "real_value")
        self.assertEqual(
            golden_status_for({"ok": False, "error_type": "ModuleNotFoundError"}),
            "weak_oracle:golden_exception:ModuleNotFoundError",
        )
        self.assertEqual(golden_status_for(None), "weak_oracle:golden_uncomputed")


class ExecutorPythonExecutableTest(unittest.TestCase):
    def _repo(self, root: Path) -> Path:
        root.mkdir(parents=True)
        (root / "m.py").write_text("def double(x):\n    return x * 2\n", encoding="utf-8")
        return root

    def test_default_python_executable_back_compat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(Path(temp_dir) / "repo")
            result = run_symbol_subprocess(str(repo), "m:double", [21], {})
            self.assertEqual(result, {"ok": True, "value": {"kind": "json", "value": 42}})

    def test_explicit_python_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(Path(temp_dir) / "repo")
            result = run_symbol_subprocess(
                str(repo), "m:double", [5], {}, python_executable=sys.executable
            )
            self.assertEqual(result["value"]["value"], 10)


class GoldenStatusPipelineTest(unittest.TestCase):
    def test_real_value_golden_status_on_spec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text("def double(x: int):\n    return x * 2\n", encoding="utf-8")
            spec = draft_env_spec(
                ingest_repo(str(repo)), symbol="m:double", fixture={"args": [3]}
            )
            self.assertEqual(spec.provenance["golden_status"], "real_value")
            self.assertEqual(spec.golden_answer["value"]["value"], 6)

    def test_weak_oracle_when_import_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text(
                "import totally_missing_pkg_xyz\n\ndef f(x: int):\n    return totally_missing_pkg_xyz.go(x)\n",
                encoding="utf-8",
            )
            spec = draft_env_spec(ingest_repo(str(repo)), symbol="m:f", fixture={"args": [1]})
            self.assertTrue(spec.provenance["golden_status"].startswith("weak_oracle:"))
            self.assertIn("ModuleNotFoundError", spec.provenance["golden_status"])

    def test_materialize_sets_golden_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text("def double(x):\n    return x * 2\n", encoding="utf-8")
            draft = draft_env_spec(
                ingest_repo(str(repo)), symbol="m:double", compute_golden=False
            )
            self.assertEqual(draft.provenance["golden_status"], "pending_golden")
            draft_path = Path(temp_dir) / "draft.json"
            out_path = Path(temp_dir) / "materialized.json"
            write_json(draft_path, draft.to_dict())
            summary = materialize_env_spec(
                draft_path, output_path=out_path, fixture={"args": [4]}
            )
            self.assertEqual(summary["golden_status"], "real_value")
            self.assertEqual(read_json(out_path)["provenance"]["golden_status"], "real_value")

    def test_runtime_falls_back_when_venv_python_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            (repo / "m.py").write_text("def double(x: int):\n    return x * 2\n", encoding="utf-8")
            # Record a non-existent venv python; runtime must fall back gracefully and
            # recompute the golden answer at reset() with the default interpreter.
            spec = draft_env_spec(
                ingest_repo(str(repo)),
                symbol="m:double",
                fixture={"args": [7]},
                python_executable="/nonexistent/venv/bin/python",
                compute_golden=False,
            )
            spec_path = Path(temp_dir) / "spec.json"
            write_json(spec_path, spec.to_dict())
            package_root = build_env_package(spec_path, Path(temp_dir) / "gen")
            env = Code2Env(package_root / "env_spec.json")
            self.assertIsNone(env._python_executable)
            self.assertTrue(env.scripted_smoke()["ok"])


class BatchGoldenStatusTest(unittest.TestCase):
    def test_weak_oracle_env_recorded_in_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            # The missing import is local to ``bad`` so it only poisons that env.
            (repo / "m.py").write_text(
                "def good(x: int):\n    return x + 1\n\n"
                "def bad(x: int):\n    import totally_missing_pkg_xyz\n"
                "    return totally_missing_pkg_xyz.go(x)\n",
                encoding="utf-8",
            )
            manifest = generate_batch(
                [str(repo)],
                output_dir=Path(temp_dir) / "out",
                target_count=100,
                generated_at="2026-06-13T00:00:00Z",
            )
            statuses = {
                env["symbol"].split(":")[-1]: env["golden_status"] for env in manifest["envs"]
            }
            self.assertEqual(statuses["good"], "real_value")
            self.assertTrue(statuses["bad"].startswith("weak_oracle:"))
            self.assertEqual(manifest["summary"]["real_value"], 1)
            self.assertEqual(manifest["summary"]["weak_oracle"], 1)


if __name__ == "__main__":
    unittest.main()
