# task012_testlink_index_ingest - History Log

<!-- METADATA:SESSION=1 -->

## Session 1 - 2026-06-13 UTC - 实现 TestLinkIndex + tests 索引 + provenance>=2

- 接受 task，分支 `intern_code2env_worker_3/task012_testlink_index_ingest`，PR #7（base=main）。
- ingest.py：新增 `test_files` 字段与 tests 单独索引（不污染 python_files），拆分 infra/test/source 判定。
- models.py：新增 `TestLink` dataclass；`RepoSnapshot.test_files` 默认 `[]`。
- indexer.py：`build_test_link_index` / `test_links_for_candidate`（import/name/fixture/golden 关联，含 evidence + confidence）。
- spec.py：`_build_provenance` 保证 task_sources>=2 且多样（source_span+signature+test_link/fixture/golden），无测试时 degradation 说明。
- cli.py scan 增 `Test files` 行；__init__ 导出新 API；更新 README.md/docs/mvp_usage.md。
- 新增 tests/test_testlink_index.py（5 例）；全量 18 例全绿。待 push、worker_4 验证与 lead review。

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_3` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。
