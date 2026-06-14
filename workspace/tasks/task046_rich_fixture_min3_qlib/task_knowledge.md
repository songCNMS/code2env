# task046_rich_fixture_min3_qlib - Task Knowledge

<!-- METADATA:SESSION=1 -->

## Knowledge Entries

1. Coordinator goal: unblock qlib `--min-semantic-helpers 3` candidates that passed task045 gate but all failed fixture synthesis.
2. Current rich fixture seams are `code2env/batch.py:synthesize_fixture`, `code2env/executor.py:call_symbol/run_symbol_subprocess/serialize_value`, and runtime `_call_source` via executor subprocess.
3. Pinned qlib N=3 gate passers include pandas DataFrame candidates, torch-style `all_preds` candidates, and unsafe network/filesystem candidates; unsafe candidates must remain skipped unless sandboxed safely.
4. Session 15 success requires at least one safe qlib min-3 env with `build_ok=1`, `golden_status=real_value`, `determinism=deterministic`, `usable=1`, plus subfunction trace rollout/export evidence when feasible.
5. PR opened at https://github.com/songCNMS/code2env/pull/32 from branch `intern_code2env_worker_1/task046_rich_fixture_min3_qlib` to `main`.
