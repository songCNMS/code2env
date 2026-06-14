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
5. 多 PR 并行合并：多个 PR 改同一批文件(spec/indexer/models/runtime/README)时，先合一个干净的→其余各自 `git merge origin/main` 解冲突+重测+复验再顺序 self-merge；互不重叠的 PR(如 PR#7 spec/indexer vs PR#8 runtime)可在 base 合入后并行收尾。
6. pytest 收集坑(ERROR_BOOK E1)：公有 API 函数名勿以 test_ 开头，否则 pytest 误当用例收集报 fixture not found；unittest 不收集裸函数会漏检。本仓 CI/基线用 `pytest tests/`，验收须以 pytest 而非 unittest 为准。
7. 本仓默认分支是 main(非 master)；team_lead 监工用事件驱动后台等待器(轮询 mailbox unread, 有即唤醒)比盲 cron 高效。
