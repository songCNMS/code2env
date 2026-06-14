# task024_integration_rollout_runner - QA + 集成放量 runner (1-3 env 验证→放量100+rollout+导出+报告)

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

Session2 目标的执行与验证侧。四个能力 PR:task020 批量pipeline(w1)/task021 rollout driver(w2)/task022 conversation导出(w3)/task023 报告(w4)。你是本轮 tester+集成 runner。team_lead 不亲自跑测试/放量,由你执行并 mailbox 回报。最终交付物必须由你产出:≥100 EnvPackage 清单(manifest)、coordinator outputs/rollouts/ 下 conversation JSON、汇总报告、合格率数字。

## 任务目标

Phase1(各 PR 到达时):checkout 分支跑单测+逐条验收 PASS/FAIL,mailbox 回报(我会 ping 分支名)。Phase3(我确认 D1/D2/D3 merged 后):先用 1-3 env 验证 rollout driver+conversation JSON 格式跑通(--llm-mode mock 或本地127.0.0.1 端点,避免 gpt-5.5 限速);格式 OK 后放量:批量生成≥100 env→对其 task 用 gpt-5.5 多轮 rollout(外网失败自动回退本地)→导出 conversation JSON 到 outputs/rollouts/→生成汇总报告。

## 实现说明

endpoint 事实:gpt-5.5 用 --endpoint-file /home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt --llm-model gpt-5.5(base_url https://xyzlapi.boyuerichdata.com/v1/);回退用同一 endpoints.txt 的本地127.0.0.1 端点(Kimi-K2.6/xyz-30b),endpoints.vpn.txt 不存在勿依赖;llm.py 默认 /work-agents/endpoints.txt 不存在必须显式传 --endpoint-file。合格 rollout 判定:每条≥2轮 tool_call+含 submit_answer+记录每步 reward 与最终 evaluation/score_breakdown。语料 requests/flask/rich/click/jinja2(不够加 poetry),shallow clone 到 .code2env_cache(勿提交外部源码)。放量耗时大、注意 gpt-5.5 限速→可分批+回退+控制并发。本任务 Phase3 依赖 task020/021/022 merge,我会 ping 你启动。测试计划先写进 task_knowledge。回报走 mailbox(worker->lead 不走 peer send)。

## 验收标准

- Phase1:对 task020-023 每个 PR 给执行命令/单测结果/逐条验收 PASS-FAIL/环境/未覆盖风险,mailbox 回报
- Phase3 格式门:1-3 env 的 rollout+conversation JSON 跑通且符合契约(≥2轮 tool_call+submit、含每步 reward 与 final score_breakdown),先 mailbox 报格式 OK 再放量
- Phase3 放量:成功 build 的 EnvPackage≥100(manifest 计);对其执行 rollout 产出 conversation JSON 到 /home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts/
- 产出汇总报告(outputs/ 下 md+json):生成成功率/按repo分布/rollout合格率/平均score/失败聚类;mailbox 回报最终数字(100env清单位置、rollouts路径、报告路径、合格率)

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_5
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
