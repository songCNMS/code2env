# task023_rollout_summary_report - Task Knowledge

<!-- METADATA:SESSION=3 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_4`。
2. 消费契约(勿改字段名)：manifest={summary:{candidates_scanned,draft_ok,build_ok,smoke_ok,by_repo},envs:[{env_id,repo,draft_ok,build_ok,smoke_ok,smoke_fail_reason,fixture:{ok,reason}}],skipped:[{symbol,repo,reason}]}；conversation={env_id,model,final:{correct,score,score_breakdown},num_tool_call_rounds,qualified,termination_reason,errors}。完整契约见 task020/task022 README。
3. qualified=num_tool_call_rounds>=2 且出现 submit_answer；report.py 优先信任 conversation.qualified 字段，缺失才派生（_is_qualified）。
4. 失败聚类固定 6 tag。classify_reason 用 **lead canonical reason→tag 映射(子串/前缀匹配，reason 形如 `tag:detail`)**，非自由词关键词：dependency_failure←modulenotfound/importerror/no module named 或 `draft_error`含import；weak_oracle←golden_error*/answer_mismatch；format_error←parse_error/schema；fixture_unsynthesizable←untyped_required_param/unsupported_param_type/requires_instance/possible_side_effect/not_module_level/function_node_not_found/no_fixture；其余→other；rollout 不合格无信号→tool_granularity(在 rollout 聚类层 re-tag，非 classify_reason)。
8. [踩坑] 失败聚类必须对齐上游真实 reason 词汇，不能凭直觉造关键词——w5 发现自由词版本导致 fixture_unsynthesizable 恒 0、生成失败全进 other。测试要用上游真实 reason 串(canonical token)，不能用自造可读句。
5. rollouts 目录加载优先 per-env `<env_id>.json`，无则回退 `rollouts.jsonl`，避免与合并文件双计数（load_rollouts）。
6. report.py 完全自包含，仅依赖 jsonio(read_json/read_jsonl/write_json)；cli.py 仅加 subparser+1 行 dispatch+_report handler，最小化与 w1/w2/w3 的 cli.py 冲突面。
7. 自测：`pytest tests/`=42 passed（31 旧 + 11 新），`unittest discover`=42 OK；CLI 端到端跑通产出 report.md/report.json。真实放量数据由 w5 在 D1/D2/D3 merge 后用本工具产出。
