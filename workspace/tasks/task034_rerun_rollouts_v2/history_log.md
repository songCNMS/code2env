# task034_rerun_rollouts_v2 - History Log

<!-- METADATA:SESSION=1 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_5` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 接受任务 + 写重跑计划

- 接受 task034（v2 重跑 runner），建分支 `intern_code2env_worker_5/task034_rerun_rollouts_v2`，Idle→Working。
- 读三依赖 task：task030(w1 装依赖+golden 重算+golden_status 字段)/task031(w2 rollout prompt 禁自造 call_entrypoint 参数)/task033(w4 报告真实 correct 率剔 weak_oracle)。
- 确认上轮假阳性根因：A) flask 等 env 未装运行依赖 → golden=ModuleNotFoundError，agent 提交同错即 exact_match=True；B) prompt 未禁 agent 自造 call_entrypoint 参数 → 与 fixture 不符假阴性。
- 核对旧产物完好并将复用：phase3 manifest(build_ok=100)、旧 rollouts/(100，**勿覆盖**)、orchestrator run_rollouts.py。
- 重跑计划写入 task_knowledge：Step0 核对 w1 接口 → Step1 装依赖重算 golden+标 weak_oracle(v2 manifest) → Step2 非 weak_oracle 子集 gpt-5.5 重跑(修正 prompt)→ rollouts_v2/ → Step3 w4 真实率报告 → Step4 回报。
- 注：task024 文档 PR#15 仍 open 待 lead merge 授权（已在接受 mail 提醒）。
- 等 lead 确认三 PR merged 后 ping 启动。
