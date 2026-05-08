# LLM Candidate Selection

`code2env select` combines static analysis with an LLM review step to produce JSONL records for candidate environments.

```bash
python -m code2env select /path/to/repo \
  --llm-model kimi \
  --endpoint-file /work-agents/endpoints.txt \
  --top-k 20 \
  --max-selected 5 \
  --output /tmp/candidates.jsonl
```

The command:

1. Ingests the repository and filters supported Python files.
2. Ranks functions with the existing AST candidate scorer.
3. Sends each candidate's metadata, metrics, risk flags, and source excerpt to the selected LLM.
4. Writes one JSON object per line with function location, static metadata, LLM suitability, task description, tool suggestions, success criteria, and provenance.

Endpoint resolution order:

1. Explicit `--llm-base-url`, `--llm-api-key`, and `--llm-model`.
2. `CODE2ENV_LLM_BASE_URL`, `CODE2ENV_LLM_API_KEY`, and `CODE2ENV_LLM_MODEL`.
3. `--endpoint-file`.
4. `CODE2ENV_LLM_ENDPOINT_FILE`.
5. `/work-agents/endpoint.txt` or `/work-agents/endpoints.txt` when present.

Secrets are only read at runtime and are never written to the JSONL output. The JSONL provenance stores a redacted endpoint summary.

For deterministic tests:

```bash
python -m code2env select /path/to/repo \
  --llm-mode mock \
  --include-rejected \
  --output /tmp/candidates.jsonl
```

Reasoning models may need a larger completion budget. The CLI default is `--llm-max-tokens 4096`; lower it only when the selected model reliably returns compact JSON.
