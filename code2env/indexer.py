from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from code2env.models import FunctionCandidate, RepoSnapshot, TestLink


CONTROL_FLOW_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Match,
    ast.BoolOp,
    ast.IfExp,
)
SIDE_EFFECT_CALL_NAMES = {
    "open",
    "remove",
    "unlink",
    "rmdir",
    "mkdir",
    "rename",
    "replace",
    "run",
    "popen",
    "system",
    "request",
    "get",
    "post",
    "put",
    "delete",
    "patch",
}


def index_repo(snapshot: RepoSnapshot) -> list[FunctionCandidate]:
    root = Path(snapshot.path)
    candidates: list[FunctionCandidate] = []
    for relative in snapshot.python_files:
        path = root / relative
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        module = _module_name_from_path(Path(relative))
        top_level_functions = _top_level_function_names(tree)
        for node, parents in _iter_functions(tree):
            if not getattr(node, "end_lineno", None):
                continue
            qualname = ".".join([*parents, node.name])
            calls = sorted(_call_names(node))
            helper_candidates = sorted(
                name for name in calls if name in top_level_functions and name != node.name
            )
            metrics = _metrics(node)
            risk_flags = _risk_flags(calls, metrics, qualname, _argument_names(node))
            score = _score(metrics, node, helper_candidates, risk_flags)
            candidates.append(
                FunctionCandidate(
                    module=module,
                    qualname=qualname,
                    symbol=f"{module}:{qualname}",
                    file=relative,
                    lineno=node.lineno,
                    end_lineno=node.end_lineno,
                    args=_argument_names(node),
                    defaults_count=len(node.args.defaults) + len(node.args.kw_defaults),
                    docstring=(ast.get_docstring(node) or "").strip(),
                    calls=calls,
                    helper_candidates=helper_candidates,
                    metrics=metrics,
                    score=score,
                    risk_flags=risk_flags,
                )
            )
    return sorted(candidates, key=lambda item: item.score, reverse=True)


def find_candidate(candidates: Iterable[FunctionCandidate], symbol: str) -> FunctionCandidate:
    candidate_list = list(candidates)
    for candidate in candidate_list:
        if candidate.symbol == symbol:
            return candidate
    available = ", ".join(candidate.symbol for candidate in candidate_list[:10])
    raise ValueError(f"Symbol not found: {symbol}. Top available symbols: {available}")


def _module_name_from_path(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def _top_level_function_names(tree: ast.Module) -> set[str]:
    return {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _iter_functions(tree: ast.AST) -> Iterable[tuple[ast.FunctionDef | ast.AsyncFunctionDef, list[str]]]:
    def walk(node: ast.AST, parents: list[str]) -> Iterable[tuple[ast.FunctionDef | ast.AsyncFunctionDef, list[str]]]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                yield from walk(child, [*parents, child.name])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield child, parents

    yield from walk(tree, [])


def _argument_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [arg.arg for arg in node.args.posonlyargs + node.args.args]
    args.extend(arg.arg for arg in node.args.kwonlyargs)
    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)
    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)
    return args


def _call_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _metrics(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, int]:
    body = list(ast.walk(node))
    return {
        "lines": int(node.end_lineno or node.lineno) - node.lineno + 1,
        "branches": sum(isinstance(child, CONTROL_FLOW_NODES) for child in body),
        "calls": sum(isinstance(child, ast.Call) for child in body),
        "returns": sum(isinstance(child, ast.Return) for child in body),
        "raises": sum(isinstance(child, ast.Raise) for child in body),
    }


def _risk_flags(calls: list[str], metrics: dict[str, int], qualname: str, args: list[str]) -> list[str]:
    flags: list[str] = []
    lower_calls = {call.lower() for call in calls}
    if lower_calls.intersection(SIDE_EFFECT_CALL_NAMES):
        flags.append("possible_side_effect")
    if "." in qualname and args[:1] in (["self"], ["cls"]):
        flags.append("requires_instance")
    if metrics["lines"] < 4:
        flags.append("too_small")
    if metrics["branches"] == 0 and metrics["calls"] == 0:
        flags.append("low_decision_surface")
    return flags


def _score(
    metrics: dict[str, int],
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    helper_candidates: list[str],
    risk_flags: list[str],
) -> float:
    doc_bonus = 10 if ast.get_docstring(node) else 0
    helper_bonus = min(len(helper_candidates), 5) * 8
    risk_penalty = sum(40 if flag == "requires_instance" else 12 for flag in risk_flags)
    return (
        metrics["lines"]
        + metrics["branches"] * 5
        + metrics["calls"] * 2
        + helper_bonus
        + doc_bonus
        - risk_penalty
    )


# --------------------------------------------------------------------------- #
# TestLinkIndex (PRD 7.2): associate source candidates with tests / fixtures /
# golden data by import reference, name similarity, and fixture usage.
# --------------------------------------------------------------------------- #

DATA_FILE_RE = re.compile(r"[\w./-]+\.(?:json|jsonl|ya?ml|golden|csv|txt)$")
_EVIDENCE_WEIGHTS = {"name_match": 0.5, "body_ref": 0.35, "import_ref": 0.25}
_MAX_LINKS_PER_CANDIDATE = 24


@dataclass(slots=True)
class _TestFunc:
    name: str
    lineno: int
    end_lineno: int
    fixtures: list[str]  # parameter names (potential fixture requests)
    refs: set[str] = field(default_factory=set)  # referenced Name/Attribute symbols
    data_refs: set[str] = field(default_factory=set)  # data-like string literals


@dataclass(slots=True)
class _TestModule:
    path: str
    imported_modules: set[str]
    imported_names: set[str]
    fixtures: dict[str, tuple[int, int]]  # fixture name -> (lineno, end_lineno)
    tests: list[_TestFunc]


def build_test_link_index(
    snapshot: RepoSnapshot, candidates: Iterable[FunctionCandidate]
) -> dict[str, list[TestLink]]:
    """Map each candidate symbol to its discovered test / fixture / golden links."""

    modules = _parse_test_modules(snapshot)
    return {
        candidate.symbol: _links_for(candidate, modules)
        for candidate in candidates
    }


def links_for_candidate(
    snapshot: RepoSnapshot, candidate: FunctionCandidate
) -> list[TestLink]:
    """Convenience wrapper returning links for a single candidate."""

    return _links_for(candidate, _parse_test_modules(snapshot))


def _parse_test_modules(snapshot: RepoSnapshot) -> list[_TestModule]:
    root = Path(snapshot.path)
    modules: list[_TestModule] = []
    for relative in snapshot.test_files:
        path = root / relative
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

        imported_modules, imported_names = _collect_imports(tree)
        fixtures: dict[str, tuple[int, int]] = {}
        tests: list[_TestFunc] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end = getattr(node, "end_lineno", None) or node.lineno
            if _is_fixture(node):
                fixtures[node.name] = (node.lineno, end)
            if node.name.startswith("test") or node.name.endswith("_test"):
                tests.append(
                    _TestFunc(
                        name=node.name,
                        lineno=node.lineno,
                        end_lineno=end,
                        fixtures=[arg.arg for arg in node.args.args if arg.arg != "self"],
                        refs=_referenced_names(node),
                        data_refs=_data_literals(node),
                    )
                )
        modules.append(
            _TestModule(
                path=relative,
                imported_modules=imported_modules,
                imported_names=imported_names,
                fixtures=fixtures,
                tests=tests,
            )
        )
    return modules


def _links_for(candidate: FunctionCandidate, modules: list[_TestModule]) -> list[TestLink]:
    simple_name = candidate.qualname.split(".")[-1]
    module = candidate.module
    links: list[TestLink] = []
    seen_fixtures: set[tuple[str, str]] = set()
    for mod in modules:
        import_ref = _module_imported(module, simple_name, mod)
        for test in mod.tests:
            evidence: list[str] = []
            if simple_name in test.name:
                evidence.append("name_match")
            if simple_name in test.refs:
                evidence.append("body_ref")
            # Importing the module only counts once a concrete reference exists,
            # to avoid linking every candidate to a module-wide import.
            if import_ref and evidence:
                evidence.append("import_ref")
            if not {"name_match", "body_ref"}.intersection(evidence):
                continue
            confidence = min(0.95, sum(_EVIDENCE_WEIGHTS[e] for e in evidence))
            links.append(
                TestLink(
                    candidate_symbol=candidate.symbol,
                    target=f"{mod.path}::{test.name}",
                    target_kind="test",
                    path=mod.path,
                    lineno=test.lineno,
                    end_lineno=test.end_lineno,
                    evidence=evidence,
                    confidence=round(confidence, 3),
                )
            )
            # Fixtures requested by a linked test are linked to the candidate too.
            for fixture_name in test.fixtures:
                if fixture_name not in mod.fixtures:
                    continue
                key = (mod.path, fixture_name)
                if key in seen_fixtures:
                    continue
                seen_fixtures.add(key)
                f_lineno, f_end = mod.fixtures[fixture_name]
                links.append(
                    TestLink(
                        candidate_symbol=candidate.symbol,
                        target=f"{mod.path}::{fixture_name}",
                        target_kind="fixture",
                        path=mod.path,
                        lineno=f_lineno,
                        end_lineno=f_end,
                        evidence=["fixture_use"],
                        confidence=0.3,
                    )
                )
            # Golden/data files referenced from a linked test.
            for data_ref in sorted(test.data_refs):
                links.append(
                    TestLink(
                        candidate_symbol=candidate.symbol,
                        target=data_ref,
                        target_kind="golden",
                        path=mod.path,
                        lineno=test.lineno,
                        end_lineno=test.end_lineno,
                        evidence=["data_ref"],
                        confidence=0.3,
                    )
                )
    links.sort(key=lambda link: link.confidence, reverse=True)
    return links[:_MAX_LINKS_PER_CANDIDATE]


def _collect_imports(tree: ast.Module) -> tuple[set[str], set[str]]:
    modules: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
                names.add((alias.asname or alias.name).split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return modules, names


def _module_imported(module: str, simple_name: str, mod: _TestModule) -> bool:
    if not module:
        return simple_name in mod.imported_names
    last = module.split(".")[-1]
    for imported in mod.imported_modules:
        if imported == module or imported.endswith("." + module) or module.endswith("." + imported):
            return True
    return last in mod.imported_names or simple_name in mod.imported_names


def _is_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
        if isinstance(target, ast.Name) and target.id == "fixture":
            return True
    return False


def _referenced_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def _data_literals(node: ast.AST) -> set[str]:
    literals: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            if DATA_FILE_RE.fullmatch(child.value.strip()):
                literals.add(child.value.strip())
    return literals
