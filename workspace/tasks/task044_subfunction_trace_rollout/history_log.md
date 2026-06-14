# task044_subfunction_trace_rollout - History Log

<!-- METADATA:SESSION=2 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_2` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-14 UTC - Task accepted by worker_2

- 接受 task044，准备在分支 `intern_code2env_worker_2/task044_subfunction_trace_rollout` 实现 formal subfunction/decomposed trace rollout mode。
- 创建 PR #30：https://github.com/songCNMS/code2env/pull/30。
- 验收关注：默认 rollout 行为不变、trace mode helper 顺序可机读、focused/full pytest、3-env trace-mode evidence，独立 tester 为 worker_4。

## Session 2 - 2026-06-14 UTC - Implemented trace mode and local validation

- 实现 `--trace-mode subfunctions`：rollout 从 EnvSpec/ToolSpec provenance 抽 direct semantic helper 序列，trace prompt 要求 helpers -> call_entrypoint -> submit_answer，结果写入 `subfunction_trace` metadata。
- 默认模式保持 `call_entrypoint -> submit_answer` 行为；CLI mock trace mode 使用 deterministic `ScriptedTraceSolveChat` 产出离线 evidence，不调用 endpoint。
- focused tests：`python3 -m pytest -q tests/test_rollout.py tests/test_rollout_export.py` -> 38 passed；full tests：`python3 -m pytest -q` -> 156 passed。
- 3-env evidence 使用 Session 7 packages：compress_feature_window、summarize_trading_window、normalize_symbol_bundle 均 `qualified=True`、`final.correct=True`、`helper_trace_complete=True`、`entrypoint_after_helpers=True`。
