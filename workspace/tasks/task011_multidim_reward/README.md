# task011_multidim_reward - P0-2 多维 reward 落地 (F7 / PRD 7.7)

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_2 -->

## 背景

对照 docs/code2env_agentic_rl_prd.md 7.7。reward.weights 已声明 schema_validity/process_progress/final_correctness/efficiency/safety(见 spec.py reward 块)，但 runtime.py 只实算 exact-match final + 固定 0.05 schema，其余维度恒为 0，score_breakdown 仅含 final_correctness/exact_match。

## 任务目标

在 Code2Env.step/evaluate 真正计算并按 reward.weights 加权五个维度：schema_validity(action 参数合法/tool 存在/返回可解析)、process_progress(中间阶段不变量,如先 inspect/调用入口再 submit)、final_correctness(exact-match oracle)、efficiency(步数/重复/无效调用惩罚)、safety(无网络越界/异常逃逸)。输出可解释 score_breakdown(每维 raw + weighted + 说明)，训练 reward 与 evaluation score 分离。

## 实现说明

落点: code2env/runtime.py(step/evaluate/_dispatch/submit_answer reward 块)。weights 从 self.spec.reward['weights'] 读取,缺省回退到现值。注意 final 维度仍以 golden_answer exact-match 为准。与 P0-1/P0-3 解耦,不要改 spec.py tool 生成。完成后 mailbox 回报 intern_code2env_lead PR# 与自测,等 tester(worker_5) 验证与 lead review。

## 验收标准

- step 累积分维 reward,evaluate 返回完整 score_breakdown,五维均可非零且按 reward.weights 加权
- score_breakdown 可解释:每维含 raw 值/weight/weighted 贡献,total 在[0,1]
- process_progress 体现阶段进展(如调用入口->提交),efficiency 对超步数/重复调用扣分,safety 对沙箱违例扣分
- scripted_smoke 及 tests/test_mvp.py 全绿;新增单测覆盖各维度计算与加权
- 更新 README.md/docs/mvp_usage.md 评分说明;独立 PR 并 push 自己分支

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_2
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
