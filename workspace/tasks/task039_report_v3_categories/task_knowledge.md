# task039_report_v3_categories - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_4`。
2. 契约(勿改名)：manifest.envs[].golden_status(real_value|weak_oracle:<reason>, w1 task030) + determinism(deterministic|nondeterministic:<reason>, w1 task038)；conversation.final.correct(信封归一后由 runtime 判)。
3. _env_bucket 互斥优先级：weak_oracle > nondeterministic > deterministic_usable(real_value+确定性) > golden_unknown。determinism 缺失→不剔(降级为可用)；golden 缺失→golden_unknown(不算 usable)。
4. 真实非零 correct 率分母=deterministic_usable(剔 weak+nondet)；保留 task033 true_correct(仅剔 weak)作原指标。categories 四类(deterministic_usable/envelope_flipped_to_correct/nondeterministic_excluded/still_wrong)+weak_oracle_excluded+golden_unknown。
5. envelope_flipped=deterministic_usable 且 current correct 且前一轮(--prev-rollouts 末个)incorrect(prev_correct_by_env[env]==False)。evolution=prev_runs+current 按位标 v1..vN，传 2 个 prev → v1/v2/v3。
6. 只动 report.py + cli.py(透传 --prev-rollouts/--baseline-manifest)，与 w1/w2 解耦。自测 pytest=112 / unittest=112；CLI 端到端验证类别/真实率/演进。
