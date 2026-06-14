# task021_llm_rollout_driver - D2 LLM rollout driver (多轮 tool-calling agent loop)

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_2 -->

## 背景

Session2 目标:用 gpt-5.5 对生成的 env 做多轮 rollout 验证。复用 code2env/llm.py 的 OpenAICompatibleLLM——但它当前只有 evaluate_candidate,没有通用 chat,需新增。Code2Env(runtime.py) 已有 reset/step/evaluate,action 协议 {type:tool_call,tool,arguments},observation 含 task/state/available_tools/budget。Session1 已让 env 有 3-8 语义工具(inspect_task/inspect_state/call_entrypoint/call_<helper>/submit_answer),足以走≥2轮。本任务只做 rollout 验证 driver,不接 RL 训练。

## 任务目标

新增 code2env/rollout.py:多轮 tool-calling agent loop——把 env observation+available_tools(+各 tool input_schema)喂给 LLM,让模型以 tool_call(JSON action)形式产出 action,parse 后跑 Code2Env.step,循环直到 submit_answer 或耗尽 step budget;带重试/超时/格式纠错。新增 OpenAICompatibleLLM.chat(messages)->message。多端点回退:主用 gpt-5.5,外网失败/限速时自动回退本地端点。返回 RolloutResult(契约)。新增 code2env rollout CLI(单 env)。

## 实现说明

重要 endpoint 事实:endpoints.txt=/home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt(行1 gpt-5.5 外网;行2+ 本地127.0.0.1 Kimi-K2.6/xyz-30b 等可作回退);llm.py 默认 /work-agents/endpoints.txt 不存在,必须显式 --endpoint-file;endpoints.vpn.txt 不存在,回退就用同一 endpoints.txt 的本地行(可用 resolve_endpoint_config 按 model 名解析或自行读多端点)。rollout CLI 参数:env_package、--endpoint-file、--llm-model gpt-5.5、--max-rounds、--llm-mode endpoint|mock、--fallback-model 等。[RolloutResult/conversation 契约-与 w3/w4 共享,字段勿改名] {env_id,model,endpoint_source(gpt-5.5|fallback:<model>|mock),started_at,finished_at,messages:[{role:system|user|assistant|tool,content,name?,tool_call?:{tool,arguments}}],steps:[{step,action:{type:tool_call,tool,arguments},tool_result,reward,parse_error}],final:{submitted_answer,correct,score,score_breakdown,steps},num_tool_call_rounds,qualified(bool:>=2 轮 tool_call 且出现 submit_answer),termination_reason(submitted|step_budget_exhausted|error),retries,errors:[]}. 你产出此 dict,w3 负责落盘/合并JSONL/校验。cli.py 仅加 subparser+一行 dispatch 减少冲突。完成 mailbox 回报 lead PR#+自测,等 tester(w5)+lead review。

## 验收标准

- OpenAICompatibleLLM 新增 chat(messages,*,tools/timeout)->dict(返回 assistant message),复用 _post_payload/_extract_message_content;mock 可注入
- rollout loop:观测→LLM 出 tool_call(推荐 prompt 模型输出 JSON action {tool,arguments},用 parse_llm_json 解析,兼容原生 tool_calls)→step;malformed action 重试有限次并记 parse_error;到 submit_answer 或 budget 停
- 多端点回退:gpt-5.5(base_url=https://xyzlapi.boyuerichdata.com/v1/)失败/超时→回退 endpoints.txt 内本地 127.0.0.1 端点(Kimi-K2.6/xyz-30b 等);记录实际使用 endpoint_source
- 返回 RolloutResult 严格符合契约(见 details):messages/steps(action+tool_result+reward)/final(submitted_answer,correct,score,score_breakdown)/num_tool_call_rounds/qualified/termination_reason/retries/errors
- 补 mock 单测(确定性 MockChatLLM 给定 tool_call 序列→验证 loop/qualified/解析纠错/budget 停),不依赖网络;现有 pytest tests/ 全绿;更新 README.md/docs/mvp_usage.md

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_2
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
