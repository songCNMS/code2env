# task050_dependency_aware_samples_valid_trajectories - Task Knowledge

<!-- METADATA:SESSION=0 -->

## Knowledge Entries

1. Task050 is a data-generation and dependency-aware rerun task, not a quality
   gate relaxation task. Accepted records must meet the same strict predicates
   as task049.
2. The main accepted-data run must not pass `--no-install-deps`; if a worker uses
   no-install mode for a cheap audit, it must be clearly labeled as audit-only
   and not the accepted-data run.
3. If accepted_count stays below 3, the blocker breakdown is an acceptance
   deliverable and must distinguish dependency installation, system dependency,
   package metadata/import path, CLI/stdout envelope, untyped/unsupported
   params, side-effect sandbox, and helper-argument synthesis blockers.
4. Because dependency installation can be expensive and flaky, targeted reruns of
   task049 dependency-likely blockers are preferred before broad full-sample
   runs.
