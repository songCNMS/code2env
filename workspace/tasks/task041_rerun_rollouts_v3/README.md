# task041_rerun_rollouts_v3 - v3 重跑:确定性可用集 → rollouts_v3 + report_v3

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_5 -->

## 背景

你是重跑 runner。v2 已交付(rollouts_v2/真实0%是信封+非确定性两根因导致的假阴性)。Session4 修复后做 v3:依赖 w2 task037(信封归一)/w1 task038(确定性门禁)/w4 task039(report_v3)三 PR merged。v2 manifest/产物在 outputs/phase3_v2 与 coordinator outputs;旧 v1/v2 勿覆盖。本机 venv 需用 uv wrapper(同 task034)。

## 任务目标

三 PR merged 后:①对 100 env 应用确定性门禁定确定性可用集(real_value+deterministic,剔 weak_oracle 与 nondeterministic)。②对确定性可用集用 gpt-5.5(本地兜底)重跑(runtime 已信封归一→确定性纯函数应判对),conversation JSON 存 outputs/rollouts_v3/(不覆盖v1/v2)。③用 w4 工具出 report_v3/:真实非零 correct率+类别占比(确定性可用/信封转对/非确定性剔除/仍错)+v1→v2→v3 对比。

## 实现说明

endpoint 同前:--endpoint-file /home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt --llm-model gpt-5.5 --fallback-model gpt-oss-120b;venv 用 uv wrapper(本机缺 python3-venv,task035 合入后可去 wrapper)。Phase 依赖 task037/038/039 merge,我会 ping。先读三 task+写 v3 计划到 task_knowledge。回报 mailbox。

## 验收标准

- 确定性可用集确定(剔 weak_oracle+nondeterministic),大小记录
- 确定性可用集 gpt-5.5 重跑→outputs/rollouts_v3/(并存不覆盖)
- report_v3/含真实非零 correct率+类别占比+v1→v2→v3 对比
- mailbox 回报:真实 correct率、确定性可用集大小、各类别数、rollouts_v3/report_v3 路径

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_5
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
