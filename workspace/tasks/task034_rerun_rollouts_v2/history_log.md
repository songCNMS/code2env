# task034_rerun_rollouts_v2 - History Log

<!-- METADATA:SESSION=3 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_5` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-13 - 接受任务 + 写重跑计划

- 接受 task034（v2 重跑 runner），建分支 `intern_code2env_worker_5/task034_rerun_rollouts_v2`，Idle→Working。
- 读三依赖 task：task030(w1 装依赖+golden 重算+golden_status 字段)/task031(w2 rollout prompt 禁自造 call_entrypoint 参数)/task033(w4 报告真实 correct 率剔 weak_oracle)。
- 确认上轮假阳性根因：A) flask 等 env 未装运行依赖 → golden=ModuleNotFoundError，agent 提交同错即 exact_match=True；B) prompt 未禁 agent 自造 call_entrypoint 参数 → 与 fixture 不符假阴性。
- 核对旧产物完好并将复用：phase3 manifest(build_ok=100)、旧 rollouts/(100，**勿覆盖**)、orchestrator run_rollouts.py。
- 重跑计划写入 task_knowledge：Step0 核对 w1 接口 → Step1 装依赖重算 golden+标 weak_oracle(v2 manifest) → Step2 非 weak_oracle 子集 gpt-5.5 重跑(修正 prompt)→ rollouts_v2/ → Step3 w4 真实率报告 → Step4 回报。
- 注：task024 文档 PR#15 仍 open 待 lead merge 授权（已在接受 mail 提醒）。
- 等 lead 确认三 PR merged 后 ping 启动。

## Session 2 - 2026-06-13 - 收尾 task024 PR#15 + 待命 task034

- lead 授权 self-merge task024 文档 PR#15：在 task024 分支 set README Completed、status 同步为当前 Working task034（避免 merge 回退 main 状态）、精炼 Session2 经验到个人 knowledge.md。
- PR#15 首次 merge 报 not mergeable（分支基线旧）→ `git merge origin/main`（无冲突）→ push → 重试 squash merge 成功（MERGED 2026-06-14T05:41:31Z）。main 上 task024 README=Completed、status=Working task034。删本地 task024 分支。
- ⚠️ **踩坑/注意**：playbook merge 收尾 step8 清理 `../outputs` 把我 Session2 的 `outputs/phase3`（gen manifest build_ok=100、EnvPackages、orchestrator run_rollouts.py）一并删了。**但可恢复**：coordinator outputs（旧 rollouts/100 + report）在另一路径未删；`.code2env_cache/repos`（克隆源）完好 → batch 确定性可复现同一 100 env 集。
- **task034 启动调整**：Step1 先重新 `code2env batch <5 Git URLs> --target 100`（确定性复现 env 集）作为"装依赖前"基线，再用 w1 机制装依赖重算 golden 得 v2 manifest；"装依赖前后对比"的 before 也可参考 coordinator 旧 report.json（smoke_ok=56、flask smoke 0 等）。
- 依赖进度（lead 告知）：task031(B) 已 APPROVE+w3 验证中；task030(A)/task033(报告) 实现中。三 PR 全 merged 后 lead ping 我启动。
- 当前：task024 已 Completed 收尾；task034 待命。

## Session 3 - 2026-06-13 - Phase task034 启动：Step1 装依赖重算 golden（含 venv 阻塞排查+uv 绕过）

- 三修复全 merged：A 装依赖+golden 重算(346d88e, envdeps.py)/B prompt(b59a067)/报告(f486609)；main 108 passed。新增 `batch --no-install-deps`、`report --baseline-manifest`、manifest.envs[].golden_status。
- Step1a baseline（--no-install-deps，确定性复现同一 100 env 集）：build_ok=100，golden_status real_value=67 / weak_oracle=33（ModuleNotFoundError=24 多为 flask、InvalidExecutorOutput=4、ValueError=2、AssertionError=2、OSError=1）。作"装依赖前"基线。
- Step1b v2（装依赖）首跑：**deps_status=venv_failed（全 repo）**，golden_status 与 baseline 相同（依赖没装上、golden 未修复）。
- **根因排查**：`python3 -m venv` 因 ensurepip 不可用失败（本节点缺 python3.12-venv apt 包，无 passwordless sudo）。envdeps `_create_venv` 用 `python -m venv` → 抛错 → venv_failed。
- **绕过（runner 侧，不改合入代码）**：本机有 `uv 0.11.21`。`uv venv --seed` 可建带 pip 的 venv（无需 ensurepip），且 `venv_python -m pip install` 正常（验证装上 flask/werkzeug）。写 wrapper `outputs/phase3_v2/batch_uv.py`：monkeypatch `envdeps._create_venv` 改用 `uv venv --seed`（`_create_venv` 在 call 时按模块全局解析，patch 生效），其余（幂等检查、_pip_install）不变。清 `.code2env_cache/venvs` 重跑。
- 已 git worktree(/tmp/wt_task034) 更新本 task 文档，避免在跑批期间切换主工作树的 executor.py（golden 子进程从磁盘 import code2env.executor）。
- 待：uv-wrapped v2 batch 跑完确认 golden 由 error→real_value（尤其 flask 24→?）→ Step2 重跑 → Step3 报告。venv 阻塞+uv 绕过会回报 lead（含建议 envdeps 兜底 uv）。

### Session 3 (续) - Step2 重跑 + Step3 报告 + 第三根因发现

- Step2：75 个 real_value env 用 gpt-5.5(修正 prompt)+gpt-oss-120b 回退重跑 → 75/75 跑通、0 失败、qualified=75(100%)、全 gpt-5.5 无回退。导出 coordinator outputs/rollouts_v2/（旧 rollouts/100 未动）。
- Step3：`code2env report <v2 manifest> --rollouts rollouts_v2/ --baseline-manifest <baseline> --output-dir report_v2/`。报告：真实 correct(剔 weak_oracle)=**0/75**、mean_score=0.35；装依赖前后：golden error→real_value=9、flask smoke 0→8。
- ⚠️ **第三根因（C）发现**：exact-match correct=0 不是模型不会做。逐条分析 75：**58/75(77%) 提交了正确 value 但 envelope 不符**——golden=`{ok:true,value:{kind,val}}`(executor 整包)，agent 提交内层 `{kind,val}`(== golden.value) 丢了 `{ok:true}` 外壳 → exact_match=False。仅 17 真错（其中含非确定性 repr，如 `<generator object at 0x..>` 永不可复现，属漏网 weak_oracle）。
- 即：根因 A(依赖/golden)+B(call_entrypoint 参数) 已修；真实"解对 value"≈77%，但 submit 比对整包 envelope 太严，exact correct=0。w2 prompt 修了 call_entrypoint 参数但未管 submit 格式。
- 结论：v2 交付完成（manifest/rollouts_v2/report_v2 全产出 + 装依赖前后对比）；新增根因 C 待 lead 决策（prompt 让 agent 提交整包 / oracle 比对 value / submit 自动 wrap）。已 mailbox 回报。
