# task044_subfunction_trace_rollout - Task Knowledge

<!-- METADATA:SESSION=4 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_2`。
2. Coordinator handoff 位于 `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session8_subfunction_trace_rollout_goal.md`，要求新增 formal trace mode 且默认 black-box rollout 不变。
3. trace metadata 使用顶层 `subfunction_trace` namespace，保留既有 RolloutResult 必填字段不变，rollout-export validation 对额外字段保持兼容。
4. 本地 trace evidence 未用 endpoint：通过 CLI `main()` + `--llm-mode mock --trace-mode subfunctions` 调用 deterministic `ScriptedTraceSolveChat`，输出在 worker 本地 `outputs/task044_trace_evidence/`。
5. PR #30 可用 GitHub REST 复核 implementation head：`a79192f27ea4e282cd6d0dc95c6ae9620148a638`，`gh pr diff 30 --name-only` 包含 rollout/cli/test 实现文件。
6. Lead approval + w4 validation PASS 后，PR merge 前需先把 task metadata 置 Completed、worker status 置 Idle 并随 PR 合入。
