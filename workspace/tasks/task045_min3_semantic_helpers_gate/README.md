# task045_min3_semantic_helpers_gate - Add minimum semantic helper gate for batch env generation

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

Session 13 requires qlib pipeline env generation to include only functions that can expose at least three dedicated semantic subfunction tools. Coordinator pre-scan on pinned qlib found 2,860 candidates, 8 with >=3 pure semantic helpers, and 6 that also satisfy current base batch filters. Full handoff: /home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/session13_min3_semantic_helpers_goal.md.

## 任务目标

Implement a configurable batch/env-generation gate so code2env batch can require at least N dedicated safe call_<helper> semantic tools, defaulting to 0 for backward compatibility; validate with N=3 on pinned qlib.

## 实现说明

Implementation worker: intern_code2env_worker_1. Independent code/test validator: intern_code2env_worker_4. Independent qlib constrained batch validator/runner: intern_code2env_worker_2. Save qlib run artifacts under /home/leisong/codes/work-agents/intern_code2env_lead/outputs/session13_min3_semantic_helpers/ (worker-local mirrors are okay but lead output path is required). Use target 20 first if qlib yields fewer eligible builds; do not silently broaden beyond --min-semantic-helpers 3. Final worker report must include PR id, tests, qlib run command/results, default compatibility, and residual risks.

## 验收标准

- code2env batch exposes an option such as --min-semantic-helpers N, default 0, wired into generate_batch API without changing default behavior.
- The gate counts only dedicated safe semantic helper tools that final ToolSpec generation would expose as call_<helper>; it excludes call_entrypoint, inspect_task, inspect_state, submit_answer, generic call_helper, and side-effect helpers recorded as sandboxed_side_effect_helpers.
- The gate reuses or exactly matches spec.py helper partition/final call_<helper> generation semantics, including MAX_SEMANTIC_HELPER_TOOLS=3; N > MAX_SEMANTIC_HELPER_TOOLS fails clearly or is rejected by CLI/API.
- Gate runs before fixture synthesis/draft/build work, skipped candidates get a reason like insufficient_semantic_helpers:<actual>/<required>, and manifest/env records include semantic_helper_count and semantic_helpers where practical for auditability.
- Focused tests cover candidate with 3 safe direct helpers accepted, candidate with 2 safe helpers skipped, candidate with 3 raw helpers but one side-effect helper skipped for N=3, default behavior unchanged when option omitted, CLI argument wired into generate_batch, and invalid N > max rejected.
- python3 -m pytest -q passes.
- Run pinned qlib constrained batch using /home/leisong/codes/work-agents/intern_code2env_coordinator/debug/qlib_cache/d7cf7c8de0969b81 with SETUPTOOLS_SCM_PRETEND_VERSION=1.0.0 and --min-semantic-helpers 3, target 20 or 60 as feasible; report candidates passing gate, build_ok, real_value, usable, rollout-eligible/trace rollout counts, skipped reasons, and artifact paths.

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_1
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
