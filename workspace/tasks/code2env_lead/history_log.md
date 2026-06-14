# code2env_lead - History Log

<!-- METADATA:SESSION=1 -->

## Session 0 - Created with team lead

- 创建 team lead `intern_code2env_lead` 时自动生成本 manage team 常驻任务。
- 本任务在 team 存在期间保持 InProgress。

## Session 1 - PRD P0 三项缺口拆解与下发

- 收到 Pressing Goal：对照 docs/code2env_agentic_rl_prd.md 落地 P0 三项（F5 ToolExtractor / F7 多维 reward / F2 TestLinkIndex）。
- 核对现状：MVP 闭环已通（main 分支）。定位三项落点：
  - P0-1 spec.py:_tools_from_candidate 只出 4 通用 tool；indexer 已有 calls/helper_candidates 基础。
  - P0-2 runtime.py:step/evaluate 仅 exact-match final + 固定 0.05 schema，五维 weights 已声明未实算。
  - P0-3 ingest.py:_is_supported_source_file 排除 tests/；indexer 无 TestLinkIndex；spec provenance 仅 1 条 source_span。
- 拆为 5 个 worker 子任务并下发（internctl team assign-worker-task，各自独立 PR）：
  - w1 task010_semantic_tool_extractor、w2 task011_multidim_reward、w3 task012_testlink_index_ingest（实现）
  - w4 task013_qa_toolextractor_testlink（验 PR1+PR3）、w5 task014_qa_reward_e2e（验 PR2 + 全链路回归）
- 全员投入：三项天然独立可并行 + 双 tester 拆分验证并兜底端到端回归。
- 下步：等 worker mailbox 回报，分支就绪后 ping 对应 tester，再 review + approve + 通知 self-merge。
- P1/P2（差分 oracle、QualityGate 6 项、Phase4 RL 接入、CorpusManager、人工审阅）列 backlog，本轮不做。

### Session 1 续 - 实现完成 + review + 合并编排
- 三项实现 PR 全部完成：PR#9(task010 ToolExtractor,16 passed)、PR#7(task012 TestLinkIndex,18 passed)、PR#8(task011 reward,23 passed)。
- Lead 代码 review（派 3 个 review 子代理对照各自 PRD 节逐条核）：三项均 APPROVE，仅非阻塞 nits。
  - PR#9 nit：WIP.md 重复行；分支落后 main(diff 幻影删除非合并危险)。
  - PR#7 nit：名称子串匹配偏宽(`add`→`test_address`)误关联；分支落后 main。
  - PR#8 nit：默认权重 0.05/0.20/0.65/0.05/0.05 与 PRD 7.7 表(0.05/0.25/0.50/0.10/0.10)不一致——既有 spec.py 声明,非本 PR 回归,记 backlog 文档/取值对齐,不阻塞。
- Tester：worker_4 [1/2] PR#9 七条验收全 PASS 建议 merge；PR#7[2/2] 与 worker_5 PR#8 验证进行中。
- 合并编排：PR#9 双签→批准 worker_1 self-merge(首合,对 main 干净)；PR#7/PR#8 待 PR#9 合并后各自 merge main 解冲突(spec/indexer/models/runtime/README/mvp_usage 重叠)+重测+复验再顺序 self-merge。
- 关键校正：默认分支是 main（非 master）。
- 监工采用事件驱动后台等待器（mailbox 有未读即唤醒），替代盲轮询 cron。
