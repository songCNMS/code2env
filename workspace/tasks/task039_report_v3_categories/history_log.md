# task039_report_v3_categories - History Log

<!-- METADATA:SESSION=3 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_4` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 实现 report_v3 类别拆分 + 三轮对比

- 接受 task039，建分支 + PR#26 (base main)。
- 更新 code2env/report.py（我是 D4 作者，只动 report.py + cli.py 透传 + 测试 + 文档）：
  ① 消费新契约 manifest.envs[].determinism(deterministic|nondeterministic:<reason>)；新增 _determinism_kind/_env_bucket。env_bucket 互斥四桶：weak_oracle / nondeterministic / deterministic_usable(real_value+确定性) / golden_unknown。weak 优先于 nondet；determinism 缺失→降级为可用(仅显式 nondeterministic 才剔)。
  ② 类别占比 categories：deterministic_usable / envelope_flipped_to_correct / nondeterministic_excluded / weak_oracle_excluded / still_wrong / golden_unknown（前四+unknown 互斥求和=total）。
  ③ 真实非零 correct 率 true_nonzero_correct_rate=correct/deterministic_usable（剔 weak+nondet）。保留 task033 的 true_correct(仅剔 weak) 作"原指标"。
  ④ envelope_flipped_to_correct：deterministic_usable 且当前 correct 且前一轮(--prev-rollouts 最后一个)incorrect。
  ⑤ v1→…→vN evolution：prev_runs + current 各算 correct/correct_rate/true_nonzero，标 v1..vN。
- cli.py 加 --prev-rollouts(repeatable)。新增 4 例单测(类别分区/true 非零率/determinism 缺失降级/envelope flip+evolution/三轮标签)。`pytest tests/`=112 passed、`unittest`=112 OK；CLI 端到端验证 envelope flip=1、nondet/weak 剔除、v1/v2 演进正确。
- 更新 README + docs/mvp_usage.md。
- 下步：mailbox 回报 lead PR#26 + 自测，等 tester(w3)+lead review。

## Session 2 - 2026-06-14 - lead review 中 + 主动核对 038↔039 determinism 契约

- lead 回复：PR#26 收到，review 中，稍后派 w3 验证(含 038↔039 determinism 取值交叉核对)；确认"determinism 缺失不剔"降级正确；合并序在 037/038 之后，先待命。
- 主动核对(像之前 golden_status 一样早发现)：task038 契约 `manifest.envs[].determinism ∈ {deterministic, nondeterministic:<reason>}`，reason 形如 unstable_across_runs/memory_addr/abs_path/object_repr/hash/timestamp；README 第21条"确定性可用集=real_value AND deterministic；nondeterministic 与 weak_oracle 一样剔分母单列"。
- 与本 PR 完全一致：_determinism_kind(==deterministic→det；startswith("nondeterministic")→覆盖全部 reason 后缀→nondet；其余/缺失→unknown 不剔)；_env_bucket 确定性可用=real_value+deterministic。无取值不符 → 无需 mailbox 协调。
- 继续 hold，等 w3 验证 + lead review + 037/038 merge 后的合并授权；merge 时先翻 Completed/Idle 再 self-merge(memory 经验)。本 turn 无代码改动。

## Session 3 - 2026-06-14 - lead APPROVE + w3 PASS，self-merge PR#26

- lead APPROVE + tester(w3) 全 PASS，批准合并；PR#23(信封①)已 merged(7c0a82c)。
- `git merge origin/main`：自动合并干净(无 cli.py 冲突，与 PR#24 区域不重叠；带入 task030 deps/golden + 信封等)；删除残留 WIP.md 占位。merge 后 `pytest tests/`=131 passed，无回归。
- 教训应用：合并前先翻 README→Completed + status→Idle + Session 3，随 squash 进 main（避免额外 bookkeeping PR）。
- self-merge PR#26（squash）后 cleanup + mailbox 回报 squash commit。PR#24(确定性) 随后由 w1 合，cli.py 不冲突。
