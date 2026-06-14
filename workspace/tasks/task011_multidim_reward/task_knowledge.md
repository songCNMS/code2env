# task011_multidim_reward - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_2`。
2. 五维 reward 全部落在 runtime.py：raw 信号在 step 累积到 `self._reward_state`，`_compute_breakdown()` 统一加权；weights 读 `spec.reward['weights']`，缺省回退 `DEFAULT_REWARD_WEIGHTS`（= spec.py 现值，和为 1.0）。
3. 训练 reward = step 返回的 potential-based shaping（Σ step reward = 末态 total − 初态 total）；evaluation score = `evaluate()` 的加权 total + 完整 `score_breakdown`（每维 raw/weight/weighted/detail）。
4. safety 违例靠匹配 executor 错误签名（"network access is disabled"/"subprocess execution is disabled"/error_type=TimeoutExpired）判定，一次违例即 safety_raw=0。
5. 默认分支是 `main`（playbook 写的是 master，已按 main 操作）；PR #8 -> base main。
6. 合并依赖：PR#9(ToolExtractor) 先合入 main（改 runtime.py 与本 PR 重叠），lead ping 后再 `git fetch origin && git merge origin/main` 解决冲突——runtime.py 需同时保留本 PR 五维 reward 与 PR#9 新增的 inspect_state/call_<helper> dispatch；README/docs/mvp_usage 也可能冲突。
7. [BACKLOG/doc-alignment] reward 权重默认值 0.05/0.20/0.65/0.05/0.05(忠实 spec.py 声明) 与 PRD 7.7 示例表(0.05/0.25/0.50/0.10/0.10)不一致；lead 裁定本轮保持现状，仅落地计算机制，取值对齐留 backlog 文档处理。
