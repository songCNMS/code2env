from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from code2env.models import FunctionCandidate, RepoSnapshot


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
                    steps=_step_blocks(node),
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


_STEP_KIND_BY_NODE = (
    (ast.Return, "finalize"),
    (ast.Raise, "raise"),
    ((ast.If, ast.IfExp), "branch"),
    ((ast.For, ast.AsyncFor, ast.While), "loop"),
    ((ast.With, ast.AsyncWith), "context"),
    (ast.Try, "guard"),
    (ast.Match, "branch"),
    ((ast.Assign, ast.AnnAssign, ast.AugAssign), "assign"),
)


def _step_blocks(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict[str, object]]:
    """Decompose a function body into ordered top-level semantic step blocks.

    Each block records its source span, a coarse phase kind, and the callees it
    references so downstream tooling can map direct callees back to the main
    function steps that invoke them.
    """

    body = list(node.body)
    start = 0
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        if isinstance(body[0].value.value, str):
            start = 1
    blocks: list[dict[str, object]] = []
    for index, stmt in enumerate(body[start:]):
        kind = _stmt_kind(stmt)
        callees = sorted(_call_names(stmt))
        blocks.append(
            {
                "index": index,
                "kind": kind,
                "line_start": stmt.lineno,
                "line_end": int(getattr(stmt, "end_lineno", stmt.lineno) or stmt.lineno),
                "callees": callees,
                "summary": _stmt_summary(stmt, kind, callees),
            }
        )
    return blocks


def _stmt_kind(stmt: ast.stmt) -> str:
    if isinstance(stmt, ast.Expr) and isinstance(getattr(stmt, "value", None), ast.Call):
        return "call"
    for node_types, kind in _STEP_KIND_BY_NODE:
        if isinstance(stmt, node_types):
            return kind
    return "statement"


def _stmt_summary(stmt: ast.stmt, kind: str, callees: list[str]) -> str:
    targets = _assignment_targets(stmt)
    if targets:
        detail = ", ".join(targets)
        return f"{kind}: {detail}"
    if callees:
        return f"{kind}: {callees[0]}()"
    return kind


def _assignment_targets(stmt: ast.stmt) -> list[str]:
    names: list[str] = []
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            names.extend(_target_names(target))
    elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
        names.extend(_target_names(stmt.target))
    return names


def _target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_target_names(element))
        return names
    if isinstance(target, ast.Attribute):
        return [target.attr]
    return []


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
