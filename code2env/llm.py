from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


DEFAULT_ENDPOINT_FILES = (
    "/work-agents/endpoint.txt",
    "/work-agents/endpoints.txt",
)


class CandidateLLM(Protocol):
    model_name: str

    def evaluate_candidate(self, candidate_context: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class EndpointConfig:
    base_url: str
    model: str
    api_key: str
    source: str

    @property
    def chat_completions_url(self) -> str:
        clean = self.base_url.rstrip("/")
        if clean.endswith("/chat/completions"):
            return clean
        return f"{clean}/chat/completions"

    def redacted(self) -> dict[str, str]:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "api_key": _redact_secret(self.api_key),
            "source": self.source,
        }


class OpenAICompatibleLLM:
    """Minimal OpenAI-compatible chat completions client using the standard library."""

    def __init__(
        self,
        config: EndpointConfig,
        *,
        timeout_seconds: float = 60,
        max_tokens: int = 1200,
        temperature: float = 0.0,
    ):
        self.config = config
        self.model_name = config.model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature

    def evaluate_candidate(self, candidate_context: dict[str, Any]) -> dict[str, Any]:
        prompt = build_candidate_prompt(candidate_context)
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        raw_body = self._post_payload(payload)

        response_payload = json.loads(raw_body)
        content = _extract_message_content(response_payload)
        return parse_llm_json(content)

    def _post_payload(self, payload: dict[str, Any]) -> str:
        request = self._build_request(payload)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if "response_format" in payload and exc.code in {400, 422}:
                retry_payload = dict(payload)
                retry_payload.pop("response_format", None)
                with urllib.request.urlopen(self._build_request(retry_payload), timeout=self.timeout_seconds) as response:
                    return response.read().decode("utf-8")
            raise RuntimeError(f"LLM request failed with HTTP {exc.code}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

    def _build_request(self, payload: dict[str, Any]) -> urllib.request.Request:
        return urllib.request.Request(
            self.config.chat_completions_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )


class MockCandidateLLM:
    """Deterministic local LLM replacement for tests and offline dry runs."""

    model_name = "mock"

    def evaluate_candidate(self, candidate_context: dict[str, Any]) -> dict[str, Any]:
        candidate = candidate_context["candidate"]
        metrics = candidate.get("metrics", {})
        risk_flags = set(candidate.get("risk_flags", []))
        line_count = int(metrics.get("lines", 0))
        suitable = line_count >= 4 and "requires_instance" not in risk_flags
        if "possible_side_effect" in risk_flags and line_count < 20:
            suitable = False
        symbol = candidate["symbol"]
        title = f"Complete the behavior of {symbol}"
        return {
            "suitable": suitable,
            "confidence": 0.82 if suitable else 0.35,
            "task_title": title if suitable else "",
            "task_description": (
                f"Given controlled JSON inputs, use tools derived from `{symbol}` to reproduce "
                "the pinned source behavior and submit the exact serialized result."
                if suitable
                else ""
            ),
            "tool_suggestions": _mock_tool_suggestions(candidate) if suitable else [],
            "success_criteria": [
                "The submitted answer exactly matches the golden source output.",
                "The solution stays within the tool-call budget.",
                "No real network or unsafe filesystem side effects occur.",
            ]
            if suitable
            else [],
            "input_assumptions": ["Inputs are JSON-serializable fixtures."] if suitable else [],
            "risk_notes": sorted(risk_flags),
            "rejection_reason": "" if suitable else "Candidate is too small, instance-bound, or risky for the MVP runtime.",
        }


def resolve_endpoint_config(
    *,
    model: str | None = None,
    endpoint_file: str | Path | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> EndpointConfig:
    env_model = os.getenv("CODE2ENV_LLM_MODEL")
    env_base_url = os.getenv("CODE2ENV_LLM_BASE_URL")
    env_api_key = os.getenv("CODE2ENV_LLM_API_KEY")
    resolved_model = model or env_model
    resolved_base_url = base_url or env_base_url
    resolved_api_key = api_key or env_api_key
    if resolved_base_url and resolved_api_key and resolved_model:
        return EndpointConfig(
            base_url=resolved_base_url,
            model=resolved_model,
            api_key=resolved_api_key,
            source="environment/cli",
        )

    for path in _candidate_endpoint_files(endpoint_file):
        if not path.exists():
            continue
        endpoints = _read_endpoint_file(path)
        if not endpoints:
            continue
        if resolved_model:
            for endpoint in endpoints:
                if _model_matches(resolved_model, endpoint.model):
                    return endpoint
        else:
            return endpoints[0]

    raise ValueError(
        "No LLM endpoint resolved. Pass --llm-base-url/--llm-api-key/--llm-model, "
        "set CODE2ENV_LLM_* env vars, or provide --endpoint-file."
    )


def parse_llm_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response did not contain a JSON object")
        cleaned = cleaned[start : end + 1]
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("LLM response JSON must be an object")
    return value


def _extract_message_content(response_payload: dict[str, Any]) -> str:
    choice = response_payload["choices"][0]
    message = choice.get("message", {})
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        joined = "\n".join(part for part in parts if part.strip())
        if joined.strip():
            return joined
    for key in ("reasoning_content", "reasoning", "text"):
        value = message.get(key) or choice.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError("LLM response message content was empty")


def normalize_llm_decision(raw: dict[str, Any]) -> dict[str, Any]:
    suitable = bool(raw.get("suitable", False))
    confidence = _coerce_float(raw.get("confidence", 0.0))
    return {
        "suitable": suitable,
        "confidence": max(0.0, min(1.0, confidence)),
        "task_title": str(raw.get("task_title", "") or ""),
        "task_description": str(raw.get("task_description", "") or ""),
        "tool_suggestions": _string_list(raw.get("tool_suggestions", [])),
        "success_criteria": _string_list(raw.get("success_criteria", [])),
        "input_assumptions": _string_list(raw.get("input_assumptions", [])),
        "risk_notes": _string_list(raw.get("risk_notes", [])),
        "rejection_reason": str(raw.get("rejection_reason", "") or ""),
    }


def build_candidate_prompt(candidate_context: dict[str, Any]) -> dict[str, str]:
    language = candidate_context.get("description_language", "zh")
    system = (
        "You screen Python functions for code2env agentic-RL environments. "
        "Prefer deterministic functions with clear input/output, enough internal logic, useful helper calls, "
        "and 3-8 possible tools. Reject trivial, instance-bound, unsafe side-effect, external-service, "
        "or hard-to-score candidates. Return only valid JSON, no markdown."
    )
    if language.lower().startswith("zh"):
        system += " Write task_title and task_description in Chinese."
    compact_context = {
        "description_language": candidate_context.get("description_language"),
        "prd_requirements": candidate_context.get("prd_requirements"),
        "repo": candidate_context.get("repo"),
        "candidate": candidate_context.get("candidate"),
        "source_excerpt": candidate_context.get("source_excerpt"),
        "source_excerpt_truncated": candidate_context.get("source_excerpt_truncated"),
    }
    schema_instruction = (
        'Return exactly this JSON shape: {"suitable": boolean, "confidence": number, '
        '"task_title": string, "task_description": string, "tool_suggestions": string[], '
        '"success_criteria": string[], "input_assumptions": string[], "risk_notes": string[], '
        '"rejection_reason": string}. Use an empty string/list when a field does not apply.'
    )
    user = (
        f"{schema_instruction}\n\n"
        f"Candidate context:\n{json.dumps(compact_context, ensure_ascii=False, indent=2)}"
    )
    return {"system": system, "user": user}


def _candidate_endpoint_files(endpoint_file: str | Path | None) -> list[Path]:
    if endpoint_file:
        return [Path(endpoint_file).expanduser()]
    env_file = os.getenv("CODE2ENV_LLM_ENDPOINT_FILE")
    if env_file:
        return [Path(env_file).expanduser()]
    return [Path(path) for path in DEFAULT_ENDPOINT_FILES]


def _read_endpoint_file(path: Path) -> list[EndpointConfig]:
    endpoints: list[EndpointConfig] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 3:
            continue
        endpoints.append(
            EndpointConfig(
                base_url=parts[0],
                model=parts[1],
                api_key=parts[2],
                source=str(path),
            )
        )
    return endpoints


def _model_matches(requested: str, available: str) -> bool:
    req = requested.lower()
    got = available.lower()
    return req == got or req in got or got in req


def _redact_secret(secret: str) -> str:
    return "***"


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value in (None, ""):
        return []
    return [str(value)]


def _mock_tool_suggestions(candidate: dict[str, Any]) -> list[str]:
    helpers = candidate.get("helper_candidates", [])
    tools = ["inspect_task"]
    tools.extend(f"call_{helper}" for helper in helpers[:4])
    tools.append("call_entrypoint")
    tools.append("submit_answer")
    return tools[:8]
