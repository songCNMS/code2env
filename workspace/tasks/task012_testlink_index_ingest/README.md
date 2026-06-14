# task012_testlink_index_ingest - P0-3 TestLinkIndex + 放开 tests 扫描 (F2 / PRD 7.2)

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

对照 docs/code2env_agentic_rl_prd.md 7.2。ingest.py:_is_supported_source_file 直接把 tests/ 加入 ignored_parts 排除,indexer.py 也无测试关联,导致 PRD 优先的'测试断言'oracle 源拿不到。PRD 要求 TestLinkIndex(候选函数<->测试/fixture/golden 关联)且每个 TaskSpec provenance>=2 条来源。

## 任务目标

1) 让 ingest 可保留并单独索引 tests(新增 test_files 字段或开关,不污染主 python_files 默认行为或提供 include_tests 选项)。2) 在 indexer 建立 TestLinkIndex:按 import 引用/名称相似度/fixture 使用把候选函数关联到测试函数/fixture/golden data。3) draft_env_spec 在 provenance.task_sources 产出 >=2 条来源(source_span + 至少一条 test_link/fixture)。

## 实现说明

落点: code2env/ingest.py(_is_supported_source_file/RepoSnapshot 字段)、code2env/indexer.py(TestLinkIndex 构建)、code2env/spec.py(draft_env_spec provenance)、code2env/models.py(可能加字段)。注意改 RepoSnapshot/models 字段要兼容 from_dict 与现有 spec.json。与 P0-1/P0-2 解耦。完成后 mailbox 回报 intern_code2env_lead PR# 与自测,等 tester(worker_4) 验证与 lead review。

## 验收标准

- ingest 支持保留/单独索引 tests(默认行为安全,新增字段或 include_tests 开关)
- indexer 产出 TestLinkIndex:候选函数关联到 test 函数/fixture/golden,含关联依据(import/name/fixture)
- draft 的 spec.provenance.task_sources >=2 条且类型多样(source_span + test_link/fixture);无测试关联时有明确降级说明
- 新增单测覆盖 tests 索引、TestLinkIndex 关联、provenance>=2;现有 tests/test_mvp.py 全绿
- 更新 README.md/docs/mvp_usage.md;独立 PR 并 push 自己分支

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_3
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
