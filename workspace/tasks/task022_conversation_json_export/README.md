# task022_conversation_json_export - D3 conversation JSON 导出 (per-env + 合并 JSONL)

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_3 -->

## 背景

Session2 目标:把 D2 rollout driver(task021,worker_2)产出的 RolloutResult 落盘成 conversation JSON 供用户查看与 D4 报告(worker_4)消费。RolloutResult 契约由 lead 统一定义(见 details),你与 w2 共享同一 schema;你负责持久化层(落盘/命名/合并/校验/加载),不重跑 rollout。输出目录:/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts/(绝对路径,在仓库外,不进 git;需自动 mkdir)。

## 任务目标

新增 code2env/rollout_export.py:把单条 RolloutResult 写成 per-env conversation JSON(<env_id>.json),并追加到合并 rollouts.jsonl;含完整 messages(system/user/assistant/tool)、每步 action+tool_result+reward、final score_breakdown 与 correct、qualified。提供 schema 校验(validate_conversation)与 loader(load_conversation/iter_jsonl)。导出函数可被 w2 的 rollout CLI 调用(提供 --export-dir 钩子)或独立 batch 导出工具。

## 实现说明

[conversation 契约-与 w2(产出)/w4(消费)共享,字段勿改名] {env_id,model,endpoint_source,started_at,finished_at,messages:[{role,content,name?,tool_call?:{tool,arguments}}],steps:[{step,action:{type,tool,arguments},tool_result,reward,parse_error}],final:{submitted_answer,correct,score,score_breakdown,steps},num_tool_call_rounds,qualified,termination_reason,retries,errors}. 合格判定 qualified=num_tool_call_rounds>=2 且 messages/steps 中出现 submit_answer。与 w2 的 RolloutResult 同 schema(w2 产 dict,你落盘)。如对 schema 有歧义先 mailbox 问 lead,勿擅自改字段名。cli.py 若需加 rollout-export 子命令仅加 subparser+一行。完成 mailbox 回报 lead PR#+自测,等 tester(w5)+lead review。

## 验收标准

- write_conversation(result,out_dir)->path:写 <env_id>.json(原子,缩进可读),并 append 到 out_dir/rollouts.jsonl(每行一条);out_dir 默认 coordinator outputs/rollouts/ 且自动 mkdir
- conversation JSON 严格符合契约 schema(见 details);validate_conversation(obj)对缺字段/类型错/qualified 不自洽(<2轮却 qualified)报错
- 提供 loader:load_conversation(path)/iter_jsonl(path);往返(write→load)等价
- 补单测(用合成 RolloutResult 样例验证写/合并/校验/往返/坏数据报错),不依赖网络与真实 rollout;现有 pytest tests/ 全绿;更新 README.md/docs/mvp_usage.md

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_3
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
