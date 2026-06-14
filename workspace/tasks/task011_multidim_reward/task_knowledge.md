# task011_multidim_reward - Task Knowledge

<!-- METADATA:SESSION=0 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_2`。
2. 五维 reward 全部落在 runtime.py：raw 信号在 step 累积到 `self._reward_state`，`_compute_breakdown()` 统一加权；weights 读 `spec.reward['weights']`，缺省回退 `DEFAULT_REWARD_WEIGHTS`（= spec.py 现值，和为 1.0）。
3. 训练 reward = step 返回的 potential-based shaping（Σ step reward = 末态 total − 初态 total）；evaluation score = `evaluate()` 的加权 total + 完整 `score_breakdown`（每维 raw/weight/weighted/detail）。
4. safety 违例靠匹配 executor 错误签名（"network access is disabled"/"subprocess execution is disabled"/error_type=TimeoutExpired）判定，一次违例即 safety_raw=0。
5. 默认分支是 `main`（playbook 写的是 master，已按 main 操作）；PR #8 -> base main。
