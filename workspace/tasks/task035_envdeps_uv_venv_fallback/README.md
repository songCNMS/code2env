# task035_envdeps_uv_venv_fallback - fix-forward: envdeps venv 创建加 uv 兜底

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

task030(A,#18 已 merged)的 envdeps 用 python -m venv 建隔离环境装依赖。w5 task034 实跑发现本节点 python3 -m venv 因 ensurepip 不可用(缺 python3.12-venv apt 包,无 sudo)→deps_status=venv_failed,A 的装依赖在本基建上实际跑不起来(w5 用 runner 侧 uv wrapper 临时绕过)。本节点有 uv 0.11.21,uv venv --seed 能建带 pip 的 venv 无需 ensurepip。

## 任务目标

把 uv 兜底折进 code2env/envdeps.py 的 venv 创建:先尝试 python -m venv(保持现状),失败时回退 uv venv --seed(若 uv 可用),再不行才 venv_failed。让 A 的依赖安装在缺 python-venv 的节点上也能真正工作。不改 golden_status 契约与既有行为。

## 实现说明

落点 code2env/envdeps.py:_create_venv 或建 venv 处。uv 命令参考:uv venv --seed <dir>(--seed 装 pip/setuptools)。检测 uv:shutil.which(uv)。与 w5 task034 并行,不阻塞其重跑(w5 用 wrapper 交付本轮数字);本 PR 是让合入代码长期可用。完成 mailbox 回报 lead PR#+自测,等 tester(w3)+lead review。

## 验收标准

- envdeps _create_venv:python -m venv 失败→尝试 uv venv --seed(检测 uv 存在);两者都不可用→deps_status=venv_failed(保持优雅降级)
- 补单测(注入式:模拟 python-venv 失败+uv 成功路径、uv 不存在仍 venv_failed),不依赖真实下载;现有 pytest tests/ 全绿
- README/docs 注明 uv 兜底与节点 python3-venv 缺失场景;独立 PR base main

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_1
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
