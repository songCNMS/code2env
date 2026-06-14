# Code2Env MVP Usage

This MVP implements the PRD path as a runnable standard-library pipeline:

```text
scan -> draft -> build -> smoke
```

## Commands

```bash
python -m code2env scan /path/to/repo --top-k 10 --json
```

`scan` parses Python files with `ast`, ranks functions by line count, branch count, call count, helper calls, docstring quality, and side-effect risk. It also reports a `Test files` count: test modules (`tests/`/`test/` directories, `test_*.py`, `*_test.py`, `conftest.py`) are mined separately into `RepoSnapshot.test_files` for the TestLinkIndex and are excluded from the ranked source corpus.

The indexer's `build_test_link_index(snapshot, candidates)` links each candidate to its tests, fixtures, and golden-data files (by import reference, name similarity, and fixture usage), recording the `evidence` and a `confidence` per link.

```bash
python -m code2env draft /path/to/repo \
  --symbol package.module:function_name \
  --fixture-json '{"args": [], "kwargs": {}}' \
  --output /tmp/env_spec.json
```

`draft` creates an `EnvSpec` with task text, tool specs, fixture, provenance, and an exact-match golden answer computed from the pinned source function. The `provenance.task_sources` list always holds at least two diverse sources — a `source_span` and a `signature` — plus any `test_link` / `fixture` / `golden` artifacts found by the TestLinkIndex. When no test artifacts are linked, `provenance.test_link_status` is `"no_test_links_found"` and a `degradation` note records that grounding fell back to signature-level evidence.

```bash
python -m code2env build /tmp/env_spec.json --output-dir /tmp/generated_envs
```

`build` copies a filtered Python source snapshot into the env package so the runtime no longer depends on the original repo checkout path.

```bash
python -m code2env smoke /tmp/generated_envs/<env_id> --json
```

`smoke` runs a scripted trajectory:

1. `call_entrypoint` with the fixture.
2. `submit_answer` with the serialized result.
3. Score with the multi-dimensional reward (see below); a clean correct run totals `1.0`.

Before building a draft EnvSpec, materialize it with a concrete JSON fixture:

```bash
python -m code2env materialize /tmp/env_spec_draft.json \
  --fixture-json '{"args": ["hello"], "kwargs": {}}' \
  --output /tmp/env_spec.json
```

## Runtime Tools

The Tool Extractor (PRD 7.5) emits a semantic tool set per env, kept within the 3–8 tool window:

- `inspect_task`: read-only; returns task, fixture, source metadata, and allowed helpers.
- `inspect_state`: read-only state inspector; returns the current episode state (step, phase, last tool result, submitted answer, available tools, remaining budget). Guarantees the env always has at least one query/validation tool so the agent never has to call blind.
- `call_entrypoint`: executes the selected entrypoint in an isolated Python subprocess. Its provenance records the decomposed main-function step blocks.
- `call_<helper>`: one dedicated tool per safe direct callee (e.g. `call_clean_text`). Each is a key step of the main function, executed by calling the backing symbol in the sandbox. Side-effecting helpers are *not* exposed this way — they are listed under the entrypoint tool's `provenance.sandboxed_side_effect_helpers` for later sandbox-adapter work.
- `call_helper`: optional backward-compatible sandboxed adapter that runs any same-module helper by name.
- `submit_answer`: ends the episode and scores the submitted payload by exact match.

Each `ToolSpec` carries `input_schema`, `output_schema`, `side_effects`, and `provenance` (`kind`, `backing` symbol/source span, and the main-function steps a helper tool maps to).

The runtime API is available as `code2env.runtime.Code2Env` with `reset`, `step`, `evaluate`, and `close`.

## Multi-dimensional reward (PRD 7.7 / F7)

Every episode accumulates raw signals for five dimensions, each weighted by
`reward.weights` from the EnvSpec (falling back to the defaults below when a spec
omits them):

| Dimension | Default weight | Raw signal |
|---|---:|---|
| `schema_validity` | 0.05 | fraction of actions that are well-formed (valid `tool_call`, known tool, object arguments, parseable result) |
| `process_progress` | 0.20 | staged milestones reached: explore → execute source → submit after progress |
| `final_correctness` | 0.65 | exact-match against the pinned golden answer (1.0 / 0.0) |
| `efficiency` | 0.05 | `1 − (error + duplicate calls)/max_steps`, minus a penalty for exhausting the step budget without submitting |
| `safety` | 0.05 | `1.0`, dropped to `0.0` when a sandbox enforcement fires (blocked network/subprocess, timeout) |

**Training reward vs. evaluation score are separate:**

- `step(action)` returns a dense, per-step **training reward** — potential-based
  shaping over the weighted total, so the per-step rewards telescope to the final
  evaluation score. Each step's `info["score_breakdown"]` carries the live breakdown.
- `evaluate()` returns the **evaluation score** and a fully explainable
  `score_breakdown`: per dimension `raw` value, `weight`, `weighted` contribution
  and a human-readable `detail`, plus a `total` clamped to `[0, 1]`.

```python
env = Code2Env("env_spec.json"); env.reset()
env.step({"type": "tool_call", "tool": "call_entrypoint", "arguments": env.spec.fixture})
env.step({"type": "tool_call", "tool": "submit_answer", "arguments": {"answer": ...}})
evaluation = env.evaluate()
evaluation["score"]                       # weighted total in [0, 1]
evaluation["score_breakdown"]["dimensions"]["safety"]  # {raw, weight, weighted, detail}
```

## Summary reports (D4)

`code2env report` aggregates the batch-generation `manifest.json` and the rollout
conversation products into a markdown + JSON summary report:

```bash
python -m code2env report /path/to/manifest.json \
  --rollouts /path/to/rollouts/ \
  --output-dir /tmp/code2env_report
```

It reads (read-only, shared field contract) the manifest `summary` / `envs` /
`skipped` and each rollout's `final.{correct,score}`, `num_tool_call_rounds`,
`qualified`, and `termination_reason`. `--rollouts` accepts a directory (per-env
`<env_id>.json`, falling back to `rollouts.jsonl`) or a `.jsonl` file, and may be
omitted to summarize generation only.

The report contains:

- **Env generation**: `draft_ok` / `build_ok` / `smoke_ok` rates over candidates,
  and a per-repo distribution (`total` / `build_ok` / `smoke_ok` / `skipped`).
- **Rollouts**: total, qualified count + rate (qualified = `>= 2` tool rounds and a
  `submit_answer`), correct count + rate, mean `final.score`, low-score count, and a
  per-model breakdown.
- **Failure clusters**: generation-stage and rollout-stage failures bucketed into a
  fixed explainable tag set — `dependency_failure`, `fixture_unsynthesizable`,
  `weak_oracle`, `tool_granularity`, `format_error`, `other` — with per-tag counts
  and example reasons. The `report.json` carries the same numbers as the markdown
  for programmatic consumption.
