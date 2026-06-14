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

### Test linking & provenance

`scan` reports both `Python files` and `Test files`: tests (anything under a `tests/`/`test/` directory, `test_*.py`, `*_test.py`, or `conftest.py`) are indexed separately into `RepoSnapshot.test_files` and never pollute the ranked source corpus.

The indexer builds a **TestLinkIndex** (`code2env.indexer.build_test_link_index`) associating each source candidate with the tests, fixtures, and golden-data files that exercise it, using import references, name similarity, and pytest fixture usage. Each link records its `evidence` and a `confidence` score.

`draft` consumes these links so every spec's `provenance.task_sources` carries **at least two diverse sources** — a `source_span` and a `signature`, plus any `test_link` / `fixture` / `golden` artifacts. When no test artifacts are linked the spec stays valid but is flagged with `test_link_status: "no_test_links_found"` and an explicit `degradation` note (oracle priority drops from test assertions to signature-level evidence).

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
