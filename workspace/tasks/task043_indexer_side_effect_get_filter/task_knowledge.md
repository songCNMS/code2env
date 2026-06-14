# task043_indexer_side_effect_get_filter - Task Knowledge

<!-- METADATA:SESSION=2 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_4`。
2. 本仓库默认分支为 `main`，本任务实现 PR 为 https://github.com/songCNMS/code2env/pull/29。
3. `FunctionCandidate.calls` 仍保留 basename 列表；`possible_side_effect` 现在直接检查 AST call target，以区分 `payload.get()` 与 `requests.get()`。
4. qlib pinned scan result: candidates=2860, old basename possible_side_effect=221, old get-only=93, patched possible_side_effect=122, patched get-only=6.
5. Session 2 verification confirmed implementation commit `a092a9e` remains green with focused tests and full pytest.
