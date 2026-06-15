# task047_strict_usable_trace_quality - Strict usable and helper trace quality

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_1 -->

## Background

Coordinator Session 18 asks us to productize two lessons from Session 17 sample validation:

- weak-oracle exception envs can build/smoke/rollout but are not runnable strict-usable data;
- subfunction trace coverage/order is not enough when required helper calls fail because no safe helper arguments were supplied.

Full handoff: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session18_strict_usable_trace_quality/task047_strict_usable_trace_quality_goal.md`.

Session 17 artifacts:

- validation JSON: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session17_samples_candidate_validation/validation_results.json`
- validation report: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session17_samples_candidate_validation/validation_results.md`
- mock trace JSONL: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session17_samples_candidate_validation/mock_trace_rollouts.jsonl`
- endpoint rank5 trace JSONL: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session17_samples_candidate_validation/endpoint_trace_rank05.jsonl`

Session 17 top10 summary:

- `draft_ok=10`, `build_ok=10`, `smoke_ok=10`
- mock `--trace-mode subfunctions` rollout/export `10/10`
- strict usable `1/10`
- weak-oracle builds `9/10`
- strict usable rank 5: `niklas-heer/speed-comparison`, `scripts.check-versions:check_language_version`, env id `code2env.scripts.check-versions.check_language_version.c4dd5023.v1`
- rank5 endpoint trace was qualified/correct/helper_trace_complete/entrypoint_after_helpers, but 3 required helper calls errored because helpers were called with empty args.

## Goal

Implement strict usable/weak-oracle product support and stricter helper-call success metadata so generated sample data can separate real runnable envs from weak-oracle exception matches and can tell whether required helper calls actually succeeded.

Default behavior must remain compatible unless a new explicit option is enabled.

## Workstream A - Strict Usable Filtering

Implement product support that prevents weak-oracle exception envs from being counted as runnable strict usable data.

Expected behavior:

- Add a batch/validation option such as `--require-real-value` or equivalent API flag.
- With the option enabled, only accept envs whose generated golden is `real_value` and deterministic.
- Add summary/manifest counters that separate `build_ok`, `smoke_ok`, `real_value`, `deterministic`, `strict_usable`, and `weak_oracle`.
- Add skip/rejection reasons for weak-oracle exception builds, preserving exception type/message for audit.
- Keep dependency probing sandboxed/isolated and avoid unsafe network execution by default. Heavy or unavailable dependencies such as `bpy`, Django app setup, and torch-heavy repos may remain dependency-blocked.

Minimum target:

- weak-oracle exception outputs are not counted as strict usable runnable envs;
- Session 17 top10 or equivalent samples top-N reports strict usable `1/10` unless additional dependencies are safely resolved to real values.

## Workstream B - Helper Trace Quality

Tighten subfunction trace quality so `helper_trace_complete=true` does not hide failed required helper calls.

Expected behavior:

- Record per required helper call success from tool result status (`tool_result.ok == true`) in `subfunction_trace` metadata.
- Add a stricter metric such as `helper_calls_successful` or `helper_trace_valid`.
- Keep existing `helper_trace_complete` compatibility if needed, but expose the stricter metric in rollout JSONL/export and summary.
- Improve helper argument synthesis when safe. If helper required parameters can be derived from entrypoint fixture values, trace mode should call helper tools with meaningful args.
- If args cannot be safely derived, record helper arg status such as `argument_unavailable`, and do not treat a TypeError call as successful strict trace quality.

Minimum target:

- rank5 trace exposes the 3 helper argument failures through strict helper-call success metadata, or safe helper argument synthesis eliminates the failures.

## Validation Requirements

Implementation worker and tester must report commands, results, environment, artifact paths, and residual risks.

Required validation:

- Focused unit tests for strict usable filtering and weak-oracle counters.
- Focused unit tests for helper-call success metadata and strict trace quality.
- Full `python3 -m pytest -q`.
- Re-run Session 17 top10 or equivalent `/home/leisong/data/samples` top-N with min semantic helpers 3 and strict usable filtering.
- Produce sample artifacts under `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session18_strict_usable_trace_quality/`:
  - JSON summary;
  - rollout JSONL records;
  - exported rollout records.
- Report:
  - scanned/validated candidate count;
  - build/smoke count;
  - weak-oracle count;
  - strict usable count;
  - endpoint/mock rollout count;
  - helper_trace_complete count;
  - helper_calls_successful / strict trace valid count.

## Assignment

- Team: `code2env`
- Team lead: `intern_code2env_lead`
- Implementation worker: `intern_code2env_worker_1`
- Independent tester / sample validation worker: `intern_code2env_worker_2`

Worker availability decision:

- `intern_code2env_worker_1` and `intern_code2env_worker_2` are idle and are assigned.
- `intern_code2env_worker_3` and `intern_code2env_worker_5` are still marked Working on older tasks.
- `intern_code2env_worker_4` still has task046 validator status in its own workspace, so it is not assigned here to avoid overlapping task ownership.
- This task touches shared batch/rollout schemas; keeping one implementation worker avoids conflicting PRs, while the independent tester covers focused tests, full pytest, and sample rerun evidence.

## Reporting Requirements

Implementation worker must report:

- PR URL/id and commit/head;
- focused tests and full pytest result;
- strict top10/top-N summary counts;
- rollout JSONL/export artifact paths;
- default behavior impact;
- residual risks.

Tester must independently report:

- exact PR head validated;
- focused tests and full pytest result;
- Session17 top10/equivalent sample rerun commands and artifacts;
- PASS/FAIL by acceptance item;
- uncovered risks.
