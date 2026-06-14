# task032_qa_session3_fixes - History Log

<!-- METADATA:SESSION=8 -->

## Session 8 - 2026-06-14 UTC - 验 PR#23 修订版 + PR#26 task039

- [PR#23 修订版 task037] PASS: _accepted_answer_forms 只剥 golden 两层得 X, 接受 [X,{kind:json,value:X},full], submitted 绝不剥。pytest 127、test_envelope 13。**E2 对抗已修**: 函数真返回 {ok:true,value:5}/{kind:json,value:7} 时提交 bare 5/7 判 INCORRECT(手验+专测); 三正确形状仍 correct; ok:false 整包比; scripted_smoke ok score1.0; 五维不变; 只动 runtime.py。建议 APPROVE。
- [PR#26 task039 report_v3] PASS: 四桶 MECE(det_usable/nondet/weak/unknown=total) + envelope_flipped/still_wrong 为 det_usable 子计数; 真实非零率=correct/deterministic_usable; --prev-rollouts 驱动 v1→vN evolution 与 envelope_flipped; determinism 缺失安全降级(D 不崩入 usable); 保留原指标。手验数字全对。建议 APPROVE(lead 已 APPROVE)。
- 待办: 038↔039 determinism 取值交叉核对等 w1 task038(PR#24)到货。两份 mailbox 已回报。

## Session 7 - 2026-06-14 UTC - PR#23 暂停(lead 发现过度剥壳假阳性)

- lead review PR#23(task037)发现**过度剥壳假阳性**: 源函数真实返回 {ok:true,value}/{kind:json,value} 形状 dict 时会被误剥→错误提交也匹配 golden。已让 w2 修订, 我暂停 PR#23 验证等修订版再 ping。
- 我漏检该对抗用例(只验正向多形状判对), 教训记 ERROR_BOOK E2: 验 strip/normalize 逻辑必须构造"合法数据命中剥离特征→不应被剥"对抗用例。
- 后续: lead review 完 w1 task038(PR#24)/w4 task039(PR#26)再 ping 分支名; task035 PR#22 我已 PASS, w1 先合。
- 当前等待中。

## Session 6 - 2026-06-13 UTC - task032(Session3 QA)收尾 + 接受 task040(Session4 QA)

- task032 Session3 QA 全部完成: PR#17/#20/#18 + PR#22(task035) 五项验证均 PASS、030↔033 契约交叉核对一致, 已逐个 mailbox 回报。
- lead 分配新任务 task040_qa_session4(tester): 验 task037(信封归一)/task038(确定性门禁)/task039(report_v3) + 收尾 task035 PR#22。
- 已读 task040 + task037/038/039 文档; task040 测试计划写入 workspace/tasks/task040_qa_session4/task_knowledge.md(三 PR 逐条 + 038↔039/037↔039 交叉核对)。
- 操作说明: 因 Stop hook 绑定 task032 Session 序列, 本轮接受记于此(Session 6); task040 逐 PR 验证将续在此序列(Session 7+)并同步记 task040 dir。
- 等 lead ping 三 PR 分支名后逐个 checkout 验证, 走 mailbox。
- [Phase1 同turn] 验 PR#23 task037(信封归一): checkout w2 分支 pytest 121 passed(test_envelope 13); 逐条 6 项全 PASS(归一剥 {ok,value}/{kind:json} 壳、ok:false/{kind:repr} 不剥、三形状同底层值都 correct、scripted_smoke ok score1.0、五维不变、只动 runtime.py); merge main 干净 post-merge 127。建议 APPROVE, mailbox 已回报。详见 task040 task_knowledge。

## Session 5 - 2026-06-13 UTC - Phase4 验证 PR#22 task035 (envdeps uv venv 兜底)

- lead ping(并行硬化): 验 PR#22 task035。checkout intern_code2env_worker_1/task035 → pytest 114 passed(test_envdeps 19, 新 CreateVenvUvFallbackTest 6)。
- 逐条 4 项全 PASS: stdlib venv 失败+uv 存在→uv venv --seed 回退; uv 缺失/也失败→上抛→build_repo_venv venv_failed 优雅降级; golden_status 契约与 happy path 零改动(runner/which keyword-only 默认, 向后兼容); 注入式单测无网络。
- 分支 0 behind main(已含 task030), 无需 merge。非阻塞: 仍跟踪 WIP.md(同 task030), 建议 w1 合前 git rm。
- 建议 APPROVE; mailbox 回报。
- 修复: 上轮发现 Stop hook 读共享 repo status.md, 本轮起每 session 同步共享 repo status + push main。

## Session 4 - 2026-06-13 UTC - Phase3 验证 PR#18 task030 (+030↔033 交叉核对)

- lead ping Phase3: 验 PR#18 task030(根因A 依赖安装/golden 重算/weak_oracle)。
- checkout intern_code2env_worker_1/task030 → pytest 99 passed(test_envdeps+test_batch 26); 逐条 5 项全 PASS。
- 030↔033 取值交叉核对(脚本复刻 report._golden_kind): real_value→real_value、weak_oracle:*→weak_oracle(剔分母)、pending/缺失→unknown(留分母) CONSISTENT。
- executor 默认解释器向后兼容(功能验证); envdeps 注入假桩不依赖网络; runtime._call_source 用 venv python 且缺失安全回退。
- merge main 仅 WIP.md 冲突(w1 占位文件未删, 非代码); 解后 post-merge 103 passed。
- 非阻塞: (a) WIP.md merge 卫生需 w1 git rm; (b) spec.py 未算 golden 时 pending_golden→report unknown 留分母, 提示 w5 放量确保 golden 已算。
- 建议 APPROVE(处理 WIP.md 后); 三 PR 全验完均 APPROVE。mailbox 回报。

## Session 3 - 2026-06-13 UTC - Phase2 验证 PR#20 task033

- lead ping Phase2: 验 PR#20 task033(报告真实 correct 率)。
- checkout intern_code2env_worker_4/task033 → pytest 91 passed(test_report 19); 逐条 5 项全 PASS。
- 手验合成样例(real/weak/缺失+baseline): raw=2/3、true=1/2、weak_excluded=1、unknown=1 留分母、golden error→real=1、flask smoke 0→1。
- merge main 干净且 post-merge 91; 建议 APPROVE, 无阻塞; mailbox 回报。
- 记跨 PR 待核: w4 读 real_value 精确 + weak_oracle 前缀, 待 task030 到货核对 w1 写出取值一致。

## Session 2 - 2026-06-13 UTC - Phase1 验证 PR#17 task031

- lead ping Phase1: 验 PR#17 task031(根因B rollout prompt)。
- checkout intern_code2env_worker_2/task031 → pytest 90 passed; 逐条 5 项全 PASS; 交叉校验契约(我 task022 validator)通过; merge main 干净且 post-merge 仍 90。
- 建议 APPROVE, 无阻塞; mailbox 回报 lead(命令/结果/逐条/未覆盖风险)。
- 等 w1 task030 / w4 task033 分支 ping。

## Session 1 - 2026-06-13 UTC - 接受 tester task + 写测试计划

- 接受 task032(本轮 tester)，分支 `intern_code2env_worker_3/task032_qa_session3_fixes`，PR #19（仅承载状态/计划/报告，不改码）。
- 读完三个待验 task 文档(task030/031/033) + main 基线相关模块(executor/runtime/rollout/report/batch)。
- 测试计划写入 task_knowledge：通用验证流程 + 三 PR 逐条验收点 + 跨 PR 契约一致性(golden_status 取值集合 w1 写=w4 读)。
- 等 lead ping 三个 PR 分支名后逐个 checkout 验证，结果走 mailbox。

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_3` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。
