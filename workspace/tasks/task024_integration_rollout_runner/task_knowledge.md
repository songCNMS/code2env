# task024_integration_rollout_runner - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_5`（tester + 集成放量 runner）。
2. 默认分支 `main`（非 master）；GitHub 仓（`gh pr`）；intern mail API `http://127.0.0.1:40737`（POST /api/intern/mail/to）。
3. 四能力 PR：D1 task020 batch pipeline(w1) / D2 task021 rollout driver(w2) / D3 task022 conversation 导出(w3) / D4 task023 报告(w4)。

## 环境事实（已核验 2026-06-13）

- endpoints 文件：`/home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt`。
  - 行1 = gpt-5.5 外网，base_url `https://xyzlapi.boyuerichdata.com/v1/`（放量主模型，限速）。
  - 行2+ 本地 127.0.0.1 回退：gpt-oss-120b@39000；Kimi-K2.6/deepseek-v4-pro/xyz-30b/mirothinker-1.7-mini @18000。
  - `endpoints.vpn.txt` 不存在，勿依赖；llm.py 默认 `/work-agents/endpoints.txt` 不存在，**必须显式 `--endpoint-file`**。
- coordinator 输出根：`/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/`，`rollouts/` 子目录尚未创建（D3 write_conversation 自动 mkdir）。
- 本地 LLM 也可经 llm-endpoints skill 走 `http://127.0.0.1:18000`（格式验证阶段用，避 gpt-5.5 限速）。
- 语料：requests/flask/rich/click/jinja2（不够加 poetry），shallow clone 到 `.code2env_cache/`（已 gitignore，勿提交外部源码）。
- 当前 main：llm.py 仅有 evaluate_candidate/_post_payload/resolve_endpoint_config，**无 chat()**（D2 新增）；尚无 batch.py/rollout.py/rollout_export.py/report.py。

## 契约速查（字段勿改名，跨 w1-w4 共享）

- gen manifest（D1 产，D4/我消费）：`{generated_at, repos[], summary:{candidates_scanned,draft_ok,build_ok,smoke_ok,skipped_no_fixture,by_repo:{repo:{build_ok,smoke_ok}}}, envs:[{env_id,repo,symbol,file,line_start,line_end,fixture:{ok,strategy,value:{args,kwargs},reason},draft_ok,build_ok,smoke_ok,smoke_fail_reason,spec_path,package_path}], skipped:[{symbol,repo,reason}]}`。
- RolloutResult / conversation（D2 产，D3 落盘，D4/我消费）：`{env_id,model,endpoint_source(gpt-5.5|fallback:<model>|mock),started_at,finished_at,messages:[{role,content,name?,tool_call?:{tool,arguments}}],steps:[{step,action:{type,tool,arguments},tool_result,reward,parse_error}],final:{submitted_answer,correct,score,score_breakdown,steps},num_tool_call_rounds,qualified,termination_reason(submitted|step_budget_exhausted|error),retries,errors[]}`。
- **qualified** = num_tool_call_rounds>=2 且 messages/steps 出现 submit_answer。

---

## 测试计划

> 命令均用 `python3`（本机无 `python`）；执行目录 `/home/leisong/codes/work-agents/intern_code2env_worker_5/code2env`。
> 验证别人 PR 分支时**只读、不改其代码、保持工作树 clean**；测完切回自己分支。

### Phase1 — 各 PR 到达时独立验证（lead ping 分支名后逐个）

通用流程（每个 PR）：
```bash
git fetch origin && git checkout <pr_branch>
python3 -m pytest tests/ -q        # 全绿且 ≥ 之前基线
```
再按各 task 验收标准逐条核对（不只看单测数，构造对照样例）：

- **D1 task020 batch**（w1）：
  - `code2env batch` 子命令存在；小规模跑通产 EnvPackage + manifest.json。
  - manifest 严格符合契约：envs[] 含 env_id/repo/symbol/file/fixture{ok,strategy,value,reason}/draft_ok/build_ok/smoke_ok/smoke_fail_reason/spec_path/package_path；summary.by_repo + 各计数；skipped[]。
  - fixture 自动合成：str/int/list/dict/bool/全默认值候选能合成；无法合成的进 skipped 且有 reason。
  - 外部源码/产物不进 git；单测用临时/合成 repo 不依赖网络。
- **D2 task021 rollout driver**（w2）：
  - `OpenAICompatibleLLM.chat(messages,...)` 新增、mock 可注入。
  - mock 单测：确定性 MockChatLLM 给定 tool_call 序列 → loop 跑通、qualified 判定、malformed action 重试+parse_error、budget 停。
  - RolloutResult 严格符合契约（messages/steps(action+tool_result+reward)/final(score_breakdown)/num_tool_call_rounds/qualified/termination_reason/retries/errors）。
  - 多端点回退逻辑：gpt-5.5 失败/超时 → 本地端点，endpoint_source 记录实际来源（**回退路径我会用本地端点实测**，避免外网限速）。
- **D3 task022 conversation 导出**（w3）：
  - `write_conversation(result,out_dir)` 写 `<env_id>.json`（原子/可读）+ append `rollouts.jsonl`；默认 coordinator outputs/rollouts/ 自动 mkdir。
  - `validate_conversation` 对缺字段/类型错/qualified 不自洽（<2 轮却 qualified）报错。
  - loader 往返（write→load）等价；单测用合成 RolloutResult，不依赖网络。
- **D4 task023 报告**（w4）：
  - `code2env report` 输入 manifest + rollouts 目录/jsonl → 输出 report.md + report.json。
  - 指标齐全：生成成功率、by_repo 分布、rollout 合格率、平均 score、失败聚类计数。
  - 单测用合成 manifest + 合成 conversation 验证统计/聚类正确。

每个 PR 验证完 mailbox 回报 lead：命令 / 单测结果 / 逐条 PASS-FAIL / 环境 / 未覆盖风险。

### Phase3 — D1/D2/D3 merged 后：格式门 → 放量 → 导出 → 报告

> lead 确认 D1/D2/D3 merged 后启动；先 `git checkout main && git pull`。

**Step A 格式门（1-3 env，避 gpt-5.5 限速）**
```bash
# 1) 小批生成 1-3 env
python3 -m code2env batch --repos requests --target 3 --output-dir <gen_dir>   # 参数名以 D1 实际为准
# 2) 对其 rollout（mock 或本地端点）
python3 -m code2env rollout <env_pkg> --llm-mode mock \
  --export-dir /home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts/
#    或本地端点：--llm-mode endpoint --endpoint-file <endpoints.txt> --llm-model Kimi-K2.6
# 3) 校验 conversation JSON 契约
python3 -c "from code2env.rollout_export import load_conversation, validate_conversation; ..."
```
格式门判据：conversation JSON 符合契约 —— ≥2 轮 tool_call + 含 submit_answer + 每步 reward + final.score_breakdown；qualified 自洽。**先 mailbox 报"格式 OK"再放量。**

**Step B 放量（成功 build EnvPackage ≥100）**
```bash
python3 -m code2env batch --repos requests flask rich click jinja2 [poetry] \
  --target 100 --output-dir <gen_dir>   # build_ok≥100 by manifest
```
- 语料 shallow clone 到 `.code2env_cache/`；'100' 按 draft+build 计，smoke 失败记原因。

**Step C rollout 放量（gpt-5.5 主、本地回退）**
```bash
# 对 manifest 中 build_ok 的 env 批量 rollout，分批+控并发避限速，外网失败自动回退本地
python3 -m code2env rollout <env_pkg> --llm-mode endpoint \
  --endpoint-file /home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt \
  --llm-model gpt-5.5 --fallback-model <local> \
  --export-dir /home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts/
```
- 合格判定：每条 ≥2 轮 tool_call + submit_answer + 每步 reward + final evaluation/score_breakdown。

**Step D 汇总报告**
```bash
python3 -m code2env report --manifest <gen_dir>/manifest.json \
  --rollouts /home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts/ \
  --output-dir <outputs>   # 产 report.md + report.json
```

**最终交付物（必须我产出）**：
1. ≥100 EnvPackage 清单 = manifest.json（位置回报）。
2. coordinator `outputs/rollouts/` 下 conversation JSON + rollouts.jsonl。
3. 汇总报告 md+json：生成成功率 / 按 repo 分布 / rollout 合格率 / 平均 score / 失败聚类。
4. mailbox 回报最终数字：100env 清单位置、rollouts 路径、报告路径、合格率。

### 回报（mailbox → team_lead，不走 peer send）

- Phase1 每 PR 一封；Phase3 格式门一封（报 OK 再放量）、放量+报告完成一封（含最终数字）。
