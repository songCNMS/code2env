# task013_qa_toolextractor_testlink - QA: 验证 P0-1 ToolExtractor + P0-3 TestLinkIndex

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_4 -->

## 背景

你是本轮 tester 之一。worker_1 在做 task010(语义化 ToolExtractor),worker_3 在做 task012(TestLinkIndex+放开 tests 扫描)。team_lead 不亲自跑测试,由你独立验证这两个 PR。分支尚未就绪;先读 PRD 7.5/7.2 与任务验收标准,准备测试计划;每个 PR 分支 push 后 team_lead 会 ping 你开始验证。

## 任务目标

对 task010、task012 两个 PR 分支分别:checkout 分支、跑 pytest/单测、按各自验收标准逐条核对、做必要的手动/边界验证(如 tool 数量区间、状态 tool 存在、provenance>=2)、确认现有 tests/test_mvp.py 全绿。

## 实现说明

先准备测试计划写进本 task 的 task_knowledge.md。等 team_lead ping 分支名后再开始实测。回报走 mailbox(worker->team_lead 不走 peer send)。

## 验收标准

- 对每个 PR 用 mailbox 向 intern_code2env_lead 回报:执行命令、结果(通过/失败明细)、运行环境、未覆盖风险
- 明确给出每条验收标准的 PASS/FAIL 判定
- 发现阻塞/失败时清晰描述复现步骤,不替 worker 改代码

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_4
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
