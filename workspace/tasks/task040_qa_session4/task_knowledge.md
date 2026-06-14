# task040_qa_session4 - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_3`（本轮 tester，Session4 QA）。
2. 我是 tester：只验证不改码；操作上本轮接受时仍挂在 task032 分支记录（Stop hook 绑定 task032 Session 序列），task040 的逐 PR 验证报告与计划记于本 dir + 走 mailbox。
3. task035 PR#22(uv 兜底)上轮(task032 Session5)已验 PASS, 待 lead 合并; 本轮如需复核可快速重跑。
4. 通用验证流程: 每 PR `git fetch && git checkout <branch>` → `git merge origin/main`(如需) → `python3 -m pytest tests/ -q`(确认基线不降)→ 逐条验收 → 契约字段对照 → 用我已合入的模块做交叉校验(如 rollout_export.validate_conversation)→ mailbox 回报。验证用 pytest(CI 同款, 勿 unittest, 见 ERROR_BOOK E1); 本机用 python3; 验完 checkout 回自己分支再结束。

## 测试计划（等 lead ping 分支名后执行）

### task037 (w2, 根因①: runtime 信封归一比较) — 落点 runtime.py
- 跑全量 pytest; 确认新增 runtime 信封归一单测。
- 逐条:
  1. 归一函数 `_normalize_answer_envelope`: 递归剥 {ok:true,value:..}→value、{kind:json,value:..}→value、{kind:repr,..}保留 repr。
  2. 同一底层值多形状都判 correct: 提交最内层 X / {kind:json,value:X} / {ok:true,value:{kind:json,value:X}} 三种, 当底层==golden 底层 → 均 correct。
  3. ok:false 错误信封不误判: error golden 仍走 weak_oracle/不匹配, 不因都被剥成空而误 correct。
  4. 不同底层值 → incorrect。
  5. scripted_smoke 仍通过(提交完整 last_tool_result 仍对); score_breakdown 五维不变; 现有 pytest 全绿。
  6. 只动 runtime.py(evaluate + _dispatch submit_answer correct 比较), 不越界 executor/report。
- 风险关注: 归一是否过度剥导致 {kind:repr,..} 也被剥(应保留); golden_answer 本身是完整信封时双向归一对称。

### task038 (w1, 根因②: 确定性门禁) — 落点 determinism.py/envdeps/batch/spec
- 跑全量 pytest + 新增 determinism 单测(注入式不依赖大网络)。
- 逐条:
  1. **契约 determinism**: manifest.envs[].determinism ∈ {deterministic, nondeterministic:<reason>}; reason ∈ unstable_across_runs/memory_addr/abs_path/object_repr/hash/timestamp(字段勿改名)。
  2. 重复执行 N>=2 次不一致 → nondeterministic:unstable_across_runs。
  3. golden repr/字符串命中特征: 0x[0-9a-fA-F]{6,}→memory_addr、`<... object at 0x..>`→object_repr、/home//tmp//Users/ 绝对路径→abs_path、hash/timestamp 各对应 reason。
  4. 确定性可用集 = real_value(①信封已修)AND deterministic; nondeterministic 与 weak_oracle 一样剔分母、单列。
  5. 现有 pytest 全绿; 注入式样例不依赖大网络。
- 与 task035 同为 w1, 注意本 PR 不回退 task035 的 uv 逻辑。

### task039 (w4, report_v3 类别) — 落点 report.py
- 跑全量 pytest + 新增 report_v3 单测(合成 manifest+多轮 rollouts)。
- 逐条:
  1. 类别占比: deterministic_usable / envelope_flipped_to_correct(v2 incorrect 但 v3 correct) / nondeterministic_excluded / still_wrong。
  2. 真实 correct 率分母 = 确定性可用集(剔 weak_oracle 与 nondeterministic)。
  3. 消费契约 golden_status(real_value|weak_oracle:<reason>)+ determinism(deterministic|nondeterministic:<reason>); 缺失安全降级不崩。
  4. v1→v2→v3 对比段(多 run 输入或 --prev-rollouts/baseline 参数); envelope_flipped 需 v2 vs v3 两轮对比。
  5. 保留原指标(生成率/by_repo/合格率/score/失败聚类/task033 的 true_correct 等)。
- 跨 PR 交叉核对(重点):
  - **038↔039 determinism**: w1 写的取值集合(deterministic / nondeterministic:<reason>)须与 w4 读取(预期 ==deterministic / startswith nondeterministic)一致, 不一致→阻塞(同上轮 030↔033 方法: 脚本复刻 report 分桶逻辑跑 w1 产值)。
  - **037↔039**: 信封归一改的是 final.correct, 039 据此算 envelope_flipped; 确认 v2(归一前 incorrect) vs v3(归一后 correct) 的转对计数口径一致。

## 验证结果

### [Phase1] task037 (PR#23) — 我建议 APPROVE 但被 lead 驳回(过度剥壳假阳性), 暂停等修订版
> ⚠️ 我漏检: lead review 发现**过度剥壳假阳性**——源函数若**真实返回** {ok:true,value:..} 或 {kind:json,value:..} 形状的 dict, 归一会把它当壳剥掉, 导致错误提交也能匹配 golden 底层 → 假阳性 correct。我的逐条只验了"同底层值多形状判对", 未构造"合法数据恰好长得像信封壳→不应被剥"的对抗用例。教训记 ERROR_BOOK E2。w2 修订中, 等 lead 再 ping 验修订版。
> 以下为初版(a108f32)记录(仅供参考, 已作废):
- pytest tests/=121 passed; test_envelope.py 13 passed; merge main 干净 post-merge 127。
- 1[PASS] _normalize_answer_envelope 循环 max32 剥 {ok:true,value}+{kind:json,value}; ok:false/{kind:repr} 不剥; _answers_equal 两端归一比。
- 2[PASS] 三形状(里层值/json 壳/完整信封)同底层值都 correct(手验 EQ 三例 True + 集成测试)。
- 3[PASS] 不同底层值 incorrect; ok:false 错误信封不误判(EQ(err,real_golden)=False, error env 由 030/038 weak_oracle 剔)。
- 4[PASS] scripted_smoke ok score=1.0(不破)。
- 5[PASS] score_breakdown 五维不变(efficiency/final_correctness/process_progress/safety/schema_validity), 仅 correct 比较改 _answers_equal。
- 6[PASS] 只动 runtime.py(+tests/test_envelope+docs)。
- 非阻塞: 归一仅覆盖 {ok,value}/{kind:json} 两类壳; envelope_flipped 口径待 task039 一并核对。
