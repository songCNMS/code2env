# task048_typed_fixture_helper_args - Task Knowledge

<!-- METADATA:SESSION=1 -->

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
6. PR opened at https://github.com/songCNMS/code2env/pull/34 from branch
   `intern_code2env_worker_1/task048_typed_fixture_helper_args` to `main`.
