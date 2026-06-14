# task033_report_true_correct_rate - History Log

<!-- METADATA:SESSION=3 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_4` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 实现真实 correct 率 + 装依赖前后对比

- 接受 task033，建分支 + PR#20 (base main)。
- 更新 code2env/report.py（我是 D4 作者）：
  ① 消费 manifest.envs[].golden_status(real_value|weak_oracle:<reason>)；_summarize_rollouts 新增 true_correct/true_correct_rate（剔除 weak_oracle 出分母）、weak_oracle_excluded、golden_unknown、usable_total；保留原 raw correct/correct_rate。缺失 golden_status→unknown，留在分母不缩水。
  ② 新增 _dependency_comparison + `--baseline-manifest`：golden error→real_value 计数(baseline 非 real_value→current real_value)、各 repo smoke_ok before/after delta（flask 0→N）；无 baseline 时降级为当前 golden 分布 + note。
  ③ markdown 新增 True correct 行 + Dependency-install Before/After 段。
- cli.py 加 --baseline-manifest 透传。新增 5 例单测(true 率/weak 剔除/unknown 降级/前后对比/无 baseline 降级)。`pytest tests/`=91 passed、`unittest`=91 OK；CLI 端到端(含 baseline)验证 flask smoke 0→2、error→real_value=2 正确。
- 更新 README + docs/mvp_usage.md。设计备注：'前后对比'需两份 manifest，故用可选 --baseline-manifest（契约只给当前 golden_status，无 before 字段）；缺失安全降级。已在 PR 报告中说明供 lead review。
- 下步：mailbox 回报 lead PR#20 + 自测，等 tester(w3)+lead review。

## Session 2 - 2026-06-13 - lead 确认方案 + 核对 golden_status 契约一致性

- lead 回复：--baseline-manifest 方案保留(pre-install 作 before，w5 重跑传新旧两份)；已派 w3 验证 + lead review；要求核对 golden_status 取值集合与 w1 task030 一致。
- 核对结果：w1 task030 契约 `manifest.envs[].golden_status ∈ {real_value, weak_oracle:<reason>}`（weak 例 golden_exception:ModuleNotFoundError / uninstallable_deps），与本 PR `_golden_kind` 消费**完全一致**：==real_value→real；startswith("weak_oracle")→weak(覆盖带后缀)；其余/缺失→unknown(留分母安全网)。task030 producer 代码尚未落 code2env/（branch 仅 README+继承的 report.py），但共享契约一致。
- 结论：无取值不符，无需 mailbox 协调（lead 仅要求不符时同步）。继续 hold 等 w3/lead review 与合并授权。
- 本 turn 无代码改动，仅核对+记录。

## Session 3 - 2026-06-13 - lead APPROVE + w3 PASS，self-merge PR#20

- lead APPROVE + tester(w3) 五条全 PASS(91 passed, dry-run merge clean)，批准合并；合并序我先合(PR#20)，A(PR#18) 随后 rebase。
- `git merge origin/main`：仅 WIP.md 冲突(删除占位解决)，docs/mvp_usage.md 自动合并干净，cli.py/report.py 无冲突(A 尚未合)。merge 后 `pytest tests/`=95 passed（含 main 新增），无回归；report doc 段保留。
- 教训应用：**合并前先翻** README→Completed + status→Idle + Session 3，使其随 squash 进 main（避免 task023 那次的额外 bookkeeping PR）。
- self-merge PR#20（squash）后 cleanup + mailbox 回报 squash commit。
