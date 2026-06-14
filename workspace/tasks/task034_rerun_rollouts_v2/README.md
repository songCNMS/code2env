# task034_rerun_rollouts_v2 - 集成:装依赖重算golden+重跑rollout(v2)+真实正确率报告

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

你是 Session2 放量 runner,本轮做修复后的重跑。依赖 w1 task030(依赖安装+golden重算+weak_oracle)、w2 task031(rollout prompt 修正)、w4 task033(报告真实率)三 PR merged。旧数据在 outputs/rollouts/(勿覆盖)。上轮 manifest:/home/leisong/codes/work-agents/intern_code2env_worker_5/outputs/phase3/envs/manifest.json(build_ok=100)。

## 任务目标

三 PR merged 后:①对 100 env 装依赖重算 golden(用 w1 机制),标出 weak_oracle 集(装后仍异常)。②对可用 env 子集(非 weak_oracle)用 gpt-5.5 重跑 rollout(本地 gpt-oss-120b 兜底不变,带修正后的 prompt),conversation JSON 存 outputs/rollouts_v2/(勿覆盖旧 rollouts/)。③用 w4 报告工具产出更新报告到 outputs/report/:真实 correct 率(剔 weak_oracle)、装依赖前后对比、各 repo smoke_ok 变化。

## 实现说明

endpoint 同 Session2:--endpoint-file /home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt --llm-model gpt-5.5 --fallback-model gpt-oss-120b。装依赖个别库装不动→跳过记 reason 不卡死。Phase 依赖 task030/031/033 merge,我会 ping 你启动。先读三 task+写重跑计划到 task_knowledge。回报走 mailbox。

## 验收标准

- 装依赖重算 golden 完成:flask 24+ 及其它 golden=异常 env 重算;weak_oracle 集单独标注
- 可用子集用 gpt-5.5 重跑 rollout,conversation JSON 存 outputs/rollouts_v2/(与旧 rollouts/ 并存不覆盖)
- 更新报告含真实 correct 率(剔 weak_oracle 分母)+装依赖前后对比+各 repo smoke_ok 变化
- mailbox 回报最终数字:真实正确率、weak_oracle 数、rollouts_v2 路径、报告路径、装依赖前后对比

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_5
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
