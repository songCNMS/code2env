# code2env

`code2env` turns Python code blocks into runnable tool-based environments for agentic RL experiments.

## MVP Quickstart

Scan a local repository:

```bash
python -m code2env scan /path/to/python/repo --top-k 10 --json
```

Draft an environment spec for a selected symbol:

```bash
python -m code2env draft /path/to/python/repo \
  --symbol package.module:function_name \
  --fixture-json '{"args": [1, 2], "kwargs": {}}' \
  --output /tmp/env_spec.json
```

Build a standalone package and run a smoke trajectory:

```bash
python -m code2env build /tmp/env_spec.json --output-dir /tmp/generated_envs
python -m code2env smoke /tmp/generated_envs/<env_id>
```

The generated runtime exposes a semantic tool set (PRD 7.5): the read-only `inspect_task` and `inspect_state` inspectors, `call_entrypoint`, dedicated `call_<helper>` tools for each safe direct callee (a key step of the main function), an optional sandboxed `call_helper` adapter, and `submit_answer`. Each tool carries an input/output JSON Schema, a `side_effects` declaration, and `provenance` (backing symbol / source span / main-function steps). Side-effecting helpers are not exposed directly; they are recorded in the entrypoint tool's provenance for sandbox-adapter follow-up. Every env stays within 3–8 tools. The default scorer uses exact match against the pinned source function output.

Export LLM-screened candidates as JSONL:

```bash
python -m code2env select /path/to/python/repo \
  --llm-model kimi \
  --endpoint-file /work-agents/endpoints.txt \
  --top-k 20 \
  --max-selected 5 \
  --output /tmp/code2env_candidates.jsonl
```

For offline tests or smoke runs, use `--llm-mode mock`.

Draft EnvSpecs from selected JSONL records:

```bash
python -m code2env draft-from-jsonl /tmp/code2env_candidates.jsonl \
  --output-dir /tmp/code2env_specs
```

Apply a concrete JSON fixture and compute a golden answer:

```bash
python -m code2env materialize /tmp/code2env_specs/spec.json \
  --fixture-json '{"args": ["user", "pass"], "kwargs": {}}' \
  --output /tmp/materialized/spec.json
```
