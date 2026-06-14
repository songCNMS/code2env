# task014_qa_reward_e2e - Task Knowledge

<!-- METADATA:SESSION=0 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_5`。
2. 本仓默认分支是 `main`（非 playbook 文案里的 `master`）；e2e 与 PR 基线都以 `origin/main` 为准。
3. 基线（task011 合入前，main HEAD）`python3 -m pytest tests/ -q` = **13 passed**（test_mvp.py + test_llm_selection.py），作为回归对照。
4. 基线 e2e 全链路已在临时 repo 验证可绿：`scan → select --llm-mode mock → draft-from-jsonl → materialize → build → smoke`，smoke `ok=true`、`evaluation.score=1.0`。
5. 基线 `score_breakdown` 仅有 `final_correctness` 与 `exact_match` 两字段（`runtime.py:_dispatch` submit_answer 分支）；task011 五维 reward 应替换/扩展此处与 `step()` 的累加逻辑。
6. PRD 7.7 五维默认权重：schema_validity 0.05 / process_progress 0.25 / final_correctness 0.50 / efficiency 0.10 / safety 0.10（合计 1.00）。

---

## 测试计划（task011 五维 reward + 全链路回归）

> 命令均已在基线 main 上 dry-run 验证语法正确；等 team_lead ping 给出 task011 分支名后实测。
> 执行目录：`/home/leisong/codes/work-agents/intern_code2env_worker_5/code2env`，统一用 `python3`（本机无 `python`）。

### A. task011 PR 验证（checkout 分支后）

环境准备：
```bash
git fetch origin
git checkout intern_code2env_worker_2/task011_multidim_reward   # 实际分支名以 team_lead ping 为准
git log --oneline -5
```

A1. 单测全绿（含回归对照）
```bash
python3 -m pytest tests/ -q
```
- PASS 判据：全部通过且数量 ≥ 基线 13；新增 reward 用例存在且通过。
- FAIL 处理：记录失败用例名 + 完整 traceback，复现命令照抄，不替 worker 改代码。

A2. 五维 reward 计算 / 加权 / score_breakdown 可解释性
- 跑 scripted_smoke 并检查 breakdown 结构：
```bash
python3 - <<'PY'
# 用 test_mvp 同款 sample repo 走 draft→build→smoke，dump score_breakdown
# （ping 后按实际 spec 路径或直接调用 Code2Env(...).scripted_smoke() 取 evaluation）
PY
```
- PASS 判据（逐项核对）：
  1. `score_breakdown` 含五个维度键：schema_validity / process_progress / final_correctness / efficiency / safety。
  2. 各维度子分 ∈ [0,1]；加权总分 = Σ(weight_i × dim_i)，与 PRD 7.7 权重一致（0.05/0.25/0.50/0.10/0.10）。
  3. 训练 reward 与 evaluation score 分离（PRD 7.7 要求“可解释评分明细，支持 reward 与 eval score 分离”）。
  4. 正确轨迹 final_correctness=1.0，总分接近 1.0；错误/越权轨迹相应维度下降、可解释。
- 边界用例核对（构造对照轨迹）：
  - schema_validity：未知 tool / 非法 arguments → schema 维度扣分。
  - efficiency：达 max_steps 或重复/无效调用 → efficiency 维度扣分。
  - safety：触发 network/subprocess 沙箱拦截（参考 test_mvp `test_runtime_blocks_network_socket`）→ safety 维度扣分。
  - process_progress：中间状态满足/不满足阶段不变量的差异体现在该维度。

A3. scripted_smoke 全绿
```bash
python3 -m code2env smoke <built_package_dir> --json
```
- PASS 判据：`ok=true`，`evaluation.correct=true`，新 reward 字段齐全无异常。

### B. 三项 P0 merge 后 · master(main) 全链路回归

> 任务点名三项 P0 全部 merge 后在 main 上跑。语料用 test_mvp 的 sample repo（离线、确定）或 PRD 7.8 浅克隆 repo 之一；select 一律 `--llm-mode mock` 离线。

```bash
git checkout main && git pull --ff-only origin main
TMP=$(mktemp -d); REPO=$TMP/repo; mkdir -p $REPO
# 写入 test_mvp 同款 sample.py（clean_text / normalize_name）
python3 -m code2env scan $REPO --top-k 3 --json
python3 -m code2env select $REPO --output $TMP/sel.jsonl --llm-mode mock --top-k 3
python3 -m code2env draft-from-jsonl $TMP/sel.jsonl --output-dir $TMP/drafts \
  --fixture-json '{"args":["  ada  lovelace "],"kwargs":{"shout":true}}'
DRAFT=$(ls $TMP/drafts/*.json | head -1)
python3 -m code2env materialize $DRAFT \
  --fixture-json '{"args":["  ada  lovelace "],"kwargs":{"shout":true}}' --output $TMP/mat.json
PKG=$(python3 -m code2env build $TMP/mat.json --output-dir $TMP/gen)
python3 -m code2env smoke $PKG --json
python3 -m pytest tests/ -q
```
- PASS 判据（逐步记录命令 + 产物状态）：
  - 每步退出码 0、产物存在（jsonl / draft json / mat json / package 目录）。
  - smoke `ok=true`，`evaluation.score=1.0`。
  - `pytest tests/` 全绿（≥ 基线 13，含 test_mvp 全部用例）。
- 回归判据：与基线（条目 3/4）对照，任何步骤变红或 smoke `ok=false` 即判回归，清晰描述复现，不改代码。

### C. 回报（mailbox → team_lead）

每轮（A 完成、B 完成）各发一封 mail to lead，内容含：
- 命令逐条 + 关键输出（PASS/FAIL）。
- 环境（分支名、commit、python3 版本）。
- 风险 / 复现步骤（如有 FAIL）。
- 不用 peer send 打断 team_lead。
