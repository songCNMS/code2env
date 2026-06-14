# task037_runtime_envelope_normalization - History Log

<!-- METADATA:SESSION=1 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_2` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-14 UTC - 实现信封归一比较 + 自测

- 接受 task，建分支 `intern_code2env_worker_2/task037_runtime_envelope_normalization`，开 PR #23。
- `code2env/runtime.py`：新增 `_normalize_answer_envelope(value)`（贪婪递归从外向内剥 `{ok:true,value}` 工具信封 + `{kind:json,value}` 序列化壳，带 32 次 guard 防自引用；`ok:false`/`{kind:repr}` 保留）与 `_answers_equal(submitted,golden)`；`evaluate()` 与 `_dispatch` submit_answer 的 correct 判定改用 `_answers_equal`。score_breakdown 五维逻辑不变。
- 仅动 runtime 比较层，与 w1(task038)/w4(report) 解耦。
- 新增 `tests/test_envelope.py`（13 用例：多形状同值判对/不同值判错/ok:false 不误判/repr 保留/self-ref guard/built-env 集成提交里层 value/json 壳/完整信封均对/错值判错）；`python3 -m pytest tests/` → 121 passed（含原 108）。更新 docs/mvp_usage.md。
- 待 mailbox 回报 lead，等 tester(w3)+lead review。
