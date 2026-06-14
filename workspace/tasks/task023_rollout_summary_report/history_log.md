# task023_rollout_summary_report - History Log

<!-- METADATA:SESSION=4 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_4` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 实现 code2env report (D4)

- 接受 task023，建分支 + PR#13 (base main)。
- 新增 `code2env/report.py`：读 D1 manifest + D3 rollouts(目录优先 per-env <env_id>.json，回退 rollouts.jsonl，或直接 .jsonl) → 产出 report.md + report.json。指标：draft/build/smoke 成功率、by_repo 分布、rollout 合格率(qualified=>=2 tool 轮+submit，trust 契约 qualified 字段并可降级派生)、平均 score、低分计数、by_model；失败聚类固定可解释 tag(dependency_failure/fixture_unsynthesizable/weak_oracle/tool_granularity/format_error/other) 关键词分类，含 examples。
- `cli.py` 仅加 report subparser + 一行 dispatch + 一个 `_report` handler（减少与 w1/w2/w3 冲突面）。消费契约严格按 lead 定义(task020/task022)，未改字段名。
- 新增 `tests/test_report.py` 11 例（合成 manifest+conversation，验证统计/聚类/qualified 派生/loader 优先级/md+json 输出/空 rollouts）。`pytest tests/`=42 passed，`unittest discover`=42 OK；CLI 端到端跑通。
- 更新 README.md + docs/mvp_usage.md（report 段）。
- 下步：mailbox 回报 lead PR#13 + 自测，等 tester(w5)+lead review。

## Session 2 - 2026-06-13 - 修 w5 medium finding（失败聚类可解释性）

- w5/lead review：PR#13 功能/指标 PASS(42 passed)，但 1 个 medium 跨模块 finding：`classify_reason` 用自由词关键词，与 D1 真实 reason 串(`tag:detail`)不匹配 → `fixture_unsynthesizable` 簇恒 0、生成失败全进 `other`。
- 按 lead canonical reason→tag 映射重写 `classify_reason`（子串/前缀匹配）：dependency_failure←modulenotfound/importerror/no module named 或 `draft_error`含import；weak_oracle←golden_error*/answer_mismatch；format_error←parse_error/schema；fixture_unsynthesizable←untyped_required_param/unsupported_param_type/requires_instance/possible_side_effect/not_module_level/function_node_not_found/no_fixture；其余 other；rollout 不合格无信号→tool_granularity（保留在 rollout 聚类层）。
- 测试：合成 manifest 改用 D1 真实词汇；新增 `test_canonical_d1_vocabulary` 等 3 例覆盖全部 canonical token；更新生成聚类断言(fixture=3/dependency=1/weak_oracle=2/tool_granularity=0)。`pytest tests/`=45 passed、`unittest`=45 OK。
- 按 lead 指示**暂不 self-merge**；合并顺序 PR#14→PR#13；等 lead 确认 PR#14 merged 后再 merge origin/main 解 cli.py(report subparser)冲突+重测+self-merge。已 mailbox 回报修复完成。

## Session 3 - 2026-06-13 - lead APPROVE，hold 等合并序

- lead 核验聚类修复(b526432) APPROVE：classify_reason 子串/前缀匹配覆盖全部 canonical token，fixture_unsynthesizable 不再恒 0，测试用 D1 真实词汇 45 passed。
- 合并序更新：我排在 **PR#11(D2)** 之后（避免与 D2 在 cli.py 并发冲突）。当前 **hold**，等 lead 确认 PR#11 merged 后 ping。
- 届时动作：`git fetch && git merge origin/main` 解 cli.py(report subparser) 冲突 → `pytest tests/` 全绿 → `gh pr merge 13 --squash` → 标 task Completed/Idle → mailbox 回报。
- 本 turn 无代码改动，仅记录 hold 状态。

## Session 4 - 2026-06-13 - 合并链轮到我，self-merge PR#13 完结

- lead ping：PR#11(D2) 已 merged(1811e1e,72 passed)，合并链轮到我。
- `git fetch && git merge origin/main`：解 3 处冲突——code2env/cli.py(import+subparser+dispatch+handler 四段，保留 batch+rollout-export+rollout+report 四能力)、README.md、docs/mvp_usage.md(各保留 D2 rollout + D4 report 两段)。
- `pytest tests/`=86 passed（72 main + 14 report）；CLI `--help` 列出全部 11 子命令含 report；report 端到端复跑正常。
- self-merge PR#13（squash, commit **91544a9**, mergedAt 2026-06-14T05:02:16Z），cleanup 分支。Session2 四能力(batch/rollout/rollout-export/report)全部在 main。
- 因合并前未先翻 Completed/Idle（按 lead 简化流程直接 merge），本次用小型 bookkeeping PR (intern_code2env_worker_4/task023_complete) 补翻 README→Completed + status→Idle，self-merge。
- 已 mailbox 回报 lead squash commit。
