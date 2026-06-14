# task014_qa_reward_e2e - History Log

<!-- METADATA:SESSION=2 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_5` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - Worker 接受任务 + 准备测试计划

- 接受 task，建分支 `intern_code2env_worker_5/task014_qa_reward_e2e`，状态 Idle→Working。
- 读 PRD 7.7（五维 reward 权重）、runtime.py 现状、tests/test_mvp.py。
- 基线（main HEAD，task011 合入前）：`pytest tests/ -q` = 13 passed。
- 基线 e2e 全链路在临时 sample repo dry-run 验证可绿：scan→select(--llm-mode mock)→draft-from-jsonl→materialize→build→smoke，smoke ok=true、score=1.0。
- 测试计划写入 task_knowledge.md（A: task011 PR 验证 / B: 全链路回归 / C: mailbox 回报）。
- 等 team_lead ping task011 分支就绪后实测。

## Session 2 - 2026-06-13 - A 轮：task011 多维 reward 独立验证

- 环境：分支 `intern_code2env_worker_2/task011_multidim_reward`（PR#8，HEAD fcb5e2c），base main，python3 3.12.3。
- 全量单测：`python3 -m pytest tests/ -q` = **23 passed**（含新增 test_reward.py 10 例），与 worker_2 自测一致。
- 独立验证（构造 5 类轨迹，未改 worker_2 代码，工作树保持 clean）逐条结论：
  - PASS step/evaluate 均经 `_compute_breakdown()` 按 `self.weights`(=spec.reward.weights，缺省回退 DEFAULT_REWARD_WEIGHTS) 加权五维。
  - PASS score_breakdown 五维各含 raw/weight/weighted/detail，total=clamp(Σweighted)∈[0,1]。
  - PASS process_progress 阶段化：explore→execute_source→submit_after_progress，仅 explore 时 1/3、smoke 3/3。
  - PASS efficiency：7 重复 inspect + 超步数未提交 → raw=0.0（penalty=waste/max_steps，未提交超步 +0.5）。
  - PASS safety：network 沙箱违例 → raw=0.0（clamp(1-violations)）。
  - PASS schema_validity：未知 tool → raw=0.0（valid/总 actions）。
  - PASS scripted_smoke 正确轨迹 ok=true、evaluation.score=1.0、五维 weighted 均非零。
  - PASS 训练 shaping 与 evaluation 分离：step 返回 PBRS 增量(Δtotal)，Σ=final−初始势(0.15)=0.85；evaluate 返回绝对加权 total=1.0。
- ⚠️ 发现（非阻塞，需 lead/worker_2 确认）：spec.reward.weights 缺省 = 0.05/0.20/0.65/0.05/0.05，与 PRD 7.7 默认表 0.05/0.25/0.50/0.10/0.10 不一致（机制正确、两者均和=1.0，仅默认值偏离）。runtime DEFAULT_REWARD_WEIGHTS 与 spec.py 一致（自洽）。
- 次要：初始势 0.15（schema/efficiency/safety 无动作时乐观取 raw=1.0），标准 PBRS，不影响 evaluation score。
- A 轮结论：**全部验收 PASS**；1 个权重默认值 discrepancy 已 mailbox 回报 lead。

