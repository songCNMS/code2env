from __future__ import annotations

from pathlib import Path
from typing import Any

from code2env.executor import run_symbol_subprocess
from code2env.jsonio import read_json, write_json
from code2env.models import EnvSpec
from code2env.spec import source_root_for_spec


def materialize_env_spec(
    spec_path: str | Path,
    *,
    output_path: str | Path,
    fixture: dict[str, Any],
    compute_golden: bool = True,
    timeout_seconds: float = 10,
) -> dict[str, Any]:
    spec_path = Path(spec_path).resolve()
    spec = EnvSpec.from_dict(read_json(spec_path))
    normalized_fixture = normalize_fixture(fixture)
    spec.fixture = normalized_fixture
    if compute_golden:
        spec.golden_answer = run_symbol_subprocess(
            source_root_for_spec(spec, spec_path.parent),
            spec.source["entrypoint"],
            list(normalized_fixture["args"]),
            dict(normalized_fixture["kwargs"]),
            timeout_seconds=timeout_seconds,
            disable_network=True,
            disable_subprocess=True,
        )
    write_json(output_path, spec.to_dict())
    return {
        "input": str(spec_path),
        "output": str(Path(output_path).resolve()),
        "entrypoint": spec.source["entrypoint"],
        "fixture": normalized_fixture,
        "golden_answer": spec.golden_answer,
    }


def normalize_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be an object")
    args = fixture.get("args", [])
    kwargs = fixture.get("kwargs", {})
    if not isinstance(args, list):
        raise ValueError("fixture args must be a list")
    if not isinstance(kwargs, dict):
        raise ValueError("fixture kwargs must be an object")
    return {"args": args, "kwargs": kwargs}
