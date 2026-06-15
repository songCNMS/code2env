# intern_code2env_worker_1 - 状态

<!-- METADATA:STATUS=Working,TASK=task049_samples_valid_helper_trajectories,ROLE=worker,TEAM_ID=code2env -->

| 字段 | 值 |
|------|-----|
| Name | intern_code2env_worker_1 |
| Status | Working |
| Role | worker |
| Team | code2env |
| Current Task | task049_samples_valid_helper_trajectories |
| PR | https://github.com/songCNMS/code2env/pull/36 |
| Session | 1 |

## Recent Progress

- Session 1 accepted task049_samples_valid_helper_trajectories; PR #36 opened for sample corpus valid helper-return trajectory generation.
- Session 3 task047 merge authorization received after W2 validation PASS; completion metadata prepared for PR #33 squash merge with no product-code changes after validated head `e48507e`.
- Session 2 task047 implementation/evidence is pushed to PR #33: explicit `--require-real-value` strict usable batch mode plus helper-call success/strict trace-quality metadata.
- Task047 focused verification: `python3 -m pytest -q tests/test_batch.py tests/test_rollout.py` -> 48 passed; full `python3 -m pytest -q` -> 178 passed, 1 skipped.
- Session17 exact top10 replay artifacts are under `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session18_strict_usable_trace_quality/w1_session17_top10_rerun`: build_ok 10, smoke_ok 10, weak_oracle 9, real_value 1, deterministic 1, strict_usable 1, rollout exports 10.
- Rank5 regression target `niklas-heer/speed-comparison` / `scripts.check-versions:check_language_version` is included in the exact replay summary and shows `helper_trace_complete=true`, `helper_calls_successful=false`, `helper_trace_valid=false`, with 3 `argument_unavailable` helper failures.
- Session 2 implementation for task046 is pushed to PR #32 at `750a714`: rich fixture descriptors/hydration, canonical serialization, qlib calc_adjusted_price fixture policy, runtime env replay for generated packages, and focused regression tests.
- Verification before WIP push: `python3 -m pytest -q tests/test_envdeps.py tests/test_rich_fixtures.py` -> 26 passed, 1 skipped; `python3 -m pytest -q` -> 169 passed, 1 skipped.
- Pinned qlib min-3 batch regenerated under `outputs/session15_rich_fixture_min3_qlib/w1_batch_target20_deps_optional_envreplay`: scanned 2860, semantic_gate_passed 6, build_ok 2, real_value 1, usable 1.
- Mock subfunction rollout/export succeeded under `outputs/session15_rich_fixture_min3_qlib/w1_rollouts_envreplay`; endpoint `gpt-oss-120b` was probed reachable but rollout produced no output after multiple minutes and was stopped.
- Session 3 validation blocker fix: source-root Path descriptors now reject absolute/outside-root paths before mkdir, and default batch no longer synthesizes generic Path annotations; focused `tests/test_rich_fixtures.py tests/test_batch.py` -> 30 passed, 1 skipped; full pytest -> 175 passed, 1 skipped.
- Endpoint cleanup check found no lingering rollout process; only the `pgrep` check command matched.
- Session 4 stale queued checkpoint handled: verified PR #32 is no longer bootstrap-only; current product-code head is `65db7ed` with rich fixture implementation, path confinement, and default Path skip included. Mailbox progress report sent again with current head/status.
- Session 5 merge authorization received; completion metadata prepared for PR #32 squash merge after worker_4 and worker_2 validations passed.
- Session 1 accepted task047_strict_usable_trace_quality; PR #33 opened for strict usable filtering and helper trace quality implementation.
- Task047 product slice implemented locally: `--require-real-value` strict usable batch mode/counters plus helper-call success trace metadata; focused `tests/test_batch.py tests/test_rollout.py` -> 48 passed.
