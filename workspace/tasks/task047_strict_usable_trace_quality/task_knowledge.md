# task047_strict_usable_trace_quality - Task Knowledge

<!-- METADATA:SESSION=2 -->

## Knowledge Entries

1. Session 17 top10 sample validation built and smoked all 10 envs, but only rank5 was strict usable; the other 9 are weak-oracle exception builds.
2. Weak-oracle exception envs can pass rollout by matching an exception envelope, so strict runnable data must require `golden_status=real_value` and deterministic output.
3. Existing `helper_trace_complete` measures required helper tool coverage/order, not whether helper tool calls succeeded.
4. Rank5 `scripts.check-versions:check_language_version` is the key trace-quality regression target: endpoint trace was correct, but 3 helper calls failed from empty args before entrypoint.
5. Required artifacts must include machine-readable summary JSON, rollout JSONL, and export output for Session17 top10 or equivalent samples top-N.
6. PR opened at https://github.com/songCNMS/code2env/pull/33 from branch `intern_code2env_worker_1/task047_strict_usable_trace_quality` to `main`.
7. Product decision: `--require-real-value` keeps default batch behavior unchanged, but makes `--target` count only strict usable (`real_value` + deterministic) envs while weak-oracle/nondeterministic builds remain audited.
8. Trace-quality decision: keep compatibility field `helper_trace_complete` for coverage/order, and add `helper_calls_successful` plus `helper_trace_valid` so TypeError helper calls are visible as strict trace failures.
9. Evidence note: do not use `--per-repo-limit 1` as the sole Session17 top10 proof because ranks 4 and 5 share `niklas-heer/speed-comparison`, allowing rank4 to consume the repo slot and skip the known strict usable rank5 target.
10. Acceptance evidence uses exact Session17 top10 package replay at `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session18_strict_usable_trace_quality/w1_session17_top10_rerun`, which proves strict_usable 1/10 and exposes rank5 helper strict trace failure metadata.
