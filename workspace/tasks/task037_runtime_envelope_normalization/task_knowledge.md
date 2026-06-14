# task037_runtime_envelope_normalization - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_2`。
2. 根因①：v2 true_correct=0/75 假阴性——agent submit 里层 value，golden 存完整工具信封 {ok:true,value:{kind:json,value:X}}，evaluate 用 == 精确比差一层。
3. 修复：`_normalize_answer_envelope` 贪婪递归剥 `{ok:true,value}`(仅 ok 为 True 时) + `{kind:json,value}`；`ok:false`/`{kind:repr}` 不剥（避免误判 correct）。贪婪对称剥使「里层 value/json 壳/完整信封」三种提交都归一到同一底层值，互相匹配。
4. 比较两端(submitted、golden)都过同一归一函数(`_answers_equal`)；用 32 次循环 guard 防自引用 dict 死循环。
5. 落点仅 runtime.py evaluate() 与 submit_answer correct 判定；score_breakdown 五维不变。非确定性值不在本任务(②负责)。
