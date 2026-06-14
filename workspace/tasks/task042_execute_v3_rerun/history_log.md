# task042_execute_v3_rerun - History Log

<!-- METADATA:SESSION=1 -->

## Session 0 - 2026-06-14 UTC - Task created by team lead

- Team lead `intern_code2env_lead` 为 worker `intern_code2env_worker_1` 创建本 task。
- Worker 应接受本 task，按普通 task/PR 流程开发、测试、提交，并在 PR merge 后完成 task。

## Session 1 - 2026-06-14 - 接受 + fix-forward + v3 开跑 (PR #27)

- 接受 task042，开 PR #27。probe(click/flask)发现 task035 uv 兜底真机 bug。
- **根因更正**(实测)：不是 lead 预警的『裸名 python3 解析失败』(我验证 `uv venv --seed --python python3 <fresh>` rc=0 正常)；真因是 `python -m venv` 失败前留半成品 venv 目录 → `uv venv` 拒绝非空目录(already exists, exit 2)。
- **fix-forward**(envdeps._create_venv)：uv 兜底前 `shutil.rmtree(venv_dir)` 清残留；`--python` 传绝对路径。加回归单测 `test_uv_fallback_clears_partial_dir_from_failed_venv`，pytest envdeps 20 passed。
- 验证：flask probe deps_status venv_failed → installed(6 依赖全装)。
- 连通性：github clone rc=0；gpt-5.5 endpoint 200。v2 产物在 coordinator outputs/rollouts_v2、report_v2、w5 phase3_v2。
- v3 Step1 batch 后台开跑(PID 195370)：requests/flask/rich/click/jinja --target 100 --determinism-runs 3 → coordinator outputs/phase3_v3/；Monitor 守候完成。
- 待 Step1 完成后跑 Step2(gpt-5.5 rollouts→rollouts_v3) + Step3(report_v3, --prev-rollouts rollouts_v2)。

### v3 结果(全部完成)

- **Step1 batch**: 100 build_ok(candidates 1458, repos requests/flask/rich), deps 全 installed(uv fix 生效)。real_value 75 / weak_oracle 25；确定性门禁剔 nondeterministic 12 → **确定性可用集 63**(real_value AND deterministic)。by_repo usable: requests 29 / rich 26 / flask 8。
- **Step2 rollouts**: 63 可用集 gpt-5.5(fallback gpt-oss-120b)→ 63 conversation JSON。qualified 63/63, correct 59, mean score 0.9587。
- **Step3 report_v3**: 真实非零 correct **59/63 = 93.7%**。四类别: deterministic_usable 63 / envelope_flipped_to_correct 59 / nondeterministic_excluded 0(rollout 前已剔 12) / weak_oracle_excluded 0(rollout 前已剔 25) / still_wrong 4。
- **v1→v2→v3**: v1 100→3(3.0%); v2 75→0(0.0% 假阴性); **v3 63→59(93.7%)**。三项修复(①信封 +②确定性 + 依赖/golden)闭环验证成功。
- 产物(coordinator outputs, 并存不覆盖 v1/v2): phase3_v3/manifest.json、rollouts_v3/(63)、report_v3/report.md+json。
- mailbox 已报数(msg c47bef2b)。PR#27 含 envdeps uv fix-forward + task042 文档；按 lead 指示稍后 review+w3 验+合，**不自合**，待 lead 指示。
