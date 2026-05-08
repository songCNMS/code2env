from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from code2env.ingest import ingest_repo
from code2env.jsonio import read_jsonl
from code2env.llm import MockCandidateLLM, _extract_message_content, parse_llm_json, resolve_endpoint_config
from code2env.selector import SelectionOptions, export_llm_candidate_jsonl


class LlmCandidateSelectionTest(unittest.TestCase):
    def test_parse_llm_json_accepts_fenced_content(self) -> None:
        parsed = parse_llm_json(
            """
```json
{"suitable": true, "confidence": 0.7, "task_description": "demo"}
```
""".strip()
        )
        self.assertTrue(parsed["suitable"])
        self.assertEqual(parsed["task_description"], "demo")

    def test_endpoint_file_resolves_model_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            endpoint_file = Path(temp_dir) / "endpoints.txt"
            endpoint_file.write_text(
                "https://example.invalid/v1/ kimi-k2.6 sk-test\n"
                "https://example.invalid/v1/ deepseek-v4-pro sk-test-2\n",
                encoding="utf-8",
            )
            config = resolve_endpoint_config(model="kimi", endpoint_file=endpoint_file)
            self.assertEqual(config.model, "kimi-k2.6")
            self.assertEqual(config.chat_completions_url, "https://example.invalid/v1/chat/completions")
            self.assertEqual(config.redacted()["api_key"], "***")

    def test_extract_message_content_supports_reasoning_field(self) -> None:
        content = _extract_message_content(
            {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "reasoning_content": '{"suitable": false, "confidence": 0.1}',
                        }
                    }
                ]
            }
        )
        self.assertIn("suitable", content)

    def test_export_jsonl_with_mock_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._create_repo(Path(temp_dir) / "repo")
            output = Path(temp_dir) / "candidates.jsonl"
            summary = export_llm_candidate_jsonl(
                ingest_repo(str(repo)),
                llm=MockCandidateLLM(),
                output_path=output,
                options=SelectionOptions(top_k=5, max_selected=1, include_rejected=True, include_source=True),
                endpoint_metadata={"model": "mock", "source": "test"},
            )
            self.assertEqual(summary["selected"], 1)
            records = read_jsonl(output)
            selected = [record for record in records if record["selected"]]
            self.assertEqual(len(selected), 1)
            record = selected[0]
            self.assertEqual(record["symbol"], "sample:normalize_name")
            self.assertIn("task_description", record["llm"])
            self.assertIn("source_excerpt", record)
            self.assertEqual(record["provenance"]["llm_model"], "mock")

    def test_cli_select_with_mock_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._create_repo(Path(temp_dir) / "repo")
            output = Path(temp_dir) / "cli_candidates.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "code2env",
                    "select",
                    str(repo),
                    "--llm-mode",
                    "mock",
                    "--top-k",
                    "5",
                    "--max-selected",
                    "1",
                    "--output",
                    str(output),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                self.fail(f"CLI failed\nstdout={result.stdout}\nstderr={result.stderr}")
            summary = json.loads(result.stdout)
            self.assertEqual(summary["selected"], 1)
            self.assertEqual(len(read_jsonl(output)), 1)

    def _create_repo(self, path: Path) -> Path:
        path.mkdir(parents=True)
        (path / "sample.py").write_text(
            """
def clean_text(value):
    return " ".join(value.strip().split())


def normalize_name(name, shout=False):
    \"\"\"Normalize a human name for display.\"\"\"
    cleaned = clean_text(name)
    if shout:
        return cleaned.upper()
    return cleaned.title()


def tiny():
    return 1
""".lstrip(),
            encoding="utf-8",
        )
        return path


if __name__ == "__main__":
    unittest.main()
