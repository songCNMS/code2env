# task049_samples_valid_helper_trajectories - Sample valid helper-return trajectories

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_1 -->

## Background

Task048 / PR #35 is merged on `main` at
`d3a5af36cefba34028eac723a9145f6e3d75a037`. It added typed fixture hydration,
canonical tensor serialization, and trace-mode helper argument synthesis. The
SIMPA acceptance artifact proved that `simpa.utils.calculate:rotation` can now
produce successful semantic helper returns, not only a complete helper trace.

Coordinator now needs the same capability applied to the offline sample corpus
under `/home/leisong/data/samples`.

Full handoff:
`/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session24_valid_tool_returns/task049_samples_valid_helper_trajectories_goal.md`.

Prior references:

- Task048 SIMPA artifact:
  `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session24_typed_fixture_helper_args/worker4_pr35_simpa/`
- Session20 sample strict scan:
  `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session20_samples_strict_scan/`
- Session24 dependency venv:
  `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session24_valid_tool_returns/venv`

## Goal

Use latest `origin/main` at or after
`d3a5af36cefba34028eac723a9145f6e3d75a037` to rescan
`/home/leisong/data/samples` and produce a reviewable JSONL dataset of sample
repo trajectories where at least three dedicated semantic helper calls actually
succeed.

The dataset is not accepted if it only proves trace coverage. Every accepted
record must prove valid helper returns and final real-value correctness.

## Candidate Gate

Use the sample archive extraction rule from Sessions 16/20 and apply these gates:

- Python repository.
- Module-level function target.
- At least three dedicated semantic helper tools.
- Strict usable: `golden_status=real_value` and `determinism=deterministic`.
- No weak-oracle exception data counted as accepted.
- Unsafe side-effect/network/filesystem candidates remain skipped or blocked.

## Required Accepted-Record Predicates

Every accepted JSONL record must preserve nested `subfunction_trace` metadata and
must satisfy all of these predicates:

- `qualified=true`.
- final correctness is true, either `final.correct=true` or flattened
  `final_correct=true`.
- `subfunction_trace.helper_trace_complete=true`.
- `subfunction_trace.helper_calls_successful=true`.
- `subfunction_trace.helper_trace_valid=true`.
- `subfunction_trace.all_source_tool_returns_ok=true`.
- source tool returns for each required helper and `call_entrypoint` are
  `ok=true`.
- `golden_status=real_value`.
- `determinism=deterministic`.
- semantic helper count is at least 3.

Flattening these fields into a top-level summary is encouraged, but the nested
trace fields must remain present for compatibility.

## Outputs

Artifact root:
`/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session24_valid_tool_returns/task049_samples_valid_helper_trajectories/`.

Required artifacts:

- Final accepted JSONL containing all valid helper-return records found.
- Summary JSON.
- Summary MD.
- Validation predicate script or focused validation report.
- Blocker breakdown for rejected candidates with at least three semantic helpers.

Summary must include:

- repos scanned;
- candidates scanned;
- envs built;
- strict usable env count;
- valid helper-return rollout count;
- accepted env IDs and symbols;
- blocker breakdown for rejected at-least-three-helper candidates;
- dependency setup and any coordinator-only paths used.

If fewer than 5 accepted records are found, the blocker breakdown is mandatory
and must be specific enough for the next implementation task.

## Validation Requirements

Implementation/data owner must provide:

- focused validation predicates for the output JSONL and summary;
- full `python3 -m pytest -q` on the product head used for generation;
- final JSONL and summary JSON/MD artifact paths;
- explicit count of accepted records;
- blocker breakdown if accepted records < 5;
- default behavior impact statement.

Independent tester must validate the exact generation head and artifacts:

- focused predicate command/result;
- full `python3 -m pytest -q` result or reason if reusing an unchanged validated
  main head;
- JSONL line count and accepted record predicates;
- sample-specific spot checks of nested `subfunction_trace`;
- blocker breakdown quality if accepted records < 5;
- residual risks and unverified areas.

## Assignment

- Team: `code2env`
- Team lead: `intern_code2env_lead`
- Implementation/data generation owner: `intern_code2env_worker_1`
- Candidate/blocker audit support: `intern_code2env_worker_4`
- Independent tester/validator: `intern_code2env_worker_2`

Worker availability decision:

- `intern_code2env_worker_1`, `intern_code2env_worker_2`, and
  `intern_code2env_worker_4` are currently Idle and are assigned.
- `intern_code2env_worker_3` still reports Working on `task032_qa_session3_fixes`.
- `intern_code2env_worker_5` still reports Working on `task041_rerun_rollouts_v3`.
- This task has one canonical JSONL output, so one owner must control the final
  generation path. Worker_4 is used for parallel candidate/blocker audit rather
  than a competing generator; worker_2 remains independent tester.

## Reporting Requirements

Worker reports must include:

- exact code head used;
- commands and results;
- artifact paths;
- accepted record count;
- accepted env IDs/symbols;
- blocker categories and counts;
- whether SIMPA `simpa.utils.calculate:rotation` appears as an anchor;
- dependency setup;
- default behavior impact;
- residual risks.
