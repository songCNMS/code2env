# task038_determinism_gate - History Log

<!-- METADATA:SESSION=2 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_1` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-14 - 实现 (PR #24)

- 先合 PR#22(task035 uv 兜底)到 main，再把 task038 分支 merge 到含 uv 兜底的新 main(避免 envdeps 自冲突)，然后实现。
- 新增 `code2env/determinism.py`：`classify_determinism(golden, repeat_results)`。
  - 强独立信号：默认对象 repr `<… at 0x…>`/`@0x`(6+ hex)→`nondeterministic:object_repr`(单次即判)。
  - 弱信号(memory_addr 裸 0x / abs_path /home//tmp/)：**仅当重复执行不一致时**才用来细化 reason，否则不判(防过度剔除——合法稳定返回的路径/hex 保持 deterministic)。
  - 重复 N 次不一致→`nondeterministic:unstable_across_runs`(捕获 timestamp/RNG/随机 hash)。
- `spec.draft_env_spec` 加 `determinism_runs`(默认 1)：real_value 时重复执行算 determinism 写 provenance；weak_oracle/未算 golden 时 determinism=None。
- `batch.generate_batch` 加 `determinism_runs`(默认 3)：env.determinism + summary.usable(=real_value AND deterministic)/nondeterministic + by_repo 同字段；`cli batch --determinism-runs`。
- 新增 tests/test_determinism.py(含合法路径/hex 稳定返回不被误判)；更新 test_batch 契约；README/mvp_usage 注明 determinism 契约与防过度剔除。
- 自测 `pytest tests/` → 131 passed。
- mailbox 回报 lead PR#24 与自测，待 tester(w3) 验证与 lead review。

## Session 2 - 2026-06-14 - lead APPROVE, 待合并序 (先待命)

- lead review PR#24 APPROVE(over-flag 防护好, 契约一致)。非阻塞: 合前 git rm 误提交的 WIP.md。
- 合并序: PR#23(信封①)先合 → 我 git merge origin/main → git rm WIP.md → pytest 全绿 → self-merge；等 w3 验 PASS + PR#23 merged，lead 再 ping。**先待命，未合并。**
- 待办(收到 ping 后): merge origin/main(可能与 PR#23 在 spec/batch 有交集需解冲突)→git rm WIP.md→pytest→self-merge PR#24→清理→mailbox 回报 squash commit。
