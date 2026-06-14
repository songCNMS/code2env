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

The Tool Extractor (PRD 7.5) emits a semantic tool set per env, kept within the 3–8 tool window:

- `inspect_task`: read-only; returns task, fixture, source metadata, and allowed helpers.
- `inspect_state`: read-only state inspector; returns the current episode state (step, phase, last tool result, submitted answer, available tools, remaining budget). Guarantees the env always has at least one query/validation tool so the agent never has to call blind.
- `call_entrypoint`: executes the selected entrypoint in an isolated Python subprocess. Its provenance records the decomposed main-function step blocks.
- `call_<helper>`: one dedicated tool per safe direct callee (e.g. `call_clean_text`). Each is a key step of the main function, executed by calling the backing symbol in the sandbox. Side-effecting helpers are *not* exposed this way — they are listed under the entrypoint tool's `provenance.sandboxed_side_effect_helpers` for later sandbox-adapter work.
- `call_helper`: optional backward-compatible sandboxed adapter that runs any same-module helper by name.
- `submit_answer`: ends the episode and scores the submitted payload by exact match.

Each `ToolSpec` carries `input_schema`, `output_schema`, `side_effects`, and `provenance` (`kind`, `backing` symbol/source span, and the main-function steps a helper tool maps to).

The runtime API is available as `code2env.runtime.Code2Env` with `reset`, `step`, `evaluate`, and `close`.
