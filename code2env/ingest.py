from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

from code2env.models import RepoSnapshot, normalize_path


DEPENDENCY_FILE_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
}


def ingest_repo(source: str, *, cache_dir: str | Path | None = None, commit: str | None = None) -> RepoSnapshot:
    """Resolve a local path or Git URL into a reproducible repository snapshot."""

    if _looks_like_git_url(source):
        path = _clone_repo(source, cache_dir=cache_dir, commit=commit)
        source_label = source
    else:
        path = Path(source).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {path}")
        source_label = normalize_path(path)

    python_files: list[str] = []
    test_files: list[str] = []
    for file in path.rglob("*.py"):
        if _is_infra_path(file, path):
            continue
        relative = str(file.relative_to(path))
        if _is_test_file(file, path):
            test_files.append(relative)
        elif _is_supported_source_file(file, path):
            python_files.append(relative)
    dependency_files = [
        str(file.relative_to(path))
        for file in path.iterdir()
        if file.is_file() and file.name in DEPENDENCY_FILE_NAMES
    ]
    license_file = _find_license_file(path)
    is_git = (path / ".git").exists()
    detected_commit = _git_commit(path) if is_git else None

    return RepoSnapshot(
        source=source_label,
        path=normalize_path(path),
        commit=commit or detected_commit,
        is_git=is_git,
        python_files=sorted(python_files),
        dependency_files=sorted(dependency_files),
        license_file=license_file,
        test_files=sorted(test_files),
    )


def _looks_like_git_url(source: str) -> bool:
    return source.startswith(("https://", "http://", "git@")) or source.endswith(".git")


def _clone_repo(source: str, *, cache_dir: str | Path | None, commit: str | None) -> Path:
    base = Path(cache_dir or ".code2env_cache/repos").expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(f"{source}@{commit or 'HEAD'}".encode("utf-8")).hexdigest()[:16]
    target = base / digest
    if target.exists():
        return target

    clone_cmd = ["git", "clone", "--depth", "1", source, str(target)]
    if commit:
        clone_cmd = ["git", "clone", source, str(target)]
    subprocess.run(clone_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if commit:
        subprocess.run(["git", "checkout", commit], check=True, cwd=target, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return target


def _git_commit(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _find_license_file(path: Path) -> str | None:
    for candidate in path.iterdir():
        if candidate.is_file() and candidate.name.lower().startswith(("license", "copying")):
            return str(candidate.relative_to(path))
    return None


# Build/tooling directories that hold no first-class source, tests or fixtures.
INFRA_PARTS = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "dist",
    ".tox",
    ".nox",
}
# Topic directories excluded from the ranked source corpus (but tests/ is mined
# separately into ``RepoSnapshot.test_files`` for the TestLinkIndex).
NON_SOURCE_PARTS = {
    "benchmarks",
    "docs",
    "docs_src",
    "examples",
    "tests",
}
TEST_DIR_NAMES = {"tests", "test"}


def _is_infra_path(file: Path, root: Path) -> bool:
    """True for build/tooling paths that should never be indexed at all."""

    return bool(INFRA_PARTS.intersection(file.relative_to(root).parts))


def _is_test_file(file: Path, root: Path) -> bool:
    """Heuristic test-file detector: by directory, by name, or conftest.py."""

    parts = file.relative_to(root).parts
    if TEST_DIR_NAMES.intersection(parts):
        return True
    name = file.name
    return name == "conftest.py" or name.startswith("test_") or name.endswith("_test.py")


def _is_supported_source_file(file: Path, root: Path) -> bool:
    relative_parts = set(file.relative_to(root).parts)
    return not (INFRA_PARTS | NON_SOURCE_PARTS).intersection(relative_parts)


def copy_source_tree(snapshot: RepoSnapshot, target: str | Path) -> None:
    """Copy a filtered Python source snapshot into a generated env package."""

    source_root = Path(snapshot.path)
    target_root = Path(target)
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    for relative in snapshot.python_files:
        source_file = source_root / relative
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)

    for relative in snapshot.dependency_files:
        source_file = source_root / relative
        if source_file.exists():
            shutil.copy2(source_file, target_root / relative)

    if snapshot.license_file:
        source_file = source_root / snapshot.license_file
        destination = target_root / snapshot.license_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)
