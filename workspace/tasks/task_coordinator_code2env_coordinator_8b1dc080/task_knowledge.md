# task_coordinator_code2env_coordinator_8b1dc080 - Task Knowledge

<!-- METADATA:SESSION=1 -->

## Knowledge Entries

1. 本任务是 coordinator 生命周期任务，只要 coordinator 存在就不可完成。
2. `code2env` 的主链路是 `scan -> draft -> build -> smoke/rollout -> export/report`：从 Python 仓库 AST 候选函数生成 EnvSpec/EnvPackage，再用 sandbox runtime、golden answer、多维 reward 和 rollout/report 工具评测 agentic RL 环境。
