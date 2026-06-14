# intern_code2env_worker_2 - 个人知识库

<!-- METADATA:SESSION=1 -->

---

## 知识条目

1. code2env 默认分支是 `main`（playbook 文案写的是 master，实际按 main 操作）；worker PR 走 `gh`（GitHub, github.com/songCNMS/code2env），不是 codeup。环境无 `python`，统一用 `python3`。
2. code2env reward 落在 `code2env/runtime.py`：step 累积五维 raw 信号到 `self._reward_state`，`_compute_breakdown()` 按 `spec.reward['weights']` 加权（缺省回退 `DEFAULT_REWARD_WEIGHTS`，和为 1.0）。训练 reward = step 返回的 potential-based shaping（Σ step reward = 末态 total − 初态 total）；evaluation score = `evaluate()` 的加权 total + `score_breakdown`（每维 raw/weight/weighted/detail，total∈[0,1]），两者刻意分离。
3. safety 维度靠匹配 executor 沙箱错误签名判定（"network access is disabled"/"subprocess execution is disabled"/error_type=TimeoutExpired），一次违例 safety_raw=0；efficiency 惩罚 error/重复调用/超步数未提交。
4. PR#9(ToolExtractor) 给 runtime 引入 `inspect_state`（只读）与 `call_<helper>` 语义工具（`self.semantic_tools`，由 ToolSpec provenance.kind==wrapper 解析）；与 reward 集成时把 inspect_state 计入 explored、semantic helper 计入 explored+executed_source，process_progress 才连贯。
5. 多 worker 同改 runtime.py：按 lead 指定顺序，先让重叠 PR 合入 main，再 `git fetch origin && git merge origin/main` 解决冲突（两边逻辑都保留），重跑 pytest 全绿后 self-merge。
6. [backlog] reward 权重默认 0.05/0.20/0.65/0.05/0.05（忠实 spec.py 声明）与 PRD 7.7 示例表（0.05/0.25/0.50/0.10/0.10）不一致，lead 裁定本轮保持现状，取值对齐留 backlog 文档。
7. [踩坑] LLM rollout：自定义 tool 描述不能当 OpenAI 原生 `tools` 字段发给网关(litellm 校验 `tools.0.function` → HTTP 400)。用 JSON-in-content 协议：tools 写进 system prompt，chat payload 不带 tools；模型回 `{"tool":...,"arguments":...}`，用 parse_llm_json 解析。
8. 多 worker 同改 cli.py：argparse 是“加 subparser + 一行 dispatch + 一个 handler 函数”的累加结构，冲突解决一律“全保留”（imports/subparser/dispatch/handler 四处都合并双方）。本会话合 D1(batch+rollout-export)×D2(rollout) 四处冲突均如此处理，72 passed。
9. endpoints.txt(/home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt)：行1 gpt-5.5 外网，本地 127.0.0.1:39000=gpt-oss-120b、:18000=Kimi-K2.6 等；端口可达性随环境变化，先 `curl :PORT/v1/models` 探活再 live 测。

