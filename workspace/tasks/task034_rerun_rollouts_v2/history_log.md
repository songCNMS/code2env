# task034_rerun_rollouts_v2 - History Log

<!-- METADATA:SESSION=2 -->

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

## Session 2 - 2026-06-13 - 收尾 task024 PR#15 + 待命 task034

- lead 授权 self-merge task024 文档 PR#15：在 task024 分支 set README Completed、status 同步为当前 Working task034（避免 merge 回退 main 状态）、精炼 Session2 经验到个人 knowledge.md。
- PR#15 首次 merge 报 not mergeable（分支基线旧）→ `git merge origin/main`（无冲突）→ push → 重试 squash merge 成功（MERGED 2026-06-14T05:41:31Z）。main 上 task024 README=Completed、status=Working task034。删本地 task024 分支。
- ⚠️ **踩坑/注意**：playbook merge 收尾 step8 清理 `../outputs` 把我 Session2 的 `outputs/phase3`（gen manifest build_ok=100、EnvPackages、orchestrator run_rollouts.py）一并删了。**但可恢复**：coordinator outputs（旧 rollouts/100 + report）在另一路径未删；`.code2env_cache/repos`（克隆源）完好 → batch 确定性可复现同一 100 env 集。
- **task034 启动调整**：Step1 先重新 `code2env batch <5 Git URLs> --target 100`（确定性复现 env 集）作为"装依赖前"基线，再用 w1 机制装依赖重算 golden 得 v2 manifest；"装依赖前后对比"的 before 也可参考 coordinator 旧 report.json（smoke_ok=56、flask smoke 0 等）。
- 依赖进度（lead 告知）：task031(B) 已 APPROVE+w3 验证中；task030(A)/task033(报告) 实现中。三 PR 全 merged 后 lead ping 我启动。
- 当前：task024 已 Completed 收尾；task034 待命。
