# task032_qa_session3_fixes - QA:验证 根因A/B 修复 + 报告更新 三个 PR

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

Session3 修假阳性:w1 task030(依赖安装+golden重算+weak_oracle)、w2 task031(rollout prompt 修正)、w4 task033(报告真实correct率)。你是本轮 tester,team_lead 不亲跑测试。分支就绪后 team_lead ping 你逐个验。

## 任务目标

对 task030/031/033 三个 PR 分别 checkout 跑单测+逐条验收+契约对照(golden_status 字段一致、prompt 含禁自造参数指示、报告真实率剔 weak_oracle)。

## 实现说明

测试计划先写 task_knowledge。等 lead ping 分支名。回报走 mailbox。

## 验收标准

- 每个 PR mailbox 回报:命令/结果/逐条 PASS-FAIL/环境/未覆盖风险
- 重点验:A 装依赖后 golden 变真实值(可用小依赖样例)、weak_oracle 标注与剔除;B prompt 含明确指示且 call_entrypoint 留空走 fixture;报告真实 correct 率分母正确
- 发现阻塞清晰复现,不替 worker 改码

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_3
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
