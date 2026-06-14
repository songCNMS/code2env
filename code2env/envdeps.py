"""Per-repo dependency installation into isolated venvs (task030 / root-cause A).

Session2's 100-env batch produced false-positive ``exact_match`` rewards because
flask envs never had their runtime deps (werkzeug, …) installed: the golden-answer
subprocess raised ``ModuleNotFoundError`` and an agent that echoed the same error
"matched". This module builds an isolated venv per repo, installs the declared
runtime dependencies, and hands back the interpreter to use for the golden answer
and for ``call_entrypoint`` at rollout time.

Design notes:
- venvs are cached under ``.code2env_cache/venvs`` (gitignored), keyed by repo +
  requirement set, so repeated drafts of the same repo reuse one environment.
- ``venv_builder`` and ``installer`` are injectable so unit tests exercise the
  orchestration offline without creating real venvs or hitting PyPI.
- A package that will not install is skipped (recorded in ``failed`` with a reason)
  rather than aborting the whole repo.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from code2env.models import RepoSnapshot

# (venv_dir, base_python) -> path to the venv's python interpreter.
VenvBuilder = Callable[[Path, str], str]
# (venv_python, requirement) -> (ok, reason).
Installer = Callable[[str, str], "tuple[bool, str]"]

_DEFAULT_CACHE = ".code2env_cache/venvs"


def prepare_repo_env(
    snapshot: RepoSnapshot,
    *,
    cache_dir: str | Path | None = None,
    base_python: str | None = None,
    install: bool = True,
    venv_builder: VenvBuilder | None = None,
    installer: Installer | None = None,
) -> dict[str, Any]:
    """Resolve the interpreter to use for ``snapshot``'s golden/runtime execution.

    Returns a dict with ``python`` (interpreter path), ``venv_dir``,
    ``requirements``, ``deps_status``, ``installed``, ``failed`` and ``reason``.
    ``deps_status`` is one of ``no_deps`` / ``skipped`` / ``installed`` /
    ``partial`` / ``uninstallable`` / ``venv_failed``.
    """

    base_python = base_python or sys.executable
    requirements = requirements_from_snapshot(snapshot)
    result: dict[str, Any] = {
        "python": base_python,
        "venv_dir": None,
        "requirements": requirements,
        "deps_status": "no_deps",
        "installed": [],
        "failed": [],
        "reason": None,
    }
    if not requirements:
        return result
    if not install:
        result["deps_status"] = "skipped"
        result["reason"] = "install_disabled"
        return result

    builder = venv_builder or _create_venv
    do_install = installer or _pip_install
    venv_dir = _venv_dir_for(snapshot, requirements, cache_dir)
    try:
        venv_python = builder(venv_dir, base_python)
    except Exception as exc:  # noqa: BLE001 - a failed venv falls back to base python.
        result["deps_status"] = "venv_failed"
        result["reason"] = f"venv_create_failed:{type(exc).__name__}:{exc}"
        return result

    result["venv_dir"] = str(venv_dir)
    result["python"] = venv_python
    installed: list[str] = []
    failed: list[dict[str, str]] = []
    for requirement in requirements:
        ok, reason = do_install(venv_python, requirement)
        if ok:
            installed.append(requirement)
        else:
            failed.append({"package": requirement, "reason": reason})
    result["installed"] = installed
    result["failed"] = failed
    if not failed:
        result["deps_status"] = "installed"
    elif installed:
        result["deps_status"] = "partial"
        result["reason"] = f"uninstallable_deps:{len(failed)}"
    else:
        result["deps_status"] = "uninstallable"
        result["reason"] = "uninstallable_deps:all"
    return result


def requirements_from_snapshot(snapshot: RepoSnapshot) -> list[str]:
    """Best-effort runtime requirement specifiers from a repo's dependency files."""

    root = Path(snapshot.path)
    requirements: list[str] = []
    seen: set[str] = set()

    def _add(spec: str) -> None:
        spec = spec.strip()
        if not spec or spec in seen:
            return
        seen.add(spec)
        requirements.append(spec)

    for relative in snapshot.dependency_files:
        path = root / relative
        name = path.name.lower()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if name.startswith("requirements") and name.endswith(".txt"):
            for spec in _parse_requirements_txt(text):
                _add(spec)
        elif name == "pyproject.toml":
            for spec in _parse_pyproject(text):
                _add(spec)
    return requirements


def _parse_requirements_txt(text: str) -> list[str]:
    specs: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Drop inline comments and environment markers; keep the bare requirement.
        line = line.split(" #", 1)[0].split(";", 1)[0].strip()
        if line:
            specs.append(line)
    return specs


def _parse_pyproject(text: str) -> list[str]:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
        return []
    try:
        data = tomllib.loads(text)
    except Exception:  # noqa: BLE001 - malformed pyproject is non-fatal.
        return []
    specs: list[str] = []
    project = data.get("project", {})
    for dependency in project.get("dependencies", []) or []:
        if isinstance(dependency, str):
            specs.append(dependency.split(";", 1)[0].strip())
    poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    for package, constraint in (poetry or {}).items():
        if package.lower() == "python":
            continue
        specs.append(package if not isinstance(constraint, str) else f"{package}{_poetry_spec(constraint)}")
    return [spec for spec in specs if spec]


def _poetry_spec(constraint: str) -> str:
    constraint = constraint.strip()
    if not constraint or constraint == "*":
        return ""
    if constraint[0] in "=<>!~":
        return constraint
    if constraint[0] == "^":
        # Approximate caret with a lower bound; good enough for install attempts.
        return f">={constraint[1:]}"
    return f"=={constraint}"


def _venv_dir_for(
    snapshot: RepoSnapshot, requirements: list[str], cache_dir: str | Path | None
) -> Path:
    base = Path(cache_dir or _DEFAULT_CACHE).expanduser().resolve()
    digest_input = snapshot.source + "::" + "\n".join(sorted(requirements))
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]
    return base / digest


def _create_venv(
    venv_dir: Path,
    base_python: str,
    *,
    runner=subprocess.run,
    which=shutil.which,
) -> str:
    """Create a venv (idempotent) and return its python interpreter path.

    Prefers the stdlib ``python -m venv`` (matches the base interpreter exactly).
    On nodes where that fails because ``ensurepip``/the ``python3-venv`` apt package
    is unavailable (task035), falls back to ``uv venv --seed`` — which builds a
    pip-enabled venv without ensurepip — when the ``uv`` binary is present. If
    neither works the original venv error propagates so the caller records
    ``deps_status=venv_failed`` and degrades to the base interpreter.

    ``runner``/``which`` are injectable so tests exercise both paths offline.
    """

    python_path = _venv_python_path(venv_dir)
    if python_path.exists():
        return str(python_path)
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        runner(
            [base_python, "-m", "venv", str(venv_dir)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return str(python_path)
    except (subprocess.CalledProcessError, OSError) as venv_exc:
        uv = which("uv")
        if not uv:
            raise
        # `python -m venv` can leave a partial directory behind before it fails on
        # ensurepip; uv refuses to populate a non-empty venv dir ("already exists",
        # exit 2), so clear it before retrying (task042 real-machine fix-forward).
        shutil.rmtree(venv_dir, ignore_errors=True)
        # uv resolves a bare interpreter name fine, but pass an absolute path when we
        # have one so the seeded venv matches the intended interpreter exactly.
        uv_python = base_python if os.path.isabs(base_python) else (which(base_python) or base_python)
        try:
            runner(
                [uv, "venv", "--seed", "--python", uv_python, str(venv_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (subprocess.CalledProcessError, OSError) as uv_exc:
            raise uv_exc from venv_exc
        return str(python_path)


def _venv_python_path(venv_dir: Path) -> Path:
    if sys.platform == "win32":  # pragma: no cover - linux runtime target
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _pip_install(venv_python: str, requirement: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [venv_python, "-m", "pip", "install", "--disable-pip-version-check", requirement],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, "pip_timeout"
    except OSError as exc:
        return False, f"pip_error:{exc}"
    if result.returncode == 0:
        return True, ""
    return False, result.stderr.strip()[-500:] or "pip_install_failed"


def golden_status_for(golden_answer: Any) -> str:
    """Classify a computed golden answer for the ``golden_status`` contract.

    ``real_value`` when the source function returned a real result; otherwise
    ``weak_oracle:golden_exception:<error_type>`` so the env can be excluded from
    the correctness denominator instead of producing false positives.
    """

    if isinstance(golden_answer, dict) and golden_answer.get("ok") is True:
        return "real_value"
    if isinstance(golden_answer, dict) and golden_answer.get("ok") is False:
        return f"weak_oracle:golden_exception:{golden_answer.get('error_type', 'unknown')}"
    if golden_answer is None:
        return "weak_oracle:golden_uncomputed"
    return "real_value"
