# task003_targeted_selection_env_specs

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## Background

The first Kimi-based JSONL collection selected one Flask candidate but rejected the static top candidates for requests and rich because many high-score candidates were instance-bound or had side-effect risks. The next step is to run a targeted selection pass that can skip known risk flags and then generate initial EnvSpec drafts from selected JSONL candidates.

## Goals

- Add reusable filtering options to `code2env select` for excluding risk flags such as `requires_instance` and `possible_side_effect`.
- Re-run targeted selection for requests and rich to surface more suitable candidates beyond the initial top 3.
- Inspect the selected Flask candidate and produce initial EnvSpec draft files for selected candidates.
- Keep generated JSONL/spec artifacts under the intern outputs directory for review.

## Acceptance

- `code2env select` supports excluding one or more static risk flags.
- Tests cover risk-flag filtering.
- Targeted JSONL files are generated for requests and rich.
- At least one selected candidate has a corresponding EnvSpec draft when selection results allow it.
