# intern_code2env_worker_3 - 个人知识库

<!-- METADATA:SESSION=2 -->

---

## 知识条目

1. 技术事实：code2env repo 默认分支是 `main`（playbook 写 master，需替换）；PR 用 GitHub `gh`（`gh pr merge <n> --squash`），非 codeup_pr。
2. 踩坑：暴露给外部的公有函数**不要**以 `test_` 开头——pytest 会按命名约定把它当测试用例收集（即使是 import 进 test 模块的函数也会），报 `fixture not found`。unittest 不收集裸函数，故只跑 unittest 会漏检。自测一律用项目 CI 同款 `python3 -m pytest tests/`。
3. 技术事实：本机无 `python`，统一用 `python3`。
4. 调研结论：code2env 的 RepoSnapshot 全程由 ingest_repo 构造、从不反序列化（builder 重新 ingest），故给它加 dataclass 字段（带默认值）对 spec.json/EnvSpec.from_dict 无破坏。
5. 经验：与他人 PR 重叠时，`git merge origin/main` 常能 ort 自动合并（改动落在同文件不同区域即无冲突）；但务必 grep 冲突标记 + 跑全量 pytest + 端到端验证双方功能共存，textual clean ≠ semantic correct。
6. 技术：落盘原子写 = 同目录 NamedTemporaryFile + flush + os.fsync + os.replace（同分区 rename 原子）；并发 append 单行用 `os.open(O_WRONLY|O_CREAT|O_APPEND)` + 单次 os.write，避免多进程交错。坏数据应先校验再写（校验失败不留半成品文件）。
7. 技术：跨 worker 共享的 JSON 契约，字段名是 API——勿改名；schema 有歧义先 mailbox 问 lead。bool 是 int 子类，校验 int 字段要显式 `isinstance(x,bool)` 排除。
8. 流程：多 PR 并行合并时，lead 会指定合并顺序；第一个合并者对 main 干净直接 self-merge，后续 PR 各自 merge origin/main 解冲突（常见冲突点 cli.py subparser）。
