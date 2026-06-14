# task041_rerun_rollouts_v3 - History Log

<!-- METADATA:SESSION=1 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_5` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 接受任务 + 写 v3 计划

- 接受 task041（v3 重跑 runner），建分支 `intern_code2env_worker_5/task041_rerun_rollouts_v3`，Idle→Working。
- 读三依赖：task037(w2 runtime 信封归一)/task038(w1 确定性门禁 determinism 字段)/task039(w4 report_v3 类别+v1→v2→v3 对比)；另 task035(w1 envdeps uv 兜底,PR#22) merged 后可去我的 uv wrapper。
- 抄录契约：golden_status/determinism；确定性可用集=real_value AND deterministic；report_v3 四类别。
- 确认 v1(100)/v2(75) 产物 + v2 manifest/baseline 完好，v3 写 rollouts_v3/report_v3/phase3_v3 不覆盖。
- v3 计划写入 task_knowledge：Step0 核对接口 → Step1 v3 manifest(golden_status+determinism)定确定性可用集 → Step2 该子集 gpt-5.5 重跑(信封归一应判对)→rollouts_v3/ → Step3 report_v3(真实非零 correct+类别+v1→v2→v3) → Step4 回报。
- 注：task034 文档 PR#21 仍 open（v2 交付已完成，将在接受 mail 询问是否 self-merge 收尾）。
- 等 lead 确认 task037/038/039 三 PR merged 后 ping 启动。
