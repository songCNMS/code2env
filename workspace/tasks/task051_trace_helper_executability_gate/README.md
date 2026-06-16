# task051_trace_helper_executability_gate - Strict trace helper executability gate

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_1 -->

## Background

Task050 completed correctly with `accepted_count=0` after an install-enabled
dependency-aware sample rerun. The single strict usable env was:

- `code2env.scripts.check-versions.check_language_version.21a74cc9.v1`
- target `scripts.check-versions:check_language_version`
- `final_correct=true`
- `helper_trace_complete=true`
- `helper_calls_successful=false`
- `helper_trace_valid=false`
- `all_source_tool_returns_ok=false`

The failing helper evidence was:

- `call_get_docker_latest_version`: `TypeError`, missing `image` and
  `tag_filter` arguments.
- `call_get_github_latest_version`: `RuntimeError`, network disabled by the
  Code2Env sandbox.
- `call_entrypoint`: `ok=true`.

Coordinator code review found the product gap: `get_docker_latest_version` and
`get_github_latest_version` call `fetch_json`, which calls
`urllib.request.Request`/`urlopen`. `_partition_helpers` in `code2env/spec.py`
checks only the direct helper candidate risk flags and does not propagate
transitive side-effect/network risk through helper calls. These network helpers
were therefore exposed as `side_effects="none"` dedicated semantic tools and
became required trace helpers.

Full handoff:
`/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session27_trace_helper_executability/task051_trace_helper_executability_gate_goal.md`.

Task050 reference artifacts:

- artifact root:
  `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session25_dependency_aware_samples/task050_dependency_aware_samples_valid_trajectories/`
- run2 manifest:
  `dependency_batch/install_enabled_targeted_run2/manifest.json`
- strict env package:
  `dependency_batch/install_enabled_targeted_run2/packages/code2env.scripts.check-versions.check_language_version.21a74cc9.v1`
- failed rollout:
  `rollouts/code2env.scripts.check-versions.check_language_version.21a74cc9.v1.json`.

## Goal

Productize a stricter, auditable helper executability gate for strict
subfunction-trace data. The task must improve early helper classification and
preflight rejection without loosening accepted-data predicates.

Accepted JSONL records still require real-value deterministic final correctness
and successful helper/source returns. This task should make non-executable
helpers skipped or rejected earlier with precise metadata instead of allowing
failed helper source returns in trace-mode data.

## Required Product Work

1. Improve helper side-effect classification:
   - detect transitive helper side effects inside a module, for example
     `entrypoint -> get_github_latest_version -> fetch_json -> Request/urlopen`;
   - treat helpers that transitively call network/file/process side-effect
     helpers as sandboxed/skipped instead of `side_effects="none"` dedicated
     required helpers;
   - include network primitives such as `urlopen`, `urlretrieve`, `requests.*`,
     and `urllib.request.*` if the current side-effect vocabulary misses them.
2. Improve trace-mode required helper selection:
   - distinguish candidate semantic helpers, sandbox-safe dedicated helpers, and
     strict executable trace helpers;
   - do not force helpers into the required helper sequence when arguments
     cannot be synthesized from fixture/default/provenance;
   - record skipped or unavailable helpers with explicit reasons such as
     `transitive_side_effect`, `network_sandboxed`, or
     `argument_unavailable:<param>`.
3. Add strict trace summary metadata:
   - total dedicated semantic helper count;
   - executable required helper count;
   - skipped helper count by reason;
   - skip/rejection reason such as `insufficient_executable_semantic_helpers`
     when strict executable helper count is below the requested threshold.
4. Preserve default behavior:
   - default rollout behavior remains black-box unless trace-mode subfunctions or
     strict executable-helper filtering is requested by accepted-data flow.

## Required Tests

Focused tests must cover:

- transitive network helper classification: a top-level helper that calls another
  top-level helper that calls `urlopen`/`Request`/`requests.get` is not exposed
  as `side_effects="none"` dedicated semantic helper;
- pure helper compatibility: safe JSON-only helpers remain exposed and counted;
- trace helper preflight: helper with required unmappable parameters is skipped
  with reason instead of counted as successful required helper;
- default-mode compatibility: default rollout behavior remains black-box unless
  trace-mode subfunctions is requested.

Because product code will change, worker_1 must run:

- focused tests relevant to the implementation;
- full `python3 -m pytest -q`.

## Required Reproduction

Worker_1 must rerun or directly validate the task050 strict env:

- package/spec:
  `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session25_dependency_aware_samples/task050_dependency_aware_samples_valid_trajectories/dependency_batch/install_enabled_targeted_run2/packages/code2env.scripts.check-versions.check_language_version.21a74cc9.v1`
- target: `scripts.check-versions:check_language_version`.

Expected post-fix behavior:

- `get_docker_latest_version` and/or `get_github_latest_version` are no longer
  treated as normal `side_effects="none"` strict required helper calls when they
  are network/sandboxed or argument-unavailable;
- the env is skipped or rejected earlier as
  `insufficient_executable_semantic_helpers` or an equivalent precise reason
  when fewer than three executable helpers remain;
- if a rollout is generated, it must not claim strict validity while source
  helper returns fail;
- accepted JSONL may still have zero records if the reason is now
  preflight/classification instead of failed helper source returns.

## Outputs

Artifact root:
`/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session27_trace_helper_executability/task051_trace_helper_executability_gate/`.

Required artifacts:

- PR with product code changes;
- focused test logs;
- full pytest log;
- task050 strict env reproduction report JSON and MD;
- targeted rerun or audit summary showing executable helper counts and
  skip/rejection reasons;
- accepted JSONL only if valid records are found, validated with unchanged strict
  gates.

## Assignment

- Team: `code2env`
- Team lead: `intern_code2env_lead`
- Implementation owner: `intern_code2env_worker_1`
- Reproduction/audit support: `intern_code2env_worker_4`
- Independent tester: `intern_code2env_worker_2`

Worker availability decision:

- `intern_code2env_worker_1`, `intern_code2env_worker_2`, and
  `intern_code2env_worker_4` are Idle and are assigned.
- `intern_code2env_worker_3` still reports Working on `task032_qa_session3_fixes`.
- `intern_code2env_worker_5` still reports Working on `task041_rerun_rollouts_v3`.
- Worker_1 owns product implementation because it has immediate task050 context.
  Worker_4 supports reproduction/audit so the task050 before/after evidence is
  independently structured. Worker_2 remains the independent tester and must
  validate worker_1's exact ready head.

## Acceptance

Completion report must include:

- PR URL, exact product head, final pre-merge head, and merge commit if merged;
- implementation worker and independent tester;
- focused/full test commands and results;
- task050 strict env reproduction result;
- before/after explanation for
  `code2env.scripts.check-versions.check_language_version.21a74cc9.v1`;
- artifact root and summary paths;
- default behavior impact;
- residual risks.

No accepted-data gate may be relaxed.
