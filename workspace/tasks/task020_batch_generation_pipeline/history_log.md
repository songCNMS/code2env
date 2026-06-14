# task020_batch_generation_pipeline - History Log

<!-- METADATA:SESSION=2 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_1` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 实现 (PR #14)

- 接受 task020，建分支 `intern_code2env_worker_1/task020_batch_generation_pipeline`，开 PR #14。
- 新增 `code2env/batch.py`：`generate_batch` 跨 repo `scan → synth fixture → draft → build [→ smoke]`，按 target 全局封顶，写契约化 `manifest.json`(summary/envs/skipped/by_repo)。
- `synthesize_fixture`：基于 AST 签名，`empty_signature`(无必填参)/`typed_signature`(必填参全受支持注解)；支持 str/int/float/bool/容器/Optional/下标泛型/前向引用字符串；无法合成→skip 记 reason。
- 跳过规则：not_module_level/requires_instance/possible_side_effect(除非 --include-side-effects)/untyped_required_param/unsupported_param_type。
- `spec.draft_env_spec` 加可选 `candidates` 参数(向后兼容)复用单次 index_repo。
- `cli.py` 加 batch subparser + 1 行 dispatch + 小 `_batch`；README.md/docs/mvp_usage.md 增 batch 段与 manifest 契约。
- 新增 tests/test_batch.py(13 个)；`pytest tests/` → 44 passed；CLI batch 跑通。
- mailbox 回报 lead PR# 与自测，待 tester(w5) 验证与 lead review。
- 本 PR 小规模合成 repo 闭环，放量 ≥100 由 w5 执行。

## Session 2 - 2026-06-13 - Review 通过 + 合并

- lead review APPROVE + tester(w5) 全验收 PASS(44 passed, manifest 契约精确)。
- 按 lead 指示 `git merge origin/main`(D3 PR#12 已 merged f79197d)：解决 cli.py 冲突(保留 batch + rollout-export 两个 subparser + 各自 dispatch + 函数定义)、README.md 冲突(保留 Batch + Rollout 两段)，docs/mvp_usage.md 自动合并。
- 清理误提交的 WIP.md 占位文件(lead nit)。
- 合并后 `pytest tests/` → 57 passed(我的 13 + D3 的 13 + 既有)；CLI batch/rollout-export 子命令均注册可用。
- 状态文件 →Idle/Completed，self-merge PR#14(squash)，mailbox 回报 squash commit。
