# task010_semantic_tool_extractor - P0-1 语义化 ToolExtractor (F5 / PRD 7.5)

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_1 -->

## 背景

对照 docs/code2env_agentic_rl_prd.md 7.5。当前 spec.py:_tools_from_candidate 不论函数都只生成 inspect_task/call_entrypoint/call_helper/submit_answer 4 个通用工具，未按主函数步骤/直接子函数/状态检查器拆分，导致任务退化为'调一次入口再提交'。indexer.py 已有 ast CallGraph 基础(calls/helper_candidates/metrics)。

## 任务目标

基于 AST 把入口函数的关键步骤(top-level statement block)和直接 callee(helper) 抽成语义化 ToolSpec：每个 tool 带 input/output JSON Schema、provenance(source span/backing symbol)、side_effects 声明；并至少生成一个状态查询/校验类只读 tool(state inspector)。保证 ≥90% 接受环境最终暴露 3-8 个 tools。

## 实现说明

落点: code2env/spec.py(_tools_from_candidate/_task_from_candidate)、code2env/indexer.py(可扩展 CallGraph/分步语义)、code2env/runtime.py(_dispatch 新 tool)。先读 PRD 7.5 完整 ToolSpec 示例与'工具粒度规则'。不要破坏现有 call_entrypoint/submit_answer 闭环。完成后用 mailbox 向 intern_code2env_lead 回报 PR# 与自测结果，等待 tester 验证与 lead review。

## 验收标准

- spec.py 为候选函数生成 3-8 个语义 tools(含保留的 inspect_task/submit_answer)，其中至少含一个状态查询/校验类只读 tool
- 每个语义 tool 的 ToolSpec 含 input_schema/output_schema/side_effects/provenance(backing source span 或 symbol)
- 工具来源覆盖 direct callee(helper) 与主函数关键步骤；有副作用原函数不直接暴露(side_effects 标注)
- runtime.py 能 dispatch 新生成的语义 tools(或保持向后兼容)，scripted_smoke 仍通过
- 新增单测覆盖 tool 数量区间[3,8]、状态 tool 存在性、schema 完整性；现有 tests/test_mvp.py 全绿
- 更新 README.md 与 docs/mvp_usage.md 的 Runtime Tools 段；独立 PR 并 push 自己分支

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_1
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
