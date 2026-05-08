# Code2Env Agentic RL 环境生成 PRD

状态：Draft PRD  
负责人：intern_code2env_dev  
任务：task001_code2env_agentic_rl_prd  
日期：2026-05-08

## 1. 背景

code2env 的核心目标是把现有代码库里的真实业务逻辑转化为可训练、可评测的 agentic RL 环境。一个理想环境不只是“运行某个函数”，而是把复杂函数或模块流程转化为：

- 一个从代码语义总结出的任务描述。
- 一组 agent 可以调用的 tools，每个 tool 对应主函数的关键步骤、子函数、外部依赖适配器或状态检查器。
- 一个可复现的 runtime，支持 `reset`、`step`、轨迹记录和隔离执行。
- 一个评分机制，根据运行结果、状态变化、测试 oracle 和工具调用行为给出 reward。

本 PRD 定义从 Python 代码库到 agentic RL env 的完整产品方案、模块拆分和实施路径。

## 2. 目标与非目标

### 2.1 目标

- 从 GitHub 或本地 Python 仓库中抽取复杂函数、类方法或模块级工作流，生成可审阅的 `EnvSpec`。
- 自动生成任务描述、工具 schema、环境 runtime wrapper、测试 oracle 和 reward 规则。
- 让生成环境可以接入 agentic RL 训练，至少支持单环境交互、批量 rollout、轨迹导出和离线评测。
- 建立基于高星 Python repo 的初始语料池，优先覆盖 HTTP、Web 框架、爬虫、终端渲染、CLI 等典型复杂代码。

### 2.2 非目标

- MVP 不支持 Python 以外语言。
- MVP 不承诺完全自动生成高质量 reward；需要保留人工 review 和标注入口。
- MVP 不允许生成环境在训练时访问任意外网或执行不受控系统命令。
- MVP 不解决通用代码修复任务，第一阶段聚焦“通过工具完成任务”，不是让 agent 任意修改源码。

## 3. 目标用户与核心场景

### 3.1 用户

- Env Builder：从代码库生成、审阅、发布训练环境的人。
- RL Researcher：把生成环境接入 agentic RL 训练、做评测和消融实验的人。
- Agent Developer：观察失败轨迹，改进模型、prompt、tool policy 或 reward 设计的人。

### 3.2 核心场景

1. Env Builder 输入一个 Git repo 或本地路径，系统扫描复杂函数和测试，给出候选任务列表。
2. Env Builder 选择候选函数，系统生成任务描述、工具集合、输入 fixture、oracle 和 reward。
3. 系统构建隔离 env package，运行 smoke test、baseline policy 和隐藏测试。
4. RL Researcher 通过统一接口加载 env，agent 以 tool call 的形式与环境交互。
5. 系统记录每一步 observation、action、tool result、reward、done、error 和最终评分，用于训练与诊断。

## 4. 术语

- CodeBlock：被选中的源码单元，可以是函数、类方法、类、模块或一个入口函数加调用图。
- TaskSpec：自然语言任务描述、输入约束、目标状态、成功标准和禁止行为。
- ToolSpec：agent 可调用工具的名称、描述、参数 schema、返回 schema、副作用声明、timeout 和底层实现绑定。
- EnvSpec：一个环境的完整静态定义，包括源代码版本、任务、工具、初始状态、runtime、reward 和测试集。
- EnvPackage：可运行产物，包含 `env_spec.yaml`、wrapper 代码、fixture、oracle、锁定依赖和元数据。
- Trajectory：一次 rollout 的完整交互记录。

## 5. 产品需求

### 5.1 功能需求

| 编号 | 需求 | 说明 | 优先级 |
|---|---|---|---|
| F1 | 仓库接入 | 支持 Git URL、本地路径、commit pin、浅克隆、依赖元数据读取 | P0 |
| F2 | 代码索引 | 基于 Python AST/CST 建立 symbol index、import graph、call graph、docstring/test 关联 | P0 |
| F3 | 候选选择 | 用复杂度、调用深度、测试覆盖、I/O 可控性、外部副作用风险对 CodeBlock 排序 | P0 |
| F4 | 任务总结 | 从函数名、docstring、README、测试、调用图和示例输入输出生成 TaskSpec | P0 |
| F5 | 工具抽取 | 将主函数步骤、关键子函数和可观测状态检查器转成 ToolSpec | P0 |
| F6 | 环境生成 | 生成支持 `reset`、`step`、`evaluate`、trajectory log 的 EnvPackage | P0 |
| F7 | Scoring | 支持最终正确性、过程进展、schema 有效性、效率、安全约束等多维 reward | P0 |
| F8 | RL 接口 | 提供 Gymnasium-like 接口和 function-call tool protocol | P0 |
| F9 | 质量门禁 | 自动跑 smoke test、determinism test、oracle test、baseline comparison | P1 |
| F10 | 人工审阅 | 支持修改任务描述、工具粒度、reward 权重、隐藏测试 | P1 |
| F11 | 语料管理 | 管理 repo snapshot、license、commit、生成记录、失败原因和版本 | P1 |
| F12 | 批量生成 | 从 repo 批量生成 env，并输出质量报告 | P2 |

### 5.2 非功能需求

- 可复现：每个 EnvPackage 必须 pin repo commit、依赖版本、fixture 和随机种子。
- 安全：执行时默认禁用网络，限制文件系统写入范围、CPU 时间、内存和子进程。
- 可解释：TaskSpec、ToolSpec 和 reward 必须能追溯到源码片段、测试或人工标注。
- 稳定：同一 env 在相同 seed 下 reward 一致，非确定性测试需要被标记或剔除。
- 可扩展：核心接口不绑定单一 RL 框架；训练侧只依赖标准 observation/action/reward/done/info。

## 6. 端到端流程

```text
Git Repo / Local Path
  -> RepoSnapshot
  -> CodeIndexer
  -> CandidateRanker
  -> TaskSummarizer
  -> ToolExtractor
  -> ScorerBuilder
  -> EnvSpec
  -> EnvPackage
  -> QualityGate
  -> RL Training / Evaluation
```

关键设计原则：

- 先生成可审阅 spec，再生成 runtime，避免直接执行未经解释的代码。
- 工具粒度控制在 3 到 8 个核心 tools，过细会让任务退化为机械调用，过粗会让 agent 没有可学习决策。
- reward 采用“隐藏最终 oracle + 可解释过程分”的混合策略，降低 reward hacking 风险。
- 所有自动生成内容都保留 provenance，标明来自源码、测试、README、动态 trace 还是 LLM 推断。

## 7. 主要模块

### 7.1 Repo Ingestor

职责：

- 接收 Git URL、本地路径、repo allowlist 或批量配置。
- 执行 shallow clone，记录 commit SHA、license、默认分支、文件规模、Python 版本和依赖文件。
- 过滤 vendored code、generated code、tests-only code、过大文件和不支持的二进制依赖。

输入：

```yaml
repo_url: https://github.com/psf/requests
commit: optional
include_tests: true
max_files: 5000
```

输出：`RepoSnapshot`，包含源码路径、commit、依赖摘要、license、文件清单和 ingest log。

### 7.2 Code Indexer

职责：

- 使用 `ast` 建立函数、类、方法、参数、docstring、decorator、return、异常、分支和调用信息。
- 后续可引入 `libcst` 保留源码 span 和注释，用于更可靠的工具 wrapper 生成。
- 关联测试文件：按 import、名称相似度、fixture 使用和 coverage trace 找到可能的 oracle 来源。

核心产物：

- `SymbolIndex`：模块、类、函数、方法、类型注解、docstring。
- `CallGraph`：入口函数到内部 helper 和外部库调用的有向图。
- `ComplexityProfile`：行数、分支数、循环数、调用数、异常路径、副作用风险。
- `TestLinkIndex`：候选函数与测试、fixture、golden data 的关联。

### 7.3 Candidate Ranker

职责：

- 从代码库中选出适合转成 env 的 CodeBlock。
- 排除纯 getter/setter、过短函数、强外部服务依赖、强随机性、不可隔离副作用和 license 不明代码。
- 优先选择有复杂流程、有测试、有明确输入输出、可分解为多个步骤的函数。

排序信号：

```text
score = complexity
      + call_graph_depth
      + test_link_confidence
      + docstring_quality
      + fixture_availability
      - side_effect_risk
      - dependency_install_risk
      - nondeterminism_risk
```

### 7.4 Task Summarizer

职责：

- 把 CodeBlock 的真实行为总结为 agent 可理解的任务。
- 生成任务目标、输入状态、约束、期望输出、失败条件和隐藏 oracle 说明。
- 对每一条任务陈述记录 provenance，区分“源码可证据支持”和“模型推断”。

信息来源优先级：

1. 测试断言、fixture、golden 文件。
2. 函数签名、类型注解、异常和返回值。
3. docstring、README、API 文档。
4. 调用图和动态 trace。
5. LLM 对复杂逻辑的总结。

输出示例：

```yaml
task:
  title: Normalize and validate a user supplied HTTP URL
  instruction: >
    Given a request object and a user supplied URL, construct the normalized URL
    that the HTTP client should send, preserving valid parameters and rejecting
    invalid schemes.
  success_criteria:
    - final URL matches oracle normalization
    - invalid inputs raise the expected structured error
    - no network request is performed
  hidden_oracle: tests plus differential call to pinned source implementation
```

### 7.5 Tool Extractor

职责：

- 将主函数的关键步骤转为 agent tools。
- 对直接子函数、关键内部 helper、状态检查器和安全替身外部依赖生成 ToolSpec。
- 生成参数 JSON Schema、返回类型、错误模型、前置条件、可见/隐藏状态读写规则。

工具来源：

- Top-level statement block：主函数里连续的解析、校验、转换、提交等阶段。
- Direct callee：主函数直接调用且语义明确的 helper。
- State inspector：只读检查器，用于让 agent 查询当前环境状态。
- Safe adapter：对网络、文件、数据库、时间、随机数等副作用的可控替身。

ToolSpec 示例：

```yaml
tools:
  - name: parse_url
    description: Parse the candidate URL into scheme, host, path, query and fragment.
    input_schema:
      type: object
      required: [url]
      properties:
        url:
          type: string
    output_schema:
      type: object
      properties:
        scheme: {type: string}
        host: {type: string}
        path: {type: string}
        query: {type: string}
    backing:
      kind: wrapper
      source: requests.models.PreparedRequest.prepare_url:parse_phase
    side_effects: none
    timeout_ms: 500
```

工具粒度规则：

- 每个 env 默认 3 到 8 个 tools。
- 单个 tool 只做一个稳定语义动作。
- 必须至少有一个状态查询或验证类 tool，避免 agent 只能盲调。
- 有副作用的原函数不能直接暴露，必须经过 sandbox adapter。

### 7.6 Env Runtime

职责：

- 加载 EnvSpec、fixture 和 wrapper。
- 实现 `reset`、`step`、`evaluate`、`close`。
- 验证 action schema，执行 tool，更新状态，计算 reward，写 trajectory。

推荐接口：

```python
class Code2Env:
    def reset(self, seed: int | None = None, task_id: str | None = None) -> dict:
        ...

    def step(self, action: dict) -> tuple[dict, float, bool, dict]:
        ...

    def evaluate(self) -> dict:
        ...
```

Action 协议：

```json
{
  "type": "tool_call",
  "tool": "parse_url",
  "arguments": {"url": "https://example.com/a?b=1"}
}
```

Observation 协议：

```json
{
  "task": "Normalize and validate a user supplied HTTP URL",
  "state": {"phase": "parsed", "attempt": 2},
  "available_tools": ["parse_url", "validate_scheme", "assemble_url", "submit"],
  "last_tool_result": {"ok": true, "value": {"scheme": "https"}},
  "budget": {"remaining_steps": 6}
}
```

### 7.7 Scorer Builder

职责：

- 为每个 env 生成最终评分和过程 reward。
- 组合测试 oracle、差分 oracle、属性测试、状态不变量和工具调用惩罚。
- 输出可解释评分明细，支持训练 reward 和离线 evaluation score 分离。

默认 reward 结构：

| 维度 | 权重 | 说明 |
|---|---:|---|
| Schema validity | 0.05 | action 参数合法、tool 存在、返回可解析 |
| Process progress | 0.25 | 中间状态满足阶段性不变量 |
| Final correctness | 0.50 | 最终输出通过隐藏 oracle 或差分测试 |
| Efficiency | 0.10 | 步数、重复调用、无效调用惩罚 |
| Safety | 0.10 | 禁止网络、越界文件写入、异常逃逸等 |

Oracle 来源：

- 原项目测试：复用或裁剪单元测试。
- Differential oracle：对固定输入同时运行原函数和 agent 产物，比较输出。
- Metamorphic oracle：例如排序不变性、幂等性、round-trip、错误类型一致性。
- Golden trace：从原函数动态 trace 提取关键中间状态。
- Human rule：人工补充不可自动推断的业务规则。

### 7.8 Corpus Manager

职责：

- 管理高星 repo 语料、clone 缓存、commit pin、license 和生成状态。
- 对每个 repo 保存候选函数列表、失败原因、已发布 env 和评测报告。

初始语料建议使用浅克隆，不把外部 repo 直接提交到本项目：

```bash
git clone --depth 1 https://github.com/fastapi/fastapi /tmp/code2env_corpus/fastapi
git clone --depth 1 https://github.com/pallets/flask /tmp/code2env_corpus/flask
git clone --depth 1 https://github.com/scrapy/scrapy /tmp/code2env_corpus/scrapy
git clone --depth 1 https://github.com/Textualize/rich /tmp/code2env_corpus/rich
git clone --depth 1 https://github.com/psf/requests /tmp/code2env_corpus/requests
```

2026-05-08 UTC 通过 GitHub 元数据确认的首批候选：

| Repo | Stars | 适合原因 | 代表性候选 |
|---|---:|---|---|
| [fastapi/fastapi](https://github.com/fastapi/fastapi) | 97,995 | 路由、参数解析、OpenAPI 生成流程复杂，测试丰富 | `fastapi/routing.py:get_request_handler` |
| [pallets/flask](https://github.com/pallets/flask) | 71,495 | request/response、blueprint、CLI 工作流清晰 | `src/flask/app.py:make_response` |
| [scrapy/scrapy](https://github.com/scrapy/scrapy) | 61,578 | 爬虫 pipeline、downloader、middleware 适合多工具交互 | `scrapy/core/spidermw.py:_process_spider_output` |
| [Textualize/rich](https://github.com/Textualize/rich) | 56,282 | 渲染、格式化、语法高亮有明确输入输出和属性测试空间 | `rich/pretty.py:traverse` |
| [psf/requests](https://github.com/psf/requests) | 53,968 | HTTP 请求准备、认证、重定向、代理逻辑适合差分 oracle | `src/requests/sessions.py:resolve_redirects` |

备选扩展语料：

- [python-poetry/poetry](https://github.com/python-poetry/poetry)：依赖解析、CLI、配置处理。
- [pytest-dev/pytest](https://github.com/pytest-dev/pytest)：测试发现、fixture、断言重写。
- [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy)：表达式构建、SQL 编译、schema 操作。

### 7.9 Quality Gate

职责：

- 在发布 env 前运行自动门禁。
- 输出每个 env 的 pass/fail、失败原因、可复现命令和修复建议。

门禁项：

- `spec_schema_check`：EnvSpec 和 ToolSpec schema 完整。
- `import_check`：环境依赖可安装，入口可导入。
- `reset_determinism_check`：相同 seed 的初始状态一致。
- `tool_smoke_check`：每个 tool 至少有一个合法样例能运行。
- `oracle_check`：最终评分能区分正确轨迹和随机轨迹。
- `sandbox_check`：网络、文件、子进程、时间限制生效。
- `baseline_check`：scripted baseline 高于 random baseline。

## 8. EnvSpec 数据结构

建议使用 YAML 作为可审阅源格式，运行时编译为 JSON。

```yaml
id: code2env.requests.prepare_url.v1
version: 1
source:
  repo: https://github.com/psf/requests
  commit: "<pinned-sha>"
  entrypoint: requests.models.PreparedRequest.prepare_url
  license: Apache-2.0
task:
  title: Normalize and validate a user supplied HTTP URL
  instruction: "..."
  constraints:
    - "Do not perform real network requests."
    - "Preserve valid query parameters."
tools:
  - name: parse_url
    input_schema: {}
    output_schema: {}
runtime:
  sandbox:
    network: false
    timeout_seconds: 3
    memory_mb: 512
  max_steps: 8
reward:
  final_oracle: tests/test_models.py::test_prepare_url
  weights:
    schema_validity: 0.05
    process_progress: 0.25
    final_correctness: 0.50
    efficiency: 0.10
    safety: 0.10
provenance:
  task_sources:
    - kind: source_span
      path: src/requests/models.py
      symbol: PreparedRequest.prepare_url
```

EnvPackage 文件布局：

```text
generated_envs/
  code2env.requests.prepare_url.v1/
    env_spec.yaml
    runtime.py
    tools.py
    scorer.py
    fixtures/
    tests/
    provenance.json
    requirements.lock
```

## 9. 实施路径

### Phase 0：PRD 与语料准备

交付：

- 完成本 PRD。
- 建立首批 repo allowlist 和 clone 策略。
- 确定 EnvSpec、ToolSpec、Trajectory 的 schema 初稿。

验收：

- 至少 5 个高星 Python repo 被确认可作为语料。
- 每个 repo 至少列出 3 个候选 CodeBlock。

### Phase 1：离线抽取 MVP

交付：

- `repo_ingestor`：支持 Git URL/local path、commit pin、文件过滤。
- `code_indexer`：输出 SymbolIndex、CallGraph、ComplexityProfile。
- `candidate_ranker`：输出候选函数榜单和风险标签。
- CLI：`code2env scan <repo> --top-k 50`。

验收：

- 能在 requests、flask、rich 三个 repo 上完成扫描。
- Top 50 候选中至少 60% 经人工判断适合转 env。
- 扫描失败必须有结构化错误码。

### Phase 2：Spec 生成与人工审阅

交付：

- `task_summarizer`：生成 TaskSpec 草稿。
- `tool_extractor`：生成 3 到 8 个 ToolSpec。
- `spec_editor`：允许人工编辑 YAML。
- CLI：`code2env draft <repo> --symbol <entrypoint>`。

验收：

- 至少生成 20 个可审阅 EnvSpec。
- 每个 TaskSpec 至少有 2 条 provenance。
- ToolSpec 参数 schema 通过 JSON Schema 校验。

### Phase 3：Runtime 与 Scoring

交付：

- `env_runtime`：实现 `reset`、`step`、`evaluate`。
- `scorer_builder`：支持测试 oracle、差分 oracle 和过程 reward。
- `sandbox_runner`：禁网、限时、隔离工作目录。
- CLI：`code2env build <env_spec.yaml>` 与 `code2env smoke <env_id>`。

验收：

- 至少 30 个 EnvPackage 通过 smoke test。
- 同 seed 重复运行 reward 一致率达到 99%。
- Scripted baseline 分数显著高于 random baseline。

### Phase 4：Agentic RL 接入

交付：

- 批量 env loader。
- Trajectory JSONL 导出。
- Gymnasium-like adapter。
- Function-call action adapter。
- 训练侧 demo：random policy、scripted policy、LLM policy 三种 rollout。

验收：

- 单进程可稳定 rollout 100 个 episode。
- 轨迹包含 observation、action、tool result、reward、done、info 和 error。
- 输出可用于离线 reward analysis。

### Phase 5：规模化与质量闭环

交付：

- 批量生成 pipeline。
- 质量报表 dashboard 或静态 HTML。
- 失败样本聚类：依赖失败、oracle 弱、工具粒度差、任务不清晰。
- Human review queue。

验收：

- 从 5 个 repo 生成至少 100 个候选 EnvSpec。
- 至少 50 个 EnvPackage 通过全部 P0 门禁。
- 每个失败 env 都有可追踪失败原因。

## 10. 成功指标

| 指标 | 目标 |
|---|---:|
| Scan success rate | >= 95% on allowlisted repos |
| Candidate useful rate | >= 60% for top 50 |
| EnvSpec schema pass rate | >= 95% |
| EnvPackage smoke pass rate | >= 70% in Phase 3, >= 85% in Phase 5 |
| Reward determinism | >= 99% with same seed |
| Scripted vs random gap | scripted baseline final score >= random + 0.35 |
| Task grounding | every TaskSpec has >= 2 provenance links |
| Tool count | 3-8 tools for >= 90% accepted envs |

## 11. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 任务描述幻觉 | agent 训练目标偏离真实代码 | 强制 provenance、人工 review、测试断言优先 |
| Reward hacking | 模型学会绕过评分器 | 隐藏 oracle、sandbox、最终正确性高权重、异常轨迹审计 |
| 依赖安装复杂 | env 无法稳定运行 | allowlist、lockfile、容器缓存、按 repo 预构建 |
| 外部副作用不可控 | 训练污染本机或不可复现 | safe adapter、禁网、临时目录、资源限制 |
| 工具粒度不合适 | 任务太简单或不可解 | 候选工具数限制、baseline 校验、人工调参 |
| 测试不足 | oracle 弱，评分不可靠 | 差分 oracle、属性测试、golden trace、人工规则补充 |
| 高星 repo 代码过复杂 | MVP 延迟 | 先选局部函数和模块，避免全框架级任务 |

## 12. 开放问题

- 训练侧最终优先接入的 RL 框架是 AXRL、自研接口还是 Gymnasium adapter。
- agent 是否只允许 tool call，还是后续要支持 code patch action。
- 自动任务总结使用哪个 LLM，是否需要离线缓存和 prompt 版本管理。
- EnvPackage 是否纳入主仓库，还是发布到单独 registry/artifact store。
- Human review 的最小产品形态是 YAML 编辑、Web UI 还是 PR-based review。

## 13. MVP 推荐切入点

最小可交付版本建议从 requests、flask、rich 三个 repo 开始，原因是它们依赖相对轻、函数边界清晰、测试可复用、外部服务风险低。首批 env 类型：

- requests：URL 规范化、认证 header 构造、代理绕过判断、multipart 编码。
- flask：response 构造、URL 构建、blueprint 注册、CLI app 查找。
- rich：markup 渲染、pretty traversal、table render、syntax token 处理。

MVP 不追求一次性覆盖完整项目，而是先验证“复杂函数 -> 任务 -> tools -> runtime -> scoring -> RL rollout”的闭环。闭环稳定后再扩展到 fastapi 和 scrapy 这类更复杂的框架流程。
