from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from code2env.builder import build_env_package
from code2env.ingest import ingest_repo
from code2env.indexer import index_repo
from code2env.jsonio import loads_object, write_json
from code2env.jsonl_specs import draft_specs_from_jsonl
from code2env.llm import MockCandidateLLM, OpenAICompatibleLLM, resolve_endpoint_config
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


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
