# task039_report_v3_categories - History Log

<!-- METADATA:SESSION=1 -->

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
