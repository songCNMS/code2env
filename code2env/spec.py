from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from code2env.determinism import classify_determinism
from code2env.envdeps import golden_status_for
from code2env.executor import run_symbol_subprocess
from code2env.indexer import find_candidate, index_repo, links_for_candidate
from code2env.models import EnvSpec, FunctionCandidate, RepoSnapshot, TestLink, ToolSpec
from code2env.rich_fixtures import fixture_component_descriptor


def draft_env_spec(
    snapshot: RepoSnapshot,
    *,
    symbol: str,
    fixture: dict[str, Any] | None = None,
    env_id: str | None = None,
    compute_golden: bool = True,
    candidates: list[FunctionCandidate] | None = None,
    python_executable: str | None = None,
    requirements: list[str] | None = None,
    deps_status: str | None = None,
    determinism_runs: int = 1,
) -> EnvSpec:
    # ``candidates`` lets batch callers reuse a single index_repo() pass across many
    # symbols in the same snapshot instead of re-indexing per draft.
    # ``python_executable`` is the repo venv interpreter (task030): it computes the
    # golden answer with the repo's runtime deps installed and is persisted so the
    # runtime executes call_entrypoint with the same interpreter.
    if candidates is None:
        candidates = index_repo(snapshot)
    candidate = find_candidate(candidates, symbol)
    normalized_fixture = _normalize_fixture(fixture)
    test_links = links_for_candidate(snapshot, candidate)
    provenance = _build_provenance(candidate, test_links)
    source = {
        "repo": snapshot.source,
        "source_root": snapshot.path,
        "commit": snapshot.commit,
        "entrypoint": candidate.symbol,
        "file": candidate.file,
        "line_start": candidate.lineno,
        "line_end": candidate.end_lineno,
        "license_file": snapshot.license_file,
    }
    runtime_environment = _runtime_environment()
    spec = EnvSpec(
        id=env_id or _default_env_id(candidate, snapshot),
        version=1,
        source=source,
        task=_task_from_candidate(candidate),
        tools=_tools_from_candidate(candidate, candidates),
        runtime={
            "max_steps": 8,
            "timeout_seconds": 3,
            "sandbox": {
                "network": False,
                "subprocess": "disabled",
                "filesystem": "package_or_snapshot_readonly",
            },
            "python_executable": python_executable,
            "requirements": requirements or [],
            "deps_status": deps_status,
            "environment": runtime_environment,
        },
        reward={
            "type": "exact_match",
            "oracle": "pinned_source_function",
            "weights": {
                "schema_validity": 0.05,
                "process_progress": 0.20,
                "final_correctness": 0.65,
                "efficiency": 0.05,
                "safety": 0.05,
            },
        },
        fixture=normalized_fixture,
        golden_answer=None,
        provenance=provenance,
    )
    if compute_golden:
        def _run_golden() -> dict[str, Any]:
            return run_symbol_subprocess(
                snapshot.path,
                candidate.symbol,
                list(normalized_fixture["args"]),
                dict(normalized_fixture["kwargs"]),
                disable_network=True,
                disable_subprocess=True,
                python_executable=python_executable,
                extra_env=runtime_environment,
            )

        spec.golden_answer = _run_golden()
        golden_status = golden_status_for(spec.golden_answer)
        spec.provenance["golden_status"] = golden_status
        # Determinism gate (task038): only meaningful for a real golden value. For
        # weak_oracle goldens the env is already excluded by golden_status, so leave
        # determinism null rather than mislabel an exception traceback as nondeterministic.
        if golden_status == "real_value":
            repeats = [_run_golden() for _ in range(max(0, determinism_runs - 1))]
            spec.provenance["determinism"] = classify_determinism(spec.golden_answer, repeats)
        else:
            spec.provenance["determinism"] = None
    else:
        spec.provenance["golden_status"] = "pending_golden"
        spec.provenance["determinism"] = None
    return spec


def _runtime_environment() -> dict[str, str]:
    """Persist narrowly scoped runtime env needed to replay package goldens.

    Pinned source checkouts can rely on build-tool metadata env vars during golden
    generation. Keep this allowlist small so generated packages do not capture
    arbitrary local secrets or machine-specific process state.
    """

    names = ("SETUPTOOLS_SCM_PRETEND_VERSION",)
    return {name: os.environ[name] for name in names if os.environ.get(name)}


_TEST_LINK_KINDS = {"test": "test_link", "fixture": "fixture", "golden": "golden"}


def _build_provenance(
    candidate: FunctionCandidate, test_links: list[TestLink]
) -> dict[str, Any]:
    """Assemble provenance with >=2 diverse task_sources (PRD 7.2 / 469).

    Always grounds the task in a ``source_span`` plus a ``signature`` source, then
    appends ``test_link`` / ``fixture`` / ``golden`` sources discovered by the
    TestLinkIndex. When no test artifacts are found the spec is still valid but
    flagged as degraded so downstream review knows the oracle priority dropped to
    signature-level evidence.
    """

    task_sources: list[dict[str, Any]] = [
        {
            "kind": "source_span",
            "path": candidate.file,
            "symbol": candidate.symbol,
            "line_start": candidate.lineno,
            "line_end": candidate.end_lineno,
        },
        {
            "kind": "signature",
            "path": candidate.file,
            "symbol": candidate.symbol,
            "args": candidate.args,
            "defaults_count": candidate.defaults_count,
            "has_docstring": bool(candidate.docstring),
            "line_start": candidate.lineno,
            "line_end": candidate.end_lineno,
        },
    ]
    for link in test_links:
        task_sources.append(
            {
                "kind": _TEST_LINK_KINDS.get(link.target_kind, "test_link"),
                "path": link.path,
                "target": link.target,
                "line_start": link.lineno,
                "line_end": link.end_lineno,
                "evidence": link.evidence,
                "confidence": link.confidence,
            }
        )

    has_tests = bool(test_links)
    provenance: dict[str, Any] = {
        "task_sources": task_sources,
        "test_link_status": "linked" if has_tests else "no_test_links_found",
        "test_link_count": len(test_links),
        "metrics": candidate.metrics,
        "risk_flags": candidate.risk_flags,
        "helper_candidates": candidate.helper_candidates,
    }
    if not has_tests:
        provenance["degradation"] = (
            "No test/fixture/golden artifacts linked to this candidate; task grounding "
            "falls back to source_span + signature evidence only (oracle priority dropped "
            "from test assertions to function signature). Consider adding tests for a "
            "stronger oracle."
        )
    return provenance


def _normalize_fixture(fixture: dict[str, Any] | None) -> dict[str, Any]:
    fixture = dict(fixture or {})
    args = fixture.get("args", [])
    kwargs = fixture.get("kwargs", {})
    if not isinstance(args, list):
        raise ValueError("fixture args must be a list")
    if not isinstance(kwargs, dict):
        raise ValueError("fixture kwargs must be an object")
    return {"args": args, "kwargs": kwargs}


def _default_env_id(candidate: FunctionCandidate, snapshot: RepoSnapshot) -> str:
    digest = hashlib.sha256(
        f"{snapshot.source}:{snapshot.commit}:{candidate.symbol}".encode("utf-8")
    ).hexdigest()[:8]
    clean_symbol = re.sub(r"[^a-zA-Z0-9_.-]+", ".", candidate.symbol.replace(":", "."))
    return f"code2env.{clean_symbol}.{digest}.v1".lower()


def _task_from_candidate(candidate: FunctionCandidate) -> dict[str, Any]:
    title = f"Run and match `{candidate.symbol}`"
    doc = candidate.docstring.splitlines()[0] if candidate.docstring else ""
    instruction = (
        f"Use the available tools to execute `{candidate.symbol}` with the provided fixture "
        "and submit the exact result payload that matches the pinned source implementation."
    )
    if doc:
        instruction += f" Source docstring summary: {doc}"
    return {
        "title": title,
        "instruction": instruction,
        "entrypoint": candidate.symbol,
        "success_criteria": [
            "Submitted answer exactly matches the golden answer generated by the pinned source function.",
            "Tool arguments are valid JSON objects.",
            "The episode finishes within the step budget.",
        ],
        "constraints": [
            "Do not perform real network operations from generated tools.",
            "Only call tools exposed by this environment.",
        ],
    }


# Total tools per env are kept inside the PRD 7.5 [3, 8] window. Four base tools
# (inspect_task, inspect_state, call_entrypoint, submit_answer) always exist; with
# the backward-compatible call_helper that leaves room for this many named,
# semantic direct-callee tools before hitting the upper bound of 8.
MAX_SEMANTIC_HELPER_TOOLS = 3
_NETWORK_SIDE_EFFECT_CALLS = {
    "Request",
    "urlopen",
    "urlretrieve",
    "requests",
}
_NETWORK_SIDE_EFFECT_PREFIXES = (
    "requests.",
    "urllib.request.",
    "urllib3.",
    "http.client.",
)
_TOOL_RESULT_SCHEMA = {
    "type": "object",
    "required": ["ok"],
    "properties": {
        "ok": {"type": "boolean"},
        "value": {"type": "object"},
        "error_type": {"type": "string"},
        "error_message": {"type": "string"},
    },
}
_ARGS_KWARGS_SCHEMA = {
    "type": "object",
    "properties": {"args": {"type": "array"}, "kwargs": {"type": "object"}},
    "additionalProperties": False,
}


def _tools_from_candidate(
    candidate: FunctionCandidate, candidates: list[FunctionCandidate] | None = None
) -> list[ToolSpec]:
    by_symbol = {item.symbol: item for item in (candidates or [])}
    source_span = {
        "path": candidate.file,
        "symbol": candidate.symbol,
        "line_start": candidate.lineno,
        "line_end": candidate.end_lineno,
    }
    pure_helpers, side_effect_helpers = _partition_helpers(candidate, by_symbol)
    helper_executability = trace_helper_executability_for_candidate(candidate, candidates)
    side_effect_reasons = _helper_side_effect_reasons(candidate, by_symbol)

    tools: list[ToolSpec] = [
        ToolSpec(
            name="inspect_task",
            description="Return the task, fixture, source metadata, and available helper names.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema={"type": "object"},
            side_effects="none",
            provenance={
                "kind": "state_inspector",
                "backing": {"kind": "env_metadata"},
                "reads": ["task", "fixture", "source", "helpers"],
            },
        ),
        # Mandatory read-only state inspector (PRD 7.5: avoid blind tool calls).
        ToolSpec(
            name="inspect_state",
            description="Read-only snapshot of the current episode state (step, phase, last result, submission).",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema={"type": "object"},
            side_effects="none",
            provenance={
                "kind": "state_inspector",
                "backing": {"kind": "runtime_state"},
                "reads": ["step", "phase", "last_tool_result", "submitted_answer", "available_tools"],
            },
        ),
        ToolSpec(
            name="call_entrypoint",
            description="Execute the selected source entrypoint with JSON args and kwargs.",
            input_schema=_ARGS_KWARGS_SCHEMA,
            output_schema=_TOOL_RESULT_SCHEMA,
            side_effects="sandboxed" if "possible_side_effect" in candidate.risk_flags else "none",
            timeout_ms=3000,
            provenance={
                "kind": "entrypoint",
                "backing": {"kind": "function", "symbol": candidate.symbol},
                "source_span": source_span,
                "steps": _entrypoint_steps(candidate),
                # Side-effecting helpers are not exposed as direct tools; recorded here
                # so reviewers can route them through a sandbox adapter later.
                "sandboxed_side_effect_helpers": side_effect_helpers,
                "sandboxed_side_effect_helper_reasons": side_effect_reasons,
                "helper_executability": helper_executability,
            },
        ),
    ]

    for helper in pure_helpers[:MAX_SEMANTIC_HELPER_TOOLS]:
        tools.append(_semantic_helper_tool(candidate, helper, by_symbol))

    if candidate.helper_candidates:
        tools.append(
            ToolSpec(
                name="call_helper",
                description="Execute an allowed top-level helper from the same module (sandboxed adapter).",
                input_schema={
                    "type": "object",
                    "required": ["helper"],
                    "properties": {
                        "helper": {"type": "string", "enum": candidate.helper_candidates},
                        "args": {"type": "array"},
                        "kwargs": {"type": "object"},
                    },
                    "additionalProperties": False,
                },
                output_schema=_TOOL_RESULT_SCHEMA,
                side_effects="sandboxed",
                timeout_ms=3000,
                provenance={
                    "kind": "wrapper",
                    "backing": {"kind": "module_helpers", "module": candidate.module},
                    "helpers": candidate.helper_candidates,
                },
            )
        )

    tools.append(
        ToolSpec(
            name="submit_answer",
            description="Submit the final serialized answer payload for exact-match scoring.",
            input_schema={
                "type": "object",
                "required": ["answer"],
                "properties": {"answer": {"type": "object"}},
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
            side_effects="state",
            provenance={
                "kind": "submit",
                "backing": {"kind": "scorer", "oracle": "pinned_source_function"},
                "writes": ["submitted_answer", "score"],
            },
        )
    )
    return tools


def semantic_helpers_for_candidate(
    candidate: FunctionCandidate, candidates: list[FunctionCandidate] | None = None
) -> list[str]:
    """Return helper names that final ToolSpec generation exposes as call_<helper>."""

    return list(trace_helper_executability_for_candidate(candidate, candidates)["semantic_helpers"])


def trace_helper_executability_for_candidate(
    candidate: FunctionCandidate,
    candidates: list[FunctionCandidate] | None = None,
    *,
    fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return auditable strict trace helper executability metadata.

    ``semantic_helpers`` are the dedicated side-effect-safe helpers that spec
    generation exposes as ``call_<helper>``. ``executable_semantic_helpers`` is
    fixture-aware when a fixture is supplied and excludes helpers whose required
    arguments cannot be mapped without model fabrication.
    """

    by_symbol = {item.symbol: item for item in (candidates or [])}
    candidate_semantic_helpers = _candidate_semantic_helpers(candidate, by_symbol)
    side_effect_reasons = _helper_side_effect_reasons(candidate, by_symbol)
    semantic_helpers = [
        helper for helper in candidate_semantic_helpers if helper not in side_effect_reasons
    ][:MAX_SEMANTIC_HELPER_TOOLS]

    skipped: list[dict[str, Any]] = []
    for helper_index, helper in enumerate(candidate_semantic_helpers):
        reason = side_effect_reasons.get(helper)
        if reason:
            item: dict[str, Any] = {"helper": helper, "tool": f"call_{helper}", "reason": reason}
            argument_reasons = _helper_argument_skip_reasons(
                candidate,
                helper,
                by_symbol,
                fixture=fixture,
                helper_index=helper_index,
            )
            if argument_reasons:
                item["additional_reasons"] = argument_reasons
            skipped.append(item)

    executable_helpers: list[str] = []
    for helper_index, helper in enumerate(semantic_helpers):
        argument_reasons = _helper_argument_skip_reasons(
            candidate,
            helper,
            by_symbol,
            fixture=fixture,
            helper_index=helper_index,
        )
        if argument_reasons:
            skipped.append(
                {
                    "helper": helper,
                    "tool": f"call_{helper}",
                    "reason": argument_reasons[0],
                    "additional_reasons": argument_reasons,
                }
            )
        else:
            executable_helpers.append(helper)

    return {
        "candidate_semantic_helper_count": len(candidate_semantic_helpers),
        "candidate_semantic_helpers": candidate_semantic_helpers,
        "dedicated_semantic_helper_count": len(semantic_helpers),
        "semantic_helpers": semantic_helpers,
        "executable_semantic_helper_count": len(executable_helpers),
        "executable_semantic_helpers": executable_helpers,
        "skipped_helper_count": len(skipped),
        "skipped_helper_count_by_reason": _reason_counts(skipped),
        "skipped_helpers": skipped,
    }


def _partition_helpers(
    candidate: FunctionCandidate, by_symbol: dict[str, FunctionCandidate]
) -> tuple[list[str], list[str]]:
    """Split direct callees into pure helpers (safe to expose) and side-effecting ones.

    Pure helpers are ordered by how many main-function steps invoke them so the most
    structurally relevant callees win the limited semantic-tool slots.
    """

    pure: list[str] = []
    side_effecting: list[str] = []
    side_effect_reasons = _helper_side_effect_reasons(candidate, by_symbol)
    for helper in candidate.helper_candidates:
        if helper in side_effect_reasons:
            side_effecting.append(helper)
        else:
            pure.append(helper)
    pure.sort(key=lambda name: (-_helper_step_count(candidate, name), name))
    return pure, side_effecting


def _candidate_semantic_helpers(
    candidate: FunctionCandidate,
    by_symbol: dict[str, FunctionCandidate],
) -> list[str]:
    """Helpers considered for strict trace before transitive filtering.

    Direct side-effect helpers were already excluded from legacy dedicated tools.
    Keeping them out here makes the strict trace denominator match the helpers
    that could otherwise have become direct ``call_<helper>`` tools.
    """

    direct_side_effect_reasons = _direct_side_effect_reasons(candidate, by_symbol)
    helpers = [
        helper
        for helper in candidate.helper_candidates
        if helper not in direct_side_effect_reasons
    ]
    helpers.sort(key=lambda name: (-_helper_step_count(candidate, name), name))
    return helpers[:MAX_SEMANTIC_HELPER_TOOLS]


def _direct_side_effect_reasons(
    candidate: FunctionCandidate,
    by_symbol: dict[str, FunctionCandidate],
) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for helper in candidate.helper_candidates:
        helper_candidate = by_symbol.get(f"{candidate.module}:{helper}")
        if helper_candidate is None:
            continue
        reason = _direct_helper_side_effect_reason(helper_candidate)
        if reason:
            reasons[helper] = reason
    return reasons


def _helper_side_effect_reasons(
    candidate: FunctionCandidate,
    by_symbol: dict[str, FunctionCandidate],
) -> dict[str, str]:
    cache: dict[str, str | None] = {}
    reasons: dict[str, str] = {}
    for helper in candidate.helper_candidates:
        reason = _helper_side_effect_reason(candidate.module, helper, by_symbol, cache, [])
        if reason:
            reasons[helper] = reason
    return reasons


def _helper_side_effect_reason(
    module: str,
    helper: str,
    by_symbol: dict[str, FunctionCandidate],
    cache: dict[str, str | None],
    stack: list[str],
) -> str | None:
    if helper in cache:
        return cache[helper]
    if helper in stack:
        return None

    helper_candidate = by_symbol.get(f"{module}:{helper}")
    if helper_candidate is None:
        cache[helper] = None
        return None

    direct_reason = _direct_helper_side_effect_reason(helper_candidate)
    if direct_reason:
        cache[helper] = direct_reason
        return direct_reason

    stack.append(helper)
    try:
        for call in helper_candidate.calls:
            callee = _same_module_helper_name(module, call, by_symbol)
            if callee is None:
                continue
            callee_reason = _helper_side_effect_reason(
                module, callee, by_symbol, cache, stack
            )
            if callee_reason:
                reason = f"transitive_side_effect:{callee}:{_reason_family(callee_reason)}"
                cache[helper] = reason
                return reason
    finally:
        stack.pop()

    cache[helper] = None
    return None


def _direct_helper_side_effect_reason(candidate: FunctionCandidate) -> str | None:
    if any(_call_is_network_side_effect(call) for call in candidate.calls):
        return "network_sandboxed"
    if "possible_side_effect" in candidate.risk_flags:
        return "side_effect_sandboxed"
    return None


def _call_is_network_side_effect(call: str) -> bool:
    name = call.strip()
    if not name:
        return False
    if name in _NETWORK_SIDE_EFFECT_CALLS:
        return True
    return name.startswith(_NETWORK_SIDE_EFFECT_PREFIXES)


def _same_module_helper_name(
    module: str, call: str, by_symbol: dict[str, FunctionCandidate]
) -> str | None:
    if f"{module}:{call}" in by_symbol:
        return call
    if "." in call:
        tail = call.rsplit(".", 1)[-1]
        if f"{module}:{tail}" in by_symbol:
            return tail
    return None


def _helper_argument_skip_reasons(
    candidate: FunctionCandidate,
    helper: str,
    by_symbol: dict[str, FunctionCandidate],
    *,
    fixture: dict[str, Any] | None,
    helper_index: int,
) -> list[str]:
    if fixture is None:
        return []
    helper_candidate = by_symbol.get(f"{candidate.module}:{helper}")
    if helper_candidate is None:
        return ["argument_unavailable:helper_signature"]

    required_positional = _required_positional_params(helper_candidate)
    if not required_positional:
        return []

    fixture_args = fixture.get("args", []) if isinstance(fixture, dict) else []
    fixture_kwargs = fixture.get("kwargs", {}) if isinstance(fixture, dict) else {}
    fixture_args = fixture_args if isinstance(fixture_args, list) else []
    fixture_kwargs = fixture_kwargs if isinstance(fixture_kwargs, dict) else {}

    reasons: list[str] = []
    for param in required_positional:
        if _fixture_has_value_for_param(param, fixture_args, fixture_kwargs, candidate.args):
            continue
        if len(required_positional) == 1 and _fixture_has_helper_index_value(
            helper_index, fixture_args
        ):
            continue
        reasons.append(f"argument_unavailable:{param}")
    return reasons


def _required_positional_params(candidate: FunctionCandidate) -> list[str]:
    if candidate.defaults_count:
        return candidate.args[: len(candidate.args) - candidate.defaults_count]
    return list(candidate.args)


def _fixture_has_value_for_param(
    param: str,
    fixture_args: list[Any],
    fixture_kwargs: dict[str, Any],
    entrypoint_positional: list[str],
) -> bool:
    if param in fixture_kwargs:
        return True
    if param not in entrypoint_positional:
        return False
    index = entrypoint_positional.index(param)
    return index < len(fixture_args)


def _fixture_has_helper_index_value(helper_index: int, fixture_args: list[Any]) -> bool:
    if len(fixture_args) > 1:
        return helper_index < len(fixture_args)
    if len(fixture_args) != 1:
        return False
    found, _, _ = fixture_component_descriptor(fixture_args[0], helper_index)
    return found


def _reason_counts(skipped: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in skipped:
        for reason in _all_skip_reasons(item):
            family = _reason_family(reason)
            counts[family] = counts.get(family, 0) + 1
    return counts


def _all_skip_reasons(item: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    reason = item.get("reason")
    if isinstance(reason, str):
        reasons.append(reason)
    additional = item.get("additional_reasons")
    if isinstance(additional, list):
        reasons.extend(reason for reason in additional if isinstance(reason, str))
    return reasons or ["unknown"]


def _reason_family(reason: str) -> str:
    if reason.startswith("transitive_side_effect:"):
        return "transitive_side_effect"
    if reason.startswith("argument_unavailable:"):
        return "argument_unavailable"
    return reason


def _helper_step_count(candidate: FunctionCandidate, helper: str) -> int:
    return sum(1 for step in candidate.steps if helper in step.get("callees", []))


def _entrypoint_steps(candidate: FunctionCandidate) -> list[dict[str, Any]]:
    return [
        {
            "index": step.get("index"),
            "kind": step.get("kind"),
            "line_start": step.get("line_start"),
            "line_end": step.get("line_end"),
            "summary": step.get("summary"),
            "callees": step.get("callees", []),
        }
        for step in candidate.steps
    ]


def _helper_step_spans(candidate: FunctionCandidate, helper: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": step.get("kind"),
            "line_start": step.get("line_start"),
            "line_end": step.get("line_end"),
            "summary": step.get("summary"),
        }
        for step in candidate.steps
        if helper in step.get("callees", [])
    ]


def _semantic_helper_tool(
    candidate: FunctionCandidate, helper: str, by_symbol: dict[str, FunctionCandidate]
) -> ToolSpec:
    helper_symbol = f"{candidate.module}:{helper}"
    helper_candidate = by_symbol.get(helper_symbol)
    if helper_candidate is not None:
        helper_span: dict[str, Any] = {
            "path": helper_candidate.file,
            "symbol": helper_symbol,
            "line_start": helper_candidate.lineno,
            "line_end": helper_candidate.end_lineno,
        }
        doc = helper_candidate.docstring.splitlines()[0] if helper_candidate.docstring else ""
    else:
        helper_span = {"symbol": helper_symbol}
        doc = ""
    description = f"Execute the `{helper}` step of `{candidate.qualname}` with JSON args and kwargs."
    if doc:
        description += f" {doc}"
    return ToolSpec(
        name=f"call_{helper}",
        description=description,
        input_schema=_ARGS_KWARGS_SCHEMA,
        output_schema=_TOOL_RESULT_SCHEMA,
        side_effects="none",
        timeout_ms=3000,
        provenance={
            "kind": "wrapper",
            "backing": {"kind": "function", "symbol": helper_symbol},
            "source_span": helper_span,
            # Main-function key steps that invoke this direct callee.
            "entrypoint_steps": _helper_step_spans(candidate, helper),
        },
    )


def source_root_for_spec(spec: EnvSpec, package_root: str | Path | None = None) -> Path:
    raw_root = Path(str(spec.source["source_root"]))
    if raw_root.is_absolute():
        return raw_root
    if package_root is None:
        return raw_root.resolve()
    return (Path(package_root).resolve() / raw_root).resolve()
