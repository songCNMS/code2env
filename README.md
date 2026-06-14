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

The generated runtime exposes a semantic tool set (PRD 7.5): the read-only `inspect_task` and `inspect_state` inspectors, `call_entrypoint`, dedicated `call_<helper>` tools for each safe direct callee (a key step of the main function), an optional sandboxed `call_helper` adapter, and `submit_answer`. Each tool carries an input/output JSON Schema, a `side_effects` declaration, and `provenance` (backing symbol / source span / main-function steps). Side-effecting helpers are not exposed directly; they are recorded in the entrypoint tool's provenance for sandbox-adapter follow-up. Every env stays within 3–8 tools.

Scoring is multi-dimensional (PRD 7.7 / F7): `schema_validity`, `process_progress`, `final_correctness` (exact match against the pinned source output), `efficiency` and `safety`, weighted by `reward.weights`. `step` returns a dense per-step training reward while `evaluate` returns an explainable `score_breakdown`. See [docs/mvp_usage.md](docs/mvp_usage.md#multi-dimensional-reward-prd-77--f7).

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

### Batch generation

Generate many EnvPackages across repos in one pass, auto-synthesising a JSON fixture
for each chosen function from its AST signature:

```bash
python -m code2env batch https://github.com/psf/requests https://github.com/pallets/flask \
  --output-dir generated_envs/batch --target 100 --cache-dir .code2env_cache/repos
```

For each repo the pipeline runs `scan → synth fixture → draft → build` (optionally `smoke`)
and writes a `manifest.json` under `--output-dir`. Fixture synthesis prefers functions with
no required parameters (`empty_signature`) or whose required parameters carry simple typed
annotations (`typed_signature`: `str/int/float/bool`, list/dict containers, `Optional`); a
candidate is skipped (recorded in `manifest.skipped` with a reason) when it is a method
(`not_module_level` / `requires_instance`), has a possible side effect (`possible_side_effect`,
unless `--include-side-effects`), or has an untyped/unsupported required parameter. A build
counts toward `--target` regardless of whether its smoke run passes (smoke failures are
recorded with a reason). Cloned repo source and generated packages stay out of git
(`.code2env_cache/` and `generated_envs/` are gitignored).
