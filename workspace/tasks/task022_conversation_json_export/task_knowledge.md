# task022_conversation_json_export - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_3`。
2. 分支 `intern_code2env_worker_3/task022_conversation_json_export`，PR #12 base=main。w2(task021) rollout driver 尚未合 main，故持久化层只吃契约 dict、与 w2 代码解耦。
3. 新增 `code2env/rollout_export.py`：`write_conversation(result,out_dir=None,validate=True)` 写 `<env_id>.json`(原子: tmp+os.replace) + append `rollouts.jsonl`(O_APPEND 防并发交错); out_dir 默认 `DEFAULT_EXPORT_DIR`(coordinator outputs/rollouts 绝对路径, 仓库外不进 git, 自动 mkdir, 可用 env `CODE2ENV_ROLLOUT_EXPORT_DIR` 覆盖)。
4. 契约 schema 字段勿改名（与 w2 产/w4 消费共享）。`validate_conversation` 校验顶层类型/messages(role∈system|user|assistant|tool)/steps/final，并强制 `qualified` 自洽：`qualified == (num_tool_call_rounds>=2 且 messages/steps 出现 submit_answer)`，不自洽报 `ConversationSchemaError`。bool 是 int 子类，需显式排除（int 字段拒 bool）。
5. loader：`load_conversation(path)`(默认校验) / `iter_jsonl(path)`(默认不校验, 容忍部分写入, 跳空行)；往返 write→load 等价（atomic 写用 indent=2,sort_keys；不改 messages/steps 列表顺序）。
6. CLI：`rollout-export <results.jsonl> --export-dir DIR [--no-validate]`，subparser+一行 dispatch+`_rollout_export`。env_id 文件名 sanitize（非 `[A-Za-z0-9_.-]`→`_`），但 JSON 内 env_id 原样保留。
7. 自测 tests/test_rollout_export.py 13 例(写/合并/校验/往返/坏数据不落盘/sanitize/原子无残留/跳空行)，合成样例不依赖网络与真实 rollout；全量 `python3 -m pytest tests/` 44 passed。
8. 复用 ERROR_BOOK E1 教训：自测用 pytest，公有名不以 test_ 开头（本模块函数均无 test_ 前缀）。
