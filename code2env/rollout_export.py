"""Persist rollout conversations to disk (D3).

This module is the persistence layer for the rollout driver (task021, worker_2):
it takes a ``RolloutResult`` produced in-memory and writes it as a human-readable
per-env conversation JSON plus an appended line in a merged ``rollouts.jsonl``.
It does **not** run rollouts.

The conversation contract is shared with the producer (worker_2) and the report
consumer (worker_4); field names must not be renamed here. Schema::

    {
      "env_id": str,
      "model": str,
      "endpoint_source": str,
      "started_at": str,
      "finished_at": str,
      "messages": [
        {"role": "system"|"user"|"assistant"|"tool", "content": str,
         "name"?: str, "tool_call"?: {"tool": str, "arguments": object}}
      ],
      "steps": [
        {"step": int, "action": {"type": str, "tool"?: str, "arguments"?: object},
         "tool_result": any, "reward": number, "parse_error": str|null}
      ],
      "final": {"submitted_answer": any, "correct": bool, "score": number,
                "score_breakdown": object, "steps": int},
      "num_tool_call_rounds": int,
      "qualified": bool,
      "termination_reason": str,
      "retries": int,
      "errors": [any]
    }

``qualified`` is defined as ``num_tool_call_rounds >= 2`` **and** a ``submit_answer``
appears in the messages or steps. ``validate_conversation`` enforces this contract,
including that ``qualified`` is self-consistent.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Output lands in the coordinator's outputs tree, which is OUTSIDE the repo and
# not tracked by git. Overridable for tests / alternate layouts.
DEFAULT_EXPORT_DIR = Path(
    os.environ.get(
        "CODE2ENV_ROLLOUT_EXPORT_DIR",
        "/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts",
    )
)
MERGED_JSONL_NAME = "rollouts.jsonl"

VALID_ROLES = {"system", "user", "assistant", "tool"}
QUALIFIED_MIN_ROUNDS = 2
SUBMIT_TOOL = "submit_answer"

# Top-level field -> accepted python type(s) for schema validation.
_TOP_LEVEL_TYPES: dict[str, type | tuple[type, ...]] = {
    "env_id": str,
    "model": str,
    "endpoint_source": str,
    "started_at": str,
    "finished_at": str,
    "messages": list,
    "steps": list,
    "final": dict,
    "num_tool_call_rounds": int,
    "qualified": bool,
    "termination_reason": str,
    "retries": int,
    "errors": list,
}
_FINAL_FIELDS = ("submitted_answer", "correct", "score", "score_breakdown", "steps")
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


class ConversationSchemaError(ValueError):
    """Raised when a conversation object violates the shared D3 contract."""


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def has_submit_answer(conversation: dict[str, Any]) -> bool:
    """True if a ``submit_answer`` tool call appears in messages or steps."""

    for message in conversation.get("messages", []) or []:
        tool_call = message.get("tool_call") if isinstance(message, dict) else None
        if isinstance(tool_call, dict) and tool_call.get("tool") == SUBMIT_TOOL:
            return True
    for step in conversation.get("steps", []) or []:
        action = step.get("action") if isinstance(step, dict) else None
        if isinstance(action, dict) and action.get("tool") == SUBMIT_TOOL:
            return True
    return False


def compute_qualified(conversation: dict[str, Any]) -> bool:
    """Recompute ``qualified`` from the contract definition."""

    rounds = conversation.get("num_tool_call_rounds", 0)
    rounds_ok = isinstance(rounds, int) and not isinstance(rounds, bool) and rounds >= QUALIFIED_MIN_ROUNDS
    return bool(rounds_ok and has_submit_answer(conversation))


def validate_conversation(conversation: Any) -> dict[str, Any]:
    """Validate a conversation object against the shared schema.

    Returns the object unchanged on success; raises ``ConversationSchemaError``
    on any missing field, wrong type, or self-inconsistent ``qualified`` flag.
    """

    if not isinstance(conversation, dict):
        raise ConversationSchemaError(f"conversation must be an object, got {type(conversation).__name__}")

    for key, expected in _TOP_LEVEL_TYPES.items():
        if key not in conversation:
            raise ConversationSchemaError(f"missing required field: {key!r}")
        value = conversation[key]
        # bool is a subclass of int; reject it where a real int is required.
        if expected is int and isinstance(value, bool):
            raise ConversationSchemaError(f"field {key!r} must be int, got bool")
        if not isinstance(value, expected):
            name = expected.__name__ if isinstance(expected, type) else expected
            raise ConversationSchemaError(f"field {key!r} must be {name}, got {type(value).__name__}")

    if not conversation["env_id"]:
        raise ConversationSchemaError("env_id must be a non-empty string")
    if conversation["num_tool_call_rounds"] < 0:
        raise ConversationSchemaError("num_tool_call_rounds must be >= 0")
    if conversation["retries"] < 0 or isinstance(conversation["retries"], bool):
        raise ConversationSchemaError("retries must be a non-negative int")

    _validate_messages(conversation["messages"])
    _validate_steps(conversation["steps"])
    _validate_final(conversation["final"])

    expected_qualified = compute_qualified(conversation)
    if conversation["qualified"] != expected_qualified:
        raise ConversationSchemaError(
            "qualified is inconsistent with the contract: stored="
            f"{conversation['qualified']} but num_tool_call_rounds="
            f"{conversation['num_tool_call_rounds']} and submit_answer_present="
            f"{has_submit_answer(conversation)} imply qualified={expected_qualified}"
        )
    return conversation


def _validate_messages(messages: list[Any]) -> None:
    for index, message in enumerate(messages):
        where = f"messages[{index}]"
        if not isinstance(message, dict):
            raise ConversationSchemaError(f"{where} must be an object")
        role = message.get("role")
        if role not in VALID_ROLES:
            raise ConversationSchemaError(f"{where}.role must be one of {sorted(VALID_ROLES)}, got {role!r}")
        if not isinstance(message.get("content"), str):
            raise ConversationSchemaError(f"{where}.content must be a string")
        if "name" in message and not isinstance(message["name"], str):
            raise ConversationSchemaError(f"{where}.name must be a string when present")
        if "tool_call" in message and message["tool_call"] is not None:
            tool_call = message["tool_call"]
            if not isinstance(tool_call, dict):
                raise ConversationSchemaError(f"{where}.tool_call must be an object")
            if not isinstance(tool_call.get("tool"), str):
                raise ConversationSchemaError(f"{where}.tool_call.tool must be a string")
            if not isinstance(tool_call.get("arguments"), dict):
                raise ConversationSchemaError(f"{where}.tool_call.arguments must be an object")


def _validate_steps(steps: list[Any]) -> None:
    for index, step in enumerate(steps):
        where = f"steps[{index}]"
        if not isinstance(step, dict):
            raise ConversationSchemaError(f"{where} must be an object")
        for key in ("step", "action", "tool_result", "reward", "parse_error"):
            if key not in step:
                raise ConversationSchemaError(f"{where} missing field: {key!r}")
        if not isinstance(step["step"], int) or isinstance(step["step"], bool):
            raise ConversationSchemaError(f"{where}.step must be an int")
        action = step["action"]
        if not isinstance(action, dict) or not isinstance(action.get("type"), str):
            raise ConversationSchemaError(f"{where}.action must be an object with a string 'type'")
        if not isinstance(step["reward"], (int, float)) or isinstance(step["reward"], bool):
            raise ConversationSchemaError(f"{where}.reward must be a number")
        if step["parse_error"] is not None and not isinstance(step["parse_error"], str):
            raise ConversationSchemaError(f"{where}.parse_error must be a string or null")


def _validate_final(final: dict[str, Any]) -> None:
    for key in _FINAL_FIELDS:
        if key not in final:
            raise ConversationSchemaError(f"final missing field: {key!r}")
    if not isinstance(final["correct"], bool):
        raise ConversationSchemaError("final.correct must be a bool")
    if not isinstance(final["score"], (int, float)) or isinstance(final["score"], bool):
        raise ConversationSchemaError("final.score must be a number")
    if not isinstance(final["score_breakdown"], dict):
        raise ConversationSchemaError("final.score_breakdown must be an object")
    if not isinstance(final["steps"], int) or isinstance(final["steps"], bool):
        raise ConversationSchemaError("final.steps must be an int")


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #
def write_conversation(
    result: dict[str, Any],
    out_dir: str | Path | None = None,
    *,
    validate: bool = True,
) -> Path:
    """Write one RolloutResult as ``<env_id>.json`` and append to ``rollouts.jsonl``.

    The per-env JSON is written atomically (temp file + ``os.replace``) with a
    readable indent. ``out_dir`` defaults to :data:`DEFAULT_EXPORT_DIR` and is
    created if missing. Returns the path to the per-env JSON file.
    """

    if validate:
        validate_conversation(result)
    elif not (isinstance(result, dict) and result.get("env_id")):
        raise ConversationSchemaError("result must be an object with a non-empty env_id")

    directory = Path(out_dir) if out_dir is not None else DEFAULT_EXPORT_DIR
    directory.mkdir(parents=True, exist_ok=True)

    per_env_path = directory / f"{_safe_env_id(result['env_id'])}.json"
    _atomic_write_json(per_env_path, result)
    _append_jsonl(directory / MERGED_JSONL_NAME, result)
    return per_env_path


def _safe_env_id(env_id: str) -> str:
    return _FILENAME_SAFE.sub("_", env_id).strip("_") or "env"


def _atomic_write_json(path: Path, data: Any) -> None:
    payload = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp", delete=False
    )
    try:
        with handle:
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


def _append_jsonl(path: Path, data: Any) -> None:
    line = json.dumps(data, sort_keys=True, ensure_ascii=False)
    # O_APPEND keeps concurrent per-env exports from interleaving a single line.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_conversation(path: str | Path, *, validate: bool = True) -> dict[str, Any]:
    """Load a per-env conversation JSON; validates the contract by default."""

    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if validate:
        validate_conversation(data)
    return data


def iter_jsonl(path: str | Path, *, validate: bool = False) -> Iterator[dict[str, Any]]:
    """Yield each conversation record from a merged ``rollouts.jsonl``.

    Validation is off by default so partially-written merged logs can still be
    streamed; pass ``validate=True`` to enforce the contract per record.
    """

    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if validate:
                validate_conversation(record)
            yield record
