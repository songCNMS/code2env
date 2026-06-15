# task048_typed_fixture_helper_args - Typed fixtures and helper arguments

<!-- METADATA:STATUS=Open,ASSIGNEE=intern_code2env_worker_1 -->

## Background

Coordinator Session 24 found that relaxed/subfunction trajectories can be
structurally complete while still failing to collect valid source-tool returns.
There are two separate causes:

- packages generated with `--no-install-deps` can still be weak-oracle exception
  envs;
- after dependencies are installed, plain JSON fixture/helper values are still
  insufficient for typed APIs.

The preferred repro is `simpa.utils.calculate:rotation`. Session 24 resolved its
missing imports in an isolated venv, but helper calls still failed because
`rotation_x`, `rotation_y`, and `rotation_z` call `torch.cos(theta)` /
`torch.sin(theta)`, while current helper calls pass JSON floats:

`TypeError: cos(): argument 'input' (position 1) must be Tensor, not float`

Full handoff:
`/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session24_valid_tool_returns/task048_typed_fixture_helper_args_goal.md`.

Session 24 context:

- report: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session24_valid_tool_returns/session24_report.md`
- venv used for dependency probing: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session24_valid_tool_returns/venv`
- prior valid-tool-return JSONL: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session24_valid_tool_returns/valid_tool_return_trajectories.jsonl`

## Goal

Implement typed fixture hydration and deterministic helper argument synthesis so
complex sample repository environments can produce successful semantic helper
tool returns, not only `helper_trace_complete=true`.

Final acceptance requires at least one real sample repo environment with at least
three dedicated semantic helpers whose rollout JSONL proves all of the following:

- `helper_trace_complete=true`;
- `helper_calls_successful=true`;
- `helper_trace_valid=true`;
- `all_source_tool_returns_ok=true` or equivalent metadata;
- final answer correct against a real-value golden, not a weak exception oracle.

Preferred target: convert `simpa.utils.calculate:rotation` into a valid trajectory
with successful `call_rotation_x`, `call_rotation_y`, `call_rotation_z`,
`call_entrypoint`, and `submit_answer`.

If SIMPA is blocked by dependency/runtime constraints, provide an alternative
real sample repo with at least three semantic helpers and a precise SIMPA blocker.

## Workstream A - Typed Fixture Descriptors And Hydration

Implement JSON-safe descriptor support for typed values.

Required minimum:

- `torch.Tensor` scalar and simple tensor values;
- `numpy.ndarray` simple arrays;
- existing scalar/list/dict fixture behavior unchanged.

Expected behavior:

- descriptors are hydrated inside the subprocess executor before invoking source
  symbols;
- helper tools and entrypoint execution see the typed runtime value, not only raw
  JSON;
- returned tensor/ndarray values are serialized canonically as JSON payloads with
  type, dtype, shape, and data rather than opaque reprs;
- sandbox controls for network/subprocess/file safety stay unchanged.

## Workstream B - Helper Argument Synthesis

Add deterministic helper argument synthesis for subfunction trace mode.

Required behavior:

- dedicated semantic helper tools may receive synthesized args when helper
  parameters correspond to entrypoint fixture components or supported typed
  descriptor values;
- synthesized helper argument provenance is recorded in rollout metadata;
- model-supplied args and synthesized args are distinguishable;
- default rollout behavior remains unchanged unless trace/synthesis mode is
  enabled.

SIMPA desired mapping:

- entrypoint `rotation(angles)` fixture uses a tensor/list-like three-angle value;
- `call_rotation_x` receives the first angle as a hydrated tensor/scalar supported
  by torch;
- `call_rotation_y` receives the second angle;
- `call_rotation_z` receives the third angle.

If a helper cannot be safely mapped, record an explicit unavailable/blocker reason
rather than treating a failed helper call as valid.

## Workstream C - Dependency-Aware Real Sample Validation

Validation must not depend permanently on coordinator's existing venv. It may use
that venv as repro context, but final artifacts must document either:

- normal code2env dependency installation that recreates the real-value env; or
- a deterministic dependency setup used by the validation worker.

Weak exception oracles do not count for acceptance.

## Validation Requirements

Implementation worker must provide:

- focused tests for tensor/ndarray descriptor hydration and canonical
  serialization;
- focused tests for helper argument synthesis metadata and helper success/failure
  accounting;
- full `python3 -m pytest -q`;
- a PR with product code and tests;
- validation artifacts under
  `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session24_typed_fixture_helper_args/`;
- rollout JSONL showing at least one real sample repo env with at least three
  semantic helpers where helper trace complete, helper calls successful, strict
  trace valid, source tool returns ok, and final answer is real-value correct.

Independent tester must validate the exact PR head and report:

- focused test commands/results;
- full `python3 -m pytest -q` result;
- artifact paths and machine-readable summary;
- whether SIMPA passed or why it is blocked;
- any alternative sample repo evidence if SIMPA is blocked;
- residual risks.

## Required Artifacts

- Validation summary JSON.
- Validation summary MD.
- Rollout JSONL with successful helper returns.
- Exported rollout conversations if the rollout-export command supports the
  result schema.
- Short comparison against Session 24:
  - old failure: missing packages / `torch.cos(float)`;
  - new result: successful hydrated helper returns, or documented SIMPA blocker
    plus alternative real sample evidence.

## Assignment

- Team: `code2env`
- Team lead: `intern_code2env_lead`
- Implementation worker: `intern_code2env_worker_1`
- Independent tester / validation worker: `intern_code2env_worker_2`

Worker availability decision:

- `intern_code2env_worker_1` and `intern_code2env_worker_2` are Idle and assigned.
- `intern_code2env_worker_3` still reports Working on `task032_qa_session3_fixes`.
- `intern_code2env_worker_4` still reports Working on `task046_rich_fixture_min3_qlib`
  in its own workspace.
- `intern_code2env_worker_5` still reports Working on `task041_rerun_rollouts_v3`.
- This task touches executor/runtime/rollout/spec fixture contracts, so one
  implementation owner plus one independent tester is the safest split with the
  currently available workers.

## Reporting Requirements

Implementation worker must report:

- PR URL/id and exact head;
- focused and full pytest command results;
- real sample repo/package/env id used for validation;
- whether SIMPA passed or exact blocker;
- validation summary JSON/MD;
- rollout JSONL/export paths;
- default behavior impact;
- residual risks.

Tester must report:

- exact PR head validated;
- commands/results;
- PASS/FAIL by each acceptance item;
- artifact paths and counts;
- whether helper tools returned `ok=true`;
- whether final answer is correct against `golden_status=real_value`;
- residual risks and unverified areas.
