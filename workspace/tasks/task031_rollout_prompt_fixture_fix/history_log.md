# task031_rollout_prompt_fixture_fix - History Log

<!-- METADATA:SESSION=2 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_2` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-14 UTC - 实现 prompt 修正 + 自测

- 接受 task，建分支 `intern_code2env_worker_2/task031_rollout_prompt_fixture_fix`，开 PR #17。
- `code2env/rollout.py`：新增模块常量 `CALL_ENTRYPOINT_FIXTURE_GUIDANCE`（明确禁止自造 call_entrypoint 参数、留空用环境 fixture，并说明 exact-match 按 fixture 评分）；注入 `build_system_prompt`；`build_initial_user_message(observation, fixture=None)` 回显具体 spec.fixture；`run_rollout` 传 `env.spec.fixture`。
- 仅动 prompt 层，未改 loop/parse/fallback；RolloutResult 契约字段不变。与 w1(task030)/w4(task033) 解耦。
- 新增 4 个单测（断言 system prompt 含 guidance、user message 回显 fixture、空 args call_entrypoint 走 fixture 回退仍 qualified+correct、并文档化根因B 假阴性）；`python3 -m pytest tests/` → 90 passed。更新 docs/mvp_usage.md D2 段。
- 待 mailbox 回报 lead，等 tester(w3)+lead review。

## Session 2 - 2026-06-14 UTC - review 通过 + self-merge

- lead review APPROVE + tester(w3) 五条验收全 PASS（90 passed，dry-run merge clean，过 D3 校验），批准合并；本 PR 为 Session3 第一个合并（rollout.py 单文件，对 main 干净）。
- 分支落后 main 3 commit（均为新 task 文档），`git merge origin/main` 无代码冲突；`python3 -m pytest tests/` → 90 passed，push。
- self-merge（squash）待执行，merge 后 mailbox 回报 squash commit。
