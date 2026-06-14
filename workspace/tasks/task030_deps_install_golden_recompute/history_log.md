# task030_deps_install_golden_recompute - History Log

<!-- METADATA:SESSION=1 -->

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
