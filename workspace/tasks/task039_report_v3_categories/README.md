# task039_report_v3_categories - report_v3:类别拆分 + v1→v2→v3 对比

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

Session4 v3 重跑需更细报告。w2(task037)修信封归一让确定性函数判对;w1(task038)加 determinism 字段剔非确定性。报告要给类别占比与三轮对比。你是 report.py 作者。

## 任务目标

更新 report.py(及 report):①类别占比:确定性可用数(real_value+deterministic)/因信封修复转对数(v2 incorrect 但 v3 correct)/非确定性剔除数(nondeterministic)/仍错数。②真实非零 correct 率=correct/确定性可用集(剔 weak_oracle+nondeterministic)。③v1→v2→v3 对比段(correct/true_correct 率演进)。

## 实现说明

消费契约:manifest.envs[].golden_status(real_value|weak_oracle:<reason>)+determinism(deterministic|nondeterministic:<reason>);conversation final.correct(信封归一后由 runtime 判)。envelope_flipped 需 v2 与 v3 两轮 rollout 对比(w5 传两轮或你支持 --prev-rollouts)。与 w1/w2 解耦,只动 report.py。完成 mailbox 回报 lead PR#+自测,等 tester(w3)+lead review。

## 验收标准

- report 输出类别占比:deterministic_usable / envelope_flipped_to_correct / nondeterministic_excluded / still_wrong
- 真实 correct 率分母=确定性可用集(剔 weak_oracle 与 nondeterministic);消费 w1 的 determinism 字段(契约 deterministic|nondeterministic:<reason>,缺失安全降级)
- v1→v2→v3 对比段(可接受多 run 输入或 baseline 参数);保留原指标
- 补单测(合成含 determinism+golden_status 的 manifest+多轮 rollouts 验证类别与真实率),不依赖网络;现有 pytest tests/ 全绿;更新 README/mvp_usage

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_4
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
