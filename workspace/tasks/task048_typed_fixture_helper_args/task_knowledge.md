# task048_typed_fixture_helper_args - Task Knowledge

<!-- METADATA:SESSION=11 -->

## Knowledge Entries

1. Session24 proved that missing packages and typed value gaps are separate
   problems: SIMPA imports can be resolved, but `torch.cos(float)` still fails
   because helper args are plain JSON floats.
2. Acceptance must not count weak exception oracles, relaxed path-only traces, or
   helper calls that return `ok=false`.
3. The minimum typed fixture product surface is JSON-safe descriptors for
   `torch.Tensor` and `numpy.ndarray`, executor hydration before source calls,
   and canonical return serialization.
4. Helper argument synthesis must record provenance so consumers can distinguish
   synthesized arguments from model-supplied arguments.
5. If SIMPA cannot pass due dependency/runtime constraints, the implementation
   still needs a real sample repo alternative with at least three semantic helper
   tools and a clear SIMPA blocker.
6. A bootstrap PR with only task/status metadata is not a validation-ready
   implementation head. If that state repeats without a worker ready report,
   reassign the implementation owner and keep the independent tester reserved for
   the eventual exact product-code head.
7. Worker_4 acceptance uses branch
   `intern_code2env_worker_4/task048_typed_fixture_helper_args`; PR #34 is
   superseded and must not be treated as the task048 acceptance head.
8. WIP PR #35 at head `b47dd5f` is reviewable but not validation-ready; w2 should
   wait for the ready mailbox with full pytest plus real-sample rollout artifact
   flags.
9. SIMPA helper calls can exceed the default 3s runtime timeout on cold imports;
   the ready artifact uses the documented Session 24 venv and a 30s runtime
   timeout so validation measures typed helper behavior rather than import
   latency.
10. The accepted SIMPA evidence path is
    `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session24_typed_fixture_helper_args/worker4_pr35_simpa/`
    with `validation_summary.json`, `validation_summary.md`, and
    `rollouts/rollouts.jsonl`.
11. PR #35 needed a current `origin/main` merge to clear GitHub's DIRTY merge
    state; the merge-clean validation head is newer than the earlier `9704b92`
    ready-evidence checkpoint but does not change product code.
12. Lead checkpoint traffic can advance task docs on `origin/main` while worker_4
    is preparing handoff; resolve task history by preserving lead-authored
    sessions and appending the worker repair/ready session, then report the
    final pushed PR head.
