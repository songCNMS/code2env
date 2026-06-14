from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


@dataclass(slots=True)
class RepoSnapshot:
    source: str
    path: str
    commit: str | None
    is_git: bool
    python_files: list[str]
    dependency_files: list[str]
    license_file: str | None
    test_files: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class TestLink:
    """Association between a source candidate and a test / fixture / golden artifact.

    ``target_kind`` is one of ``test``, ``fixture`` or ``golden``. ``evidence`` lists
    the signals that produced the link (``name_match``, ``body_ref``, ``import_ref``,
    ``fixture_use``, ``data_ref``) so provenance can stay auditable.
    """

    candidate_symbol: str
    target: str
    target_kind: str
    path: str
    lineno: int
    end_lineno: int
    evidence: list[str]
    confidence: float

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class FunctionCandidate:
    module: str
    qualname: str
    symbol: str
    file: str
    lineno: int
    end_lineno: int
    args: list[str]
    defaults_count: int
    docstring: str
    calls: list[str]
    helper_candidates: list[str]
    metrics: JsonDict
    score: float
    risk_flags: list[str] = field(default_factory=list)
    steps: list[JsonDict] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return asdict(self)

    @property
    def line_count(self) -> int:
        return self.end_lineno - self.lineno + 1


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: JsonDict
    output_schema: JsonDict
    side_effects: str = "none"
    timeout_ms: int = 1000
    provenance: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class EnvSpec:
    id: str
    version: int
    source: JsonDict
    task: JsonDict
    tools: list[ToolSpec]
    runtime: JsonDict
    reward: JsonDict
    fixture: JsonDict
    golden_answer: JsonDict | None
    provenance: JsonDict

    def to_dict(self) -> JsonDict:
        data = asdict(self)
        data["tools"] = [tool.to_dict() for tool in self.tools]
        return data

    @classmethod
    def from_dict(cls, data: JsonDict) -> "EnvSpec":
        tools = [ToolSpec(**tool) for tool in data.get("tools", [])]
        return cls(
            id=data["id"],
            version=int(data.get("version", 1)),
            source=dict(data["source"]),
            task=dict(data["task"]),
            tools=tools,
            runtime=dict(data.get("runtime", {})),
            reward=dict(data.get("reward", {})),
            fixture=dict(data.get("fixture", {"args": [], "kwargs": {}})),
            golden_answer=data.get("golden_answer"),
            provenance=dict(data.get("provenance", {})),
        )


def normalize_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())
