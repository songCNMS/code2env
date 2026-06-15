# task048_typed_fixture_helper_args - Task Knowledge

<!-- METADATA:SESSION=2 -->

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
