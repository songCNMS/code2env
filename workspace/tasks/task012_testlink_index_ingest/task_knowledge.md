# task012_testlink_index_ingest - Task Knowledge

<!-- METADATA:SESSION=0 -->

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
