# task042_execute_v3_rerun - 执行 v3 重跑(接替 w5):确定性可用集→rollouts_v3+report_v3

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

v3 关键路径:三项修复全 merged 到 main(信封①7c0a82c+确定性②716b62d 你写的+report_v3 ba7dbf7,148 passed)。原 runner w5(task041)疑似 session 卡住——ping 后 status 仍待 ping、无进程、outputs/rollouts_v3 无产物。coordinator 授权改派给空闲 worker。你深谙 envdeps/determinism/golden,uv 兜底已折进 envdeps(task035 merged)无需 wrapper。旧 v1(rollouts/100)/v2(rollouts_v2/75+phase3_v2 manifest/baseline)保留勿覆盖。

## 任务目标

git checkout main && git pull 后执行 v3:Step1 batch 复现同一100 env 集产 v3 manifest(--determinism-runs 3,带 golden_status+determinism),确定性可用集=real_value AND deterministic(剔 weak_oracle+nondeterministic 单列)。Step2 可用集用 gpt-5.5(--endpoint-file /home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt --llm-model gpt-5.5 --fallback-model gpt-oss-120b)重跑,conversation JSON 存 outputs/rollouts_v3/(不覆盖 v1/v2)。Step3 code2env report <v3_manifest> --rollouts outputs/rollouts_v3/ --prev-rollouts <v2 rollouts> --output-dir outputs/report_v3/。

## 实现说明

uv 兜底已在 envdeps(_create_venv 自动 uv venv --seed),直接 code2env batch。装不动库跳过记 reason。语料 requests/flask/rich/click/jinja。后台跑+阶段性回报。步骤参考 task041 README。回报 mailbox。

## 验收标准

- v3 manifest 带 golden_status+determinism;确定性可用集大小记录
- 确定性可用集 gpt-5.5 重跑→outputs/rollouts_v3/(不覆盖 v1/v2)
- report_v3/含真实非零 correct率+四类别+v1→v2→v3 对比
- mailbox 回报真实非零 correct率/可用集大小/四类别数/rollouts_v3//report_v3/ 路径

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_1
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
