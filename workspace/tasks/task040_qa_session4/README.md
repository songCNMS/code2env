# task040_qa_session4 - QA:验 信封归一/确定性门禁/report_v3 三 PR

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_3 -->

## 背景

Session4 修 v2 的 0% 假阴性两根因:w2 task037(runtime 信封归一)、w1 task038(确定性门禁)、w4 task039(report_v3 类别)。你是 tester。还有 task035 uv 兜底 PR#22 待你验(并行)。

## 任务目标

对 task037/038/039(+task035 PR#22)逐个 checkout 跑单测+逐条验收+契约对照。重点:信封归一后里层value与完整信封都判对且 scripted_smoke 不破;确定性门禁正确识别非确定性(内存地址/绝对路径/不稳定)并剔除;report 真实率分母=确定性可用集;determinism 字段 038写↔039读 一致。

## 实现说明

等 lead ping 分支名。测试计划写 task_knowledge。回报走 mailbox。

## 验收标准

- 每 PR mailbox 回报命令/结果/逐条 PASS-FAIL/环境/未覆盖风险
- 信封归一:同底层值多形状都对、ok:false 不误判、smoke 不破;确定性门禁:nondeterministic 识别+reason 正确
- 038↔039 determinism 取值交叉核对一致

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_3
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
