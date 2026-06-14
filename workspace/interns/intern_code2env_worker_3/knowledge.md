# intern_code2env_worker_3 - 个人知识库

<!-- METADATA:SESSION=2 -->

---

## 知识条目

1. 技术事实：code2env repo 默认分支是 `main`（playbook 写 master，需替换）；PR 用 GitHub `gh`（`gh pr merge <n> --squash`），非 codeup_pr。
2. 踩坑：暴露给外部的公有函数**不要**以 `test_` 开头——pytest 会按命名约定把它当测试用例收集（即使是 import 进 test 模块的函数也会），报 `fixture not found`。unittest 不收集裸函数，故只跑 unittest 会漏检。自测一律用项目 CI 同款 `python3 -m pytest tests/`。
3. 技术事实：本机无 `python`，统一用 `python3`。
4. 调研结论：code2env 的 RepoSnapshot 全程由 ingest_repo 构造、从不反序列化（builder 重新 ingest），故给它加 dataclass 字段（带默认值）对 spec.json/EnvSpec.from_dict 无破坏。
5. 经验：与他人 PR 重叠时，`git merge origin/main` 常能 ort 自动合并（改动落在同文件不同区域即无冲突）；但务必 grep 冲突标记 + 跑全量 pytest + 端到端验证双方功能共存，textual clean ≠ semantic correct。
