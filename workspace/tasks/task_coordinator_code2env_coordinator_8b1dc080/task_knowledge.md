# task_coordinator_code2env_coordinator_8b1dc080 - Task Knowledge

<!-- METADATA:SESSION=14 -->

## Knowledge Entries

1. 本任务是 coordinator 生命周期任务，只要 coordinator 存在就不可完成。
2. code2env 当前实现状态（Session 1 审计）：闭环已通 scan→select→draft→materialize→build→smoke（Phase 1/2/3 部分）。已实现：ingest（含 commit pin/clone 缓存）、AST indexer+排序、LLM 候选筛选、EnvSpec(JSON)、4 个通用 tools 的 runtime（reset/step/evaluate）、sandbox（禁网/禁子进程/超时）、exact-match golden。
3. code2env 主要缺口：①TestLinkIndex 缺失且 ingest 直接排除 tests 目录；②ToolExtractor 只生成 inspect_task/call_entrypoint/call_helper/submit_answer 通用工具，未做 PRD 要求的语义化按步骤 3-8 tools；③reward 仅 exact-match+0.05 schema，process/efficiency/safety 维度声明了权重但未计算，差分/变形/golden-trace oracle 缺失；④Phase 4 RL 接入（批量 loader、Trajectory JSONL 导出、Gym-like adapter、random/scripted/LLM rollout demo）几乎全缺；⑤Phase 5 规模化（批量 pipeline、质量报表、失败聚类、review queue）缺；⑥QualityGate 7 项只实现 smoke，其余 6 项缺；⑦CorpusManager / 人工审阅(spec_editor) 缺；⑧ToolSpec 无 JSON Schema 校验门禁。
4. 【Session 2 已闭环】P0 三项已合并 main(HEAD f2b3b42) 并经 coordinator 独立验证(pytest=31 passed, scan E2E 绿)：①缺口②(多维reward) PR#8 已落地 step/evaluate 五维加权+score_breakdown；①缺口①(语义ToolExtractor) PR#9 已按 step/direct-callee 抽语义 tools、tool 数恒[4,8]含 inspect_state、副作用 helper sandboxed；①缺口③(TestLinkIndex) PR#7 已单独索引 tests、建关联、provenance≥2。→ 故 task_knowledge 条目3 中的 ①②③ 已解决，剩 ④⑤⑥⑦⑧ 仍为 backlog。
5. 验证手法记录：worktree add origin/main → python3(非python) -m pytest -q → 用完 `git worktree remove --force` 需在 repo 目录内执行(cwd 会被重置到非 git 目录导致 fatal)。
