from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from code2env.batch import generate_batch
from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.indexer import index_repo
from code2env.jsonio import loads_object, write_json
from code2env.jsonl_specs import draft_specs_from_jsonl
from code2env.llm import MockCandidateLLM, OpenAICompatibleLLM, resolve_endpoint_config
from code2env.materialize import materialize_env_spec
from code2env.report import write_report
from code2env.rollout import ScriptedSolveChat, run_rollout
from code2env.rollout_export import iter_jsonl, write_conversation
from code2env.runtime import Code2Env
from code2env.selector import SelectionOptions, export_llm_candidate_jsonl
from code2env.spec import draft_env_spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="code2env")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scan_parser = subcommands.add_parser("scan", help="Rank Python functions in a repo")
    scan_parser.add_argument("repo")
    scan_parser.add_argument("--top-k", type=int, default=20)
    scan_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    scan_parser.add_argument("--cache-dir", default=None)

    draft_parser = subcommands.add_parser("draft", help="Generate an EnvSpec JSON file")
    draft_parser.add_argument("repo")
    draft_parser.add_argument("--symbol", required=True, help="Symbol like package.module:function")
    draft_parser.add_argument("--fixture-json", default='{"args": [], "kwargs": {}}')
    draft_parser.add_argument("--output", required=True)
    draft_parser.add_argument("--env-id", default=None)
    draft_parser.add_argument("--cache-dir", default=None)
    draft_parser.add_argument("--no-golden", action="store_true")

    build_parser = subcommands.add_parser("build", help="Build a standalone EnvPackage")
    build_parser.add_argument("spec")
    build_parser.add_argument("--output-dir", required=True)

    smoke_parser = subcommands.add_parser("smoke", help="Run a scripted smoke trajectory")
    smoke_parser.add_argument("env_package_or_spec")
    smoke_parser.add_argument("--json", action="store_true")

    select_parser = subcommands.add_parser("select", help="Use an LLM to screen repo candidates and export JSONL")
    select_parser.add_argument("repo")
    select_parser.add_argument("--output", required=True)
    select_parser.add_argument("--top-k", type=int, default=20)
    select_parser.add_argument("--max-selected", type=int, default=None)
    select_parser.add_argument("--min-static-score", type=float, default=None)
    select_parser.add_argument(
        "--exclude-risk-flag",
        action="append",
        default=[],
        help="Skip candidates with this static risk flag. Repeatable.",
    )
    select_parser.add_argument("--include-rejected", action="store_true")
    select_parser.add_argument("--include-source", action="store_true")
    select_parser.add_argument("--max-source-chars", type=int, default=6000)
    select_parser.add_argument("--description-language", default="zh")
    select_parser.add_argument("--cache-dir", default=None)
    select_parser.add_argument("--llm-mode", choices=["endpoint", "mock"], default="endpoint")
    select_parser.add_argument("--llm-model", default=None, help="Model name or alias, e.g. kimi")
    select_parser.add_argument("--endpoint-file", default=None)
    select_parser.add_argument("--llm-base-url", default=None)
    select_parser.add_argument("--llm-api-key", default=None)
    select_parser.add_argument("--llm-timeout", type=float, default=60)
    select_parser.add_argument("--llm-max-tokens", type=int, default=4096)

    jsonl_draft_parser = subcommands.add_parser("draft-from-jsonl", help="Generate EnvSpec drafts from selected JSONL records")
    jsonl_draft_parser.add_argument("jsonl")
    jsonl_draft_parser.add_argument("--output-dir", required=True)
    jsonl_draft_parser.add_argument("--fixture-json", default='{"args": [], "kwargs": {}}')
    jsonl_draft_parser.add_argument("--include-unselected", action="store_true")
    jsonl_draft_parser.add_argument("--compute-golden", action="store_true")

    materialize_parser = subcommands.add_parser(
        "materialize",
        help="Apply a fixture to an EnvSpec and compute its golden answer",
    )
    materialize_parser.add_argument("spec")
    materialize_parser.add_argument("--fixture-json", required=True)
    materialize_parser.add_argument("--output", required=True)
    materialize_parser.add_argument("--no-golden", action="store_true")
    materialize_parser.add_argument("--timeout", type=float, default=10)

    report_parser = subcommands.add_parser(
        "report",
        help="Summarize env generation + rollouts into markdown/json reports",
    )
    report_parser.add_argument("manifest", help="Path to the D1 generation manifest.json")
    report_parser.add_argument(
        "--rollouts",
        default=None,
        help="Path to a rollouts directory (<env_id>.json / rollouts.jsonl) or a .jsonl file",
    )
    report_parser.add_argument("--output-dir", required=True, help="Directory to write report.md + report.json")
    report_parser.add_argument("--low-score-threshold", type=float, default=0.5)

    rollout_parser = subcommands.add_parser("rollout", help="Run a multi-round LLM tool-calling rollout on one env")
    rollout_parser.add_argument("env_package_or_spec")
    rollout_parser.add_argument("--output", default=None, help="Write the RolloutResult JSON to this path")
    rollout_parser.add_argument("--max-rounds", type=int, default=8)
    rollout_parser.add_argument("--llm-mode", choices=["endpoint", "mock"], default="endpoint")
    rollout_parser.add_argument("--llm-model", default="gpt-5.5")
    rollout_parser.add_argument("--fallback-model", default=None, help="Model name to fall back to (e.g. Kimi-K2.6)")
    rollout_parser.add_argument("--endpoint-file", default=None)
    rollout_parser.add_argument("--llm-base-url", default=None)
    rollout_parser.add_argument("--llm-api-key", default=None)
    rollout_parser.add_argument("--llm-timeout", type=float, default=60)
    rollout_parser.add_argument("--llm-max-tokens", type=int, default=1200)
    rollout_parser.add_argument("--max-parse-retries", type=int, default=2)
    rollout_parser.add_argument("--max-llm-retries", type=int, default=1)
    rollout_parser.add_argument("--seed", type=int, default=0)

    batch_parser = subcommands.add_parser(
        "batch", help="Batch-generate EnvPackages across repos with auto-synthesised fixtures"
    )
    batch_parser.add_argument("repos", nargs="+", help="Repo paths or Git URLs")
    batch_parser.add_argument("--output-dir", default="generated_envs/batch")
    batch_parser.add_argument("--target", type=int, default=100, help="Stop after this many successful builds")
    batch_parser.add_argument("--per-repo-limit", type=int, default=None)
    batch_parser.add_argument("--cache-dir", default=None)
    batch_parser.add_argument("--no-smoke", action="store_true")
    batch_parser.add_argument("--include-side-effects", action="store_true")

    rollout_export_parser = subcommands.add_parser(
        "rollout-export",
        help="Persist RolloutResult records (JSONL) as per-env conversation JSON + merged rollouts.jsonl",
    )
    rollout_export_parser.add_argument("results", help="JSONL file with one RolloutResult object per line")
    rollout_export_parser.add_argument(
        "--export-dir",
        default=None,
        help="Output directory (default: coordinator outputs/rollouts; auto-created)",
    )
    rollout_export_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation (use only for already-trusted records)",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            return _scan(args)
        if args.command == "draft":
            return _draft(args)
        if args.command == "build":
            return _build(args)
        if args.command == "smoke":
            return _smoke(args)
        if args.command == "select":
            return _select(args)
        if args.command == "draft-from-jsonl":
            return _draft_from_jsonl(args)
        if args.command == "materialize":
            return _materialize(args)
        if args.command == "report":
            return _report(args)
        if args.command == "rollout":
            return _rollout(args)
        if args.command == "batch":
            return _batch(args)
        if args.command == "rollout-export":
            return _rollout_export(args)
    except Exception as exc:  # noqa: BLE001 - CLI should return structured failure.
        print(f"code2env: error: {exc}", file=sys.stderr)
        return 1
    return 1


def _scan(args: argparse.Namespace) -> int:
    snapshot = ingest_repo(args.repo, cache_dir=args.cache_dir)
    candidates = index_repo(snapshot)[: args.top_k]
    data = {
        "repo": snapshot.to_dict(),
        "candidates": [candidate.to_dict() for candidate in candidates],
    }
    if args.json:
        _print_json(data)
    else:
        print(f"Repository: {snapshot.source}")
        print(f"Python files: {len(snapshot.python_files)}")
        print(f"Test files: {len(snapshot.test_files)}")
        for index, candidate in enumerate(candidates, start=1):
            flags = ",".join(candidate.risk_flags) or "none"
            print(
                f"{index:>3}. {candidate.symbol} "
                f"score={candidate.score:.1f} lines={candidate.metrics['lines']} "
                f"branches={candidate.metrics['branches']} calls={candidate.metrics['calls']} "
                f"risk={flags}"
            )
    return 0


def _draft(args: argparse.Namespace) -> int:
    fixture = loads_object(args.fixture_json, label="fixture-json")
    snapshot = ingest_repo(args.repo, cache_dir=args.cache_dir)
    spec = draft_env_spec(
        snapshot,
        symbol=args.symbol,
        fixture=fixture,
        env_id=args.env_id,
        compute_golden=not args.no_golden,
    )
    write_json(args.output, spec.to_dict())
    print(args.output)
    return 0


def _build(args: argparse.Namespace) -> int:
    package_root = build_env_package(args.spec, args.output_dir)
    print(package_root)
    return 0


def _smoke(args: argparse.Namespace) -> int:
    path = Path(args.env_package_or_spec).resolve()
    spec_path = path / "env_spec.json" if path.is_dir() else path
    env = Code2Env(spec_path)
    result = env.scripted_smoke()
    if args.json:
        _print_json(result)
    else:
        print(f"ok={result['ok']} reward={result['reward']:.3f}")
        print(f"score={result['evaluation']['score']:.3f} steps={result['evaluation']['steps']}")
    return 0 if result["ok"] else 2


def _select(args: argparse.Namespace) -> int:
    snapshot = ingest_repo(args.repo, cache_dir=args.cache_dir)
    if args.llm_mode == "mock":
        llm = MockCandidateLLM()
        endpoint_metadata = {"model": llm.model_name, "source": "mock"}
    else:
        endpoint_config = resolve_endpoint_config(
            model=args.llm_model,
            endpoint_file=args.endpoint_file,
            base_url=args.llm_base_url,
            api_key=args.llm_api_key,
        )
        llm = OpenAICompatibleLLM(
            endpoint_config,
            timeout_seconds=args.llm_timeout,
            max_tokens=args.llm_max_tokens,
        )
        endpoint_metadata = endpoint_config.redacted()
    summary = export_llm_candidate_jsonl(
        snapshot,
        llm=llm,
        output_path=args.output,
        options=SelectionOptions(
            top_k=args.top_k,
            max_selected=args.max_selected,
            min_static_score=args.min_static_score,
            exclude_risk_flags=args.exclude_risk_flag,
            include_rejected=args.include_rejected,
            include_source=args.include_source,
            max_source_chars=args.max_source_chars,
            description_language=args.description_language,
        ),
        endpoint_metadata=endpoint_metadata,
    )
    _print_json(summary)
    return 0


def _draft_from_jsonl(args: argparse.Namespace) -> int:
    fixture = loads_object(args.fixture_json, label="fixture-json")
    summary = draft_specs_from_jsonl(
        args.jsonl,
        output_dir=args.output_dir,
        fixture=fixture,
        include_unselected=args.include_unselected,
        compute_golden=args.compute_golden,
    )
    _print_json(summary)
    return 0


def _materialize(args: argparse.Namespace) -> int:
    fixture = loads_object(args.fixture_json, label="fixture-json")
    summary = materialize_env_spec(
        args.spec,
        output_path=args.output,
        fixture=fixture,
        compute_golden=not args.no_golden,
        timeout_seconds=args.timeout,
    )
    _print_json(summary)
    return 0


def _report(args: argparse.Namespace) -> int:
    paths = write_report(
        args.manifest,
        args.rollouts,
        args.output_dir,
        low_score_threshold=args.low_score_threshold,
    )
    _print_json(paths)
    return 0


def _rollout(args: argparse.Namespace) -> int:
    path = Path(args.env_package_or_spec).resolve()
    spec_path = path / "env_spec.json" if path.is_dir() else path
    env = Code2Env(spec_path)

    if args.llm_mode == "mock":
        result = run_rollout(
            env,
            ScriptedSolveChat(env),
            primary_source="mock",
            max_rounds=args.max_rounds,
            max_parse_retries=args.max_parse_retries,
            max_llm_retries=args.max_llm_retries,
            seed=args.seed,
        )
    else:
        primary_config = resolve_endpoint_config(
            model=args.llm_model,
            endpoint_file=args.endpoint_file,
            base_url=args.llm_base_url,
            api_key=args.llm_api_key,
        )
        primary = OpenAICompatibleLLM(
            primary_config,
            timeout_seconds=args.llm_timeout,
            max_tokens=args.llm_max_tokens,
        )
        fallback = None
        fallback_source = None
        if args.fallback_model:
            fallback_config = resolve_endpoint_config(
                model=args.fallback_model,
                endpoint_file=args.endpoint_file,
            )
            fallback = OpenAICompatibleLLM(
                fallback_config,
                timeout_seconds=args.llm_timeout,
                max_tokens=args.llm_max_tokens,
            )
            fallback_source = fallback_config.model
        result = run_rollout(
            env,
            primary,
            fallback_llm=fallback,
            primary_source=primary_config.model,
            fallback_source=fallback_source,
            max_rounds=args.max_rounds,
            max_parse_retries=args.max_parse_retries,
            max_llm_retries=args.max_llm_retries,
            seed=args.seed,
        )

    if args.output:
        write_json(args.output, result)
    _print_json(result)
    return 0 if result["final"].get("correct") else 2


def _batch(args: argparse.Namespace) -> int:
    manifest = generate_batch(
        args.repos,
        output_dir=args.output_dir,
        target_count=args.target,
        cache_dir=args.cache_dir,
        per_repo_limit=args.per_repo_limit,
        run_smoke=not args.no_smoke,
        include_side_effects=args.include_side_effects,
    )
    _print_json({"output_dir": str(Path(args.output_dir).resolve()), "summary": manifest["summary"]})
    return 0


def _rollout_export(args: argparse.Namespace) -> int:
    written: list[str] = []
    for record in iter_jsonl(args.results):
        path = write_conversation(record, args.export_dir, validate=not args.no_validate)
        written.append(str(path))
    _print_json({"exported": len(written), "paths": written})
    return 0


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
