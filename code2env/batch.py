"""Batch EnvPackage generation pipeline (task020 / Session2 D1).

Drives the existing scan -> draft -> build chain across many repositories and
auto-synthesises a JSON fixture for each chosen function from its AST signature,
producing a set of EnvPackages plus a single ``manifest.json`` that downstream
reporting (w4) and scale-out (w5) consume.

The ``manifest.json`` contract is fixed (do not rename fields)::

    {
      "generated_at": str,
      "repos": [str, ...],
      "summary": {
        "candidates_scanned": int,
        "draft_ok": int,
        "build_ok": int,
        "smoke_ok": int,
        "skipped_no_fixture": int,
        "by_repo": {repo: {"build_ok": int, "smoke_ok": int}}
      },
      "envs": [
        {
          "env_id", "repo", "symbol", "file", "line_start", "line_end",
          "fixture": {"ok", "strategy", "value": {"args", "kwargs"}, "reason"},
          "draft_ok", "build_ok", "smoke_ok", "smoke_fail_reason",
          "spec_path", "package_path"
        }, ...
      ],
      "skipped": [{"symbol", "repo", "reason"}, ...]
    }
"""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from code2env.builder import build_env_package
from code2env.indexer import index_repo
from code2env.ingest import ingest_repo
from code2env.jsonio import write_json
from code2env.models import FunctionCandidate, RepoSnapshot
from code2env.runtime import Code2Env
from code2env.spec import draft_env_spec

# Annotation name -> synthesised JSON value for scalar parameter types.
_SCALAR_VALUES: dict[str, Any] = {
    "str": "x",
    "int": 1,
    "float": 1.0,
    "bool": False,
    "complex": 0,
    "Any": "x",
    "object": "x",
}
# Annotation names that map to an empty JSON container.
_LIST_TYPES = {
    "list",
    "List",
    "tuple",
    "Tuple",
    "set",
    "Set",
    "frozenset",
    "FrozenSet",
    "Sequence",
    "MutableSequence",
    "Iterable",
    "Iterator",
    "Collection",
}
_DICT_TYPES = {"dict", "Dict", "Mapping", "MutableMapping", "OrderedDict", "DefaultDict"}
# Annotation names that are safe to satisfy with ``null``.
_NONE_TYPES = {"None", "NoneType", "Optional", "Union"}


def generate_batch(
    repos: list[str],
    *,
    output_dir: str | Path,
    target_count: int = 100,
    cache_dir: str | Path | None = None,
    per_repo_limit: int | None = None,
    run_smoke: bool = True,
    include_side_effects: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Generate EnvPackages across ``repos`` and return the manifest dict.

    Stops once ``target_count`` successful builds are reached (counted globally),
    iterating repos in order and candidates by descending static score.
    """

    output_root = Path(output_dir).expanduser().resolve()
    specs_dir = output_root / "specs"
    packages_dir = output_root / "packages"
    specs_dir.mkdir(parents=True, exist_ok=True)
    packages_dir.mkdir(parents=True, exist_ok=True)

    envs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    repo_labels: list[str] = []
    by_repo: dict[str, dict[str, int]] = {}
    candidates_scanned = 0
    build_ok_total = 0

    for repo in repos:
        snapshot = ingest_repo(repo, cache_dir=cache_dir)
        repo_label = snapshot.source
        repo_labels.append(repo_label)
        by_repo.setdefault(repo_label, {"build_ok": 0, "smoke_ok": 0})
        candidates = index_repo(snapshot)
        candidates_scanned += len(candidates)
        tree_cache: dict[str, ast.Module | None] = {}
        repo_build_ok = 0

        for candidate in candidates:
            if build_ok_total >= target_count:
                break
            if per_repo_limit is not None and repo_build_ok >= per_repo_limit:
                break

            skip_reason = _disqualify(candidate, include_side_effects=include_side_effects)
            if skip_reason:
                skipped.append({"symbol": candidate.symbol, "repo": repo_label, "reason": skip_reason})
                continue

            func_node = _function_node(snapshot, candidate, tree_cache)
            fixture = synthesize_fixture(func_node)
            if not fixture["ok"]:
                skipped.append(
                    {"symbol": candidate.symbol, "repo": repo_label, "reason": fixture["reason"]}
                )
                continue

            env_record = _generate_one(
                snapshot=snapshot,
                candidate=candidate,
                candidates=candidates,
                fixture=fixture,
                repo_label=repo_label,
                specs_dir=specs_dir,
                packages_dir=packages_dir,
                run_smoke=run_smoke,
            )
            envs.append(env_record)
            if env_record["build_ok"]:
                build_ok_total += 1
                repo_build_ok += 1
                by_repo[repo_label]["build_ok"] += 1
            if env_record["smoke_ok"]:
                by_repo[repo_label]["smoke_ok"] += 1

        if build_ok_total >= target_count:
            break

    summary = {
        "candidates_scanned": candidates_scanned,
        "draft_ok": sum(1 for env in envs if env["draft_ok"]),
        "build_ok": sum(1 for env in envs if env["build_ok"]),
        "smoke_ok": sum(1 for env in envs if env["smoke_ok"]),
        "skipped_no_fixture": len(skipped),
        "by_repo": by_repo,
    }
    manifest = {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "repos": repo_labels,
        "summary": summary,
        "envs": envs,
        "skipped": skipped,
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest


def _generate_one(
    *,
    snapshot: RepoSnapshot,
    candidate: FunctionCandidate,
    candidates: list[FunctionCandidate],
    fixture: dict[str, Any],
    repo_label: str,
    specs_dir: Path,
    packages_dir: Path,
    run_smoke: bool,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "env_id": None,
        "repo": repo_label,
        "symbol": candidate.symbol,
        "file": candidate.file,
        "line_start": candidate.lineno,
        "line_end": candidate.end_lineno,
        "fixture": fixture,
        "draft_ok": False,
        "build_ok": False,
        "smoke_ok": False,
        "smoke_fail_reason": None,
        "spec_path": None,
        "package_path": None,
    }

    try:
        spec = draft_env_spec(
            snapshot,
            symbol=candidate.symbol,
            fixture=fixture["value"],
            candidates=candidates,
        )
        record["env_id"] = spec.id
        record["draft_ok"] = True
    except Exception as exc:  # noqa: BLE001 - a failed draft is a recorded outcome, not a crash.
        record["smoke_fail_reason"] = f"draft_error:{type(exc).__name__}:{exc}"
        return record

    spec_path = specs_dir / f"{spec.id}.json"
    try:
        write_json(spec_path, spec.to_dict())
        record["spec_path"] = str(spec_path)
        package_root = build_env_package(spec_path, packages_dir)
        record["package_path"] = str(package_root)
        record["build_ok"] = True
    except Exception as exc:  # noqa: BLE001 - a failed build is a recorded outcome.
        record["smoke_fail_reason"] = f"build_error:{type(exc).__name__}:{exc}"
        return record

    if run_smoke:
        record["smoke_ok"], record["smoke_fail_reason"] = _run_smoke(
            package_root, spec.golden_answer
        )
    return record


def _run_smoke(package_root: Path, golden_answer: Any) -> tuple[bool, str | None]:
    if isinstance(golden_answer, dict) and golden_answer.get("ok") is False:
        return False, f"golden_error:{golden_answer.get('error_type', 'unknown')}"
    try:
        result = Code2Env(package_root / "env_spec.json").scripted_smoke()
    except Exception as exc:  # noqa: BLE001 - smoke failures are recorded, not raised.
        return False, f"smoke_exception:{type(exc).__name__}:{exc}"
    if result.get("ok"):
        return True, None
    return False, "answer_mismatch"


def _disqualify(candidate: FunctionCandidate, *, include_side_effects: bool) -> str | None:
    """Return a skip reason for candidates that cannot be auto-driven, else None."""

    if "." in candidate.qualname:
        return "not_module_level"
    if "requires_instance" in candidate.risk_flags:
        return "requires_instance"
    if not include_side_effects and "possible_side_effect" in candidate.risk_flags:
        return "possible_side_effect"
    return None


def synthesize_fixture(func_node: ast.FunctionDef | ast.AsyncFunctionDef | None) -> dict[str, Any]:
    """Synthesise a JSON fixture for ``func_node`` from its signature.

    Returns ``{"ok", "strategy", "value": {"args", "kwargs"}, "reason"}``. Functions
    with no required parameters use the ``empty_signature`` strategy; functions whose
    required parameters all carry simple supported annotations use ``typed_signature``.
    Anything else (an untyped or unsupported required parameter) is reported as not
    synthesisable with a ``reason`` so the caller can skip it.
    """

    if func_node is None:
        return _fixture_skip("function_node_not_found")

    args = func_node.args
    positional = list(args.posonlyargs) + list(args.args)
    num_pos_defaults = len(args.defaults)
    required_positional = positional[: len(positional) - num_pos_defaults] if num_pos_defaults else positional
    required_kwonly = [
        arg for arg, default in zip(args.kwonlyargs, args.kw_defaults) if default is None
    ]

    if not required_positional and not required_kwonly:
        return {
            "ok": True,
            "strategy": "empty_signature",
            "value": {"args": [], "kwargs": {}},
            "reason": None,
        }

    arg_values: list[Any] = []
    for arg in required_positional:
        ok, value = _annotation_value(arg.annotation)
        if not ok:
            return _fixture_skip(_param_skip_reason(arg))
        arg_values.append(value)

    kwarg_values: dict[str, Any] = {}
    for arg in required_kwonly:
        ok, value = _annotation_value(arg.annotation)
        if not ok:
            return _fixture_skip(_param_skip_reason(arg))
        kwarg_values[arg.arg] = value

    return {
        "ok": True,
        "strategy": "typed_signature",
        "value": {"args": arg_values, "kwargs": kwarg_values},
        "reason": None,
    }


def _fixture_skip(reason: str) -> dict[str, Any]:
    return {"ok": False, "strategy": None, "value": {"args": [], "kwargs": {}}, "reason": reason}


def _param_skip_reason(arg: ast.arg) -> str:
    if arg.annotation is None:
        return f"untyped_required_param:{arg.arg}"
    return f"unsupported_param_type:{arg.arg}:{_annotation_name(arg.annotation)}"


def _annotation_value(annotation: ast.expr | None) -> tuple[bool, Any]:
    """Map a parameter annotation AST node to a synthesised JSON value."""

    if annotation is None:
        return False, None
    if isinstance(annotation, ast.Constant):
        if annotation.value is None:
            return True, None
        if isinstance(annotation.value, str):
            # Forward-ref / PEP 563 string annotation: re-parse and recurse.
            try:
                inner = ast.parse(annotation.value, mode="eval").body
            except SyntaxError:
                return False, None
            return _annotation_value(inner)
        return False, None
    name = _annotation_name(annotation)
    if name is None:
        return False, None
    if name in _NONE_TYPES:
        return True, None
    if name in _LIST_TYPES:
        return True, []
    if name in _DICT_TYPES:
        return True, {}
    if name in _SCALAR_VALUES:
        return True, _SCALAR_VALUES[name]
    return False, None


def _annotation_name(annotation: ast.expr) -> str | None:
    """Best-effort base name of an annotation node (``List[int]`` -> ``List``)."""

    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Subscript):
        return _annotation_name(annotation.value)
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        # PEP 563 string annotation, e.g. "int" or "List[int]".
        return annotation.value.split("[", 1)[0].strip().rsplit(".", 1)[-1]
    return None


def _function_node(
    snapshot: RepoSnapshot,
    candidate: FunctionCandidate,
    tree_cache: dict[str, ast.Module | None],
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Locate the module-level function node backing ``candidate``."""

    if candidate.file not in tree_cache:
        path = Path(snapshot.path) / candidate.file
        try:
            tree_cache[candidate.file] = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            tree_cache[candidate.file] = None
    tree = tree_cache[candidate.file]
    if tree is None:
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == candidate.qualname and node.lineno == candidate.lineno:
                return node
    return None
