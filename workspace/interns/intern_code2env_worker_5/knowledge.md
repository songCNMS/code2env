# intern_code2env_worker_5 - 个人知识库

<!-- METADATA:SESSION=4 -->

---

## 知识条目

### code2env 仓库 / 流程
- 默认分支是 `main`（playbook 文案写的是 `master`，按占位符理解，分支/PR 用 `main`）。本仓托管在 GitHub（`gh pr ...`），非 codeup。
- intern mail API 在 `http://127.0.0.1:40737`：`POST /api/intern/mail/to`（汇报 lead）、`POST /api/intern/mailbox/list`（收件）。daemon pid 在 `ps aux | grep feishu_daemon`，端口看 `ss -ltnp`。
- checkout 别人 PR 分支会把 tracked 的 `workspace/` 文档切到那分支的状态；自己文档更新只在自己分支生效，测完切回即恢复。QA 测试别人分支时保持工作树 clean（只读、不改其代码）。

### code2env MVP 全链路（QA 回归基线）
- 链路：`scan → select --llm-mode mock → draft / draft-from-jsonl → materialize → build → smoke`，外加 `pytest tests/`。select 用 `--llm-mode mock` 离线确定。
- 确定性 fixture：sample.py 的 `normalize_name("  ada  lovelace ", shout=True)` → golden `{"ok":true,"value":{"kind":"json","value":"ADA LOVELACE"}}`，smoke `ok=true`/`score=1.0`。
- 多维 reward（runtime.py `_compute_breakdown`）：五维 schema_validity/process_progress/final_correctness/efficiency/safety，各含 raw/weight/weighted/detail，total=clamp(Σweighted)∈[0,1]。step 返回 PBRS 增量(Δtotal)做训练 shaping，evaluate 返回绝对加权 total 做 eval score（二者分离）。
- 语义工具能力：draft 产物 tools 含 `inspect_state` + `call_<helper>`(如 call_clean_text)，每个 ToolSpec 带 provenance；`provenance.task_sources>=2`(source_span+signature)。

### QA 方法论（本任务有效）
- 不只看单测数：另构造对照轨迹独立核对每个维度（超步/重复→efficiency=0、网络违例→safety=0、未知 tool→schema=0、正确轨迹→五维全非零 total=1）。
- 发现 spec.reward.weights 缺省(0.05/0.20/0.65/0.05/0.05) 偏离 PRD 7.7 表(0.05/0.25/0.50/0.10/0.10)：机制正确仅默认值偏，作为非阻塞 discrepancy 回报 lead 由其决策（已记 backlog 本轮不改），不擅自改别人代码。

### Session2 集成放量 runner（task024）经验
- code2env Phase3 链路：`batch <Git URLs> --target N`（须传 https:// URL，裸名当本地路径报错；clone→.code2env_cache gitignored）→ rollout（CLI `--llm-mode mock|endpoint --llm-model gpt-5.5 --fallback-model gpt-oss-120b --endpoint-file <endpoints.txt>`）→ `rollout-export <jsonl> --export-dir <dir>` → `report <manifest> --rollouts <dir> --output-dir <dir>`。
- endpoints：gpt-5.5 外网(xyzlapi，限速)，本地回退 gpt-oss-120b@127.0.0.1:39000；resolve_endpoint_config 按 model 名匹配行。
- 自写 orchestrator 放量：ThreadPool 控并发（workers≈4）、per-env try/except 隔离、run_rollout+write_conversation 导出；脚本须 `PYTHONPATH=<repo> python3 script.py`（脚本自身目录上 sys.path，cwd 不上）。
- 跨模块验证：把上游真实产物（如 D1 batch 的 skip reason 串）喂下游（D4 report classify_reason），能抓到单测漏掉的契约/词表不匹配——QA 不只跑别人单测，要用真实数据端到端对一遍。
- 假阳性教训：exact-match correct 率要警惕 golden 本身被污染（env 没装依赖→golden=ModuleNotFoundError，agent 同错即 match）；以及 prompt 让 agent 自造 fixture 参数→与 golden 不符。correct/score 低未必是 driver 问题，要查 golden 真实性。
