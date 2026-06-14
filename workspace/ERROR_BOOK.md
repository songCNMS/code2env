# code2env - Error Book

> Records project-related errors.

---

## E1 (task012, worker_3): 公有 API 以 `test_` 开头被 pytest 误收集

- 现象：`python3 -m pytest tests/` exit 1，报 `fixture 'snapshot' not found`，指向 `code2env/indexer.py` 的 `def test_links_for_candidate(snapshot, candidate)`。
- 根因：pytest 按命名约定收集 `test_*` 函数为测试用例，连 import 进测试模块的同名函数也会被收集；其参数 `snapshot` 被当成 fixture 请求而找不到。
- 漏检原因：自测用 `python3 -m unittest`，unittest 不收集裸函数，故没暴露。
- 修复：重命名公有函数 `test_links_for_candidate` → `links_for_candidate`。
- 教训：① 任何对外暴露的函数/变量不要以 `test_` 开头；② 自测一律用 CI 同款 `python3 -m pytest tests/`，不要只跑 unittest。

## E2 (task040, worker_3, tester): 验"剥壳/归一"逻辑漏检过度剥壳假阳性

- 现象：验 PR#23 task037 信封归一(`_normalize_answer_envelope` 剥 {ok:true,value}/{kind:json,value} 壳)，我逐条只验"同一底层值的多种信封形状都判 correct"+"不同值判错"+"ok:false 不误判"，给了 APPROVE；lead review 发现**过度剥壳假阳性**。
- 根因：归一会无条件剥掉形如 {ok:true,value:..}/{kind:json,value:..} 的 dict。若**源函数的合法返回值本身**就是这种形状的 dict，会被误当壳剥掉，导致错误提交也能匹配 golden 底层 → 假阳性 correct。
- 漏检原因：只测了"壳包真值"的正向场景，没构造"合法数据恰好长得像壳→不应被剥"的对抗用例。
- 教训：验任何 strip/unwrap/normalize/dedup 类逻辑，必须额外构造**对抗用例**——让合法数据本身命中剥离/归一的模式特征，断言它**不被**错误处理（over-strip / 误并）。正向"能剥对"不等于"不会多剥"。
