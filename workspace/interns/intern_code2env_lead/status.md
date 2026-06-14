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

最近进展：Session3 清除假阳性+拿真实正确率。Coordinator 抽查 Session2 100 rollout:99% 合格成立、五维 reward 正确,但 exact-match correct 3/100 全是假阳性(根因A 依赖缺失致 golden 污染成 import 报错;根因B agent 自造 fixture 与 golden 不符)。三项修复 PR 全部 lead review+tester PASS 并 merged 到 main(108 passed):A 装依赖+golden重算 346d88e(#18)/B rollout prompt b59a067(#17)/报告真实correct率 f486609(#20)。golden_status 契约 030写↔033读 交叉核对一致;合并时确认 B 的 CALL_ENTRYPOINT_FIXTURE_GUIDANCE 未丢。v2 重跑完成:根因A/B 修复证实(flask golden error→real_value=9、smoke 0→8、deps 装齐)。但 v2 true_correct=0/75——lead 诊断+coordinator 核验=两个 env/oracle 设计根因(非模型能力):①提交契约错位(agent submit 里层 value,golden 存完整工具信封{ok,value}{kind,value},差壳判错;75 中 70+ 实际 value-correct≈93%)②非确定性 golden(内存地址/绝对路径/hash 每次不同)。coordinator 开 Session4 新目标:信封归一+确定性过滤→v3 重跑。已拆 5 worker:w2 task037 runtime信封归一、w1 task038 确定性门禁、w4 task039 report_v3、w3 task040 tester、w5 task041 v3重跑。lead 定义 determinism 契约。v3 blockedBy 三 PR merge。
（Session2 已交付:100 env+rollout,四能力 PR 全 merged 到 main 86 passed,coordinator 已 review 并提出本轮假阳性修复。Session1:PRD P0 三项 merged。）
