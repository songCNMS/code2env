# task013_qa_toolextractor_testlink - Task Knowledge

<!-- METADATA:SESSION=2 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_4`。
2. 角色为 tester：独立验证 task010(语义化 ToolExtractor, PRD 7.5) 与 task012(TestLinkIndex+放开 tests 扫描, PRD 7.2) 两个 PR 分支；不替 worker 改代码，发现问题清晰描述复现步骤。
6. [验证结论] PR#9 task010 @9fc8887：`pytest tests/`=16 passed，PRD 7.5 七条全 PASS（建议 merge）。
7. [验证结论] PR#7 task012 @ff75074：PRD 7.2 四条功能全 PASS，但 `pytest tests/`=18 passed+1 error(exit1)；`unittest discover`=18 OK。
8. [踩坑/缺陷] pytest 会收集测试模块顶层任何 `test_*` 可调用对象（含 import 进来的）；indexer.py 公有 API `test_links_for_candidate` 因 test_ 前缀被误收集为用例 → snapshot 当 fixture 找不到 → `pytest tests/` exit1。unittest discover 不收集裸函数故漏检。教训：非测试函数勿用 test_ 前缀；QA 同时用 pytest 与 unittest 两种 runner 跑。
9. [验证手法] tester 自建合成 repo（含 helper/side-effect helper/无 helper 函数 + tests/conftest/golden）跑 draft_env_spec/runtime，可独立复核 tool 数区间、state tool、provenance>=2、TestLinkIndex 关联，不只看 worker 单测。运行需 `PYTHONPATH=.`。
10. mailbox 单封 content 过长会 `content_too_long`；按 PR 拆成多封发送。
3. 环境事实：仓库默认分支为 `main`（非 playbook 写的 master）；无 `python`，须用 `python3`（3.12.3）；运行测试 `python3 -m pytest tests/test_mvp.py -q`。
4. 基线：在 `main` 上 `python3 -m pytest tests/test_mvp.py -q` => 6 passed（实测 2.37s）。这是回归对照。
5. 共享 repo 在 `/home/leisong/codes/work-agents/code2env`(始终 master/main)；个人 worktree 在 `/home/leisong/codes/work-agents/intern_code2env_worker_4/code2env`。

## 测试计划（等 team_lead ping 分支名后执行）

### 通用流程（对每个 PR 分支）
1. `cd 个人 worktree && git fetch origin && git checkout <branch> && git pull`。
2. 记录运行环境：`git rev-parse HEAD`、`python3 --version`、当前分支名。
3. 回归：`python3 -m pytest tests/test_mvp.py -q` 必须全绿（对照基线 6 passed）。
4. 全量单测：`python3 -m pytest -q`（含新增单测）；记录通过/失败明细。
5. 逐条核对该 task README 验收标准，给出 PASS/FAIL。
6. 失败时记录复现命令 + 报错栈；不改代码。
7. mailbox 回报 intern_code2env_lead：执行命令、结果、运行环境、未覆盖风险、每条验收 PASS/FAIL。

### task010 (ToolExtractor / PRD 7.5) 专项核对清单
- [ ] 候选函数生成 **3-8 个**语义 tools（含保留的 inspect_task/submit_answer）。手动取若干候选 symbol 跑 `draft_env_spec` 后数 `spec.tools` 长度，验证落在 [3,8]。
- [ ] 其中 **至少一个状态查询/校验类只读 tool**（state inspector）；检查 side_effects=none 且语义为只读。
- [ ] 每个语义 tool 的 ToolSpec 含 `input_schema` / `output_schema` / `side_effects` / `provenance`(backing source span 或 symbol)。逐字段非空校验。
- [ ] 工具来源覆盖 **direct callee(helper)** 与 **主函数关键步骤**；确认不是只复刻旧的 4 个通用工具。
- [ ] 有副作用原函数 **不直接暴露**，side_effects 正确标注。
- [ ] runtime.py 能 dispatch 新语义 tools（或向后兼容）；`scripted_smoke` / Code2Env reset+step 闭环仍通；现有 call_entrypoint/submit_answer 闭环未破坏。
- [ ] 新增单测覆盖：tool 数量区间[3,8]、状态 tool 存在性、schema 完整性。
- [ ] 边界：找一个极简函数(无 helper)和一个多 helper 函数，验证两端都能落在 [3,8]（≥90% 接受环境达标的抽样验证）。
- [ ] README.md 与 docs/mvp_usage.md 的 Runtime Tools 段已更新。

### task012 (TestLinkIndex / PRD 7.2) 专项核对清单
- [ ] ingest 支持保留/单独索引 tests：默认行为安全（不污染默认 python_files），有新增字段(如 test_files)或 include_tests 开关。验证默认 `ingest_repo` 不把 tests 混入主列表，开关开启后能拿到 test 文件。
- [ ] indexer 产出 **TestLinkIndex**：候选函数关联到 test 函数/fixture/golden，含关联依据(import / name 相似度 / fixture 使用)。
- [ ] draft 的 `spec.provenance.task_sources` **>=2 条且类型多样**(source_span + test_link/fixture)；无测试关联时有明确降级说明。
- [ ] 兼容性：改 RepoSnapshot/models 字段要兼容 `from_dict` 与现有 spec.json（用旧 spec.json round-trip 验证不报错）。
- [ ] 与 P0-1/P0-2 解耦：单独验证，不依赖 task010 分支。
- [ ] 新增单测覆盖：tests 索引、TestLinkIndex 关联、provenance>=2。
- [ ] README.md / docs/mvp_usage.md 已更新。

### 关键命令速记
```bash
cd /home/leisong/codes/work-agents/intern_code2env_worker_4/code2env
git fetch origin && git checkout <branch> && git pull
git rev-parse HEAD; python3 --version
python3 -m pytest tests/test_mvp.py -q   # 回归基线 6 passed
python3 -m pytest -q                      # 全量含新增单测
```
