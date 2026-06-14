# task037_runtime_envelope_normalization - 根因①:runtime 信封归一比较

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_worker_2 -->

## 背景

v2 重跑 true_correct=0/75 全是假阴性:agent submit 的是里层 value(如 flask.json.dumps 提交 {kind:json,value:"x"}),但 golden_answer 存的是完整工具信封 {ok:true,value:{kind:json,value:"x"}};runtime.evaluate 用 submitted==golden_answer 精确比,差一层信封→确定性纯函数其实算对却判错。lead 抽查确认 75 个 incorrect 中 70+ 是这种拆包形状不符,agent 实际 value-correct≈93%。coordinator 定方案:runtime 比较前做信封归一。

## 任务目标

在 runtime 比较前(evaluate 与 submit_answer 的 correct 判定)对 submitted 与 golden_answer 做信封归一:统一剥到底层 value(剥 {ok,value} 工具信封 + {kind:json,value} 序列化壳),或统一都带信封;使 agent 提交里层 value 或完整信封两种都能对确定性纯函数判对。务必 scripted_smoke 仍通过。

## 实现说明

落点 code2env/runtime.py:evaluate() 与 _dispatch submit_answer 的 correct 比较。建归一函数 _normalize_answer_envelope(x):递归剥 {ok:true,value:..}→value、{kind:json,value:..}→value、{kind:repr,...}保留repr 比较。比较时对 submitted 与 golden 都归一再 ==。注意保留 score_breakdown 五维不变。与 w1(task038 确定性门禁)/w4(report) 解耦,只动 runtime 比较。完成 mailbox 回报 lead PR#+自测,等 tester(w3)+lead review。

## 验收标准

- runtime 比较前信封归一:agent 提交里层 value(如 {kind:json,value:X} 或更内层 X)与提交完整 {ok:true,value:{kind:json,value:X}} 两种都判 correct(当底层值==golden 底层值)
- ok:false 的错误信封不被误判为 correct(error golden 仍走 weak_oracle/不匹配);非确定性值不在本任务处理(②负责)
- scripted_smoke 仍通过(提交完整 last_tool_result 仍对);现有 pytest tests/ 全绿
- 补单测:同一底层值的多种信封形状都判对、不同底层值判错、ok:false 不误判;更新 README/mvp_usage

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_2
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
