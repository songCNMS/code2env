# task010_semantic_tool_extractor - History Log

<!-- METADATA:SESSION=1 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_1` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 实现 + 合并

- 接受 task010，建分支 `intern_code2env_worker_1/task010_semantic_tool_extractor`，开 PR #9。
- 实现语义化 ToolExtractor：
  - `indexer._step_blocks` 把入口函数 body 拆成语义 step(span/kind/callees)；`FunctionCandidate.steps` 新字段。
  - `ToolSpec.provenance` 新字段；`spec._tools_from_candidate` 生成 inspect_task/inspect_state(只读 state inspector)/call_entrypoint/call_<helper>(direct callee)/call_helper(sandbox 向后兼容)/submit_answer，每 tool 带 input+output schema+side_effects+provenance；工具数恒在 [4,8]。
  - 有副作用 helper 不生成 call_<helper>，记入 call_entrypoint.provenance.sandboxed_side_effect_helpers。
  - `runtime` 经 provenance name→symbol 映射 dispatch 语义 helper tool，新增 inspect_state，向后兼容原 tool。
  - 新增 3 个单测；更新 README.md 与 docs/mvp_usage.md Runtime Tools 段。
- 自测 `python3 -m pytest tests/ -q` → 16 passed(13 旧+3 新)。
- lead 代码 review APPROVE + tester(worker_4) 七条验收全 PASS。
- 清理 WIP.md 重复 `# WIP` 行(lead nit)。
- 按 worker merge 流程 squash 合并 PR #9 到 main，确认 MERGED，清理本地分支，mailbox 回报 lead。
