# task033_report_true_correct_rate - 报告更新:真实 correct 率(剔除假阳性)+装依赖前后对比

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_4 -->

## 背景

Session2 报告 correct=3% 全是假阳性(error-match)。本轮 w1(task030)装依赖重算 golden 并给每 env 打 golden_status(real_value|weak_oracle:<reason>)。需更新 code2env/report.py(你是 D4 作者),消费 golden_status 算出剔除 weak_oracle 后的真实 correct 率,并给装依赖前后对比。

## 任务目标

更新 report.py(及 code2env report):①真实 correct 率=correct/(可用 env=非 weak_oracle 的 rollout 数);weak_oracle 计数单列、不入分母。②装依赖前后对比:golden 由 error→real_value 的 env 数、各 repo smoke_ok 变化(尤其 flask 0→?)。③保留原有指标(生成成功率/by_repo/合格率/平均score/失败聚类)。

## 实现说明

落点:code2env/report.py + 测试。与 w1(task030 产 golden_status)、w5(task034 跑最终报告)对齐。真实数据由 w5 放量后用本工具产出。可先用合成样例开发。完成 mailbox 回报 lead PR#+自测,等 tester(w3)+lead review。

## 验收标准

- report 计算并输出'真实 correct 率'(剔除 weak_oracle 分母)与 weak_oracle 单列计数
- 报告含装依赖前后对比段:golden error→real_value 数、各 repo smoke_ok 前后变化
- 消费 w1 的 golden_status 字段(契约:manifest.envs[].golden_status ∈ {real_value, weak_oracle:<reason>}),字段勿改名;缺失时安全降级
- 补单测(合成含 golden_status 的 manifest + 合成 rollouts 验证真实率/weak_oracle 剔除/前后对比),不依赖网络;现有 pytest tests/ 全绿;更新 README/mvp_usage

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_4
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
