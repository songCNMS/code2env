# task034_rerun_rollouts_v2 - Task Knowledge

<!-- METADATA:SESSION=4 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_5`（v2 重跑 runner）。
2. 本轮是 Session2(task024) 放量后的修复重跑：上轮 correct=3% 全是假阳性（flask golden 本身=ModuleNotFoundError，未装依赖；agent 自造 call_entrypoint 参数与 fixture 不符）。
3. 依赖三 PR merged 后启动：task030(w1 装依赖+golden 重算+golden_status)、task031(w2 rollout prompt 修正)、task033(w4 报告真实率)。

## 复用 Session2(task024) 资产

- ⚠️ **上轮 outputs/phase3 已被 task024 merge 收尾的 playbook step8 清理删除**（manifest/packages/orchestrator）。**可恢复**：`.code2env_cache/repos`（克隆源）完好 → `batch` 确定性可复现同一 100 env 集；coordinator 旧 report.json/rollouts 在另一路径未删（作"装依赖前"基线）。**task034 Step1 须先重新 batch 复现 env 集**。
- 上轮 manifest（已删，需重生）原路径：`outputs/phase3/envs/manifest.json`（build_ok=100）。orchestrator run_rollouts.py 也已删，将重写 v2 版。
- **旧 rollouts（勿覆盖/勿删）**：`/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts/`（100 json + rollouts.jsonl）。
- 上轮 orchestrator：`outputs/phase3/run_rollouts.py`（gpt-5.5 主 + gpt-oss-120b 回退，ThreadPool）。本轮改造复用：输出改 rollouts_v2、仅跑非 weak_oracle 子集。
- 踩坑沿用：batch repo 须传 Git URL；自写脚本须 `PYTHONPATH=<repo> python3`。
- endpoint：`--endpoint-file /home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt --llm-model gpt-5.5 --fallback-model gpt-oss-120b`。

## 共享契约（字段勿改名）

- golden_status（w1 产，w4 报告/我消费）：`manifest.envs[].golden_status ∈ {real_value, weak_oracle:<reason>}`；可能另有 `deps_installed`/`deps_status`。weak_oracle 从正确率分母剔除。
- conversation 契约不变（task024 已验证）；report 新增真实 correct 率 + 装依赖前后对比。

---

## 重跑计划（v2）

> 三 PR merged + lead ping 后启动；先 `git checkout main && git pull`，跑全量 `pytest tests/` 确认绿（含 w1/w2/w4 新单测）。
> 命令用 `python3`；只读复用旧产物，新产物全部写 *_v2 / 并存目录，**不覆盖** Session2 的 rollouts/。

### Step 0 — 启动核对（确认 w1 实际接口）

- 读 w1 task030 落地：确认装依赖+golden 重算的**调用方式**（最可能其一）：
  a) `code2env batch` 新增 deps 开关 → 重新 batch 5 repo（风险：候选/ env_id 可能与上轮不同）；或
  b) 新命令/`materialize` 对**已有 100 specs** 逐个装依赖重算 golden + 写 golden_status（首选，env 集合稳定、可装前后对比）；或
  c) envdeps.py 暴露 per-repo venv，建好后重跑 build/materialize。
- 以 w1 README/CLI/单测为准，优先 b)（env 集合稳定，便于装依赖前后对比）。确认 manifest 写出 `golden_status`。

### Step 1 — 装依赖 + 重算 golden（w1 机制）

- 对上轮 100 env（或同 5 repo）装运行依赖到隔离 venv（.code2env_cache/venvs，已 gitignore）重算 golden。
- 产物：v2 manifest（含每 env `golden_status`、`deps_installed`/`deps_status`），写 `outputs/phase3_v2/envs/manifest.json`（不覆盖旧 manifest）。
- 装不动的库 → 跳过记 reason，不卡死整轮。
- 标出 **weak_oracle 集**（装后 golden 仍异常）；可用集合 = golden_status==real_value。

### Step 2 — 可用子集 rollout（gpt-5.5 + 修正 prompt）

- 仅对 `golden_status==real_value` 的 env 跑（剔 weak_oracle）。
- 用 w2 修正后的 rollout.py（agent 不自造 call_entrypoint 参数 → 用环境 fixture）；runtime call_entrypoint 走 w1 的 venv python（真实执行）。
- orchestrator 改造：输出 = `/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts_v2/`（自动 mkdir，**不碰旧 rollouts/**）。
- 主 gpt-5.5、回退 gpt-oss-120b；分批+控并发（workers≈4）+超时；per-env 隔离失败记 reason。

### Step 3 — 更新报告（w4 真实率工具）

- `code2env report <v2 manifest> --rollouts <rollouts_v2/> --output-dir <outputs/report/>`。
- 须含：**真实 correct 率 = correct/(非 weak_oracle 的 rollout 数)**、weak_oracle 单列计数、**装依赖前后对比**（golden error→real_value 数、各 repo smoke_ok 前后变化，尤其 flask 0→?）、保留生成成功率/by_repo/合格率/平均score/失败聚类。

### Step 4 — 回报（mailbox → lead）

最终数字：真实正确率、weak_oracle 数、rollouts_v2 路径、报告路径、装依赖前后对比（golden 修复数 / flask 等 smoke_ok 变化）。

### 验证要点（runner 自检）

- rollouts_v2/ 与旧 rollouts/ 并存，旧 100 json + jsonl 未被改动（跑前后 ls 计数对比）。
- v2 conversation 全过 D3 validate_conversation。
- 真实 correct 率分母 = 非 weak_oracle env 数（核对报告分母与 weak_oracle 计数自洽）。
- 抽 1-2 个上轮 flask 假阳性 env，确认装依赖后 golden 由 error→real_value（根因A 修复证据）。
- 抽 requests.cookies.create_cookie 类例，确认修正 prompt 后 agent 不自造参数（根因B 修复证据）。

## Session 3 — 关键踩坑与绕过

- **venv 阻塞**：本节点 `python3 -m venv` 失败（ensurepip 不可用，缺 python3.12-venv，无 passwordless sudo）→ envdeps `_create_venv` 抛错 → deps_status=venv_failed → golden 不修复。
- **uv 绕过**：本机 `uv 0.11.21`；`uv venv --seed <dir>` 建带 pip 的 venv，`venv_python -m pip install <req>` 正常。wrapper `outputs/phase3_v2/batch_uv.py` monkeypatch `envdeps._create_venv`→uv（不改合入代码）。建议 lead/w1 把 uv 兜底折进 envdeps（python -m venv 失败时 try `uv venv --seed`）。
- baseline（装依赖前）golden_status：real_value=67 / weak_oracle=33（ModuleNotFoundError=24/InvalidExecutorOutput=4/ValueError=2/AssertionError=2/OSError=1）。路径 outputs/phase3_v2/baseline/manifest.json。
- v2（装依赖后，uv）manifest：outputs/phase3_v2/envs/manifest.json；orchestrator outputs/phase3_v2/run_rollouts_v2.py（仅跑 golden_status==real_value 子集，导出 outputs/rollouts_v2/）。
- 路径全部在仓外 `../outputs`（不是 repo 内 code2env/outputs，注意别写错）；rollouts_v2 与旧 rollouts 并存不覆盖。

## Step2/3 结果 + 第三根因（C）

- Step2 rollout：75 real_value env，75/75 跑通、qualified 100%、exact correct=0、mean_score 0.35、全 gpt-5.5。导出 coordinator outputs/rollouts_v2/。
- Step3 报告：coordinator outputs/report_v2/report.{md,json}；真实 correct=0/75；装依赖前后 golden error→real_value=9、flask smoke 0→8。
- **根因 C（submit-envelope 不符）**：golden=executor 整包 `{ok:true,value:{kind,val}}`，agent 多提交内层 value → exact_match 假阴性。58/75=77% 是"解对 value 仅 envelope 错"，17 真错（含非确定性 repr）。真实解题质量≈77%，被 exact-match 整包比对掩盖。
- 待 lead 决策修法：prompt 指示提交 call_entrypoint 整包 / oracle 比对 value / submit 自动 wrap。属新一轮 fix（非本 task 范围）。
