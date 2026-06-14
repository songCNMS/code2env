# code2env_lead - History Log

<!-- METADATA:SESSION=1 -->

## Session 0 - Created with team lead

- 创建 team lead `intern_code2env_lead` 时自动生成本 manage team 常驻任务。
- 本任务在 team 存在期间保持 InProgress。

## Archive P0-1 - PRD P0 三项缺口拆解与下发

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

### Archive P0-1 续 - 实现完成 + review + 合并编排
- 三项实现 PR 全部完成：PR#9(task010 ToolExtractor,16 passed)、PR#7(task012 TestLinkIndex,18 passed)、PR#8(task011 reward,23 passed)。
- Lead 代码 review（派 3 个 review 子代理对照各自 PRD 节逐条核）：三项均 APPROVE，仅非阻塞 nits。
  - PR#9 nit：WIP.md 重复行；分支落后 main(diff 幻影删除非合并危险)。
  - PR#7 nit：名称子串匹配偏宽(`add`→`test_address`)误关联；分支落后 main。
  - PR#8 nit：默认权重 0.05/0.20/0.65/0.05/0.05 与 PRD 7.7 表(0.05/0.25/0.50/0.10/0.10)不一致——既有 spec.py 声明,非本 PR 回归,记 backlog 文档/取值对齐,不阻塞。
- Tester：worker_4 [1/2] PR#9 七条验收全 PASS 建议 merge；PR#7[2/2] 与 worker_5 PR#8 验证进行中。
- 合并编排：PR#9 双签→批准 worker_1 self-merge(首合,对 main 干净)；PR#7/PR#8 待 PR#9 合并后各自 merge main 解冲突(spec/indexer/models/runtime/README/mvp_usage 重叠)+重测+复验再顺序 self-merge。
- 关键校正：默认分支是 main（非 master）。
- 监工采用事件驱动后台等待器（mailbox 有未读即唤醒），替代盲轮询 cron。

### Archive P0-1 完结 - 三项 P0 全 merge + 最终验证 + 回报 coordinator
- 合并顺序执行无碍：PR#9(e2825ad) 先合(对 main 干净)；PR#7(c166e2f) 先修阻塞缺陷(test_links_for_candidate→links_for_candidate, pytest 误收集 test_ 前缀公有函数, unittest 漏检)再 merge main(ort 自动无冲突)；PR#8(f2b3b42) merge main 解 runtime.py 冲突(五维 reward + inspect_state/call_<helper> dispatch 两边共存)。
- 最终 main HEAD f2b3b42 含三项；pytest=31 passed；worker_5 B 轮 E2E scan→select(mock)→draft→materialize→build→smoke 全绿(ok=true,score=1.0)，新能力端到端可见(语义工具+inspect_state+ToolSpec.provenance、task_sources>=2、五维 score_breakdown)，判无回归。
- 已回报 coordinator(default 通道)；通知 w4/w5 self-merge QA 文档 PR#6/#10 并回 Idle。
- 5 worker 全投入(w1/w2/w3 实现、w4/w5 tester)，符合用满 active workers 原则。
- backlog：reward 默认权重 vs PRD 7.7 表对齐(裁定本轮保持现状)、TestLink 子串匹配改词边界。
- team_lead 管理任务按生命周期规则保持 InProgress。

## Session 2 - 规模化100 env + gpt-5.5 多轮 rollout 验证（拆解下发）
- 新目标:GitHub 拉 requests/flask/rich/click/jinja2→生成≥100 env→gpt-5.5 多轮 rollout 验证→conversation JSON+报告。非 RL 训练,只做 rollout 验证 driver。
- 侦察关键事实:
  - OpenAICompatibleLLM 只有 evaluate_candidate,无通用 chat→driver 须新增 chat()。
  - endpoints.txt(/home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt) 行1 gpt-5.5(外网)+行2- 本地127.0.0.1(Kimi-K2.6/xyz-30b)可作回退;endpoints.vpn.txt 不存在;llm.py 默认 /work-agents/endpoints.txt 不存在,必须显式 --endpoint-file。
  - CLI 无 batch/rollout/report 命令需新建;.code2env_cache/ 已 gitignore(clone 安全);coordinator outputs/rollouts/ 需 mkdir。
  - Session1 语义工具(3-8 tools+inspect_state)支撑'≥2轮 tool_call'可达。
- 拆 5 子任务(4 能力独立 PR+1 集成/tester,用满5 worker):
  - w1 task020 批量pipeline+fixture合成+gen manifest;w2 task021 rollout driver(+LLM.chat+多端点回退);w3 task022 conversation JSON 导出;w4 task023 汇总报告;w5 task024 QA+集成放量runner。
- lead 定义跨worker契约解耦:gen manifest schema(w1产,w4/w5消费)+conversation JSON schema(w2产,w3落盘,w4消费)。字段勿改名,歧义先问 lead。
- 依赖:w5 Phase3 放量 blockedBy task020/021/022 merge;Phase1 各 PR 到达即验。先 1-3 env 验格式(mock/本地)再放量100(避 gpt-5.5 限速)。
- 踩坑提醒已下发:公有函数名勿以 test_ 开头(pytest 收集坑,ERROR_BOOK E1);cli.py 三 worker 都加子命令→各仅加 subparser+一行减冲突,merge 顺序解决。

## Archive P0-3 - 清除假阳性 + 拿真实正确率（拆解下发）
- Coordinator 抽查 Session2 100 rollout:99% 合格成立、五维 reward 正确,但 exact-match correct 3/100 全是假阳性,真实正确率≈0。
- 两根因(coordinator 已定位):A 依赖缺失—flask 全 env golden=ModuleNotFoundError(werkzeug 未装),agent 同样报错即 exact_match=True;B agent 自造 fixture—requests.cookies.create_cookie 自传 args=[x,x] 与 golden fixture 不符。
- 侦察确认:executor.run_symbol_subprocess 用 sys.executable 跑子进程,repo 第三方依赖未装;runtime._call_source 同问题。
- 拆 5 子任务下发(用满5 worker):
  - w1 task030 依赖安装(per-repo venv)+golden重算+weak_oracle 标注(executor/envdeps/spec/materialize/builder/runtime/batch)
  - w2 task031 rollout prompt 修正(禁自造 call_entrypoint 参数,留空走 fixture 缺省回退)
  - w4 task033 报告真实 correct率(剔 weak_oracle 分母+装依赖前后对比+各repo smoke变化)
  - w3 task032 tester(验三 PR)
  - w5 task034 集成重跑(装依赖重算 golden→定 weak_oracle 集→可用子集 gpt-5.5 重跑→rollouts_v2/→报告)
- lead 定义 golden_status 契约(manifest.envs[].golden_status ∈ {real_value, weak_oracle:<reason>})解耦 w1/w4/w5。
- 依赖:w5 重跑 blockedBy task030/031/033 merge;rollouts_v2/ 与旧 rollouts/ 并存不覆盖。
- 范围控制:只做依赖修复+prompt修正+重跑+报告,差分oracle/QualityGate 仍 backlog;装不动的库跳过记 reason 不卡死。

## Archive P0-3 to P0-4 - 信封归一+确定性过滤(拿真实非零正确率)
- Session3 三修复(A 装依赖/B prompt/报告)全 merged(main 108 passed)。w5 v2 重跑:根因A 证实(flask golden ModuleNotFoundError 24→0、real_value 0→9、smoke 0→8),根因B 证实(agent call_entrypoint 传空 args 用 fixture)。
- 但 v2 true_correct=0/75。lead 抽查+全量核对发现:75 个 incorrect 全是 wrapper 形状不符,非值错——agent submit 里层 value,golden 存完整工具信封 {ok:true,value:{kind:json,value:..}};70/75 submit==call_result.value(verbatim 即对),agent 实际 value-correct≈93%。0% 是假阴性。
- coordinator 核验后开 Session4 新目标,并补第二根因:②非确定性 golden(内存地址 repr/绝对路径/hash/时间戳,每次跑不同,永不可 match;v2 weak_oracle_skipped=25 只剔'仍报错'的,75 里仍混非确定性→可用集高估)。coordinator 选 runtime 信封归一(优于 lead 原 prompt 方案)+确定性门禁。
- 拆 5 worker:w2 task037 runtime 信封归一比较(evaluate/submit 归一,scripted_smoke 不破,双形状都对);w1 task038 确定性门禁(重复执行N次+非确定性特征→nondeterministic 剔除,determinism 字段);w4 task039 report_v3 类别拆分(确定性可用/信封转对/非确定性剔除/仍错+v1→v2→v3);w3 task040 tester;w5 task041 v3 重跑(确定性可用集→rollouts_v3/→report_v3/)。
- lead 契约:manifest.envs[].determinism ∈ {deterministic, nondeterministic:<reason>};与 golden_status 配合定确定性可用集。
- 并行:w1 task035 uv venv 兜底 PR#22 待 w3 验+合(硬化 A 装依赖在缺 python3-venv 节点可用;v2 用 runner 侧 uv wrapper 临时绕过)。
- 范围:只做信封归一+确定性过滤+重跑+报告;差分/变形 oracle 仍 backlog。

## Session 4 - 信封归一+确定性过滤 review/合并编排
- 实现 PR 推进:w2 task037 信封归一(PR#23,121 passed)、w1 task038 确定性门禁(PR#24)、w4 task039 report_v3(PR#26)、w1 task035 uv 兜底(PR#22, w3 PASS 待合)。
- lead review PR#23 抓到关键正确性问题(REQUEST_CHANGES):贪婪剥壳"剥到没壳为止"在目标函数本身返回 wrapper 形状 dict({ok:true,value:X}/{kind:json,value:X})时,会把 golden 一路剥到最内,agent 提交错误 bare 内值即误判 correct——重引 Session3 修掉的碰撞假阳性。修法:不贪婪归一 submitted,改为把 golden 按已知 executor 结构剥恰好2层得 canonical X,correct ⟺ submitted ∈ {X, {kind:json,value:X}, {ok:true,value:{kind:json,value:X}}} 三种确定形状。已让 w2 改+补测+rebase。
- w3 PR#23 验证暂停待修订版;PR#22 uv 兜底 w3 PASS,w1 先合再 rebase task038。
- 回 coordinator session9 跟进:037 review中/038待审/039待审/041 blocked;ETA~50-70min;卡点仅 037 过度剥壳(已处理)。
- 教训:信封归一不能贪婪剥(会过度剥到函数自身 wrapper 形状返回值),要按 golden 已知固定结构定深、和确定形状集比对。

## Session 5 - v3 三修复合并完成 + w5 卡住改派 w1
- Session4 三 PR 全 merged:信封①(#23 7c0a82c)/report_v3(#26 ba7dbf7)/确定性②(#24 716b62d),main 148 passed。lead review 全 APPROVE(PR#23 抓过度剥壳 REQUEST_CHANGES 后修订)+ tester(w3)全 PASS + 037↔039/038↔039 交叉核对一致。Deliverable① 完成。
- v3 重跑关键路径事故:原 runner w5(task041)疑似 session 卡住——lead ping 启动后 w5 status 仍"待 ping"、无 rerun 进程、outputs/rollouts_v3 无产物。coordinator roll-call 告警并授权改派。
- 处置:核实(0 产物/0 进程/status 未动)确认 w5 卡住→改派 v3 执行给空闲 w1(task042,深谙 envdeps/determinism;uv 兜底已折进 envdeps 无需 wrapper)→令 w5 stand down 避免双跑 outputs/rollouts_v3→回 coordinator。
- 教训:peer send "delivered" 只到 transport,不保证 worker session 消费;关键路径单点 runner 卡住要靠客观信号(产物/进程/status)核实,不能只看 delivered;coordinator roll-call 用客观活跃度(git+PR+产物)发现卡点很有效。worker 卡住时果断改派给空闲 worker,别让关键路径空等。

## Session 1 - qlib indexer side-effect refinement

- 收到 coordinator qlib 扫描结论：microsoft/qlib commit d5379c520f66a39953bad76234a7019a72796fd0 共 2860 candidates、493 有 test links，221 个标 possible_side_effect，其中 93 个仅因 generic `get` 命中。
- 评估 5 个 active workers：w1/w2/w4 idle，w3/w5 working；本项为单一 indexer 代码路径 + 独立验证，分配 w4 实现、w2 tester，未用满 5 人以避免窄改动上的 PR/验证冲突。
- 在共享 repo 创建并推送 task043_indexer_side_effect_get_filter；w4 实现 PR#29，w2 独立验证。
- Lead review 结论：PR#29 将 possible_side_effect 从 basename-only call matching 改为 AST call-target matching，普通 dict/object `.get()` 不再标风险，`requests.get`、`session.post`、`open`、`subprocess.run` 仍标风险；聚焦测试覆盖验收点。
- Tester w2 验证 PASS：`python3 -m pytest -q tests/test_indexer_side_effects.py` 为 2 passed，`python3 -m pytest -q` 为 150 passed，qlib pinned scan old basename get-only=93 降为 patched get-only=6。
- PR#29 已由 w4 self-merge 到 main，merge commit d3b1e9e6；GitHub formal approve 因同一 GitHub identity 被拒，team lead merge decision 仍为 APPROVE 并通过 peer send 通知 worker self-merge。
- 已记录 broader future work：基于测试的 fixture extraction for `pd.Timestamp`/`np`/class instance，以及 instance-method env support。
