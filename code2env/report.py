"""D4 rollout summary report generation.

Consumes two upstream products and produces a human-readable markdown report plus
a machine-readable JSON report:

1. The D1 generation ``manifest.json`` (task020 / worker_1). Consumed contract::

       {
         "generated_at": ...,
         "summary": {
           "candidates_scanned", "draft_ok", "build_ok", "smoke_ok",
           "skipped_no_fixture", "by_repo": {repo: {build_ok, smoke_ok}}
         },
         "envs": [{env_id, repo, symbol, file, fixture:{ok,strategy,value,reason},
                   draft_ok, build_ok, smoke_ok, smoke_fail_reason, spec_path, package_path}],
         "skipped": [{symbol, repo, reason}]
       }

2. The D3 rollout conversation products (task022 / worker_3): a directory of
   per-env ``<env_id>.json`` files and/or a merged ``rollouts.jsonl``. Consumed
   contract (per record)::

       {env_id, model, endpoint_source,
        final: {submitted_answer, correct, score, score_breakdown, steps},
        num_tool_call_rounds, qualified, termination_reason, retries, errors}

Field names above are a shared contract owned by the team lead; this module only
reads them and never mutates them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from code2env.jsonio import read_json, read_jsonl, write_json

# Explainable failure taxonomy. Order matters: ``classify_reason`` returns the
# first matching rule wins, falling back to ``other``.
FAILURE_TAGS: list[str] = [
    "dependency_failure",
    "fixture_unsynthesizable",
    "weak_oracle",
    "tool_granularity",
    "format_error",
    "other",
]

# Canonical D1/D3 reason tokens -> tag (team-lead defined). Reasons are emitted as
# ``tag:detail`` (e.g. "build_error:ModuleNotFoundError: ...") or bare tokens
# (e.g. "untyped_required_param"), so substring/prefix matching is used.
_FIXTURE_TOKENS: tuple[str, ...] = (
    "untyped_required_param",
    "unsupported_param_type",
    "requires_instance",
    "possible_side_effect",
    "not_module_level",
    "function_node_not_found",
    "no_fixture",
)
_DEPENDENCY_IMPORT_SIGNALS: tuple[str, ...] = (
    "modulenotfound",
    "importerror",
    "no module named",
)
_WEAK_ORACLE_SIGNALS: tuple[str, ...] = (
    "golden_error",
    "answer_mismatch",
)
_FORMAT_SIGNALS: tuple[str, ...] = (
    "parse_error",
    "schema",
)


def classify_reason(reason: str | None) -> str:
    """Map a canonical D1/D3 failure reason to one explainable failure tag.

    Mapping (team-lead canonical contract):

    - ``dependency_failure`` ← ``build_error:ModuleNotFound*`` / ``ImportError`` /
      ``draft_error`` containing ``import``.
    - ``weak_oracle`` ← ``golden_error*`` / ``answer_mismatch``.
    - ``format_error`` ← (rollout) ``parse_error`` / ``schema``.
    - ``fixture_unsynthesizable`` ← ``untyped_required_param`` /
      ``unsupported_param_type`` / ``requires_instance`` / ``possible_side_effect`` /
      ``not_module_level`` / ``function_node_not_found`` / ``no_fixture``.
    - ``other`` ← anything else. (Unqualified rollouts with no other signal are
      re-tagged ``tool_granularity`` at the rollout-clustering layer.)
    """

    if not reason:
        return "other"
    text = str(reason).lower()
    # Dependency: import-related build/draft errors.
    if any(signal in text for signal in _DEPENDENCY_IMPORT_SIGNALS):
        return "dependency_failure"
    if text.startswith("draft_error") and "import" in text:
        return "dependency_failure"
    # Weak oracle.
    if any(signal in text for signal in _WEAK_ORACLE_SIGNALS):
        return "weak_oracle"
    # Format error (rollout-stage parse/schema problems).
    if any(signal in text for signal in _FORMAT_SIGNALS):
        return "format_error"
    # Fixture synthesis failures (D1 skipped / fixture.reason tokens).
    if any(token in text for token in _FIXTURE_TOKENS):
        return "fixture_unsynthesizable"
    return "other"


def _empty_tag_counts() -> dict[str, int]:
    return {tag: 0 for tag in FAILURE_TAGS}


# --------------------------------------------------------------------------- #
# Rollout loading
# --------------------------------------------------------------------------- #
def load_rollouts(rollouts_path: str | Path | None) -> list[dict[str, Any]]:
    """Load rollout conversation records from a directory or a jsonl file.

    For a directory, per-env ``<env_id>.json`` files are preferred; if none are
    present the merged ``rollouts.jsonl`` is used. This avoids double-counting a
    rollout that exists in both forms.
    """

    if rollouts_path is None:
        return []
    path = Path(rollouts_path)
    if path.is_dir():
        json_files = sorted(p for p in path.glob("*.json"))
        if json_files:
            return [read_json(p) for p in json_files]
        merged = path / "rollouts.jsonl"
        if merged.exists():
            return read_jsonl(merged)
        return []
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    return [read_json(path)]


# --------------------------------------------------------------------------- #
# Env generation summary
# --------------------------------------------------------------------------- #
def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _summarize_generation(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("summary", {}) or {}
    envs = manifest.get("envs", []) or []
    skipped = manifest.get("skipped", []) or []

    candidates = summary.get("candidates_scanned")
    if not isinstance(candidates, int) or candidates <= 0:
        candidates = len(envs) + len(skipped)
    draft_ok = summary.get("draft_ok")
    if not isinstance(draft_ok, int):
        draft_ok = sum(1 for e in envs if e.get("draft_ok"))
    build_ok = summary.get("build_ok")
    if not isinstance(build_ok, int):
        build_ok = sum(1 for e in envs if e.get("build_ok"))
    smoke_ok = summary.get("smoke_ok")
    if not isinstance(smoke_ok, int):
        smoke_ok = sum(1 for e in envs if e.get("smoke_ok"))

    return {
        "candidates_scanned": candidates,
        "draft_ok": draft_ok,
        "build_ok": build_ok,
        "smoke_ok": smoke_ok,
        "skipped": len(skipped),
        "draft_rate": _rate(draft_ok, candidates),
        "build_rate": _rate(build_ok, candidates),
        # smoke_ok is gated on a successful build, so report it relative to build_ok.
        "smoke_rate_of_built": _rate(smoke_ok, build_ok),
        "by_repo": _by_repo(manifest),
    }


def _by_repo(manifest: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Per-repo generation distribution, recomputed from ``envs`` for totals.

    ``summary.by_repo`` (build_ok/smoke_ok) is merged in when present; totals and
    skipped counts are always derived from the full envs/skipped lists.
    """

    envs = manifest.get("envs", []) or []
    skipped = manifest.get("skipped", []) or []
    by_repo: dict[str, dict[str, int]] = {}
    for env in envs:
        repo = env.get("repo", "unknown")
        bucket = by_repo.setdefault(repo, {"total": 0, "build_ok": 0, "smoke_ok": 0, "skipped": 0})
        bucket["total"] += 1
        if env.get("build_ok"):
            bucket["build_ok"] += 1
        if env.get("smoke_ok"):
            bucket["smoke_ok"] += 1
    for item in skipped:
        repo = item.get("repo", "unknown")
        bucket = by_repo.setdefault(repo, {"total": 0, "build_ok": 0, "smoke_ok": 0, "skipped": 0})
        bucket["skipped"] += 1
    # Fall back to summary.by_repo if envs were not provided at all.
    if not by_repo:
        for repo, counts in (manifest.get("summary", {}) or {}).get("by_repo", {}).items():
            by_repo[repo] = {
                "total": int(counts.get("build_ok", 0)),
                "build_ok": int(counts.get("build_ok", 0)),
                "smoke_ok": int(counts.get("smoke_ok", 0)),
                "skipped": 0,
            }
    return dict(sorted(by_repo.items()))


def _cluster_generation_failures(manifest: dict[str, Any]) -> dict[str, Any]:
    """Cluster every generation-stage failure into explainable tags.

    Sources: skipped candidates, draft failures, build failures, and smoke
    failures. The most specific available reason text is used per env.
    """

    counts = _empty_tag_counts()
    examples: dict[str, list[str]] = {tag: [] for tag in FAILURE_TAGS}
    total = 0

    def record(reason: str | None, label: str) -> None:
        nonlocal total
        tag = classify_reason(reason)
        counts[tag] += 1
        total += 1
        if len(examples[tag]) < 3:
            examples[tag].append(f"{label}: {reason}" if reason else label)

    for item in manifest.get("skipped", []) or []:
        record(item.get("reason"), item.get("symbol", item.get("repo", "skipped")))

    for env in manifest.get("envs", []) or []:
        env_id = env.get("env_id", env.get("symbol", "env"))
        fixture_reason = (env.get("fixture") or {}).get("reason")
        if not env.get("draft_ok"):
            record(fixture_reason or "draft failed", f"{env_id} (draft)")
        elif not env.get("build_ok"):
            record(env.get("smoke_fail_reason") or fixture_reason or "build failed", f"{env_id} (build)")
        elif not env.get("smoke_ok"):
            record(env.get("smoke_fail_reason"), f"{env_id} (smoke)")

    return {"total": total, "counts": counts, "examples": examples}


# --------------------------------------------------------------------------- #
# Rollout summary
# --------------------------------------------------------------------------- #
def _has_submit(conv: dict[str, Any]) -> bool:
    for step in conv.get("steps", []) or []:
        action = step.get("action") or {}
        if action.get("tool") == "submit_answer":
            return True
    for message in conv.get("messages", []) or []:
        call = message.get("tool_call") or {}
        if call.get("tool") == "submit_answer":
            return True
        if message.get("name") == "submit_answer":
            return True
    return False


def _is_qualified(conv: dict[str, Any]) -> bool:
    """Prefer the contract's ``qualified`` flag; derive it when absent.

    Derivation matches the shared rule: ``num_tool_call_rounds >= 2`` and a
    ``submit_answer`` appears in the trajectory.
    """

    flag = conv.get("qualified")
    if isinstance(flag, bool):
        return flag
    rounds = conv.get("num_tool_call_rounds", 0) or 0
    return rounds >= 2 and _has_submit(conv)


def _final(conv: dict[str, Any]) -> dict[str, Any]:
    final = conv.get("final")
    return final if isinstance(final, dict) else {}


# --------------------------------------------------------------------------- #
# golden_status (task030 / w1 contract): manifest.envs[].golden_status is
# "real_value" or "weak_oracle:<reason>". A weak_oracle env cannot give a trusted
# correctness signal, so its rollouts are excluded from the *true* correct-rate
# denominator and counted separately. Missing golden_status degrades to "unknown"
# (kept in the denominator so we never silently shrink it).
# --------------------------------------------------------------------------- #
GOLDEN_REAL = "real_value"
GOLDEN_WEAK_PREFIX = "weak_oracle"


def _golden_status_by_env(manifest: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for env in manifest.get("envs", []) or []:
        env_id = env.get("env_id")
        status = env.get("golden_status")
        if env_id is not None and isinstance(status, str) and status:
            statuses[env_id] = status
    return statuses


def _golden_kind(status: str | None) -> str:
    """Bucket a golden_status string into real_value / weak_oracle / unknown."""

    if not isinstance(status, str) or not status:
        return "unknown"
    if status == GOLDEN_REAL:
        return "real_value"
    if status.startswith(GOLDEN_WEAK_PREFIX):
        return "weak_oracle"
    return "unknown"


def _summarize_rollouts(
    rollouts: list[dict[str, Any]],
    low_score_threshold: float,
    golden_status_by_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    golden_status_by_env = golden_status_by_env or {}
    total = len(rollouts)
    qualified = sum(1 for c in rollouts if _is_qualified(c))
    correct = sum(1 for c in rollouts if _final(c).get("correct") is True)
    scores = [float(_final(c).get("score", 0.0) or 0.0) for c in rollouts]
    mean_score = round(sum(scores) / total, 4) if total else 0.0
    low_score = sum(1 for s in scores if s < low_score_threshold)

    # True correct rate: exclude rollouts whose env has a weak oracle from the
    # denominator; count them separately. correct among the usable (non-weak) set.
    weak_oracle_excluded = 0
    golden_unknown = 0
    usable = 0
    true_correct = 0
    for conv in rollouts:
        kind = _golden_kind(golden_status_by_env.get(conv.get("env_id")))
        if kind == "weak_oracle":
            weak_oracle_excluded += 1
            continue
        if kind == "unknown":
            golden_unknown += 1
        usable += 1
        if _final(conv).get("correct") is True:
            true_correct += 1

    by_model: dict[str, dict[str, Any]] = {}
    for conv in rollouts:
        model = conv.get("model", "unknown")
        bucket = by_model.setdefault(model, {"total": 0, "qualified": 0, "correct": 0, "score_sum": 0.0})
        bucket["total"] += 1
        if _is_qualified(conv):
            bucket["qualified"] += 1
        if _final(conv).get("correct") is True:
            bucket["correct"] += 1
        bucket["score_sum"] += float(_final(conv).get("score", 0.0) or 0.0)
    for bucket in by_model.values():
        n = bucket.pop("score_sum")
        bucket["mean_score"] = round(n / bucket["total"], 4) if bucket["total"] else 0.0

    return {
        "total": total,
        "qualified": qualified,
        "qualified_rate": _rate(qualified, total),
        # Raw correct over all rollouts (includes weak-oracle false positives).
        "correct": correct,
        "correct_rate": _rate(correct, total),
        # True correct: weak-oracle envs removed from the denominator.
        "usable_total": usable,
        "weak_oracle_excluded": weak_oracle_excluded,
        "golden_unknown": golden_unknown,
        "true_correct": true_correct,
        "true_correct_rate": _rate(true_correct, usable),
        "mean_score": mean_score,
        "low_score_threshold": low_score_threshold,
        "low_score_count": low_score,
        "by_model": dict(sorted(by_model.items())),
    }


def _cluster_rollout_failures(rollouts: list[dict[str, Any]], low_score_threshold: float) -> dict[str, Any]:
    """Cluster unqualified / incorrect / low-score rollouts into failure tags.

    Classification uses ``termination_reason`` first, then any ``errors`` text;
    an unqualified rollout with no other signal is tagged ``tool_granularity``
    (the agent never reached two tool-call rounds + submit).
    """

    counts = _empty_tag_counts()
    examples: dict[str, list[str]] = {tag: [] for tag in FAILURE_TAGS}
    total = 0
    for conv in rollouts:
        qualified = _is_qualified(conv)
        final = _final(conv)
        correct = final.get("correct") is True
        score = float(final.get("score", 0.0) or 0.0)
        if qualified and correct and score >= low_score_threshold:
            continue  # healthy rollout
        total += 1
        reason = conv.get("termination_reason")
        errors = conv.get("errors")
        reason_text = reason or (errors if isinstance(errors, str) else (errors[0] if errors else None))
        tag = classify_reason(reason_text)
        if tag == "other" and not qualified:
            tag = "tool_granularity"
        counts[tag] += 1
        env_id = conv.get("env_id", "rollout")
        if len(examples[tag]) < 3:
            examples[tag].append(f"{env_id}: {reason_text or ('unqualified' if not qualified else 'low_score')}")
    return {"total": total, "counts": counts, "examples": examples}


# --------------------------------------------------------------------------- #
# Dependency-install before/after comparison
# --------------------------------------------------------------------------- #
def _golden_distribution(manifest: dict[str, Any]) -> dict[str, Any]:
    """Count golden_status kinds overall and per repo for one manifest."""

    counts = {"real_value": 0, "weak_oracle": 0, "unknown": 0}
    by_repo: dict[str, dict[str, int]] = {}
    for env in manifest.get("envs", []) or []:
        kind = _golden_kind(env.get("golden_status"))
        counts[kind] += 1
        repo = env.get("repo", "unknown")
        bucket = by_repo.setdefault(repo, {"real_value": 0, "weak_oracle": 0, "unknown": 0})
        bucket[kind] += 1
    return {"counts": counts, "by_repo": dict(sorted(by_repo.items()))}


def _smoke_ok_by_repo(manifest: dict[str, Any]) -> dict[str, int]:
    by_repo: dict[str, int] = {}
    for env in manifest.get("envs", []) or []:
        repo = env.get("repo", "unknown")
        by_repo.setdefault(repo, 0)
        if env.get("smoke_ok"):
            by_repo[repo] += 1
    return by_repo


def _dependency_comparison(
    manifest: dict[str, Any], baseline_manifest: dict[str, Any] | None
) -> dict[str, Any]:
    """Before/after dependency-install comparison.

    Without a baseline this reports the current golden_status distribution only
    (and notes that transitions cannot be computed). With a baseline it adds, per
    ``env_id``, the count of golden ``error -> real_value`` transitions (baseline
    not real_value, current real_value) and the per-repo ``smoke_ok`` before/after
    deltas — surfacing e.g. flask going from 0 to N.
    """

    current_dist = _golden_distribution(manifest)
    if baseline_manifest is None:
        return {
            "baseline_provided": False,
            "note": "baseline manifest not provided; showing current golden_status distribution only.",
            "current_golden": current_dist,
        }

    baseline_golden = _golden_status_by_env(baseline_manifest)
    error_to_real = 0
    transitions: list[str] = []
    for env in manifest.get("envs", []) or []:
        env_id = env.get("env_id")
        if env_id is None:
            continue
        if _golden_kind(env.get("golden_status")) != "real_value":
            continue
        # real_value now; was it non-real (error/weak/missing) before?
        if _golden_kind(baseline_golden.get(env_id)) != "real_value":
            error_to_real += 1
            if len(transitions) < 5:
                transitions.append(env_id)

    before_smoke = _smoke_ok_by_repo(baseline_manifest)
    after_smoke = _smoke_ok_by_repo(manifest)
    repos = sorted(set(before_smoke) | set(after_smoke))
    smoke_by_repo = {
        repo: {
            "before": before_smoke.get(repo, 0),
            "after": after_smoke.get(repo, 0),
            "delta": after_smoke.get(repo, 0) - before_smoke.get(repo, 0),
        }
        for repo in repos
    }
    return {
        "baseline_provided": True,
        "golden_error_to_real_value": error_to_real,
        "golden_transitions_sample": transitions,
        "smoke_ok_by_repo": smoke_by_repo,
        "baseline_golden": _golden_distribution(baseline_manifest),
        "current_golden": current_dist,
    }


# --------------------------------------------------------------------------- #
# Top-level report
# --------------------------------------------------------------------------- #
def build_report(
    manifest_path: str | Path,
    rollouts_path: str | Path | None = None,
    *,
    low_score_threshold: float = 0.5,
    baseline_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build the structured report dict from a manifest and rollout products.

    ``baseline_manifest_path`` is an optional pre-dependency-install manifest used
    for the golden ``error -> real_value`` / smoke before-after comparison.
    """

    manifest = read_json(manifest_path)
    rollouts = load_rollouts(rollouts_path)
    baseline_manifest = read_json(baseline_manifest_path) if baseline_manifest_path else None
    golden_status_by_env = _golden_status_by_env(manifest)
    return {
        "sources": {
            "manifest": str(manifest_path),
            "rollouts": str(rollouts_path) if rollouts_path is not None else None,
            "baseline_manifest": str(baseline_manifest_path) if baseline_manifest_path else None,
            "manifest_generated_at": manifest.get("generated_at"),
            "rollout_records": len(rollouts),
        },
        "env_generation": _summarize_generation(manifest),
        "rollouts": _summarize_rollouts(rollouts, low_score_threshold, golden_status_by_env),
        "dependency_comparison": _dependency_comparison(manifest, baseline_manifest),
        "failure_clusters": {
            "generation": _cluster_generation_failures(manifest),
            "rollout": _cluster_rollout_failures(rollouts, low_score_threshold),
        },
    }


def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _render_tag_table(cluster: dict[str, Any]) -> list[str]:
    lines = ["| Tag | Count |", "|---|---:|"]
    for tag in FAILURE_TAGS:
        lines.append(f"| {tag} | {cluster['counts'].get(tag, 0)} |")
    lines.append(f"| **total** | **{cluster.get('total', 0)}** |")
    return lines


def _render_golden_counts(dist: dict[str, Any]) -> list[str]:
    counts = dist.get("counts", {})
    return [
        f"| real_value | {counts.get('real_value', 0)} |",
        f"| weak_oracle | {counts.get('weak_oracle', 0)} |",
        f"| unknown | {counts.get('unknown', 0)} |",
    ]


def _render_dependency_comparison(comparison: dict[str, Any]) -> list[str]:
    if not comparison:
        return []
    lines = ["## Dependency-install Before/After", ""]
    if not comparison.get("baseline_provided"):
        lines.append(f"_{comparison.get('note', 'baseline not provided')}_")
        lines.append("")
        lines.append("Current golden status distribution:")
        lines.append("")
        lines.append("| golden_status | Count |")
        lines.append("|---|---:|")
        lines.extend(_render_golden_counts(comparison.get("current_golden", {})))
        lines.append("")
        return lines

    lines.append(f"- Golden **error → real_value** envs: **{comparison.get('golden_error_to_real_value', 0)}**")
    sample = comparison.get("golden_transitions_sample") or []
    if sample:
        lines.append(f"  - e.g. {', '.join(sample)}")
    lines.append("")
    smoke = comparison.get("smoke_ok_by_repo", {})
    if smoke:
        lines.append("### smoke_ok by repo (before → after)")
        lines.append("")
        lines.append("| Repo | Before | After | Δ |")
        lines.append("|---|---:|---:|---:|")
        for repo, vals in smoke.items():
            lines.append(f"| {repo} | {vals['before']} | {vals['after']} | {vals['delta']:+d} |")
        lines.append("")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    env = report["env_generation"]
    rollouts = report["rollouts"]
    clusters = report["failure_clusters"]
    sources = report["sources"]

    lines: list[str] = []
    lines.append("# code2env Rollout Summary Report")
    lines.append("")
    lines.append(f"- Manifest: `{sources['manifest']}`")
    if sources.get("manifest_generated_at"):
        lines.append(f"- Manifest generated at: {sources['manifest_generated_at']}")
    lines.append(f"- Rollouts: `{sources.get('rollouts')}` ({sources['rollout_records']} records)")
    lines.append("")

    lines.append("## Env Generation")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Candidates scanned | {env['candidates_scanned']} |")
    lines.append(f"| draft_ok | {env['draft_ok']} ({_pct(env['draft_rate'])}) |")
    lines.append(f"| build_ok | {env['build_ok']} ({_pct(env['build_rate'])}) |")
    lines.append(f"| smoke_ok | {env['smoke_ok']} ({_pct(env['smoke_rate_of_built'])} of built) |")
    lines.append(f"| skipped | {env['skipped']} |")
    lines.append("")

    if env["by_repo"]:
        lines.append("### By Repo")
        lines.append("")
        lines.append("| Repo | Total | build_ok | smoke_ok | skipped |")
        lines.append("|---|---:|---:|---:|---:|")
        for repo, counts in env["by_repo"].items():
            lines.append(
                f"| {repo} | {counts.get('total', 0)} | {counts.get('build_ok', 0)} "
                f"| {counts.get('smoke_ok', 0)} | {counts.get('skipped', 0)} |"
            )
        lines.append("")

    lines.append("## Rollouts")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total rollouts | {rollouts['total']} |")
    lines.append(f"| Qualified (>=2 tool rounds + submit) | {rollouts['qualified']} ({_pct(rollouts['qualified_rate'])}) |")
    lines.append(f"| Correct (raw, incl. weak-oracle false positives) | {rollouts['correct']} ({_pct(rollouts['correct_rate'])}) |")
    lines.append(
        f"| **True correct (weak-oracle excluded)** | "
        f"**{rollouts['true_correct']}/{rollouts['usable_total']} ({_pct(rollouts['true_correct_rate'])})** |"
    )
    lines.append(f"| Weak-oracle excluded from denominator | {rollouts['weak_oracle_excluded']} |")
    lines.append(f"| Golden status unknown (kept in denominator) | {rollouts['golden_unknown']} |")
    lines.append(f"| Mean score | {rollouts['mean_score']} |")
    lines.append(f"| Low score (< {rollouts['low_score_threshold']}) | {rollouts['low_score_count']} |")
    lines.append("")

    if rollouts["by_model"]:
        lines.append("### By Model")
        lines.append("")
        lines.append("| Model | Total | Qualified | Correct | Mean score |")
        lines.append("|---|---:|---:|---:|---:|")
        for model, counts in rollouts["by_model"].items():
            lines.append(
                f"| {model} | {counts['total']} | {counts['qualified']} "
                f"| {counts['correct']} | {counts['mean_score']} |"
            )
        lines.append("")

    lines.extend(_render_dependency_comparison(report.get("dependency_comparison", {})))

    lines.append("## Failure Clusters")
    lines.append("")
    lines.append("### Generation failures")
    lines.append("")
    lines.extend(_render_tag_table(clusters["generation"]))
    lines.append("")
    lines.append("### Rollout failures")
    lines.append("")
    lines.extend(_render_tag_table(clusters["rollout"]))
    lines.append("")
    return "\n".join(lines)


def write_report(
    manifest_path: str | Path,
    rollouts_path: str | Path | None,
    output_dir: str | Path,
    *,
    low_score_threshold: float = 0.5,
    baseline_manifest_path: str | Path | None = None,
) -> dict[str, str]:
    """Build and write ``report.json`` + ``report.md`` into ``output_dir``."""

    report = build_report(
        manifest_path,
        rollouts_path,
        low_score_threshold=low_score_threshold,
        baseline_manifest_path=baseline_manifest_path,
    )
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "report.json"
    md_path = out / "report.md"
    write_json(json_path, report)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path)}
