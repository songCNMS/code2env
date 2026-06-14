# task012_testlink_index_ingest - Task Knowledge

<!-- METADATA:SESSION=2 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_3`。
2. 仓库默认分支是 `main`（playbook 写的是 master）；分支 `intern_code2env_worker_3/task012_testlink_index_ingest`，PR #7 base=main。
3. ingest：新增 `RepoSnapshot.test_files`（默认 `[]`，向后兼容）。`_is_infra_path`（.git/.venv/build/dist 等永不索引）与 `_is_test_file`（tests/test 目录、test_*.py、*_test.py、conftest.py）拆分；测试文件单独进 test_files，不污染 python_files，`_is_supported_source_file` 行为不变。
4. indexer：`build_test_link_index` / `test_links_for_candidate` 产出 `TestLink`（models.py 新增 dataclass）。关联依据 evidence=name_match/body_ref/import_ref/fixture_use/data_ref；只有 name_match 或 body_ref 才建链（import_ref 仅加权，避免整模块 import 误连所有候选）。fixture 按测试参数名匹配同模块 `@*.fixture`；golden 按测试体里 .json/.yaml/.golden 等字符串字面量。
5. spec：`_build_provenance` 始终给 source_span + signature 两条多样来源（保证 >=2），再追加 test_link/fixture/golden；无测试时 `test_link_status=no_test_links_found` 且写 `degradation` 说明（oracle 优先级降级为签名级证据）。
6. RepoSnapshot 全程由 ingest_repo 构造、不反序列化（builder 重新 ingest），故加字段对 EnvSpec.from_dict/spec.json 无影响。
7. 自测：新增 tests/test_testlink_index.py 5 例；全量 `python3 -m unittest discover -s tests` 18 例全绿。本机 `python` 不存在，用 `python3`。
8. [阻塞修复] 公有 API 不能以 `test_` 开头：pytest 会把 `test_links_for_candidate` 当测试用例收集 → `fixture 'snapshot' not found`（unittest 不收集裸函数故漏检）。已重命名为 `links_for_candidate`（indexer 定义/__init__ 导出/spec 调用/tests import 四处）。验证用 `python3 -m pytest tests/` 而非 unittest。教训记 ERROR_BOOK。
9. [rebase] PR#9(ToolExtractor, squash e2825ad) 先合入 main。`git merge origin/main` 用 ort 策略**自动合并无冲突**（双方改 spec.py/indexer.py/models.py/README/mvp_usage 但落在不同区域）。校验：grep 无冲突标记 + pytest 21 passed（我 18 + PR#9 新增 3）+ 端到端 draft 同时含 PR#9 语义工具(inspect_state/call_clean_text/ToolSpec.provenance) 与我的 task_sources=[source_span,signature,test_link]。models.py 两 dataclass(TestLink + ToolSpec.provenance/FunctionCandidate.steps)与字段(RepoSnapshot.test_files)均在。
10. [backlog 非阻塞] 名称子串匹配偏宽(add→test_address 误关联)，后续改词边界匹配。
