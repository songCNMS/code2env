# task021_llm_rollout_driver - History Log

<!-- METADATA:SESSION=3 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_2` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-14 UTC - 实现 rollout driver + 自测

- 接受 task，建分支 `intern_code2env_worker_2/task021_llm_rollout_driver`，开 PR #11。
- `code2env/llm.py`：新增 `OpenAICompatibleLLM.chat(messages,*,tools/timeout/max_tokens/temperature)` 复用 `_post_payload`(加 timeout 形参)；新增模块函数 `assistant_message_from_response`（tool_calls 时 content 回退空串）。
- `code2env/rollout.py`：`run_rollout(env, llm, *, fallback_llm, max_rounds, max_parse_retries, max_llm_retries, ...)` 多轮 loop；JSON-in-content 协议（tools 写进 system prompt）+ 兼容原生 tool_calls；`parse_action_from_message` 支持 {tool,arguments}/{type:tool_call}/{name,args}/fenced；malformed 有限重试记 parse_error；`_FallbackChat` 主端点失败→重试→回退；`MockChatLLM`(脚本化)/`ScriptedSolveChat`(自适应读 env 求解)。返回 RolloutResult 契约。
- `code2env/cli.py`：加 `rollout` subparser + 一行 dispatch（减少与他人冲突）。
- 新增 `tests/test_rollout.py`（15 用例：解析/抽取/合格/纠错/budget/error/fallback）；`python3 -m pytest tests/` → 46 passed。更新 README.md/docs/mvp_usage.md。
- 实测发现并修复 BUG：原把自定义 tool 描述当作 OpenAI 原生 `tools` 字段发给网关 → litellm HTTP 400(`tools.0.function` required)。修为 JSON-in-content 协议下 **不发** `tools`（仅写进 system prompt）。修后用本地可达端点 gpt-oss-120b(127.0.0.1:39000) 实测 live rollout：2 轮 inspect_task→submit_answer，qualified=True，termination=submitted，errors=[]（答案对错取决于模型能力，driver 本身 OK）。
- 待 mailbox 回报 lead，等 tester(w5)+lead review。

## Session 2 - 2026-06-14 UTC - review 通过，待按序合并

- lead review APPROVE + tester(w5) 全验收 PASS（46 passed，契约/回退/纠错/budget 均验证），批准合并。
- Phase3 放量合并序：PR#14(D1) → 本 PR#11(D2) → PR#13(D4)。
- 等 lead 确认 PR#14 merged 并 ping 后：`git fetch origin && git merge origin/main` 解 `cli.py` 冲突（batch + rollout-export + rollout 多个 subparser 及各自 dispatch 全部保留）→ `python3 -m pytest tests/` 全绿 → self-merge。
- 当前：先不动，等待 ping。

## Session 3 - 2026-06-14 UTC - 合并 origin/main + self-merge

- lead ping PR#14(D1) 已 merged(3c247c1)。执行 `git fetch origin && git merge origin/main`。
- `code2env/cli.py` 四处冲突全部解决：imports(rollout + rollout_export 两个 import 都留)、subparser 块(rollout + batch + rollout-export 三个 subparser 都留)、dispatch 块(三条 dispatch 都留)、handler 函数块(_rollout + _batch + _rollout_export 都留)。README/docs 自动合并。
- `python3 -m pytest tests/` → 72 passed；`code2env -h` 列出 10 个子命令(含 rollout/batch/rollout-export)，`import code2env.cli` OK。
- self-merge 待执行；merge 后 mailbox 立即回报 squash commit。
