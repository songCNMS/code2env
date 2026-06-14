# task033_report_true_correct_rate - Task Knowledge

<!-- METADATA:SESSION=3 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_4`。
2. 契约(勿改名)：manifest.envs[].golden_status ∈ {"real_value","weak_oracle:<reason>"}（w1/task030 产）。report 解析：==real_value→real_value；startswith("weak_oracle")→weak_oracle；其余/缺失→unknown(_golden_kind)。
3. 真实 correct 率=true_correct/usable_total，usable=非 weak_oracle 的 rollout（按 env_id 关联 manifest golden_status）；weak_oracle_excluded 单列不入分母；缺失 golden_status→unknown 但仍计入 usable(分母不缩水)。保留 raw correct/correct_rate 对照。
4. 前后对比需两份 manifest，契约只有当前 golden_status 无 before 字段→用可选 `--baseline-manifest`；error→real_value=baseline 非 real_value 且 current real_value（按 env_id）；smoke_ok by repo before/after delta；无 baseline 降级为当前 golden 分布+note（安全降级）。
5. 自测：`pytest tests/`=91 passed（86+5），`unittest`=91 OK；CLI 端到端含 baseline 验证 flask smoke 0→2、error→real_value=2。
