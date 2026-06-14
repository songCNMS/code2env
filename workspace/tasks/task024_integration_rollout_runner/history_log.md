# task024_integration_rollout_runner - History Log

<!-- METADATA:SESSION=2 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_5` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 接受任务 + 准备测试/放量计划

- 接受 task024（tester + 集成放量 runner），建分支 `intern_code2env_worker_5/task024_integration_rollout_runner`，Idle→Working。
- 读四能力 PR 文档：D1 task020 batch(w1)/D2 task021 rollout driver(w2)/D3 task022 conversation 导出(w3)/D4 task023 报告(w4)，抄录三套共享契约（gen manifest / RolloutResult-conversation / qualified 定义）。
- 核验环境：endpoints.txt（行1 gpt-5.5 外网 + 行2+ 本地 127.0.0.1 回退）存在；endpoints.vpn.txt 不存在；coordinator outputs/ 存在但无 rollouts/ 子目录（D3 自动 mkdir）；当前 main 的 llm.py 无 chat()，无 batch/rollout/rollout_export/report.py。
- 测试计划写入 task_knowledge.md：Phase1 各 PR 逐条验收，Phase3 格式门(1-3 env, mock/本地端点)→放量(≥100 env, gpt-5.5 主+本地回退)→导出 conversation JSON 到 coordinator outputs/rollouts/→汇总报告。
- 等 team_lead ping 各 PR 分支名启动 Phase1。

## Session 2 - 2026-06-13 - Phase1：PR#12 task022 conversation 导出 (D3) 验证

- 环境：分支 intern_code2env_worker_3/task022_conversation_json_export（HEAD 2758a97），base main，python3 3.12.3；只读测试、未改其码、工作树 clean。
- 全量单测：`python3 -m pytest tests/ -q` = **44 passed**（新增 tests/test_rollout_export.py），与 worker_3 自测一致。
- 独立验证（自造 RolloutResult 样例，12 项子检全 PASS）：
  - PASS write_conversation：自动 mkdir、写 `<env_id>.json`、append `rollouts.jsonl`（多次写行数递增）。
  - PASS 默认目录 = coordinator outputs/rollouts/；`CODE2ENV_ROLLOUT_EXPORT_DIR` 覆盖生效（注：import 期读取，须进程启动前设或显式传 out_dir）。
  - PASS validate_conversation：<2 轮却 qualified→报错；qualified 但无 submit_answer→报错；诚实 unqualified(1 轮/qualified=False)→通过；缺字段→报错。
  - PASS loader 往返：write→load 等价；iter_jsonl 计数正确、跳空行。
  - PASS 坏数据不落盘：类型错触发 ConversationSchemaError，且因 validate 在 mkdir 前→目标目录/文件均未创建。
  - 契约字段未改名（env_id/model/endpoint_source/.../final{submitted_answer,correct,score,score_breakdown,steps}/num_tool_call_rounds/qualified/termination_reason/retries/errors）。
- 附注（非缺陷）：diff vs main 显示 task023/task024 文档"被删"，实为 worker_3 分支基线早于这两 task 创建的 base-skew，merge against main 不会真删；CLI 另含 `rollout-export` 子命令（加分）。
- 结论：PR#12 全部验收 **PASS**，已 mailbox 回报 lead。
