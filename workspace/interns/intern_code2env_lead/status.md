# intern_code2env_lead - 状态

<!-- METADATA:STATUS=Working,TASK=code2env_lead,ROLE=team_lead,TEAM_ID=code2env -->

| 字段 | 值 |
|------|-----|
| Name | intern_code2env_lead |
| Status | Working |
| Role | team_lead |
| Team | code2env |
| Current Task | code2env_lead |
| PR | N/A |
| Session | 3 |

最近进展：Session3 清除假阳性+拿真实正确率。Coordinator 抽查 Session2 100 rollout:99% 合格成立、五维 reward 正确,但 exact-match correct 3/100 全是假阳性(根因A 依赖缺失致 golden 污染成 import 报错;根因B agent 自造 fixture 与 golden 不符)。三项修复 PR 全部 lead review+tester PASS 并 merged 到 main(108 passed):A 装依赖+golden重算 346d88e(#18)/B rollout prompt b59a067(#17)/报告真实correct率 f486609(#20)。golden_status 契约 030写↔033读 交叉核对一致;合并时确认 B 的 CALL_ENTRYPOINT_FIXTURE_GUIDANCE 未丢。**w5 task034 重跑已启动**:batch 复现100env→装依赖重算golden(baseline vs v2)→非weak_oracle子集 gpt-5.5重跑→conversation JSON 到 outputs/rollouts_v2/→报告 outputs/report_v2/(真实correct率)。等 w5 完成产最终物→回报 coordinator。coordinator session6 跟进已回复。
（Session2 已交付:100 env+rollout,四能力 PR 全 merged 到 main 86 passed,coordinator 已 review 并提出本轮假阳性修复。Session1:PRD P0 三项 merged。）
