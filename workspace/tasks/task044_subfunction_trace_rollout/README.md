# task044_subfunction_trace_rollout - Productize subfunction trace rollout mode

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_2 -->

## 背景

Default code2env rollout often produces call_entrypoint -> submit_answer, which is correct for black-box smoke but not useful when rollout JSONL should show target helper/sub-function trajectories. Session 7 validated a temporary prompt-only approach on qlib-style envs: 10/10 qualified, 10/10 correct, 10/10 helper_trace_complete. Evidence: debug repo /home/leisong/codes/work-agents/intern_code2env_coordinator/debug/session7_trace_task_repo and JSONL /home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session7_trace_rollouts/session7_trace_rollouts.jsonl.

## 任务目标

Add a formal subfunction/decomposed trace rollout mode to code2env while preserving default rollout behavior.

## 实现说明

Implementation worker: intern_code2env_worker_2. Independent tester: intern_code2env_worker_4. Coordinator handoff: /home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session8_subfunction_trace_rollout_goal.md. Keep default black-box rollout available; do not make every rollout longer by default. Preserve existing RolloutResult field names and rollout-export validation. Suggested result namespace may be subfunction_trace, following Session 7 artifact. Final worker report should include PR id, test commands/results, default-mode compatibility, 3-env trace evidence, and residual risks.

## 验收标准

- code2env rollout exposes a trace mode such as --trace-mode subfunctions, with current default behavior unchanged.
- Required helper sequence is extracted from EnvSpec/ToolSpec provenance, preferring direct semantic helper tools call_<helper>, preserving entrypoint step/callee order where possible, and recording skipped/unavailable helpers with reasons.
- Trace-mode system prompt prohibits call_entrypoint first, requires helper tools in order, then call_entrypoint, then submit_answer with the entrypoint result.
- Rollout result includes machine-verifiable trace metadata: required_helper_tools, observed_tools, helper_trace_complete, entrypoint_after_helpers, skipped_helpers or reasons, without breaking existing JSONL/rollout-export compatibility.
- Focused unit tests cover helper sequence extraction, prompt construction, trace metadata, mock helper->entrypoint->submit rollout behavior, and default-mode compatibility.
- python3 -m pytest -q passes.
- Run trace mode on at least 3 envs from the Session 7 debug repo or an equivalent fixture, report exact commands/results, and explain if endpoint is not used.

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_2
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
