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

Drive an LLM through a multi-round tool-calling rollout (D2) with `python -m code2env rollout <env_package>` (`--llm-mode mock` for an offline deterministic solve, or `--llm-model gpt-5.5 --fallback-model <local>` for live runs with automatic endpoint fallback). The driver (`code2env.rollout.run_rollout`) returns a `RolloutResult` with the full conversation, per-step actions/rewards, final score, and a `qualified` flag. See [docs/mvp_usage.md](docs/mvp_usage.md#llm-rollout-driver-d2).

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

#### Dependency install & golden status

For each repo the pipeline first builds an isolated venv (cached under
`.code2env_cache/venvs`, gitignored) and installs the declared runtime dependencies
(`requirements*.txt`, `pyproject` dependencies), so the golden answer and rollout
`call_entrypoint` execute with real third-party imports instead of producing a
`ModuleNotFoundError` that an agent could trivially "match". The interpreter is
persisted on the spec (`runtime.python_executable`) and reused by the runtime; if
that path is missing at rollout time the runtime falls back to the default
interpreter. A package that will not install is skipped (recorded with a reason),
never aborting the repo. Pass `--no-install-deps` to skip this step.

After deps are installed, each env carries a `golden_status`:

- `real_value` — the source function returned a real result; these form the
  qualified/usable set counted toward correctness.
- `weak_oracle:<reason>` (e.g. `golden_exception:ModuleNotFoundError`) — the golden
  answer is still an exception; the env is reported separately and **excluded from
  the correctness denominator** so it cannot create false positives.

`manifest.summary` reports `real_value` / `weak_oracle` counts and per-repo
`deps_status`; `manifest.repo_deps` records installed/failed packages per repo.
Running real venvs requires `python3-venv`/`ensurepip` on the host; without it the
pipeline records `deps_status: venv_failed` and falls back to the base interpreter.

### Rollout conversation export (D3)

Persist rollout results (`RolloutResult` records, one JSON object per line) as
readable per-env conversation JSON plus a merged `rollouts.jsonl`:

```bash
python -m code2env rollout-export /tmp/results.jsonl --export-dir /tmp/rollouts
```

`--export-dir` defaults to the coordinator's `outputs/rollouts/` (outside the repo,
not tracked by git, auto-created). The library API — `write_conversation`,
`validate_conversation`, `load_conversation`, `iter_jsonl` — is documented in
[docs/mvp_usage.md](docs/mvp_usage.md); `write → load` round-trips, and
`validate_conversation` enforces the shared schema (including that `qualified` is
self-consistent: `num_tool_call_rounds >= 2` and a `submit_answer` present).

### Rollout summary report

Summarize a generation `manifest.json` (from `code2env batch`) together with the
rollout conversation products into a markdown + JSON report — env generation
success rate, per-repo distribution, rollout qualified rate, mean score, and
explainable failure clusters:

```bash
python -m code2env report /path/to/manifest.json \
  --rollouts /path/to/rollouts/ \
  --output-dir /tmp/code2env_report \
  [--baseline-manifest /path/to/pre_install_manifest.json]
# writes /tmp/code2env_report/report.md and report.json
```

`--rollouts` accepts a directory (per-env `<env_id>.json` files, falling back to a
merged `rollouts.jsonl`) or a `.jsonl` file directly, and may be omitted to report
on generation only. A rollout is *qualified* when it has `>= 2` tool-call rounds
and a `submit_answer`.

The report computes a **true correct rate** from `manifest.envs[].golden_status`
(`real_value` / `weak_oracle:<reason>`): rollouts on weak-oracle envs are excluded
from the denominator (and counted separately), removing error-match false
positives from the raw correct rate. With `--baseline-manifest` (a pre-dependency
manifest) it also reports golden `error → real_value` transitions and per-repo
`smoke_ok` before/after deltas. Failure clusters use a fixed, explainable tag set:
`dependency_failure`, `fixture_unsynthesizable`, `weak_oracle`, `tool_granularity`,
`format_error`, `other`.
