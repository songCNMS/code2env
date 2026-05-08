from __future__ import annotations

from pathlib import Path

from code2env.ingest import copy_source_tree, ingest_repo
from code2env.jsonio import read_json, write_json
from code2env.models import EnvSpec


def build_env_package(spec_path: str | Path, output_dir: str | Path) -> Path:
    spec_path = Path(spec_path).resolve()
    spec = EnvSpec.from_dict(read_json(spec_path))
    snapshot = ingest_repo(str(spec.source["source_root"]))
    package_root = Path(output_dir).resolve() / spec.id
    package_root.mkdir(parents=True, exist_ok=True)
    copy_source_tree(snapshot, package_root / "source")

    packaged_spec = EnvSpec.from_dict(spec.to_dict())
    packaged_spec.source["source_root"] = "source"
    packaged_spec.source["packaged_from"] = str(spec_path)
    write_json(package_root / "env_spec.json", packaged_spec.to_dict())
    write_json(
        package_root / "manifest.json",
        {
            "id": packaged_spec.id,
            "version": packaged_spec.version,
            "entrypoint": packaged_spec.source["entrypoint"],
            "source_root": "source",
        },
    )
    return package_root
