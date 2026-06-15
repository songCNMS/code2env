# task047_strict_usable_trace_quality - Task Knowledge

<!-- METADATA:SESSION=0 -->

## Knowledge Entries

1. Session 17 top10 sample validation built and smoked all 10 envs, but only rank5 was strict usable; the other 9 are weak-oracle exception builds.
2. Weak-oracle exception envs can pass rollout by matching an exception envelope, so strict runnable data must require `golden_status=real_value` and deterministic output.
3. Existing `helper_trace_complete` measures required helper tool coverage/order, not whether helper tool calls succeeded.
4. Rank5 `scripts.check-versions:check_language_version` is the key trace-quality regression target: endpoint trace was correct, but 3 helper calls failed from empty args before entrypoint.
5. Required artifacts must include machine-readable summary JSON, rollout JSONL, and export output for Session17 top10 or equivalent samples top-N.
