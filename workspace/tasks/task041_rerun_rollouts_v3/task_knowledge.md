# task041_rerun_rollouts_v3 - Task Knowledge

<!-- METADATA:SESSION=4 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_5`（v3 重跑 runner）。
2. 本轮源于 v2(task034) 诊断：v2 exact correct=0 是假阴性，根因 = 信封不符(58/75=77% 解对 value 仅丢 {ok} 外壳) + 非确定性(repr 含内存地址)。
3. 依赖三 PR merged 后启动：task037(w2 runtime 信封归一)/task038(w1 确定性门禁)/task039(w4 report_v3 类别)。另 task035(w1 envdeps uv 兜底,PR#22) merged 后可去掉我的 uv wrapper。

## 共享契约（字段勿改名）

- golden_status（w1）：`manifest.envs[].golden_status ∈ {real_value, weak_oracle:<reason>}`。
- determinism（w1 task038）：`manifest.envs[].determinism ∈ {deterministic, nondeterministic:<reason>}`；reason 形如 unstable_across_runs/memory_addr/abs_path/object_repr/hash/timestamp。
- **确定性可用集 = golden_status==real_value AND determinism==deterministic**（剔 weak_oracle 与 nondeterministic，二者均不计正确率分母、单列）。
- runtime 信封归一（w2 task037）：evaluate/submit_answer 比较前对 submitted 与 golden 都 `_normalize_answer_envelope`（剥 {ok,value}/{kind:json,value}），→ agent 提交里层 value 或完整信封都判对（确定性纯函数）。
- report_v3 类别（w4 task039）：deterministic_usable / envelope_flipped_to_correct(v2 incorrect→v3 correct) / nondeterministic_excluded / still_wrong；真实 correct 率分母=确定性可用集；v1→v2→v3 对比段（report 支持 --prev-rollouts 或 baseline/多 run 输入）。

## 复用资产（v1/v2，勿覆盖）

- v2 manifest(deps+golden_status)：outputs/phase3_v2/envs/manifest.json；baseline：outputs/phase3_v2/baseline/manifest.json。
- v1 rollouts(100)：coordinator outputs/rollouts/；v2 rollouts(75)：coordinator outputs/rollouts_v2/（**v3 写 rollouts_v3/，勿覆盖**）。
- v2 report：coordinator outputs/report_v2/；v3 写 report_v3/。
- orchestrator：outputs/phase3_v2/run_rollouts_v2.py（v3 改造：过滤 real_value AND deterministic，输出 rollouts_v3）。
- uv wrapper：outputs/phase3_v2/batch_uv.py（若 task035 已 merged 且本机 venv 仍缺 → 仍用；若 envdeps 已带 uv 兜底则可直接 batch）。
- endpoint：`--endpoint-file /home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt --llm-model gpt-5.5 --fallback-model gpt-oss-120b`。

---

## v3 重跑计划

> 三 PR merged + lead ping 后启动；先 `git checkout main && git pull`，`pytest tests/` 全绿。
> 路径用仓外 `../outputs`（不是 code2env/outputs）；rollouts_v3/report_v3 并存不覆盖 v1/v2。

### Step0 — 启动核对
- 确认 task037/038/039 接口：batch 是否写 `determinism` 字段（task038 落点 batch/spec 或新 determinism.py）；report 类别 + `--prev-rollouts`/对比参数名；runtime 信封归一是否生效（跑 scripted_smoke + 一个 v2 信封假阴性例确认 v3 判对）。
- 确认 task035(uv 兜底)是否 merged：若 envdeps 已带 uv fallback → 直接 `code2env batch`（去 wrapper）；否则继续用 batch_uv.py。

### Step1 — v3 manifest（deps + golden_status + determinism）
- 重新 batch（uv wrapper 或原生）确定性复现 100 env 集 → 写 v3 manifest（含 golden_status + determinism）到 outputs/phase3_v3/envs/manifest.json。
- 统计：**确定性可用集 = real_value AND deterministic** 的大小；weak_oracle 数、nondeterministic 数（单列）。
- 自检：v2 的非确定性例（generator repr 0x..）应被标 nondeterministic 剔除。

### Step2 — 确定性可用集 rollout（信封归一后应判对）
- 仅对确定性可用集用 gpt-5.5(本地 gpt-oss-120b 回退) 重跑；runtime 已信封归一 → 确定性纯函数 agent 提交里层 value 也判 correct。
- 导出 conversation 到 coordinator outputs/rollouts_v3/（自动 mkdir，**不覆盖 v1/v2**）。
- 预期：真实 correct 率应显著非零（v2 的 58 信封假阴性多数应翻正）。

### Step3 — report_v3
- `code2env report <v3 manifest> --rollouts rollouts_v3/ --baseline-manifest <baseline> [--prev-rollouts rollouts_v2/] --output-dir report_v3/`（参数名以 task039 实际为准）。
- 须含：真实非零 correct 率（分母=确定性可用集）、类别占比（deterministic_usable/envelope_flipped_to_correct/nondeterministic_excluded/still_wrong）、v1→v2→v3 对比。

### Step4 — 回报（mailbox → lead）
真实 correct 率、确定性可用集大小、各类别数（含 nondeterministic 剔除数、信封翻正数、仍错数）、rollouts_v3/ 与 report_v3/ 路径、v1→v2→v3 演进。

### 自检要点
- v1(100)/v2(75) 产物未被改动（前后 ls 计数）。
- v3 conversation 全过 D3 validate_conversation。
- 抽 1-2 个 v2 "right_value_wrong_envelope" 例，确认 v3 判 correct（信封归一证据）。
- 抽 1-2 个非确定性例，确认被 determinism 门禁剔除（不在 rollout 集）。
- 真实 correct 率分母 == 确定性可用集大小（与报告自洽）。
