# intern_code2env_worker_1 - 个人知识库

<!-- METADATA:SESSION=5 -->

---

## 知识条目

1. 技术事实：code2env 工具链 = indexer(AST 抽 FunctionCandidate) → spec.draft_env_spec(生成 EnvSpec+ToolSpec) → builder.build_env_package → runtime.Code2Env(reset/step/evaluate)；executor 在隔离 subprocess 跑目标符号并 serialize 结果。
2. 技术事实：dataclass 加字段务必带 default，EnvSpec/ToolSpec.from_dict 用 `**dict` 构造，无 default 会让旧 spec JSON 反序列化失败。
3. 调研结论(PRD 7.5)：每 env 工具粒度 3-8；必须 ≥1 个只读 state/校验 tool；有副作用原函数不直接暴露需走 sandbox adapter；工具来源=主函数关键步骤 + direct callee + state inspector + safe adapter。
4. 文件修改(task010)：runtime 想 dispatch 动态生成的语义 tool，可在 ToolSpec.provenance 里写 backing.symbol，runtime __init__ 据此建 name→symbol 映射，避免硬编码 tool 名。
5. 流程：本仓库默认分支是 `main`(非 playbook 写的 master)；GitHub repo 用 `gh pr merge <n> --squash`(playbook 的 codeup_pr 是 codeup 仓库专用)。
6. 流程：daemon HTTP API 端口是 ephemeral，记录在 /tmp/feishu_daemon.json 的 http_port；mailbox 汇报 POST http://127.0.0.1:<http_port>/api/intern/mail/to。
7. 技术事实(task045)：batch 侧需要筛选最终 dedicated semantic helper tools 时应复用 `spec.semantic_helpers_for_candidate`，避免与 `ToolSpec` 里的 `call_<helper>`、side-effect helper partition、`MAX_SEMANTIC_HELPER_TOOLS` 上限语义漂移。
8. 技术事实(task046)：rich fixture hydration 只能对显式 `__code2env_rich_fixture__` 描述符生效；source_root Path 描述符必须拒绝 absolute path 和 resolved outside-root path，且在任何 `mkdir` 前校验。
9. 技术事实(task046)：default batch 不应 generic synthesize `Path` required params；否则 Path writer 函数可能在 golden/smoke 阶段写入 source tree，安全做法是默认 unsupported skip，除非 symbol-specific safe policy 显式处理。
10. 技术事实(task047)：strict usable batch gating should be opt-in (`--require-real-value`) so default build/target behavior stays compatible while strict mode counts only deterministic `real_value` envs and audits weak-oracle rejections.
11. 技术事实(task047)：`helper_trace_complete` only proves helper coverage/order; rollout trace quality also needs per-helper success metadata plus `helper_calls_successful`/`helper_trace_valid` to expose failed helper calls such as `argument_unavailable` TypeErrors.
12. 流程(task049)：artifact-only任务若在ready后追加metadata commit，必须用最终PR head刷新summary/JSONL证据，并避免在history_log里复用已有Session编号。
