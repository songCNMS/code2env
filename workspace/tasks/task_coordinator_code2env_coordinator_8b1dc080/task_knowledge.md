# task_coordinator_code2env_coordinator_8b1dc080 - Task Knowledge

<!-- METADATA:SESSION=1 -->

## Knowledge Entries

1. 本任务是 coordinator 生命周期任务，只要 coordinator 存在就不可完成。
2. code2env 当前实现状态（Session 1 审计）：闭环已通 scan→select→draft→materialize→build→smoke（Phase 1/2/3 部分）。已实现：ingest（含 commit pin/clone 缓存）、AST indexer+排序、LLM 候选筛选、EnvSpec(JSON)、4 个通用 tools 的 runtime（reset/step/evaluate）、sandbox（禁网/禁子进程/超时）、exact-match golden。
3. code2env 主要缺口：①TestLinkIndex 缺失且 ingest 直接排除 tests 目录；②ToolExtractor 只生成 inspect_task/call_entrypoint/call_helper/submit_answer 通用工具，未做 PRD 要求的语义化按步骤 3-8 tools；③reward 仅 exact-match+0.05 schema，process/efficiency/safety 维度声明了权重但未计算，差分/变形/golden-trace oracle 缺失；④Phase 4 RL 接入（批量 loader、Trajectory JSONL 导出、Gym-like adapter、random/scripted/LLM rollout demo）几乎全缺；⑤Phase 5 规模化（批量 pipeline、质量报表、失败聚类、review queue）缺；⑥QualityGate 7 项只实现 smoke，其余 6 项缺；⑦CorpusManager / 人工审阅(spec_editor) 缺；⑧ToolSpec 无 JSON Schema 校验门禁。
