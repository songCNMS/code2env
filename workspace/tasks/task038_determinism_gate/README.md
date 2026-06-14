# task038_determinism_gate - 根因②:确定性门禁(剔除非确定性 golden)

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_1 -->

## 背景

v2 的 weak_oracle_skipped=25 只剔了'装依赖后仍报错'的;剩 75 real_value 里仍混非确定性 golden:含内存地址 repr(<sha1 ...@0x72b6...>)、worker 绝对路径(/home/.../intern_code2env_worker_5/...)、hash 对象、可能时间戳——每次跑都不同,任何 agent 永不可 match,导致确定性可用集被高估。你是 envdeps/golden 重算的作者。

## 任务目标

加确定性门禁:对每个 env 源函数重复执行 N(>=2-3)次,若结果不一致,或 golden 命中非确定性特征(0x 内存地址/绝对路径前缀/<...object at ...>/HASH/时间戳),标 nondeterministic 并从确定性可用集剔除(单列类别,不计入正确率分母)。写进 manifest/spec 的 determinism 字段。

## 实现说明

落点:新增确定性检测(可在 envdeps 或新 determinism.py)+ batch/spec 写 determinism 字段。非确定性正则参考:内存地址 r'0x[0-9a-fA-F]{6,}'、object repr r'<[\w.]+ (object )?at 0x'、绝对路径 r'/home/|/tmp/|/Users/'、可结合重复执行比对。[determinism 契约-与 w4 报告/w5 执行共享,字段勿改名]。与 w2(task037 信封归一)解耦。注意 task035(uv 兜底,PR#22)也是你的,先把这个做了。完成 mailbox 回报 lead PR#+自测,等 tester(w3)+lead review。

## 验收标准

- determinism 字段(契约):manifest.envs[].determinism ∈ {deterministic, nondeterministic:<reason>};reason 形如 unstable_across_runs / memory_addr / abs_path / object_repr / hash / timestamp
- 重复执行 N>=2 次不一致→nondeterministic:unstable_across_runs;golden repr/字符串命中特征(0x[0-9a-f]+/绝对路径/object at/...)→对应 reason
- 确定性可用集=real_value(①已修信封) AND deterministic;nondeterministic 与 weak_oracle 一样剔除分母、单列
- 补单测(确定性函数判 deterministic、含内存地址/绝对路径/不稳定的判 nondeterministic+reason),不依赖大网络;现有 pytest tests/ 全绿;更新 README/mvp_usage

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_1
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
