# task037_runtime_envelope_normalization - History Log

<!-- METADATA:SESSION=3 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_2` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-14 UTC - 实现信封归一比较 + 自测

- 接受 task，建分支 `intern_code2env_worker_2/task037_runtime_envelope_normalization`，开 PR #23。
- `code2env/runtime.py`：新增 `_normalize_answer_envelope(value)`（贪婪递归从外向内剥 `{ok:true,value}` 工具信封 + `{kind:json,value}` 序列化壳，带 32 次 guard 防自引用；`ok:false`/`{kind:repr}` 保留）与 `_answers_equal(submitted,golden)`；`evaluate()` 与 `_dispatch` submit_answer 的 correct 判定改用 `_answers_equal`。score_breakdown 五维逻辑不变。
- 仅动 runtime 比较层，与 w1(task038)/w4(report) 解耦。
- 新增 `tests/test_envelope.py`（13 用例：多形状同值判对/不同值判错/ok:false 不误判/repr 保留/self-ref guard/built-env 集成提交里层 value/json 壳/完整信封均对/错值判错）；`python3 -m pytest tests/` → 121 passed（含原 108）。更新 docs/mvp_usage.md。
- 待 mailbox 回报 lead，等 tester(w3)+lead review。

## Session 2 - 2026-06-14 UTC - 按 review 改用 canonical 形状集 + merge origin/main

- lead REQUEST_CHANGES：贪婪双向剥壳重引 Session3 假阳性——若目标函数本身返回 wrapper 形状 dict({ok:true,value:5}/{kind:json,value:7})，golden 被一路剥到最内，agent 提交错误 bare 内值会误判 correct。
- 改法：不再贪婪归一 submitted；改为 `_accepted_answer_forms(golden)`——按已知 executor 结构剥**恰好 2 层**({ok:true,value}→{kind:json,value}→X)得 canonical X，correct ⟺ submitted ∈ {X, {kind:json,value:X}, full golden} 精确之一；ok:false/非 json 壳走整包精确比。`_answers_equal` 用 any(==)。evaluate/submit_answer 调用点不变。
- 补回归测：函数返回 {ok:true,value:5} 时 agent 提交 bare 5 判 INCORRECT；返回 {kind:json,value:7} 时提交 bare 7 判 INCORRECT；三正确形状仍 correct。
- 先 `git merge origin/main`（落后 6 commit，含 task030/035；无代码冲突，仅 docs/task 文档自动合并，避免回退）。`python3 -m pytest tests/` → 127 passed。更新 docs/mvp_usage.md 段落。
- 待 mailbox 回报 lead 复审。

## Session 3 - 2026-06-14 UTC - 复审通过 + self-merge

- lead 复审 APPROVE（不剥 submitted、只枚举 golden 三接受形状）+ tester(w3) 全 PASS（127 passed，E2 对抗确认）。批准合并；本 PR 为 Session4 第一个合并（runtime.py 单文件，0 behind main）。
- self-merge（squash）待执行，merge 后 mailbox 回报 squash commit；其后 PR#24/PR#26 依次 rebase 合。
