from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from code2env.ingest import ingest_repo
from code2env.jsonio import read_jsonl, write_json
from code2env.models import EnvSpec
from code2env.spec import draft_env_spec


def draft_specs_from_jsonl(
    jsonl_path: str | Path,
    *,
    output_dir: str | Path,
    fixture: dict[str, Any] | None = None,
    include_unselected: bool = False,
    compute_golden: bool = False,
) -> dict[str, Any]:
    records = read_jsonl(jsonl_path)
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    written: list[dict[str, Any]] = []
    skipped = 0

    snapshot_cache: dict[str, Any] = {}
    for record in records:
        if not record.get("selected") and not include_unselected:
            skipped += 1
            continue
        repo_source = record["repo"]["source"]
        if repo_source not in snapshot_cache:
            snapshot_cache[repo_source] = ingest_repo(repo_source)
        spec = draft_env_spec(
            snapshot_cache[repo_source],
            symbol=record["symbol"],
            fixture=fixture or {"args": [], "kwargs": {}},
            compute_golden=compute_golden,
        )
        apply_llm_record_to_spec(spec, record)
        path = target / f"{_safe_filename(spec.id)}.json"
        write_json(path, spec.to_dict())
        written.append({"symbol": record["symbol"], "path": str(path), "env_id": spec.id})

    return {
        "input": str(Path(jsonl_path).resolve()),
        "output_dir": str(target),
        "written": len(written),
        "skipped": skipped,
        "specs": written,
    }


def apply_llm_record_to_spec(spec: EnvSpec, record: dict[str, Any]) -> None:
    llm = record.get("llm", {})
    title = llm.get("task_title") or spec.task.get("title")
    description = llm.get("task_description") or spec.task.get("instruction")
    success_criteria = llm.get("success_criteria") or spec.task.get("success_criteria", [])
    input_assumptions = llm.get("input_assumptions") or []
    risk_notes = llm.get("risk_notes") or []
    tool_suggestions = llm.get("tool_suggestions") or []
    spec.task.update(
        {
            "title": title,
            "instruction": description,
            "success_criteria": success_criteria,
            "input_assumptions": input_assumptions,
            "risk_notes": risk_notes,
            "tool_suggestions": tool_suggestions,
            "source_jsonl_symbol": record.get("symbol"),
        }
    )
    spec.provenance["llm_candidate_record"] = {
        "schema_version": record.get("schema_version"),
        "selected": record.get("selected"),
        "llm": llm,
        "provenance": record.get("provenance", {}),
        "jsonl_file": record.get("file"),
        "line_start": record.get("line_start"),
        "line_end": record.get("line_end"),
    }


def _safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value)
