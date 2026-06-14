# task023_rollout_summary_report - D4 汇总报告生成 (env 生成 + rollout 合格率 + 失败聚类)

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_4 -->

## 背景

Session2 目标:对规模化100 env+gpt-5.5 rollout 出一份汇总报告。输入两类产物:(1) D1(task020,w1)的 gen manifest.json;(2) D3(task022,w3)写到 coordinator outputs/rollouts/ 的 conversation JSON/rollouts.jsonl。契约 schema 由 lead 统一定义(见 details),与 w1/w2/w3 共享。

## 任务目标

新增 code2env/report.py(+CLI code2env report):读 manifest + rollouts(目录或 jsonl)→产出 markdown + json 双格式报告,含:env 生成成功率(draft_ok/build_ok/总候选)、按 repo 分布、rollout 合格率(qualified=≥2轮 tool_call+submit)、平均 score、失败聚类(依赖失败/fixture无法合成/oracle弱/工具粒度/格式错误等 tag 计数)。报告写到 outputs/ 下。

## 实现说明

[消费契约-勿改字段名] manifest:{summary:{candidates_scanned,draft_ok,build_ok,smoke_ok,by_repo},envs:[{env_id,repo,build_ok,smoke_ok,smoke_fail_reason,...}],skipped:[{symbol,repo,reason}]}; conversation:{env_id,model,endpoint_source,final:{correct,score,score_breakdown},num_tool_call_rounds,qualified,termination_reason}. 合格率=合 qualified 的 rollout 数/总 rollout 数;平均 score=mean(final.score)。可先用合成样例数据开发,真实放量由 w5 在三项 merge 后执行后再用本报告工具产出最终报告。report.py 实现独立,cli.py 仅加 subparser+一行。完成 mailbox 回报 lead PR#+自测,等 tester(w5)+lead review。

## 验收标准

- code2env report 命令:输入 manifest 路径 + rollouts 目录/jsonl→输出 report.md 与 report.json 到指定 outputs 目录
- 报告含全部要求指标:生成成功率、by_repo 分布、rollout 合格率、平均 score、失败聚类计数(可解释 tag)
- 失败聚类:对 smoke 失败(manifest.smoke_fail_reason)与 rollout 不合格/低分归类计数(依赖失败/fixture无法合成/oracle弱/工具粒度/格式错误/其他)
- 补单测(用合成 manifest + 合成 conversation JSON 样例验证统计与聚类正确),不依赖网络/真实 rollout;现有 pytest tests/ 全绿;更新 README.md/docs/mvp_usage.md

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_4
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
