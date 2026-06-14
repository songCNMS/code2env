# task014_qa_reward_e2e - History Log

<!-- METADATA:SESSION=4 -->

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

## Session 3 - 2026-06-13 - B 轮：三项 P0 merge 后 main 全链路回归

- 环境：main HEAD f2b3b42（PR#9 e2825ad ToolExtractor + PR#7 c166e2f TestLinkIndex + PR#8 f2b3b42 多维 reward 均已 merge），python3 3.12.3。
- 全量单测：`python3 -m pytest tests/ -q` = **31 passed, 0 error**（与 worker_2 post-merge 一致；含 test_reward.py / test_testlink_index.py）。
- E2E 全链路（临时 sample repo，select 离线 mock），每步 rc=0、无 stderr：
  - scan → cand0=sample:normalize_name
  - select --llm-mode mock → sel.jsonl 1 行
  - draft-from-jsonl → 1 个 draft spec
  - draft（单路交叉验证）→ 同样能力
  - materialize → mat.json（golden=ADA LOVELACE）
  - build → package dir
  - smoke → ok=true、evaluation.score=1.0、correct=true
- 新能力可见性核对（PASS）：
  - 语义工具：draft 产物 tools 含 `inspect_state` 与 `call_clean_text`(call_<helper>)；6 个 tool 均带 ToolSpec.provenance。
  - provenance.task_sources = 2（>=2），kinds=[source_span, signature]。
  - smoke/evaluate 输出五维 score_breakdown，正确轨迹五维 weighted 均非零、total=1.0∈[0,1]。
- 回归判定：**无回归**，MVP 闭环基线保绿。
- 既有 discrepancy（A 轮已报）：spec.reward.weights 仍为 0.05/0.20/0.65/0.05/0.05，偏离 PRD 7.7 表 0.05/0.25/0.50/0.10/0.10；非回归、待 lead 决策，B 轮不重复阻塞。
- B 轮结论：**本轮 P0 交付最终验证 PASS**，已 mailbox 回报 lead。

## Session 4 - 2026-06-13 - 完结：self-merge PR#10，task Completed，切回 Idle

- lead 授权 self-merge QA 文档 PR#10；权重默认值偏离 PRD 7.7 已记 backlog、本轮不改。
- Merge 前更新（自己分支）：status STATUS=Idle/清空 TASK、README STATUS=Completed、精炼知识到个人 knowledge.md。
- 执行 merge PR#10，确认 state=MERGED 后清理本地分支、回 main pull。
- 通过 mailbox 向 team_lead 汇报 merge 结果。task014（A 轮 reward 验证 + B 轮全链路回归）正式完结。

