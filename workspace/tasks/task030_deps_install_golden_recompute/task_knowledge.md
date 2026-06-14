# task030_deps_install_golden_recompute - Task Knowledge

<!-- METADATA:SESSION=0 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_1`。
2. 根因A：executor.run_symbol_subprocess 用 sys.executable 跑子进程，repo 第三方依赖未装→import 报错→golden 被污染成 error dict，agent 提交同样报错即 exact_match 假阳性(flask 3/100)。
3. executor 新增 `python_executable` 参(默认 sys.executable 向后兼容)；当 python≠sys.executable 时通过 env PYTHONPATH 注入 code2env 包父目录，保证 venv python 仍能 `-m code2env.executor`(venv 里没装 code2env)。
4. 新增 code2env/envdeps.py：prepare_repo_env(snapshot, install, venv_builder, installer) 建 venv(缓存 .code2env_cache/venvs)+逐包 pip 装；venv_builder/installer 可注入便于单测离线。deps_status ∈ {no_deps,skipped,installed,partial,uninstallable,venv_failed}；装不动的包记 failed[{package,reason}] 不卡死。
5. golden_status_for(golden)：ok=True→real_value；ok=False→weak_oracle:golden_exception:<type>；None→weak_oracle:golden_uncomputed。契约字段 golden_status 写入 spec.provenance + manifest.envs[]。
6. spec.draft_env_spec 加 python_executable/requirements/deps_status 参，持久化到 spec.runtime；compute_golden 时算 golden_status，否则 pending_golden。materialize 同样(默认用 spec.runtime.python_executable)。
7. runtime._call_source 用 spec.runtime.python_executable(经 _python_executable 属性校验路径存在，否则 fallback sys.executable，避免跨机/缓存丢失硬失败)。builder manifest 存 python_executable/requirements/deps_status/golden_status。
8. batch 每 repo 调一次 prepare_repo_env，python 传给该 repo 所有候选 draft；manifest 新增 summary.real_value/weak_oracle + by_repo.deps_status + 顶层 repo_deps；env 新增 golden_status/deps_status/deps_installed。weak_oracle 从正确率分母剔除(w4 报告用)。
9. 坑：测试本机无 python3-venv/ensurepip→真实 _create_venv 失败→deps_status=venv_failed 优雅 fallback base python(reason 记 venv_create_failed:CalledProcessError)。w5 真实放量需 run host 装 python3-venv。
10. 坑：测 good=real_value/bad=weak_oracle 同 repo 时，缺失 import 必须放在函数体内(局部)而非模块顶层，否则整模块不可 import 全部 weak_oracle。
11. 坑：测 runtime fallback 时 draft 要 compute_golden=False(否则 draft 已用坏 python 算出 error golden)，让 reset() 用 fallback python 重算真实 golden。
12. 自测：pytest tests/ → 99 passed(新 test_envdeps.py 16 + 既有)；CLI batch 加 --no-install-deps/--venv-cache-dir。cli.py 此时已含 report(w4)/rollout(D2?)/rollout-export(D3) 子命令(分支基线继承自 main)。
