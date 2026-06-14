# task030_deps_install_golden_recompute - History Log

<!-- METADATA:SESSION=3 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_1` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 实现 (PR #18)

- 接受 task030，建分支 `intern_code2env_worker_1/task030_deps_install_golden_recompute`，开 PR #18。
- 根因A 修复：
  - `executor.run_symbol_subprocess` 加 `python_executable` 参(默认 sys.executable 向后兼容)；非默认解释器时 PYTHONPATH 注入 code2env 包路径。
  - 新增 `code2env/envdeps.py`：`prepare_repo_env` 建 venv(缓存 `.code2env_cache/venvs`)+pip 装运行依赖；`venv_builder`/`installer` 可注入便于离线单测；装不动跳过记 reason；`golden_status_for` 分类。
  - `spec.draft_env_spec` / `materialize_env_spec` 用 venv python 算 golden + 写 `golden_status`；venv 信息持久化到 `spec.runtime`。
  - `runtime._call_source` 用 `spec.runtime.python_executable`(路径缺失 fallback sys.executable)；`builder` manifest 存 venv/golden 信息。
  - `batch` 每 repo 一次 `prepare_repo_env`；manifest 加 `summary.real_value/weak_oracle` + `by_repo.deps_status` + `repo_deps` + `env.golden_status/deps_status/deps_installed`；weak_oracle 从正确率分母剔除。
  - `cli batch` 加 `--no-install-deps` / `--venv-cache-dir`。
- 新增 `tests/test_envdeps.py`(16)；`pytest tests/` → 99 passed；README/docs 更新。
- mailbox 回报 lead PR# 与自测，待 tester(w3) 验证与 lead review。
- 真实装依赖重算 100 env 由 w5 执行；真实 venv 需 run host 装 python3-venv/ensurepip。

## Session 2 - 2026-06-13 - lead APPROVE, 待合并序 (先别合)

- lead review PR#18 APPROVE(golden_status 契约与 report 精确匹配, 6 条全 PASS)。
- 合并序：等 w3 验证通过 + PR#20 先 merged，lead 再 ping 我；**先别合**。
- 只读 recon(未合并)：确认本分支未改 rollout.py(减行是陈旧分支假象)；origin/main 的 rollout.py 已含 CALL_ENTRYPOINT_FIXTURE_GUIDANCE×2(B/PR#17 b59a067 已并入 main)；PR#20 尚未进 main。
- 合并待办(收到 ping 后)：`git merge origin/main`(解决 WIP.md 小冲突, 拉进 B rollout.py + PR#20 cli.py)→确认 rollout.py 仍含 CALL_ENTRYPOINT_FIXTURE_GUIDANCE→pytest 全绿→self-merge PR#18→清理→mailbox 回报。

## Session 3 - 2026-06-13 - 三签齐, 合并 (最后一个)

- PR#18 三签齐：lead APPROVE + tester(w3) 99 passed + 030↔033 golden_status 交叉核对一致。批准合并(最后一个)。
- `git fetch && git merge origin/main`(含 #17 B + 报告 PR)：仅 WIP.md modify/delete 冲突，`git rm WIP.md` 解决；README/cli.py/docs 自动合并。
- 合并后核验全 PASS：rollout.py 仍含 CALL_ENTRYPOINT_FIXTURE_GUIDANCE×2(B 不丢)；cli.py 同时含 `--baseline-manifest`(report) 与 `--no-install-deps`(本任务)；envdeps.py 在位。
- `pytest tests/` → 108 passed。
- 状态文件 →Idle/Completed；self-merge PR#18(squash)；mailbox 回报 squash commit；lead 随即 ping w5 启动重跑。
