# task002_llm_repo_candidate_jsonl_export Knowledge

<!-- METADATA:SESSION=2 -->

## Writing Rule

Record durable task-specific decisions, constraints, and implementation notes here. Keep entries concise and update when new information would help future sessions.

## Entries

- LLM endpoint configuration is available locally under `/work-agents/endpoints.txt` in this environment; secrets must not be committed.
- User said Kimi can be used for debugging.
- Kimi reasoning responses may consume more completion budget before emitting final JSON; `code2env select` defaults to `--llm-max-tokens 4096`.
- The first requests/flask/rich JSONL collection used top 3 static candidates per repo and included rejected records so high-risk top candidates remain auditable.
