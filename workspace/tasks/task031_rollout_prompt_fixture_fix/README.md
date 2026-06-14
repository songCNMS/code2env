# task031_rollout_prompt_fixture_fix - 根因B:rollout prompt 修正(禁止自造 call_entrypoint 参数)

<!-- METADATA:STATUS=Open,ASSIGNEE= -->

## 背景

Session2 rollout 抽查发现干净例 requests.cookies.create_cookie:任务说'用 provided fixture',但 agent 自己传了 args=[x,x],与 golden 用的 fixture 不符→即使执行成功也 exact_match=False。根因:rollout 的 system/task prompt 未明确禁止 agent 自造 call_entrypoint 参数。runtime 已支持 call_entrypoint 的 args 缺省回退 spec.fixture(见 runtime.py _dispatch call_entrypoint:arguments.get(args, spec.fixture.args))。你是 D2 rollout.py 作者。

## 任务目标

修正 code2env/rollout.py 的 system/task prompt:明确指示模型'调用 call_entrypoint 时不要自造/猜测参数,留空 arguments(或省略 args/kwargs)以使用环境提供的 fixture';或在喂给模型的 task 文本里回显具体 fixture 值让模型照用。目标:消除根因B 这类'执行成功但参数不符 golden'的假阴性。

## 实现说明

落点:code2env/rollout.py(构建 system/user prompt 处,以及可能 task 文本回显 fixture)。可选增强:把 spec.fixture 的具体值回显进 task 描述。注意与 w1(task030,改 runtime/executor)、w4(task033 报告)解耦,你只动 rollout.py prompt 层。完成 mailbox 回报 lead PR#+自测,等 tester(w3)+lead review。

## 验收标准

- rollout system/task prompt 含明确指示:call_entrypoint 不自造参数、留空用环境 fixture(可附 runtime 缺省回退说明)
- 在 mock/ScriptedSolveChat 单测中验证:不传 args 的 call_entrypoint 走 fixture 回退、轨迹仍 qualified;prompt 文本含该指示(可断言关键句)
- 不破坏既有 rollout loop/parse/fallback;RolloutResult 契约字段不变;现有 pytest tests/ 全绿
- 更新 README/mvp_usage 相关说明(如有)

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_2
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
