# code2env_lead - Task Knowledge

<!-- METADATA:SESSION=2 -->

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
8. LLM/endpoint(Session2):code2env/llm.py OpenAICompatibleLLM 仅有 evaluate_candidate(候选筛选),无通用 chat;resolve_endpoint_config 支持 --endpoint-file+按 model 名匹配多端点。gpt-5.5 endpoint=/home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt(行1 外网 gpt-5.5,行2- 本地127.0.0.1 Kimi-K2.6/xyz-30b 作回退);endpoints.vpn.txt 不存在;默认 /work-agents/endpoints.txt 不存在必须显式传 --endpoint-file。
9. 多 worker 共改 cli.py(batch/rollout/report 子命令):每个仅加 subparser+一行 dispatch、实现放各自模块,冲突面小;参考 Session1 PR#7/#9 不同区域 ort 自动合并经验。
10. 跨 worker 数据契约由 lead 在 task 文档统一定义(gen manifest / conversation JSON schema),产出方与消费方共享、字段勿改名、歧义先 mailbox 问 lead——避免并行实现 schema 漂移。
11. 大执行任务(放量100+rollout)由 tester/集成 runner 跑(team_lead 不亲跑);先小样(1-3 env,mock/本地端点)验格式再放量,避免外网模型限速浪费。
12. 假阳性教训(Session3):exact-match oracle 的两类坑——①依赖缺失:golden 子进程(executor.run_symbol_subprocess 用 sys.executable)与 runtime call_entrypoint 未装 repo 第三方依赖→golden=ModuleNotFoundError,agent 同样报错即 exact_match=True(error-match 假阳性)。修法:per-repo venv 装依赖,golden 与 runtime 都用 venv python;装后仍异常→标 weak_oracle 剔除分母。②agent 自造 call_entrypoint 参数与 golden fixture 不符→假阴性。修法:rollout prompt 明确禁自造参数、留空走 runtime 的 fixture 缺省回退。
13. 验收要看真实语义而非表面数字:99% 合格率(≥2轮+submit)成立但 correct 3% 全假阳性——合格率衡量交互闭环,正确率才衡量解题;exact-match 正确率必须先保证 golden 是真实值(依赖齐全)且剔除 weak_oracle。
14. exact-match oracle 第三/四类坑(Session4):③提交契约信封错位——golden_answer 存的是 executor 完整信封 {ok:true,value:{kind:json,value:X}},agent 自然 submit 里层 X→精确比差壳判错(假阴性)。修法:runtime 比较前对 submitted 与 golden 做信封归一(剥到底层 value)。④非确定性 golden——内存地址 repr(0x..)/绝对路径/<object at>/hash/时间戳每次跑不同,任何 agent 永不可 match;须确定性门禁(重复执行N次不一致 或 命中特征)标 nondeterministic 剔除分母。教训:0% 正确率别急着归因模型能力,先核 submit 形状与 golden 是否确定/无壳——75 个 incorrect 经核 70+ 实为 value-correct。
15. 诊断纪律:报告关键数字(正确率)前,team_lead 应抽样核对底层语义(submit vs golden 逐条),而非直接转述 worker 报的数字——本轮正是抽查一条 requests env 发现 0% 是信封假阴性,避免了把"真实正确率0%"误报成模型结论。
16. qlib 调试教训: indexer 的 side-effect risk 不能只看 call basename；`payload.get()`/普通 object `.get()` 与 `requests.get()` 需要用 AST call target/receiver 区分，否则大型仓库会产生大量 get-only false positives。
17. qlib 后续改进方向:复杂函数入选后要补测试夹具抽取能力(`pd.Timestamp`、`np`、class instance)与 instance-method env support，才能覆盖 `FullHistoryStateInterpreter.interpret` 一类有测试但依赖实例/fixture 的目标。
18. rollout 数据质量教训:默认 black-box rollout 的 `call_entrypoint -> submit_answer` 能验正确性但不能代表目标函数内部 helper 轨迹；需要显式 trace mode 和机读 `subfunction_trace` metadata 才能生产 helper/sub-function 轨迹数据。
19. trace mode 范围边界:helper sequence 应优先用 direct semantic `call_<helper>` 工具并记录 skipped/unavailable helpers；不要默认强迫所有 rollout 变长，也不要把 generic `call_helper` 当作 direct helper trace 的无损替代。
