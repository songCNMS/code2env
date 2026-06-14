# task043_indexer_side_effect_get_filter - Refine indexer side-effect detection for ordinary get calls

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_4 -->

## 背景

Coordinator qlib scan at microsoft/qlib commit d5379c520f66a39953bad76234a7019a72796fd0 found 2860 function candidates, 493 with test links, and 221 marked possible_side_effect. 93 of those possible_side_effect candidates were get-only matches, including ordinary method names such as Alpha158DL.get_feature_config, SoftTopkStrategy.generate_target_weight_position, and QlibConfig.set. This creates false positives when dict.get or object.get is treated like risky IO.

## 任务目标

Patch code2env/indexer.py so ordinary dict.get/object.get-style calls do not mark possible_side_effect, while qualified HTTP calls such as requests.get/session.post and known filesystem/subprocess calls still do.

## 实现说明

Implementation worker: intern_code2env_worker_4. Reserved tester: intern_code2env_worker_2. Keep broader qlib future work documented but out of scope for this first patch: test-backed fixture extraction for pd.Timestamp/np/class-instance tests and instance-method env support.

## 验收标准

- code2env/indexer.py side-effect classification no longer treats bare/generic get method calls as possible side effects unless they are qualified HTTP/network calls or known filesystem/subprocess calls.
- Focused unit tests cover dict.get and ordinary object.get as non-risk, and requests.get, session.post, open, and subprocess calls as risk.
- python3 -m pytest -q passes.
- A qlib scan snippet/report shows reduced get-only false positives compared with the coordinator baseline of 93 get-only possible_side_effect matches.

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_4
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
