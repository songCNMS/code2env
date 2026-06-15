# task050_dependency_aware_samples_valid_trajectories - Dependency-aware sample valid trajectories

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_1 -->

## Background

Task049 produced one strict valid helper-return trajectory from the sample
corpus:

- `code2env.simpa.utils.calculate.rotation.2b54724b.v1`
- `simpa.utils.calculate:rotation`
- `semantic_helper_count=3`
- `helper_trace_complete=true`
- `helper_calls_successful=true`
- `helper_trace_valid=true`
- `all_source_tool_returns_ok=true`
- `final_correct=true`
- `golden_status=real_value`
- `determinism=deterministic`

The quality bar was correct, but accepted count was only 1. The blocker
breakdown showed dependency/runtime and weak-oracle failures from the broad
sample audit:

- samples=200
- python worktrees=38
- candidates=12063
- semantic_gate_passed=83
- envs_built=30
- strict_usable=1
- accepted_shortfall=4
- blockers included `strict_unusable:weak_oracle=29`, `ModuleNotFoundError=20`,
  `not_module_level=8799`, `insufficient_semantic_helpers=2825`,
  `possible_side_effect=356`, `untyped_required_param=44`, and
  `unsupported_param_type=8`.

Task050 must try to increase accepted strict valid helper-return trajectories by
running dependency-aware sample reruns. It must not weaken task049 quality
gates.

Full handoff:
`/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session25_dependency_aware_samples/task050_dependency_aware_samples_valid_trajectories_goal.md`.

Relevant prior artifacts:

- Task049 artifact root:
  `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session24_valid_tool_returns/task049_samples_valid_helper_trajectories/`
- Session20 sample strict scan:
  `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session20_samples_strict_scan/`
- Task048/PR #35 typed fixture and helper argument implementation.

## Goal

Use latest `origin/main` at or after
`438d13a12111c78422721bbf3dea5482ccf829b4` to rerun `/home/leisong/data/samples`
with dependency installation enabled and produce more strict valid
helper-return trajectories, if available.

Accepted count should increase beyond task049 when dependencies unblock
strict-real deterministic candidates. If accepted_count remains below 3, the
deliverable must include a concrete blocker breakdown that explains why.

## Main Run Requirements

The main accepted-data run must:

- not use `--no-install-deps`;
- use a dedicated venv cache under the task050 artifact root;
- use `--require-real-value`;
- use `--min-semantic-helpers 3`;
- include determinism checking;
- preserve trace-mode subfunctions and helper-return metadata;
- prefer targeted reruns of task049 dependency-likely blockers before expensive
  full-sample reruns.

If existing product behavior is insufficient, worker_1 may make a small PR
change that improves dependency-aware sample reruns without weakening default
safety. Acceptable examples include dependency attempt metadata, clearer
system-dependency skip reasons, safer timeout or allowlist controls, or fixing
sample batch plumbing that accidentally forces no-install behavior.

## Accepted Record Gate

Every accepted JSONL record must satisfy all of these predicates:

- real sample repository target;
- `semantic_helper_count >= 3`;
- `golden_status == real_value`;
- deterministic;
- `helper_trace_complete == true`;
- `helper_calls_successful == true`;
- `helper_trace_valid == true`;
- `all_source_tool_returns_ok == true`;
- all source helper tools and `call_entrypoint` return `ok=true`;
- `final_correct == true`;
- no weak-oracle exception correctness is accepted.

Trace completeness alone is insufficient. Helper tool calls must succeed.

## Required Blocker Breakdown

If accepted_count is below 3, summary JSON/MD must categorize blockers at least
into:

- dependency install failed;
- system-only dependency, for example `bpy`;
- package metadata or import path issue;
- CLI/stdout executor envelope issue;
- untyped or unsupported required params;
- side-effect or network sandbox rejection;
- helper argument synthesis still unavailable.

The blocker breakdown should include counts and representative examples.

## Outputs

Artifact root:
`/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session25_dependency_aware_samples/task050_dependency_aware_samples_valid_trajectories/`.

Required artifacts:

- accepted JSONL;
- summary JSON;
- summary MD;
- rollout JSONL/export artifacts for accepted records;
- dependency-aware batch manifest or equivalent audit manifest;
- focused validation script or focused validation report;
- dependency install/status evidence and blocker breakdown.

## Validation Requirements

Implementation/data owner must report:

- exact PR/head or no-product-code data head;
- commands and results;
- dependency-aware sample commands and venv cache path;
- focused validation predicate result;
- full `python3 -m pytest -q` if product code changed, or explicit reason if
  metadata/data-only work reuses current main tests;
- accepted JSONL and summary paths;
- accepted_count and per-record predicates;
- blocker breakdown if accepted_count < 3;
- default behavior impact and residual risks.

Independent tester must validate the exact owner head and artifacts:

- checkout/fetch exact head;
- run focused validation predicate;
- run full `python3 -m pytest -q` for product-code changes or justify reuse for
  metadata/data-only work;
- verify every accepted record has all required predicates;
- verify source helper returns and `call_entrypoint` are `ok=true`;
- verify no weak-oracle records are accepted;
- assess blocker breakdown quality if accepted_count < 3;
- report PASS/FAIL by acceptance item, commands/results, environment, artifact
  paths, and residual risk.

## Assignment

- Team: `code2env`
- Team lead: `intern_code2env_lead`
- Implementation/data owner: `intern_code2env_worker_1`
- Dependency/blocker audit support: `intern_code2env_worker_4`
- Independent tester: `intern_code2env_worker_2`

Worker availability decision:

- `intern_code2env_worker_1`, `intern_code2env_worker_2`, and
  `intern_code2env_worker_4` are Idle and are assigned.
- `intern_code2env_worker_3` still reports Working on `task032_qa_session3_fixes`.
- `intern_code2env_worker_5` still reports Working on `task041_rerun_rollouts_v3`.
- This task has one canonical accepted JSONL, so worker_1 owns generation.
  Worker_4 supports dependency/blocker audit in parallel instead of producing a
  competing final JSONL. Worker_2 remains independent tester.

## Reporting Requirements

Final lead report must include:

- task id;
- PR/head/merge status;
- test commands and results;
- artifact root;
- accepted JSONL path;
- summary JSON/MD paths;
- accepted_count;
- per-record predicates;
- dependency-aware blocker breakdown when accepted_count < 3;
- default behavior impact;
- residual risks.
