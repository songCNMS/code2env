# task046_rich_fixture_min3_qlib - Rich fixtures for qlib min-3 semantic-helper envs

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

Session 15 continues from task045. `code2env batch --min-semantic-helpers 3` now correctly gates to qlib candidates with at least three direct safe semantic helper tools, but the pinned qlib constrained run still produces zero envs because all six gate-passing candidates fail fixture synthesis. Full handoff: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session15_rich_fixture_min3_qlib_goal.md`.

Pinned qlib repo: `/home/leisong/codes/work-agents/intern_code2env_coordinator/debug/qlib_cache/d7cf7c8de0969b81` at commit `d5379c520f66a39953bad76234a7019a72796fd0`.

## 任务目标

Implement a general rich fixture descriptor/hydration and canonical serialization mechanism so at least one safe qlib `--min-semantic-helpers 3` candidate can build into a usable EnvPackage and produce a subfunction-trace rollout artifact. Preserve default JSON fixture behavior and strict side-effect safety.

## 当前证据

Session 14 verified:

```bash
SETUPTOOLS_SCM_PRETEND_VERSION=1.0.0 python3 -m code2env batch \
  /home/leisong/codes/work-agents/intern_code2env_coordinator/debug/qlib_cache/d7cf7c8de0969b81 \
  --target 20 --min-semantic-helpers 3 --no-install-deps --no-smoke --determinism-runs 2
```

Result: `candidates_scanned=2860`, `semantic_gate_passed=6`, `draft_ok/build_ok/usable=0/0/0`.

Six gate-passing blockers:

- `scripts.data_collector.utils:calc_adjusted_price`: `unsupported_param_type:df:DataFrame`; helpers `calc_paused_num`, `generate_minutes_calendar_from_daily`, `get_1d_data`.
- `qlib.backtest.profit_attribution:brinson_pa`: `untyped_required_param:positions`; helpers `decompose_portofolio`, `get_benchmark_weight`, `get_stock_group`; validate qlib provider side effects/deps before forcing.
- `qlib.contrib.model.pytorch_tra:transport_daily`: `untyped_required_param:all_preds`; helpers `minmax_norm`, `loss_fn`, `sinkhorn`; torch-style inputs.
- `scripts.data_collector.contrib.future_trading_date_collector.future_trading_date_collector:future_calendar_collector`: `unsupported_param_type:qlib_dir:None`; helpers `generate_qlib_calendar`, `read_calendar_from_qlib`, `write_calendar_to_qlib`; likely network/filesystem side effects, keep skipped unless sandboxed safely.
- `qlib.contrib.model.pytorch_tra:transport_sample`: `untyped_required_param:all_preds`; helpers `minmax_norm`, `loss_fn`, `sinkhorn`; torch-style inputs.
- `qlib.contrib.report.analysis_position.parse_position:get_position_data`: `unsupported_param_type:label_data:DataFrame`; helpers `_add_bench_to_position`, `_add_label_to_position`, `_calculate_label_rank`.

Current code seams:

- `code2env/batch.py:synthesize_fixture()` only emits plain JSON scalar/container fixtures and returns `unsupported_param_type` for rich annotations.
- `code2env/executor.py:run_symbol_subprocess()` JSON-serializes `{args, kwargs}` and `call_symbol()` passes values directly to target functions.
- `code2env/executor.py:serialize_value()` falls back to `repr` for non-JSON return values.
- `code2env/runtime.py:_call_source()` ultimately uses executor subprocess calls, so fixture hydration must work for golden generation and runtime tool calls.

## 实现范围

- Introduce JSON-safe fixture descriptors for common safe rich objects:
  - pandas `DataFrame`, `Series`, timestamp-like values;
  - numpy arrays/scalars;
  - torch tensors when `torch` is importable;
  - `pathlib.Path` / temporary directory fixtures only when filesystem behavior is sandboxed and safe.
- Hydrate descriptors inside the executor subprocess before calling the source function. Existing plain JSON fixtures must remain unchanged.
- Canonically serialize rich return values:
  - pandas `DataFrame`/`Series` with deterministic data/index/columns metadata;
  - numpy arrays/scalars with shape/dtype/data payloads;
  - torch tensors with shape/dtype/data payloads when `torch` is available;
  - keep clear weak-oracle/skip behavior for unavailable optional dependencies.
- Add provenance/audit fields to fixture records or manifest records so reviewers can tell which params were synthesized by rich fixture logic.
- Keep side-effect safety strict. Network/filesystem-writing candidates must remain skipped with explicit reasons unless sandboxed safely.
- Prefer a general descriptor/hydration mechanism over hard-coded opaque qlib payloads. Qlib-specific minimal safe examples are acceptable only as fixture synthesis policies layered on the general descriptors.

## 验收标准

- Default scalar fixture synthesis and default `generate_batch` / `code2env batch` behavior remain backward compatible.
- Focused tests cover descriptor hydration into pandas `DataFrame` and `Path`.
- Focused tests cover canonical serialization for pandas/numpy and torch when available; torch tests must skip cleanly when `torch` is missing.
- Focused tests cover a qlib-style synthetic function with at least three semantic helpers that builds, smokes, and produces a subfunction trace rollout using hydrated fixtures.
- Unsafe network/filesystem candidates remain skipped or clearly marked unsafe; do not broaden side-effect candidates into runnable envs.
- Full `python3 -m pytest -q` passes.
- Pinned qlib constrained batch with `--min-semantic-helpers 3` no longer ends at `draft_ok=0/build_ok=0` unless every gate-passing candidate is explicitly unsafe or blocked by missing optional dependencies with clear skip reasons.
- Target outcome: at least one safe qlib min-3 candidate has `build_ok=1`, `golden_status=real_value`, `determinism=deterministic`, and `usable=1`.
- For every built usable qlib env from the constrained run, run `code2env rollout --trace-mode subfunctions --llm-mode mock`; run endpoint mode when feasible and record precise reasons if not feasible.
- Validate/export rollout JSONL with `code2env rollout-export`.

## 分配信息

- Team: code2env
- Team lead: intern_code2env_lead
- Implementation worker: intern_code2env_worker_1
- Independent code/test validator: intern_code2env_worker_4
- Independent qlib batch + rollout/export validator: intern_code2env_worker_2
- Worker_3 and worker_5 are currently marked Working on older tasks, so they are not assigned in this dispatch to avoid overloading stale runner/test tasks.
- Save Session 15 artifacts under `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session15_rich_fixture_min3_qlib/`.

## 回报要求

Implementation worker must report PR id, focused tests, full pytest, qlib batch summary, rollout/export artifact paths, default behavior impact, and residual risks via mailbox. Tester workers must independently report command lines, results, environment, PASS/FAIL by acceptance item, artifact paths, and uncovered risk.
