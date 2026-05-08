from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from code2env.indexer import index_repo
from code2env.jsonio import write_jsonl
from code2env.llm import CandidateLLM, normalize_llm_decision
from code2env.models import FunctionCandidate, RepoSnapshot


PROMPT_VERSION = "llm_candidate_select_v1"


@dataclass(slots=True)
class SelectionOptions:
    top_k: int = 20
    max_selected: int | None = None
    min_static_score: float | None = None
    exclude_risk_flags: list[str] | None = None
    include_rejected: bool = False
    include_source: bool = False
    max_source_chars: int = 6000
    description_language: str = "zh"


def export_llm_candidate_jsonl(
    snapshot: RepoSnapshot,
    *,
    llm: CandidateLLM,
    output_path: str | Path,
    options: SelectionOptions | None = None,
    endpoint_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    options = options or SelectionOptions()
    records: list[dict[str, Any]] = []
    selected_count = 0
    considered = 0

    for candidate in _filtered_candidates(index_repo(snapshot), options):
        considered += 1
        context = build_candidate_context(snapshot, candidate, options=options)
        try:
            raw_decision = llm.evaluate_candidate(context)
            llm_decision = normalize_llm_decision(raw_decision)
            llm_error = None
        except Exception as exc:  # noqa: BLE001 - one bad LLM call should not drop the whole export.
            llm_decision = normalize_llm_decision(
                {
                    "suitable": False,
                    "confidence": 0.0,
                    "rejection_reason": f"llm_error: {type(exc).__name__}: {exc}",
                }
            )
            llm_error = {"type": type(exc).__name__, "message": str(exc)}

        selected = bool(llm_decision["suitable"])
        if selected:
            selected_count += 1
        record = build_jsonl_record(
            snapshot,
            candidate,
            context=context,
            llm_decision=llm_decision,
            llm_model=llm.model_name,
            endpoint_metadata=endpoint_metadata,
            llm_error=llm_error,
            include_source=options.include_source,
        )
        if selected or options.include_rejected:
            records.append(record)
        if options.max_selected is not None and selected_count >= options.max_selected:
            break

    write_jsonl(output_path, records)
    return {
        "output": str(Path(output_path).resolve()),
        "considered": considered,
        "written": len(records),
        "selected": selected_count,
    }


def build_candidate_context(
    snapshot: RepoSnapshot,
    candidate: FunctionCandidate,
    *,
    options: SelectionOptions,
) -> dict[str, Any]:
    source_excerpt, truncated = load_source_excerpt(snapshot, candidate, max_chars=options.max_source_chars)
    return {
        "description_language": options.description_language,
        "prd_requirements": {
            "prefer": [
                "complex deterministic functions with clear input/output behavior",
                "functions that can be decomposed into 3-8 tools",
                "functions with useful helper calls or meaningful intermediate steps",
                "candidates that can be scored by exact match or a reliable oracle",
            ],
            "reject": [
                "trivial wrappers/getters",
                "functions requiring hard-to-create object instances",
                "uncontrolled network, database, subprocess, or filesystem side effects",
                "highly nondeterministic behavior",
            ],
        },
        "repo": {
            "source": snapshot.source,
            "commit": snapshot.commit,
            "license_file": snapshot.license_file,
        },
        "candidate": _candidate_payload(candidate),
        "source_excerpt": source_excerpt,
        "source_excerpt_truncated": truncated,
    }


def build_jsonl_record(
    snapshot: RepoSnapshot,
    candidate: FunctionCandidate,
    *,
    context: dict[str, Any],
    llm_decision: dict[str, Any],
    llm_model: str,
    endpoint_metadata: dict[str, Any] | None,
    llm_error: dict[str, str] | None,
    include_source: bool,
) -> dict[str, Any]:
    source_excerpt = context.get("source_excerpt", "")
    record: dict[str, Any] = {
        "schema_version": 1,
        "selected": bool(llm_decision["suitable"]),
        "repo": {
            "source": snapshot.source,
            "commit": snapshot.commit,
            "license_file": snapshot.license_file,
        },
        "file": candidate.file,
        "symbol": candidate.symbol,
        "module": candidate.module,
        "qualname": candidate.qualname,
        "line_start": candidate.lineno,
        "line_end": candidate.end_lineno,
        "signature": candidate_signature(candidate),
        "static": {
            "score": candidate.score,
            "metrics": candidate.metrics,
            "risk_flags": candidate.risk_flags,
            "args": candidate.args,
            "defaults_count": candidate.defaults_count,
            "docstring": candidate.docstring,
            "calls": candidate.calls,
            "helper_candidates": candidate.helper_candidates,
        },
        "llm": llm_decision,
        "provenance": {
            "source": "ast_static_analysis+llm_candidate_screening",
            "prompt_version": PROMPT_VERSION,
            "llm_model": llm_model,
            "endpoint": endpoint_metadata or {"model": llm_model},
            "source_excerpt_sha256": hashlib.sha256(source_excerpt.encode("utf-8")).hexdigest(),
            "source_excerpt_truncated": bool(context.get("source_excerpt_truncated", False)),
        },
    }
    if llm_error:
        record["llm_error"] = llm_error
    if include_source:
        record["source_excerpt"] = source_excerpt
    return record


def load_source_excerpt(
    snapshot: RepoSnapshot,
    candidate: FunctionCandidate,
    *,
    max_chars: int,
) -> tuple[str, bool]:
    source_path = Path(snapshot.path) / candidate.file
    lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, candidate.lineno)
    end = min(len(lines), candidate.end_lineno)
    excerpt = "\n".join(lines[start - 1 : end])
    if max_chars > 0 and len(excerpt) > max_chars:
        return excerpt[:max_chars], True
    return excerpt, False


def candidate_signature(candidate: FunctionCandidate) -> str:
    args = ", ".join(candidate.args)
    return f"{candidate.qualname}({args})"


def _filtered_candidates(
    candidates: Iterable[FunctionCandidate],
    options: SelectionOptions,
) -> Iterable[FunctionCandidate]:
    yielded = 0
    for candidate in candidates:
        if options.min_static_score is not None and candidate.score < options.min_static_score:
            continue
        excluded_flags = set(options.exclude_risk_flags or [])
        if excluded_flags.intersection(candidate.risk_flags):
            continue
        yield candidate
        yielded += 1
        if yielded >= options.top_k:
            break


def _candidate_payload(candidate: FunctionCandidate) -> dict[str, Any]:
    return {
        "file": candidate.file,
        "module": candidate.module,
        "qualname": candidate.qualname,
        "symbol": candidate.symbol,
        "line_start": candidate.lineno,
        "line_end": candidate.end_lineno,
        "signature": candidate_signature(candidate),
        "args": candidate.args,
        "defaults_count": candidate.defaults_count,
        "docstring": candidate.docstring,
        "calls": candidate.calls,
        "helper_candidates": candidate.helper_candidates,
        "metrics": candidate.metrics,
        "static_score": candidate.score,
        "risk_flags": candidate.risk_flags,
    }
