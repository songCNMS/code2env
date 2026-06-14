# task020_batch_generation_pipeline - Task Knowledge

<!-- METADATA:SESSION=2 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_1`。
2. 落点：新增 `code2env/batch.py`(主逻辑) + cli.py 加 batch subparser+1 行 dispatch+小 `_batch`；spec.draft_env_spec 加可选 `candidates` 参数(向后兼容)以复用单次 index_repo，避免批量 O(n²) 重复索引。
3. fixture 合成策略：无必填参→empty_signature{args:[],kwargs:{}}；必填参全有受支持注解→typed_signature(str→"x"/int→1/float→1.0/bool→False/容器→[]或{}/Optional|Union|None→null/下标泛型取 base/字符串前向引用 re-parse)；否则跳过 reason=untyped_required_param/unsupported_param_type。
4. 跳过规则(skipped[])：qualname 含"."→not_module_level；risk requires_instance；risk possible_side_effect(除非 --include-side-effects)；无 fixture。summary.skipped_no_fixture=len(skipped)。
5. 坑：golden 计算的 executor 子进程只 sandbox network/subprocess，不拦文件写；对 possible_side_effect 函数(如 open) draft 会真的在 cwd 建文件——所以默认跳过副作用函数，单测改在 _disqualify 层断言而不执行该函数(避免污染 cwd 生成 `x` 文件)。
6. 产物默认目录 generated_envs/batch + clone 缓存 .code2env_cache/repos 均已 gitignore，勿提交外部源码/生成物。
7. manifest 契约字段固定(w4 报告/w5 放量输入)：generated_at/repos/summary{candidates_scanned,draft_ok,build_ok,smoke_ok,skipped_no_fixture,by_repo}/envs[{env_id,repo,symbol,file,line_start,line_end,fixture{ok,strategy,value{args,kwargs},reason},draft_ok,build_ok,smoke_ok,smoke_fail_reason,spec_path,package_path}]/skipped[{symbol,repo,reason}]。
8. build_ok 计 target(不强求 smoke)；smoke_fail_reason: golden_error:*/answer_mismatch/smoke_exception:*/draft_error:*/build_error:*。
9. 自测：pytest tests/ → 44 passed(含 test_batch.py 13 个)；CLI `python -m code2env batch <repo> --output-dir ...` 跑通输出 summary。本 PR 小规模合成 repo 闭环，放量 100 由 w5。
10. 基线提醒：本仓库默认分支 main；task010(我)+task011(w2 reward)+task012(w3 testlink)已合并，draft_env_spec 现也产 signature/test_link provenance、spec.py 的 _tools_from_candidate(candidate,candidates) 仍是我 task010 的语义工具。
