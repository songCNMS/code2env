# code2env - Error Book

> Records project-related errors.

---

## E1 (task012, worker_3): 公有 API 以 `test_` 开头被 pytest 误收集

- 现象：`python3 -m pytest tests/` exit 1，报 `fixture 'snapshot' not found`，指向 `code2env/indexer.py` 的 `def test_links_for_candidate(snapshot, candidate)`。
- 根因：pytest 按命名约定收集 `test_*` 函数为测试用例，连 import 进测试模块的同名函数也会被收集；其参数 `snapshot` 被当成 fixture 请求而找不到。
- 漏检原因：自测用 `python3 -m unittest`，unittest 不收集裸函数，故没暴露。
- 修复：重命名公有函数 `test_links_for_candidate` → `links_for_candidate`。
- 教训：① 任何对外暴露的函数/变量不要以 `test_` 开头；② 自测一律用 CI 同款 `python3 -m pytest tests/`，不要只跑 unittest。
