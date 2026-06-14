# task_coordinator_code2env_coordinator_8b1dc080 - Task Knowledge

<!-- METADATA:SESSION=7 -->

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
