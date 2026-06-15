# task_coordinator_code2env_coordinator_8b1dc080 - Task Knowledge

<!-- METADATA:SESSION=21 -->

## Knowledge Entries

1. 本任务是 coordinator 生命周期任务，只要 coordinator 存在就不可完成。
2. `code2env` 的主链路是 `scan -> draft -> build -> smoke/rollout -> export/report`：从 Python 仓库 AST 候选函数生成 EnvSpec/EnvPackage，再用 sandbox runtime、golden answer、多维 reward 和 rollout/report 工具评测 agentic RL 环境。
3. qlib 调试显示：当前 side-effect 检测把所有名为 `get` 的调用都视为风险，会在数据/配置密集代码中产生大量 `possible_side_effect` 误报；应区分 HTTP/network qualified calls（如 `requests.get` / `session.post`）和普通 `dict.get` / object getter。
4. qlib 的强测试候选常需要非 JSON fixture（`pd.Timestamp`、numpy、类实例、数据目录/provider）和 test assertion oracle；后续要从测试构造 task，需要支持测试派生 fixture/harness，而不仅是 `{"args": [], "kwargs": {}}` JSON 直传。
5. `task043_indexer_side_effect_get_filter` 已在 PR #29 合入 `main`：普通 `.get()` 误报已显著收敛（qlib get-only 93 -> 6），后续类似筛选应优先基于 merged `main` 重新扫描。
6. 当前代码能力可以通过 repo 外 standalone harness 先闭环 qlib-derived task：把非 JSON fixture 的 qlib 测试语义改写成 JSON-friendly entrypoint，可立即生成 EnvPackage 和 endpoint rollout JSONL；真正从 qlib 原测试直接抽取 `pd.Timestamp`/实例对象仍需要后续 harness/fixture extractor 能力。
7. 向主管飞书发送本地文件时，当前 daemon HTTP 层只公开文本发送；文件可复用 `intern-cli/scripts/daemon/feishu_daemon.py` 的 `FeishuAPI.upload_file` + `send_file`，目标 chat_id 可从 `/home/leisong/codes/work-agents/.feishu_registry/<intern>.json` 读取。
8. 当前 rollout 记录的是 agent 外部工具调用轨迹，不是目标函数内部动态调用轨迹；`call_entrypoint` 是黑盒执行整个目标函数，helper 工具只是可选。若希望 rollout 成为“真实实现子函数序列”，需要显式 subfunction-trace/decomposed 模式：按 `ToolSpec.provenance.steps`/动态 trace 约束 required helper sequence，并把 reward/qualified 从“>=2 tool calls + submit”改为覆盖真实 helper 调用链后 submit。
9. 在不改产品代码的前提下，可以用 `run_rollout(..., system_prompt=<custom>)` 强化 endpoint 先调用真实 `call_<helper>` 工具，再 `call_entrypoint`/`submit_answer`；这能生成可审核的 subfunction-trace rollout 数据，但长期应产品化为正式 rollout mode，避免依赖一次性 prompt 约束。
10. coordinator 下发长期实现目标时应优先用 `/api/intern/goal/set`；如果 goal API HTTP timeout 没有回执，应记录为 delivery 未确认，并用 peer send 兜底通知 team_lead，同时在历史中保留 handoff 文件路径和 peer send 回执。
11. `task044_subfunction_trace_rollout` 已在 PR #30 合入 `main`：`code2env rollout --trace-mode subfunctions` 正式可用，默认模式保持黑盒 `call_entrypoint -> submit_answer`；trace records 包含 `subfunction_trace` metadata，可机器验证 required/observed/helper_trace_complete/entrypoint_after_helpers/skipped/missing。
12. 正式 `--trace-mode subfunctions` 在 Session 7 的 10 个 JSON-friendly EnvPackage 上完成 endpoint 数据闭环：primary `gpt-5.5` 能按 required helper tools 生成完整 trace；side-effect helper 未暴露时会进入 `skipped_helpers`，不影响 `helper_trace_complete` 对“可要求 helper”的判定。
13. 真实 qlib 原仓库上的 limiting factor 已实测定位：fresh batch 60 个 env 只有 1 个同时 usable + semantic helper tools。正式 trace-mode 在这个 env 上 endpoint 1/1 correct/helper_trace_complete，说明 trace 产品化可用；提高真实 qlib 数据量应优先解决 test-backed fixture extraction、typed fixture（`pd.Timestamp`/numpy/class instance）、最小依赖/import slicing 和 instance-method env support，而不是继续微调 rollout prompt。
14. semantic helper 是从目标函数实现中抽出的安全直接 callee，并以 dedicated `call_<helper>` ToolSpec 暴露；它的价值是把黑盒 entrypoint 执行拆成可验证的源码子步骤，用于 subfunction trace 覆盖、provenance 审计和过程奖励，而不是代表运行时自动捕获的真实内部调用栈。
15. “至少三个子函数”限制必须按最终可暴露的 dedicated semantic helper tools 计算：只统计安全 direct callee 生成的 `call_<helper>`，不统计 generic `call_helper` 或 side-effect helper；qlib 预扫描显示该门槛很强，2,860 个候选里基础过滤后只有 6 个满足 pure semantic helpers >=3。
16. `task045_min3_semantic_helpers_gate` 已在 PR #31 合入 `main`：`code2env batch --min-semantic-helpers N` 可以强制 batch 只处理至少 N 个 dedicated safe semantic helper 的候选。真实 qlib `N=3` 复验说明 gate 能正确筛出 6 个候选，但 rollout 数据量仍为 0，下一瓶颈是 fixture synthesis/test-backed typed fixtures，而不是 semantic helper gate。
17. qlib min3 候选的下一瓶颈需要同时解决输入和输出两侧：EnvSpec fixture 仍应 JSON-safe，但 executor 必须能 hydrate pandas/numpy/Path/torch 等 descriptor 为真实对象；返回值也需要 canonical serialization，避免复杂对象退化为不可审计的 `repr`。对 network/filesystem side-effect 候选应继续跳过或 sandbox，而不是为了数量强行转 env。
18. `/home/leisong/data/samples` 的离线样本不是已展开 worktree，而是含 bare git repo 与 profile/issue/PR 元数据的 `.tgz` archive；扫描“最新分支”时应抽取 bare git、按本地 heads 最新 committerdate 选 branch，再 `git archive` 展开 commit。Session 16 的可转换候选结果保存在 `../outputs/session16_samples_scan/candidate_results.json` 和 `.md`。
19. Session 16 的静态 eligibility 会高估真实可用性：Session 17 top10 验证显示 10/10 可 draft/build/smoke/mock trace，但只有 1/10 是 `golden_status=real_value` 且 deterministic。后续数据质量统计必须把 weak-oracle build 与 strict usable env 分开；只有 strict usable 才适合计入真实 endpoint rollout 数据。
20. subfunction trace completeness 当前检查的是 required helper tool 覆盖和 `call_entrypoint` 顺序，不保证 helper call 本身成功。Session 17 的 usable endpoint trace 出现 helper 空参数调用错误但仍 helper_trace_complete，因此后续 trace 质量改进应增加 helper call success 校验，或根据 entrypoint fixture/签名合成 helper 参数。
21. Session 18 已将 strict usable/weak-oracle 过滤与 helper call success metric 合并为 `task047_strict_usable_trace_quality` handoff；后续验收应同时看数据口径和 trace 质量口径，避免“构建可跑但只是在复现错误”或“helper 覆盖完整但 helper 调用失败”的假阳性。
22. `task047_strict_usable_trace_quality` 已在 PR #33 合入 `main`：后续生成真实 runnable 数据时应启用 `code2env batch --require-real-value` 或 API `require_real_value=True`，并以 `strict_usable` / `real_value + deterministic` 作为可用 env 口径；`weak_oracle` 只能用于审计和阻塞分析。
23. task047 后 subfunction trace 同时有兼容字段 `helper_trace_complete` 和严格字段 `helper_calls_successful` / `helper_trace_valid` / per-helper results。评估 trace 质量时应优先看严格字段；`helper_trace_complete=true` 只说明 required helper 覆盖和顺序完整，不说明 helper 调用成功。
24. Session 20 fresh strict scan 说明 `/home/leisong/data/samples` 当前 38 个 Python repo 在 `--require-real-value --min-semantic-helpers 3 --no-install-deps` 下只有 1 个 strict usable env，29 个 build 为 weak-oracle；因此后续扩大真实数据量应优先处理安全依赖安装、typed fixture/hydration 或测试派生 fixture，而不是依赖静态 semantic helper gate。
25. fresh strict rollout 的唯一可用 env 仍然 `helper_trace_complete=true` 但 `helper_trace_valid=false`，原因是 helper 参数无法从当前 fixture 自动提供。后续若目标是高质量 subfunction trajectory，应推进 helper argument synthesis 或把 `helper_trace_valid=true` 作为数据入选门槛。
26. Session 21 对 Session20 的 29 个 non-strict built env 归因：全部因为 golden 执行落到 weak-oracle exception，主因是缺依赖/运行环境（`bpy`、`torch`、`matplotlib`、`django`、`languages`）、缺 package metadata、缺输入文件或 CLI/stdout 干扰 executor JSON；没有 nondeterministic 导致的 non-strict built env。后续提升 strict usable 数量应优先做 dependency/runtime fixture/CLI-output 隔离。
