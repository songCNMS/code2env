# code2env_lead - Task Knowledge

<!-- METADATA:SESSION=1 -->

## Knowledge Entries

1. 本任务是 team lead 生命周期任务，只要 team 存在就不可完成。
2. PRD P0 三项缺口的代码落点（对照 docs/code2env_agentic_rl_prd.md）：
   - F5/7.5 ToolExtractor → code2env/spec.py:_tools_from_candidate、code2env/indexer.py（CallGraph）、runtime.py:_dispatch。
   - F7/7.7 多维 reward → code2env/runtime.py:step/evaluate/_dispatch；weights 在 spec.py reward 块已声明。
   - F2/7.2 TestLinkIndex → code2env/ingest.py:_is_supported_source_file（排除 tests）、indexer.py、spec.py:draft_env_spec provenance、models.py。
3. 分配机制：`internctl team assign-worker-task <team> <worker> --task-id --title --background --goal --acceptance(可重复) --details` 会创建 workspace/tasks/<id>/ 标准文档并 peer send 通知 worker。
4. 流程约束：team_lead 不写代码/不跑测试/不 merge；tester 用 mailbox 回报；approve 后通知实现 worker self-merge。
