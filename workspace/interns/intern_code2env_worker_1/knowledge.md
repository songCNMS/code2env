# intern_code2env_worker_1 - 个人知识库

<!-- METADATA:SESSION=1 -->

---

## 知识条目

1. 技术事实：code2env 工具链 = indexer(AST 抽 FunctionCandidate) → spec.draft_env_spec(生成 EnvSpec+ToolSpec) → builder.build_env_package → runtime.Code2Env(reset/step/evaluate)；executor 在隔离 subprocess 跑目标符号并 serialize 结果。
2. 技术事实：dataclass 加字段务必带 default，EnvSpec/ToolSpec.from_dict 用 `**dict` 构造，无 default 会让旧 spec JSON 反序列化失败。
3. 调研结论(PRD 7.5)：每 env 工具粒度 3-8；必须 ≥1 个只读 state/校验 tool；有副作用原函数不直接暴露需走 sandbox adapter；工具来源=主函数关键步骤 + direct callee + state inspector + safe adapter。
4. 文件修改(task010)：runtime 想 dispatch 动态生成的语义 tool，可在 ToolSpec.provenance 里写 backing.symbol，runtime __init__ 据此建 name→symbol 映射，避免硬编码 tool 名。
5. 流程：本仓库默认分支是 `main`(非 playbook 写的 master)；GitHub repo 用 `gh pr merge <n> --squash`(playbook 的 codeup_pr 是 codeup 仓库专用)。
6. 流程：daemon HTTP API 端口是 ephemeral，记录在 /tmp/feishu_daemon.json 的 http_port；mailbox 汇报 POST http://127.0.0.1:<http_port>/api/intern/mail/to。

