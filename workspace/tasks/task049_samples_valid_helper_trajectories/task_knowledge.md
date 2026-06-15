# task049_samples_valid_helper_trajectories - Task Knowledge

<!-- METADATA:SESSION=3 -->

## Knowledge Entries

1. For task049, trace completeness alone is not enough. Accepted records must
   prove helper-call success and all source tool returns ok, not just
   `entrypoint_after_helpers`.
2. Accepted records must retain nested `subfunction_trace` fields for
   compatibility even if summary/export also flattens flags.
3. If fewer than 5 valid records are found, the blocker breakdown is part of
   the deliverable, not a residual note.
4. The task may use prior Session20 archive extraction and Session24 dependency
   context, but any dependency on coordinator-only paths must be documented in
   the summary.
5. PR opened at https://github.com/songCNMS/code2env/pull/36 from branch
   `intern_code2env_worker_1/task049_samples_valid_helper_trajectories` to `main`.
6. Latest shared task history commit `3522114` is merged into the PR branch for
   Session 2 before generating canonical task049 artifacts.
7. The first scan plan uses current code over Session20 worktrees derived from
   `/home/leisong/data/samples` for the broad blocker audit, plus a current-code
   SIMPA rebuild/trace rollout using the Session24 dependency venv for an
   accepted real-value helper-return trajectory.
8. SIMPA `simpa.utils.calculate:rotation` needs a 30 second subprocess timeout
   for cold dependency imports when recomputing the real-value golden; the
   default 3 second timeout produces a weak-oracle `TimeoutExpired` and must not
   be accepted.
9. Worker4 audit-support JSON stores the full blocker counts under
   `session20_gate_summary` and `blocker_taxonomy.raw_session20_ge3_rejections`,
   not as flat top-level fields.
