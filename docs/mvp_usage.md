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
3. Score by exact match against the golden source output.

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
