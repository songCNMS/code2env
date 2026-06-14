# task046_rich_fixture_min3_qlib - Task Knowledge

<!-- METADATA:SESSION=6 -->

## Knowledge Entries

1. Coordinator goal: unblock qlib `--min-semantic-helpers 3` candidates that passed task045 gate but all failed fixture synthesis.
2. Current rich fixture seams are `code2env/batch.py:synthesize_fixture`, `code2env/executor.py:call_symbol/run_symbol_subprocess/serialize_value`, and runtime `_call_source` via executor subprocess.
3. Pinned qlib N=3 gate passers include pandas DataFrame candidates, torch-style `all_preds` candidates, and unsafe network/filesystem candidates; unsafe candidates must remain skipped unless sandboxed safely.
4. Session 15 success requires at least one safe qlib min-3 env with `build_ok=1`, `golden_status=real_value`, `determinism=deterministic`, `usable=1`, plus subfunction trace rollout/export evidence when feasible.
5. Worker_4 validation scope is code/tests only until PR arrives: confirm rich descriptor hydration, canonical serialization, default behavior preservation, unsafe candidate skipping, focused tests, and full pytest; worker_2 owns pinned qlib batch plus rollout/export validation evidence.
6. PR#32 head `7635f5289bd577bbb7d297ae129e3164730b3beb` is metadata-only, so task046 acceptance cannot be validated until worker_1 pushes implementation and focused tests.
7. Session 5 stop-hook correction aligned task046 history/task knowledge metadata with the active worker session; validation result remains unchanged.
8. PR#32 head `750a714d8fbd8b1b5ad360ba24e7fb990a44a464` has rich fixture implementation and tests, but independent validation found a blocker: `Path` fixture synthesis plus incomplete filesystem side-effect detection can run source-tree writes in default batch mode.
9. Local dependency environment for Session 6 validation: pandas and numpy installed, torch missing; torch descriptor/serialization test skipped as designed.
