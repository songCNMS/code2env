# task023_rollout_summary_report - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_4`。
2. 消费契约(勿改字段名)：manifest={summary:{candidates_scanned,draft_ok,build_ok,smoke_ok,by_repo},envs:[{env_id,repo,draft_ok,build_ok,smoke_ok,smoke_fail_reason,fixture:{ok,reason}}],skipped:[{symbol,repo,reason}]}；conversation={env_id,model,final:{correct,score,score_breakdown},num_tool_call_rounds,qualified,termination_reason,errors}。完整契约见 task020/task022 README。
3. qualified=num_tool_call_rounds>=2 且出现 submit_answer；report.py 优先信任 conversation.qualified 字段，缺失才派生（_is_qualified）。
4. 失败聚类固定 6 tag：dependency_failure/fixture_unsynthesizable/weak_oracle/tool_granularity/format_error/other，按 FAILURE_TAGS 顺序关键词匹配，未命中→other；rollout 未达标且无关键词且 unqualified→归 tool_granularity。
5. rollouts 目录加载优先 per-env `<env_id>.json`，无则回退 `rollouts.jsonl`，避免与合并文件双计数（load_rollouts）。
6. report.py 完全自包含，仅依赖 jsonio(read_json/read_jsonl/write_json)；cli.py 仅加 subparser+1 行 dispatch+_report handler，最小化与 w1/w2/w3 的 cli.py 冲突面。
7. 自测：`pytest tests/`=42 passed（31 旧 + 11 新），`unittest discover`=42 OK；CLI 端到端跑通产出 report.md/report.json。真实放量数据由 w5 在 D1/D2/D3 merge 后用本工具产出。
