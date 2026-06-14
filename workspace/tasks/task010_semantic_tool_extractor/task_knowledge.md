# task010_semantic_tool_extractor - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_1`。
2. 工具预算固定为 4 个基础 tool(inspect_task/inspect_state/call_entrypoint/submit_answer)，有 helper 时 +call_helper(=5)，再补最多 3 个 `call_<helper>` 语义 tool，总数恒在 [4,8]，满足 PRD 3-8 区间。
3. `inspect_state` 为强制只读 state inspector(provenance.kind=state_inspector)；inspect_task 也是只读。
4. direct callee 与"主函数关键步骤"统一：indexer 新增 `_step_blocks` 把入口函数 body 拆成 step(line span/kind/callees)，`call_<helper>` 的 provenance.entrypoint_steps 记录调用该 helper 的步骤；call_entrypoint.provenance.steps 记录全部步骤。
5. 有副作用的 helper(risk_flags 含 possible_side_effect)不生成 `call_<helper>`，改记到 call_entrypoint.provenance.sandboxed_side_effect_helpers，side_effects 标注。
6. runtime 通过 ToolSpec.provenance(kind=wrapper,backing.kind=function) 构建 name->symbol 映射来 dispatch 语义 helper tool；inspect_state 单独处理；call_entrypoint/call_helper/submit_answer 保持原逻辑(向后兼容)。
7. ToolSpec 新增 `provenance` 字段、FunctionCandidate 新增 `steps` 字段，均带 default，from_dict 向后兼容旧 spec。
8. 自测：tests/test_mvp.py 16 passed(13 旧+3 新)；scripted_smoke 仍 ok。
