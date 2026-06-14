# task031_rollout_prompt_fixture_fix - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_2`。
2. 根因B：agent 自造 call_entrypoint 的 args（与 golden 用的 fixture 不符）→ 执行成功但 exact_match=False 假阴性。修复在 prompt 层。
3. runtime `_dispatch` 的 call_entrypoint 对缺省 args/kwargs 回退 spec.fixture（`arguments.get("args", spec.fixture.args)`），所以留空 arguments 即用环境 fixture——prompt 据此指示模型留空。
4. 落点仅 `code2env/rollout.py` prompt 层：常量 `CALL_ENTRYPOINT_FIXTURE_GUIDANCE` 注入 system prompt；`build_initial_user_message(obs, fixture)` 回显 fixture。未改 loop/parse/fallback，RolloutResult 契约不变。
