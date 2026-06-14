"""Determinism gate for golden answers (task038 / root-cause 2).

Even after dependency install (task030) and runtime envelope normalization (task037),
some envs keep a golden answer that *no* agent can ever match because the source
function returns something different on every run: an object ``repr`` carrying a
memory address (``<sha1 ... object at 0x72b6...>``), an absolute worker path, a hash
of a random seed, or a timestamp. Counting those toward the usable/correctness set
over-states how many environments are actually solvable.

This module classifies a golden answer as ``deterministic`` or
``nondeterministic:<reason>`` so the batch pipeline can exclude the latter from the
qualified set (same treatment as ``weak_oracle``).

Avoiding over-flagging (review feedback): a bare ``0x...`` hex substring or a
``/home//tmp/`` path can be a *legitimate, stable* return value, so they are **not**
flagged on their own. Detection therefore uses:

1. A strong standalone signature — a default object ``repr`` of the shape
   ``<... at 0x...>`` / ``<...@0x...>``. That is the CPython default repr and is never
   a sensible stable return; it is flagged on a single run.
2. Repeated execution (N>=2): if results disagree the golden is nondeterministic.
   Only when corroborated by such a mismatch do the weaker ``memory_addr`` / ``abs_path``
   signatures refine the reason; otherwise the reason is ``unstable_across_runs``.

``determinism`` field contract (shared with w4 reporting / w5 scale-out):
``deterministic`` | ``nondeterministic:<reason>`` where reason ∈
``object_repr`` / ``memory_addr`` / ``abs_path`` / ``unstable_across_runs``.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Strong standalone signal: a default object repr always carries a live address and is
# never a legitimate stable return value. Requires the `` at 0x``/``@0x`` shape inside
# angle brackets so plain strings that merely contain "0x" do not match.
_OBJECT_REPR = re.compile(r"<[^>]*(?: at |@)0x[0-9a-fA-F]{6,}[^>]*>")

# Weak signals: suspicious but possibly legitimate; only used to refine the reason when
# a repeat-execution mismatch has already proven nondeterminism.
_WEAK_SIGNATURES: list[tuple[str, re.Pattern[str]]] = [
    ("memory_addr", re.compile(r"0x[0-9a-fA-F]{6,}")),
    ("abs_path", re.compile(r"/(?:home|tmp|Users|root|var/folders)/")),
]


def _serialize(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def standalone_signature(golden_answer: Any) -> str | None:
    """Return a standalone nondeterminism reason (object repr), else None."""

    if _OBJECT_REPR.search(_serialize(golden_answer)):
        return "object_repr"
    return None


def weak_signature(golden_answer: Any) -> str | None:
    """Return a corroborating weak-signal reason (memory_addr/abs_path), else None."""

    text = _serialize(golden_answer)
    for reason, pattern in _WEAK_SIGNATURES:
        if pattern.search(text):
            return reason
    return None


def results_differ(results: list[Any]) -> bool:
    """True if any two results in ``results`` serialize differently."""

    if len(results) < 2:
        return False
    first = _serialize(results[0])
    return any(_serialize(other) != first for other in results[1:])


def classify_determinism(golden_answer: Any, repeat_results: list[Any] | None = None) -> str:
    """Classify a golden answer as ``deterministic`` or ``nondeterministic:<reason>``.

    A default object ``repr`` is flagged standalone. Otherwise nondeterminism must be
    proven by a repeat-run mismatch; the reason is then refined to ``memory_addr`` /
    ``abs_path`` if such a weak signature is present, else ``unstable_across_runs``.
    A bare hex/path that is *stable* across runs is treated as deterministic.
    """

    if standalone_signature(golden_answer):
        return "nondeterministic:object_repr"
    if repeat_results and results_differ([golden_answer, *repeat_results]):
        return f"nondeterministic:{weak_signature(golden_answer) or 'unstable_across_runs'}"
    return "deterministic"


def is_usable(golden_status: str | None, determinism: str | None) -> bool:
    """The qualified/usable set is ``real_value`` AND ``deterministic`` (task038)."""

    return golden_status == "real_value" and determinism == "deterministic"
