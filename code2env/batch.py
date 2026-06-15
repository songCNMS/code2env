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
        "min_semantic_helpers": int,
        "semantic_gate_passed": int,
        "skipped_insufficient_semantic_helpers": int,
        "skipped_no_fixture": int,
        "by_repo": {repo: {"build_ok": int, "smoke_ok": int}}
      },
      "envs": [
        {
          "env_id", "repo", "symbol", "file", "line_start", "line_end",
          "fixture": {"ok", "strategy", "value": {"args", "kwargs"}, "reason"},
          "draft_ok", "build_ok", "smoke_ok", "smoke_fail_reason",
          "semantic_helper_count", "semantic_helpers", "spec_path", "package_path"
        }, ...
      ],
      "skipped": [{"symbol", "repo", "reason"}, ...]
    }
"""

from __future__ import annotations

import ast
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from code2env.builder import build_env_package
from code2env.determinism import is_usable
from code2env.envdeps import prepare_repo_env
from code2env.indexer import index_repo
from code2env.ingest import ingest_repo
from code2env.jsonio import write_json
from code2env.models import FunctionCandidate, RepoSnapshot
from code2env.rich_fixtures import (
    dataframe_descriptor,
    numpy_array_descriptor,
    rich_fixture_audit,
    series_descriptor,
    timestamp_descriptor,
    torch_tensor_descriptor,
)
from code2env.runtime import Code2Env
from code2env.spec import (
    MAX_SEMANTIC_HELPER_TOOLS,
    draft_env_spec,
    semantic_helpers_for_candidate,
)

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
    install_deps: bool = True,
    venv_cache_dir: str | Path | None = None,
    determinism_runs: int = 3,
    min_semantic_helpers: int = 0,
    require_real_value: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Generate EnvPackages across ``repos`` and return the manifest dict.

    Stops once ``target_count`` successful builds are reached (counted globally),
    iterating repos in order and candidates by descending static score. For each
    repo a venv is prepared once (task030) so golden answers and rollout
    call_entrypoint run with the repo's runtime dependencies installed.
    """

    _validate_min_semantic_helpers(min_semantic_helpers)

    output_root = Path(output_dir).expanduser().resolve()
    specs_dir = output_root / "specs"
    packages_dir = output_root / "packages"
    specs_dir.mkdir(parents=True, exist_ok=True)
    packages_dir.mkdir(parents=True, exist_ok=True)

    envs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    repo_labels: list[str] = []
    by_repo: dict[str, dict[str, int]] = {}
    repo_deps: dict[str, dict[str, Any]] = {}
    candidates_scanned = 0
    build_ok_total = 0
    accepted_total = 0
    semantic_gate_passed = 0
    skipped_insufficient_semantic_helpers = 0

    for repo in repos:
        snapshot = ingest_repo(repo, cache_dir=cache_dir)
        repo_label = snapshot.source
        repo_labels.append(repo_label)
        by_repo.setdefault(
            repo_label,
            {
                "build_ok": 0,
                "smoke_ok": 0,
                "real_value": 0,
                "deterministic": 0,
                "strict_usable": 0,
                "weak_oracle": 0,
                "usable": 0,
                "nondeterministic": 0,
                "semantic_gate_passed": 0,
                "skipped_insufficient_semantic_helpers": 0,
            },
        )
        # One venv per repo: install runtime deps so golden answers are real values.
        repo_env = prepare_repo_env(
            snapshot, cache_dir=venv_cache_dir, install=install_deps
        )
        repo_deps[repo_label] = {
            "deps_status": repo_env["deps_status"],
            "python": repo_env["python"],
            "requirements": repo_env["requirements"],
            "installed": repo_env["installed"],
            "failed": repo_env["failed"],
            "reason": repo_env["reason"],
        }
        by_repo[repo_label]["deps_status"] = repo_env["deps_status"]
        candidates = index_repo(snapshot)
        candidates_scanned += len(candidates)
        tree_cache: dict[str, ast.Module | None] = {}
        repo_build_ok = 0

        for candidate in candidates:
            if accepted_total >= target_count:
                break
            if per_repo_limit is not None and repo_build_ok >= per_repo_limit:
                break

            skip_reason = _disqualify(candidate, include_side_effects=include_side_effects)
            if skip_reason:
                skipped.append({"symbol": candidate.symbol, "repo": repo_label, "reason": skip_reason})
                continue

            semantic_helpers = semantic_helpers_for_candidate(candidate, candidates)
            semantic_helper_count = len(semantic_helpers)
            if semantic_helper_count < min_semantic_helpers:
                skipped_insufficient_semantic_helpers += 1
                by_repo[repo_label]["skipped_insufficient_semantic_helpers"] += 1
                skipped.append(
                    {
                        "symbol": candidate.symbol,
                        "repo": repo_label,
                        "reason": (
                            f"insufficient_semantic_helpers:"
                            f"{semantic_helper_count}/{min_semantic_helpers}"
                        ),
                        "semantic_helper_count": semantic_helper_count,
                        "semantic_helpers": semantic_helpers,
                    }
                )
                continue

            semantic_gate_passed += 1
            by_repo[repo_label]["semantic_gate_passed"] += 1

            unsafe_reason = _rich_fixture_unsafe_reason(candidate)
            if unsafe_reason:
                skipped.append(
                    {
                        "symbol": candidate.symbol,
                        "repo": repo_label,
                        "reason": unsafe_reason,
                        "semantic_helper_count": semantic_helper_count,
                        "semantic_helpers": semantic_helpers,
                    }
                )
                continue

            func_node = _function_node(snapshot, candidate, tree_cache)
            fixture = synthesize_fixture(func_node, candidate=candidate)
            if not fixture["ok"]:
                skipped.append(
                    {
                        "symbol": candidate.symbol,
                        "repo": repo_label,
                        "reason": fixture["reason"],
                        "semantic_helper_count": semantic_helper_count,
                        "semantic_helpers": semantic_helpers,
                    }
                )
                continue

            env_record = _generate_one(
                snapshot=snapshot,
                candidate=candidate,
                candidates=candidates,
                fixture=fixture,
                repo_label=repo_label,
                repo_env=repo_env,
                specs_dir=specs_dir,
                packages_dir=packages_dir,
                run_smoke=run_smoke,
                determinism_runs=determinism_runs,
                semantic_helpers=semantic_helpers,
            )
            envs.append(env_record)
            if env_record["build_ok"]:
                build_ok_total += 1
                repo_build_ok += 1
                by_repo[repo_label]["build_ok"] += 1
            if env_record["smoke_ok"]:
                by_repo[repo_label]["smoke_ok"] += 1
            if env_record["golden_status"] == "real_value":
                by_repo[repo_label]["real_value"] += 1
            elif env_record["golden_status"]:
                by_repo[repo_label]["weak_oracle"] += 1
            if env_record["determinism"] == "deterministic":
                by_repo[repo_label]["deterministic"] += 1
            if is_usable(env_record["golden_status"], env_record["determinism"]):
                by_repo[repo_label]["usable"] += 1
                by_repo[repo_label]["strict_usable"] += 1
            elif env_record["determinism"] and env_record["determinism"] != "deterministic":
                by_repo[repo_label]["nondeterministic"] += 1
            if require_real_value and env_record["strict_rejection_reason"]:
                skipped.append(_strict_rejection_skip(env_record, repo_label))
            if env_record["strict_usable"] or (env_record["build_ok"] and not require_real_value):
                accepted_total += 1

        if accepted_total >= target_count:
            break

    real_value = sum(1 for env in envs if env["golden_status"] == "real_value")
    deterministic = sum(1 for env in envs if env["determinism"] == "deterministic")
    strict_usable = sum(1 for env in envs if env["strict_usable"])
    summary = {
        "candidates_scanned": candidates_scanned,
        "draft_ok": sum(1 for env in envs if env["draft_ok"]),
        "build_ok": sum(1 for env in envs if env["build_ok"]),
        "smoke_ok": sum(1 for env in envs if env["smoke_ok"]),
        "skipped_no_fixture": len(skipped),
        # task030: real_value envs have a real golden; weak_oracle excluded & listed apart.
        "real_value": real_value,
        "deterministic": deterministic,
        "strict_usable": strict_usable,
        "weak_oracle": sum(
            1 for env in envs if env["golden_status"] and env["golden_status"] != "real_value"
        ),
        # task038: the qualified/usable set is real_value AND deterministic; nondeterministic
        # envs are excluded from the correctness denominator and reported separately.
        "usable": sum(1 for env in envs if is_usable(env["golden_status"], env["determinism"])),
        "nondeterministic": sum(
            1
            for env in envs
            if env["determinism"] and env["determinism"] != "deterministic"
        ),
        "require_real_value": require_real_value,
        "min_semantic_helpers": min_semantic_helpers,
        "semantic_gate_passed": semantic_gate_passed,
        "skipped_insufficient_semantic_helpers": skipped_insufficient_semantic_helpers,
        "by_repo": by_repo,
    }
    manifest = {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "repos": repo_labels,
        "summary": summary,
        "repo_deps": repo_deps,
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
    repo_env: dict[str, Any],
    specs_dir: Path,
    packages_dir: Path,
    run_smoke: bool,
    determinism_runs: int = 3,
    semantic_helpers: list[str] | None = None,
) -> dict[str, Any]:
    semantic_helpers = list(semantic_helpers or [])
    fixture_rich_params = rich_fixture_audit(fixture["value"])
    record: dict[str, Any] = {
        "env_id": None,
        "repo": repo_label,
        "symbol": candidate.symbol,
        "file": candidate.file,
        "line_start": candidate.lineno,
        "line_end": candidate.end_lineno,
        "fixture": fixture,
        "fixture_rich_params": fixture_rich_params,
        "draft_ok": False,
        "build_ok": False,
        "smoke_ok": False,
        "smoke_fail_reason": None,
        "golden_status": None,
        "determinism": None,
        "strict_usable": False,
        "strict_rejection_reason": None,
        "golden_error_type": None,
        "golden_error_message": None,
        "semantic_helper_count": len(semantic_helpers),
        "semantic_helpers": semantic_helpers,
        "deps_status": repo_env["deps_status"],
        "deps_installed": repo_env["installed"],
        "spec_path": None,
        "package_path": None,
    }

    try:
        spec = draft_env_spec(
            snapshot,
            symbol=candidate.symbol,
            fixture=fixture["value"],
            candidates=candidates,
            python_executable=repo_env["python"],
            requirements=repo_env["requirements"],
            deps_status=repo_env["deps_status"],
            determinism_runs=determinism_runs,
        )
        record["env_id"] = spec.id
        record["draft_ok"] = True
        record["golden_status"] = spec.provenance.get("golden_status")
        record["determinism"] = spec.provenance.get("determinism")
        record["strict_usable"] = is_usable(record["golden_status"], record["determinism"])
        record["strict_rejection_reason"] = _strict_rejection_reason(
            record["golden_status"], record["determinism"]
        )
        if isinstance(spec.golden_answer, dict) and spec.golden_answer.get("ok") is False:
            record["golden_error_type"] = spec.golden_answer.get("error_type")
            record["golden_error_message"] = spec.golden_answer.get("error_message")
        spec.provenance["fixture_strategy"] = fixture.get("strategy")
        spec.provenance["fixture_rich_params"] = fixture_rich_params
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


def _strict_rejection_reason(golden_status: str | None, determinism: str | None) -> str | None:
    if is_usable(golden_status, determinism):
        return None
    if golden_status and golden_status != "real_value":
        suffix = golden_status.removeprefix("weak_oracle:")
        return f"strict_unusable:weak_oracle:{suffix}"
    if golden_status == "real_value" and determinism != "deterministic":
        return f"strict_unusable:nondeterministic:{determinism or 'unknown'}"
    return "strict_unusable:golden_unavailable"


def _strict_rejection_skip(env_record: dict[str, Any], repo_label: str) -> dict[str, Any]:
    entry = {
        "symbol": env_record["symbol"],
        "repo": repo_label,
        "reason": env_record["strict_rejection_reason"],
        "env_id": env_record["env_id"],
        "golden_status": env_record["golden_status"],
        "determinism": env_record["determinism"],
    }
    if env_record.get("golden_error_type"):
        entry["error_type"] = env_record["golden_error_type"]
    if env_record.get("golden_error_message"):
        entry["error_message"] = env_record["golden_error_message"]
    return entry


def _validate_min_semantic_helpers(value: int) -> None:
    if not isinstance(value, int):
        raise ValueError("min_semantic_helpers must be an integer")
    if value < 0 or value > MAX_SEMANTIC_HELPER_TOOLS:
        raise ValueError(
            f"min_semantic_helpers must be between 0 and {MAX_SEMANTIC_HELPER_TOOLS}: {value}"
        )


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


def _rich_fixture_unsafe_reason(candidate: FunctionCandidate) -> str | None:
    unsafe_calls = {
        "login",
        "logout",
        "query_trade_dates",
        "write_calendar_to_qlib",
        "savetxt",
        "requests.get",
        "post",
    }
    if any(call in unsafe_calls for call in candidate.calls):
        return "unsafe_rich_fixture_candidate:network_or_filesystem"
    if "write" in candidate.qualname.lower() or "collector" in candidate.qualname.lower():
        if any(call.startswith("write") or call in {"login", "query_trade_dates"} for call in candidate.calls):
            return "unsafe_rich_fixture_candidate:network_or_filesystem"
    return None


def synthesize_fixture(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef | None,
    *,
    candidate: FunctionCandidate | None = None,
) -> dict[str, Any]:
    """Synthesise a JSON fixture for ``func_node`` from its signature.

    Returns ``{"ok", "strategy", "value": {"args", "kwargs"}, "reason"}``. Functions
    with no required parameters use the ``empty_signature`` strategy; functions whose
    required parameters all carry simple supported annotations use ``typed_signature``.
    Anything else (an untyped or unsupported required parameter) is reported as not
    synthesisable with a ``reason`` so the caller can skip it.
    """

    if func_node is None:
        return _fixture_skip("function_node_not_found")

    rich_policy = _rich_fixture_policy(func_node, candidate)
    if rich_policy is not None:
        return rich_policy

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
    if name == "DataFrame":
        return True, dataframe_descriptor(
            [{"value": 1.0}],
            columns=["value"],
        )
    if name == "Series":
        return True, series_descriptor([1.0], name="value")
    if name in {"ndarray", "array"}:
        return True, numpy_array_descriptor([1.0], dtype="float64")
    if name == "Timestamp":
        return True, timestamp_descriptor("2020-01-02T00:00:00")
    return False, None


def _rich_fixture_policy(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    candidate: FunctionCandidate | None,
) -> dict[str, Any] | None:
    symbol = candidate.symbol if candidate is not None else ""
    if symbol == "simpa.utils.calculate:rotation":
        return {
            "ok": True,
            "strategy": "rich_signature:simpa_rotation_torch_angles",
            "value": {
                "args": [torch_tensor_descriptor([0.1, 0.2, 0.3], dtype="float32")],
                "kwargs": {},
            },
            "reason": None,
        }
    if symbol == "scripts.data_collector.utils:calc_adjusted_price":
        return _qlib_calc_adjusted_price_fixture()
    if symbol in {
        "qlib.contrib.model.pytorch_tra:transport_daily",
        "qlib.contrib.model.pytorch_tra:transport_sample",
    }:
        if importlib.util.find_spec("torch") is None:
            return _fixture_skip("missing_optional_dependency:torch")
    return None


def _qlib_calc_adjusted_price_fixture() -> dict[str, Any]:
    symbol = "SH000001"
    price_rows = [
        {
            "datetime": "2020-01-02 09:30:00",
            "instrument": symbol,
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": 10.0,
            "volume": 100.0,
        },
        {
            "datetime": "2020-01-02 09:31:00",
            "instrument": symbol,
            "open": 10.5,
            "high": 11.5,
            "low": 10.0,
            "close": 11.0,
            "volume": 120.0,
        },
    ]
    daily_rows = [
        {
            "datetime": "2020-01-02",
            "instrument": symbol,
            "$close": 10.0,
            "$volume": 1000.0,
        }
    ]
    return {
        "ok": True,
        "strategy": "rich_signature:qlib_calc_adjusted_price",
        "value": {
            "args": [
                dataframe_descriptor(
                    price_rows,
                    columns=["datetime", "instrument", "open", "high", "low", "close", "volume"],
                    parse_dates=["datetime"],
                ),
                dataframe_descriptor(
                    daily_rows,
                    columns=["datetime", "instrument", "$close", "$volume"],
                    index_columns=["datetime", "instrument"],
                    parse_dates=["datetime"],
                ),
                "datetime",
                "instrument",
                "1min",
            ],
            "kwargs": {"consistent_1d": False, "calc_paused": True},
        },
        "reason": None,
    }


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
