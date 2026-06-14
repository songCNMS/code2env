# intern_code2env_worker_4 - 个人知识库

<!-- METADATA:SESSION=1 -->

---

## 知识条目

### QA / 测试

- **pytest 会收集测试模块顶层任何 `test_*` 可调用对象（包括 import 进来的非测试函数）**。若产品代码里有以 `test_` 开头的公有 API（如 `test_links_for_candidate`）被测试文件顶层 import，pytest 会误当用例收集，首参被当 fixture → `pytest tests/` 整轮 exit 1。`unittest discover` 不收集裸函数，故只跑 unittest 会漏检。→ 教训：① 非测试函数勿用 `test_` 前缀；② QA 同时用 pytest 与 unittest 两种 runner 跑，并核对 exit code（不只看 "N passed"）。(task013, PR#7)
- **tester 不应只看 worker 自测**：自建合成 repo（含 helper / side-effect helper / 无 helper 函数 + tests/conftest/golden）跑 `draft_env_spec`/`runtime`，可独立复核 tool 数区间、state tool、provenance>=2、TestLinkIndex 关联。运行需 `PYTHONPATH=.`。(task013)

### 环境 / 流程

- code2env 仓库默认分支是 `main`（playbook 写的是 master，需自行适配）；GitHub repo（songCNMS/code2env），merge 用 `gh pr merge <n> --squash`，非 codeup_pr。
- 无 `python`，统一 `python3`（3.12.3）。
- mailbox 单封 content 过长会返回 `content_too_long`；长报告按 PR/主题拆成多封发送。
- QA checkout 别的 worker 分支时，会把自己的 `workspace/interns/.../status.md` 切到该分支版本；**不要在别人分支上 commit**，验证完切回自己分支再更新状态。
