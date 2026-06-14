# task045_min3_semantic_helpers_gate - Task Knowledge

<!-- METADATA:SESSION=3 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_1`。
2. PR opened at https://github.com/songCNMS/code2env/pull/31 from branch `intern_code2env_worker_1/task045_min3_semantic_helpers_gate` to `main`.
3. The semantic gate uses `spec.semantic_helpers_for_candidate`, which matches final `call_<helper>` ToolSpec semantics by partitioning side-effect helpers out and applying `MAX_SEMANTIC_HELPER_TOOLS`.
4. Pinned qlib target-20 initial run with `--min-semantic-helpers 3 --no-install-deps` found 6 gate-passing candidates but 0 generated envs because those 6 require unsupported/untyped fixture inputs (`DataFrame`, untyped `positions`/`all_preds`, or `qlib_dir:None`).
5. qlib artifacts: manifest `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session13_min3_semantic_helpers/w1_initial_batch_target20_no_deps/manifest.json`; summary `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session13_min3_semantic_helpers/w1_initial_batch_summary.md`.
6. Merge approval received from `intern_code2env_lead` after lead review plus worker_4 and worker_2 independent PASS validation.
