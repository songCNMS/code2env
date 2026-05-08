from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any


def serialize_value(value: Any) -> dict[str, Any]:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return {
            "kind": "repr",
            "type": type(value).__name__,
            "repr": repr(value),
        }
    return {"kind": "json", "value": value}


def call_symbol(
    source_root: str | Path,
    symbol: str,
    args: list[Any],
    kwargs: dict[str, Any],
    *,
    disable_network: bool = False,
    disable_subprocess: bool = False,
) -> dict[str, Any]:
    module_name, qualname = symbol.split(":", 1)
    root = str(Path(source_root).resolve())
    sys.path.insert(0, root)
    src_root = str((Path(source_root).resolve() / "src"))
    if Path(src_root).exists():
        sys.path.insert(0, src_root)
    try:
        target: Any = importlib.import_module(module_name)
        for part in qualname.split("."):
            target = getattr(target, part)
        _apply_runtime_guards(disable_network=disable_network, disable_subprocess=disable_subprocess)
        value = target(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - runtime must serialize user code failures.
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(limit=8),
        }
    return {"ok": True, "value": serialize_value(value)}


def run_symbol_subprocess(
    source_root: str | Path,
    symbol: str,
    args: list[Any],
    kwargs: dict[str, Any],
    *,
    timeout_seconds: float = 3,
    disable_network: bool = False,
    disable_subprocess: bool = False,
) -> dict[str, Any]:
    payload = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    command = [
        sys.executable,
        "-m",
        "code2env.executor",
        "--source-root",
        str(source_root),
        "--symbol",
        symbol,
        "--payload",
        payload,
    ]
    if disable_network:
        command.append("--disable-network")
    if disable_subprocess:
        command.append("--disable-subprocess")
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error_type": "TimeoutExpired", "error_message": "tool timeout"}
    if result.returncode != 0:
        return {
            "ok": False,
            "error_type": "ExecutorFailed",
            "error_message": result.stderr.strip(),
        }
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error_type": "InvalidExecutorOutput",
            "error_message": result.stdout,
        }
    return parsed


def _apply_runtime_guards(*, disable_network: bool, disable_subprocess: bool) -> None:
    if disable_network:
        def blocked_socket(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("network access is disabled by Code2Env sandbox")

        socket.socket = blocked_socket  # type: ignore[assignment]
        socket.create_connection = blocked_socket  # type: ignore[assignment]

    if disable_subprocess:
        def blocked_subprocess(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("subprocess execution is disabled by Code2Env sandbox")

        subprocess.Popen = blocked_subprocess  # type: ignore[assignment]
        subprocess.run = blocked_subprocess  # type: ignore[assignment]
        subprocess.call = blocked_subprocess  # type: ignore[assignment]
        subprocess.check_call = blocked_subprocess  # type: ignore[assignment]
        subprocess.check_output = blocked_subprocess  # type: ignore[assignment]
        os.system = blocked_subprocess  # type: ignore[assignment]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--payload", required=True, help="JSON object with args and kwargs")
    parser.add_argument("--disable-network", action="store_true")
    parser.add_argument("--disable-subprocess", action="store_true")
    args = parser.parse_args(argv)

    payload = json.loads(args.payload)
    result = call_symbol(
        args.source_root,
        args.symbol,
        list(payload.get("args", [])),
        dict(payload.get("kwargs", {})),
        disable_network=args.disable_network,
        disable_subprocess=args.disable_subprocess,
    )
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
