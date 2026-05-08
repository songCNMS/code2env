# task003_targeted_selection_env_specs Knowledge

<!-- METADATA:SESSION=1 -->

## Writing Rule

Record durable task-specific decisions, constraints, and implementation notes here. Keep entries concise and update when new information would help future sessions.

## Entries

- First-pass outputs are under `/work-agents/intern_code2env_dev/outputs/task002_llm_selection/`.
- First-pass Kimi selection chose `flask.cli:find_app_by_string` and rejected requests/rich top 3 candidates.
- Risk-filtered targeted selection produced 4 additional selected candidates across requests and rich when excluding `requires_instance` and `possible_side_effect`.
- EnvSpec drafts generated from JSONL intentionally default to no golden answer because many selected candidates still need fixture design.
