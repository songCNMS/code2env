# task035_envdeps_uv_venv_fallback - Task Knowledge

<!-- METADATA:SESSION=2 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_1`。
2. fix-forward task030(A)：本节点 python3 -m venv 因缺 python3.12-venv/ensurepip(无 sudo)→venv_failed；本节点有 uv 0.11.21，`uv venv --seed <dir>` 建带 pip 的 venv 无需 ensurepip。
3. envdeps._create_venv 改造：先 `python -m venv`，except CalledProcessError/OSError 后 `shutil.which("uv")` 在则 `uv venv --seed --python <base> <dir>`，uv 缺失或也失败则原 venv 异常 propagate→prepare_repo_env 记 venv_failed(优雅降级保持)。
4. _create_venv 加 `runner=subprocess.run, which=shutil.which` keyword-only 注入参(默认不变, 仍是 (venv_dir,base_python) 的 VenvBuilder)；单测注入 fake runner(按 cmd 含 '--seed' 区分 stdlib/uv)+fake which，离线覆盖 stdlib成功/uv兜底/uv缺失raise/两者失败raise + prepare_repo_env 集成两路径。
5. 不改 golden_status 契约与既有行为，无新 manifest 字段；只让 venv 创建在缺 python-venv 节点能真正工作。
6. 自测：pytest tests/ → 114 passed(test_envdeps.py 新增 6 个 uv 兜底用例)。与 w5 task034 并行(w5 用 runner 侧 uv wrapper 交付本轮数字)，本 PR 让合入代码长期可用。
