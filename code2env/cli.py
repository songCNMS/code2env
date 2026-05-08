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
from code2env.runtime import Code2Env
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


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
