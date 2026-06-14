# task030_deps_install_golden_recompute - 根因A:依赖安装+golden重算+weak_oracle 标注

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_1 -->

## 背景

Session2 放量 100 env 后 coordinator 抽查发现 exact-match correct 3/100 全是假阳性:flask 全部 env 的 golden_answer 本身是 ModuleNotFoundError(env 未装运行依赖 werkzeug 等),agent 提交同样报错即 exact_match=True。根因:code2env/executor.py run_symbol_subprocess 用 sys.executable 跑子进程,repo 第三方依赖未装→import 报错→golden 污染成 error dict。runtime.py Code2Env._call_source 同样问题(rollout 期 agent call_entrypoint 也是 import 报错)。

## 任务目标

①EnvPackage 生成/materialize 时按 repo 依赖文件(pyproject/requirements/setup)装齐运行依赖到隔离 venv,让 golden 子进程与 runtime call_entrypoint 都用该 venv 的 python→golden 是真实返回值而非 import 报错。②装好依赖后 golden 仍为异常/无法计算的 env 标记 weak_oracle(写 manifest/spec 的 golden_status 字段),从合格可用集合剔除(不计入正确率分母),报告单列。装依赖如个别库装不动→跳过并记 reason,不卡死整轮。

## 实现说明

落点:code2env/executor.py(python_executable 参)、新 code2env/envdeps.py(建 venv+装依赖,缓存到 .code2env_cache/venvs 已 gitignore)、code2env/spec.py(draft golden 计算路径+golden_status)、code2env/materialize.py、code2env/builder.py(EnvPackage 存 venv 信息)、code2env/runtime.py(_call_source 用 venv python)、code2env/batch.py(per-repo venv 编排)。[golden_status 契约-与 w4 报告/w5 执行共享,字段勿改名]:manifest.envs[].golden_status ∈ {real_value, weak_oracle:<reason>};另可加 envs[].deps_installed/deps_status。单测用合成小 repo+小依赖(或 mock venv)不依赖大网络下载;真实装依赖重算由 w5 执行。完成 mailbox 回报 lead PR#+自测,等 tester(w3)+lead review。

## 验收标准

- executor.run_symbol_subprocess 加 python_executable 参数(默认 sys.executable 向后兼容);venv 装依赖后 golden 子进程用 venv python 计算
- 新增依赖安装模块(如 envdeps.py):按 repo 依赖文件建 venv+pip 装运行依赖(werkzeug/click/itsdangerous/jinja2 等);装不动的库跳过记 reason
- runtime.py Code2Env._call_source 用同一 venv python(spec 存 venv/python 路径或 requirements),保证 rollout 期 call_entrypoint 真实执行
- golden_status 字段(契约):每 env=real_value | weak_oracle:<reason>(如 golden_exception:ModuleNotFoundError / uninstallable_deps);weak_oracle env 从正确率分母剔除,manifest/spec 标注
- 补单测(venv 装依赖/golden 真实值/weak_oracle 标注/装不动跳过/python_executable 向后兼容);现有 pytest tests/ 全绿;更新 README/mvp_usage

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_1
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
