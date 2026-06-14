# task044_subfunction_trace_rollout - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_2`。
2. Independent tester is `intern_code2env_worker_4`; do not change the implementation assignee away from w2.
3. Coordinator handoff path: `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session8_subfunction_trace_rollout_goal.md`.
4. Session 7 evidence paths: debug repo `/home/leisong/codes/work-agents/intern_code2env_coordinator/debug/session7_trace_task_repo`; rollout artifacts `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session7_trace_rollouts/`.
5. Acceptance requires trace mode to preserve default rollout behavior and expose machine-verifiable metadata such as `required_helper_tools`, `observed_tools`, `helper_trace_complete`, `entrypoint_after_helpers`, and skipped helper reasons.
6. Tester plan when w2 PR is ready: focused tests, full `python3 -m pytest -q`, default-mode compatibility check, rollout-export compatibility check if trace metadata touches conversation schema, and at least 3 trace-mode package runs from Session 7 artifacts or equivalent fixtures.
