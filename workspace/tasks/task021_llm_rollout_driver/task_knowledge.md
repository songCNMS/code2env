# task021_llm_rollout_driver - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_2`。
2. [踩坑] 网关(litellm)会校验 OpenAI `tools` 字段格式：若把自定义 `[{name,description,input_schema}]` 当 tools 发送会 HTTP 400(`Field required at body.tools.0.function`)。本 driver 用 JSON-in-content 协议——tools 只写进 system prompt，chat payload 不带 `tools`。
3. endpoints.txt=/home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt：行1 gpt-5.5(外网 https://xyzlapi.boyuerichdata.com/v1/)，本地 127.0.0.1:39000=gpt-oss-120b、:18000=Kimi-K2.6/deepseek-v4-pro/xyz-30b 等。实测本会话 18000 未起(Connection refused)，39000 可达——回退/错误处理逻辑均经实网验证。
4. RolloutResult 契约字段勿改名（与 w3/w4 共享）：env_id/model/endpoint_source(gpt-5.5|fallback:<model>|mock)/started_at/finished_at/messages/steps(action+tool_result+reward+parse_error)/final(submitted_answer,correct,score,score_breakdown,steps)/num_tool_call_rounds/qualified(>=2轮 tool_call 且有 submit_answer)/termination_reason(submitted|step_budget_exhausted|error)/retries/errors。
5. `retries` = LLM 传输重试 + parse 纠错重试之和；CLI mock 用 `ScriptedSolveChat`（读 env.last_tool_result 自适应求解，2 轮即 qualified+correct，无网络）。
