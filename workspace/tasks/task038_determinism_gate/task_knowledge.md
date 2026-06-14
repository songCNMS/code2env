# task038_determinism_gate - Task Knowledge

<!-- METADATA:SESSION=3 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_1`。
2. 顺序约束：task035(uv 兜底)与 task038 都改 envdeps/spec，lead 要求先合 PR#22 再在更新 main 上做 task038(避免自冲突)；我把 task038 分支 merge 含 uv 兜底的新 main 后再实现。
3. determinism 契约(与 w4 报告/w5 共享, 勿改名)：manifest.envs[].determinism ∈ {deterministic, nondeterministic:<reason>}；reason ∈ object_repr/memory_addr/abs_path/unstable_across_runs；非 real_value env determinism=None。
4. 防过度剔除(lead review 重点)：强独立信号只用默认对象 repr `<… at 0x…>`(6+ hex)→object_repr 单次判；裸 0x hex / 绝对路径 是弱信号，仅当重复执行不一致时才细化为 memory_addr/abs_path，否则不判——合法稳定返回的路径/hex 必须保持 deterministic。
5. classify_determinism(golden, repeat_results)：先查强信号→再查重复不一致(weak_signature 细化 reason, 无则 unstable_across_runs)→否则 deterministic。is_usable=real_value AND deterministic。
6. spec.draft_env_spec determinism_runs 默认 1(单 draft 只做 pattern, 省 subprocess)；batch 默认 3(真正重复检测)；cli batch --determinism-runs。
7. 坑：_OBJECT_REPR 要求 0x 后 6+ hex(真实内存地址长)，单测别用 0x55a1 这类短 hex(不匹配)，用 0x7f8a1b2c3d4e。
8. 自测：pytest tests/ → 131 passed(新 test_determinism.py 17 + 既有)。
