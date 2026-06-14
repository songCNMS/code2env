# Code2Env MVP Usage

This MVP implements the PRD path as a runnable standard-library pipeline:

```text
scan -> draft -> build -> smoke
```

## Commands

```bash
python -m code2env scan /path/to/repo --top-k 10 --json
```

`scan` parses Python files with `ast`, ranks functions by line count, branch count, call count, helper calls, docstring quality, and side-effect risk.

```bash
python -m code2env draft /path/to/repo \
  --symbol package.module:function_name \
  --fixture-json '{"args": [], "kwargs": {}}' \
  --output /tmp/env_spec.json
```

`draft` creates an `EnvSpec` with task text, tool specs, fixture, provenance, and an exact-match golden answer computed from the pinned source function.

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

- `inspect_task`: returns task, fixture, source metadata, and allowed helpers.
- `call_entrypoint`: executes the selected function in an isolated Python subprocess.
- `call_helper`: optional, executes same-module top-level helper functions discovered from the entrypoint call graph.
- `submit_answer`: ends the episode and scores the submitted payload by exact match.

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
