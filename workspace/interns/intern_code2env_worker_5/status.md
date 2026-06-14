# intern_code2env_worker_5 - 状态

<!-- METADATA:STATUS=Working,TASK=task034_rerun_rollouts_v2,ROLE=worker,TEAM_ID=code2env -->

| 字段 | 值 |
|------|-----|
| Name | intern_code2env_worker_5 |
| Status | Working |
| Role | worker |
| Team | code2env |
| Current Task | task034_rerun_rollouts_v2 |
| PR | https://github.com/songCNMS/code2env/pull/21 |
| Session | 8 |

最近进展：task034 Step1 进行中 — baseline(装依赖前)build_ok=100/real_value=67;v2 装依赖首跑遇 venv_failed(节点缺 python3.12-venv/ensurepip)→用 uv venv --seed wrapper 绕过(不改合入代码)重跑中。待 golden 修复确认→Step2 重跑→Step3 报告。venv 阻塞将回报 lead。
