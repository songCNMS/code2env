# task014_qa_reward_e2e - QA: 验证 P0-2 多维 reward + 全链路回归

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_5 -->

## 背景

你是本轮 tester 之一。worker_2 在做 task011(多维 reward 落地)。team_lead 不亲自跑测试,由你独立验证该 PR;并在三项 P0 全部 merge 后负责跑端到端全链路回归 scan->select->draft->materialize->build->smoke 保绿(本轮 MVP 闭环基线不能被打破)。分支尚未就绪;先读 PRD 7.7 与验收标准准备测试计划,team_lead 会 ping 你。

## 任务目标

1) task011 PR:checkout 分支、跑单测、核对五维 reward 计算/加权/score_breakdown 可解释性、scripted_smoke 全绿。2) 三项 merge 后:在 master 跑完整 scan->select(--llm-mode mock)->draft->materialize->build->smoke 全链路与 tests/test_mvp.py,确认无回归。

## 实现说明

测试计划先写进本 task 的 task_knowledge.md。select 用 --llm-mode mock 离线。等 team_lead ping 再实测。回报走 mailbox。

## 验收标准

- task011 各验收标准 PASS/FAIL 判定 + mailbox 回报(命令/结果/环境/风险)
- 全链路回归结果回报:每步命令与产物状态,smoke ok=true,test_mvp 全绿
- 发现回归/失败清晰描述复现,不替 worker 改代码

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_5
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
