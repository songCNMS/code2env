# task024_integration_rollout_runner - History Log

<!-- METADATA:SESSION=2 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_5` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 接受任务 + 准备测试/放量计划

- 接受 task024（tester + 集成放量 runner），建分支 `intern_code2env_worker_5/task024_integration_rollout_runner`，Idle→Working。
- 读四能力 PR 文档：D1 task020 batch(w1)/D2 task021 rollout driver(w2)/D3 task022 conversation 导出(w3)/D4 task023 报告(w4)，抄录三套共享契约（gen manifest / RolloutResult-conversation / qualified 定义）。
- 核验环境：endpoints.txt（行1 gpt-5.5 外网 + 行2+ 本地 127.0.0.1 回退）存在；endpoints.vpn.txt 不存在；coordinator outputs/ 存在但无 rollouts/ 子目录（D3 自动 mkdir）；当前 main 的 llm.py 无 chat()，无 batch/rollout/rollout_export/report.py。
- 测试计划写入 task_knowledge.md：Phase1 各 PR 逐条验收，Phase3 格式门(1-3 env, mock/本地端点)→放量(≥100 env, gpt-5.5 主+本地回退)→导出 conversation JSON 到 coordinator outputs/rollouts/→汇总报告。
- 等 team_lead ping 各 PR 分支名启动 Phase1。

## Session 2 - 2026-06-13 - Phase1：PR#12 task022 conversation 导出 (D3) 验证

- 环境：分支 intern_code2env_worker_3/task022_conversation_json_export（HEAD 2758a97），base main，python3 3.12.3；只读测试、未改其码、工作树 clean。
- 全量单测：`python3 -m pytest tests/ -q` = **44 passed**（新增 tests/test_rollout_export.py），与 worker_3 自测一致。
- 独立验证（自造 RolloutResult 样例，12 项子检全 PASS）：
  - PASS write_conversation：自动 mkdir、写 `<env_id>.json`、append `rollouts.jsonl`（多次写行数递增）。
  - PASS 默认目录 = coordinator outputs/rollouts/；`CODE2ENV_ROLLOUT_EXPORT_DIR` 覆盖生效（注：import 期读取，须进程启动前设或显式传 out_dir）。
  - PASS validate_conversation：<2 轮却 qualified→报错；qualified 但无 submit_answer→报错；诚实 unqualified(1 轮/qualified=False)→通过；缺字段→报错。
  - PASS loader 往返：write→load 等价；iter_jsonl 计数正确、跳空行。
  - PASS 坏数据不落盘：类型错触发 ConversationSchemaError，且因 validate 在 mkdir 前→目标目录/文件均未创建。
  - 契约字段未改名（env_id/model/endpoint_source/.../final{submitted_answer,correct,score,score_breakdown,steps}/num_tool_call_rounds/qualified/termination_reason/retries/errors）。
- 附注（非缺陷）：diff vs main 显示 task023/task024 文档"被删"，实为 worker_3 分支基线早于这两 task 创建的 base-skew，merge against main 不会真删；CLI 另含 `rollout-export` 子命令（加分）。
- 结论：PR#12 全部验收 **PASS**，已 mailbox 回报 lead。

### PR#14 task020 批量pipeline (D1) — PASS

- 分支 intern_code2env_worker_1/task020_batch_generation_pipeline（HEAD f3e7ab7），pytest=**44 passed**（+test_batch.py）。
- 合成本地 repo 独立跑 generate_batch + synthesize_fixture：manifest 严格契约（top/summary/envs/fixture/skipped 字段精确）、empty_signature+typed_signature 两策略、跳过记 reason、build_ok 计数正确、EnvPackage 含 env_spec.json 均 PASS。
- generated_envs/ 与 .code2env_cache/ 均已 gitignore（外部源码/产物不入 git）；spec.py 改动向后兼容（draft_env_spec 加可选 candidates）。
- 结论 **PASS**，已 mailbox 回报。

### PR#13 task023 报告 (D4) — PASS（带 1 个跨模块聚类 finding）

- 分支 intern_code2env_worker_4/task023_rollout_summary_report（HEAD 462bfff），pytest=**42 passed**（+test_report.py）。
- 合成 D1 manifest + D3 conversation（按已验证契约）跑 write_report：report.md+report.json 产出；生成成功率/by_repo/合格率(2/3)/平均 score/by_model 全部数值正确；契约字段未改名；md 含 Qualified/Mean score/By Repo。
- ⚠️ **Finding（非阻塞，medium）**：report.py 失败聚类关键词表与 D1 batch.py 实际 reason 串不匹配——`untyped_required_param:*`、`unsupported_param_type:*`（fixture 合成失败主因）、`requires_instance`/`possible_side_effect`/`not_module_level`/`function_node_not_found` 全落入 `other` 而非 `fixture_unsynthesizable`。w4 单测用含 "fixture"/"synthes" 的合成串故未暴露。建议 w4 在 `_TAG_KEYWORDS["fixture_unsynthesizable"]` 增补这些子串，否则 Phase3 最终报告"fixture无法合成"簇恒为 0、可解释性打折。数值指标不受影响。
- 结论：功能/指标 **PASS**，1 finding 已回报 lead（由 lead/w4 决定 fix-forward 或合并前修）。

### PR#11 task021 rollout driver (D2) — PASS

- 分支 intern_code2env_worker_2/task021_llm_rollout_driver（HEAD 01c6152），pytest=**46 passed**（+test_rollout.py）。
- 独立验证（真实 built env + MockChatLLM/ScriptedSolveChat，4 场景 + parse 单测全 PASS）：
  - PASS OpenAICompatibleLLM.chat() 新增（llm.py:84）；run_rollout 多轮 loop（obs+tools→JSON tool_call→step→至 submit/budget）。
  - PASS parse_action_from_message 多格式：native tool_calls / {type:tool_call} / {tool,arguments} / {name,args} 别名 / ```json 围栏；prose 与 arguments 非 object 正确报错。
  - PASS malformed→重试：parse_error 记录、retries 递增、纠错后续继续到 submit。
  - PASS 多端点回退：primary 全失败→fallback，endpoint_source=fallback:Kimi-K2.6，errors 记录。
  - PASS budget 停：max_rounds=4 未提交→termination_reason=step_budget_exhausted、qualified=False。
  - PASS RolloutResult 契约字段精确（13 顶层 + final 5 字段）；steps 含 action/tool_result/reward/parse_error；final.score_breakdown 五维；qualified=≥2轮+submit。
  - 确认 w2 关键设计：tools 仅用于建 system prompt，caller.generate 传 tools=None（不发 OpenAI 原生 tools 字段，规避网关拒绝）。
- CLI：`code2env rollout <env_pkg> --max-rounds --llm-mode endpoint|mock --llm-model gpt-5.5 --fallback-model --endpoint-file`。
- 注：本轮用 mock 验证（确定性）；真实本地端点(127.0.0.1:39000 gpt-oss-120b)/gpt-5.5 的 live 调用留到 Phase3 格式门实跑。
- 结论 **PASS**，已 mailbox 回报。Phase1 四个 PR(D1/D2/D3/D4) 全部验证完毕。
