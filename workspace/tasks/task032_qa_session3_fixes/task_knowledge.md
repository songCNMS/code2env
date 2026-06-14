# task032_qa_session3_fixes - Task Knowledge

<!-- METADATA:SESSION=3 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_3`（本轮 tester）。
2. 我是 tester：只验证不改码；分支 `intern_code2env_worker_3/task032_qa_session3_fixes`、PR #19 仅承载状态/测试计划/验证报告。
3. main 基线已确认存在待改文件：executor.py(run_symbol_subprocess 当前硬编码 sys.executable, 行 70)、runtime.py(_call_source 行 446 调 run_symbol_subprocess; call_entrypoint 缺省回退 spec.fixture)、rollout.py(build_system_prompt 行 114; ScriptedSolveChat 行 72)、report.py(classify_reason 行 76、_summarize_rollouts 行 287 correct_rate=correct/total)、batch.py。
4. 通用验证流程：每个 PR `git fetch origin && git checkout <branch>`，`git merge origin/main`(如需) → `python3 -m pytest tests/ -q`(基线 44 passed，须不降)→ 逐条对验收标准 → 契约字段对照 → mailbox 回报。验证用 pytest（项目 CI 同款，勿用 unittest，见 ERROR_BOOK E1）。环境本机 `python3`（无 `python`）。

## 测试计划（等 lead ping 分支名后执行）

### task030 (w1, 根因A: 依赖安装+golden重算+weak_oracle)
- 跑全量 pytest；确认新增 envdeps.py 单测 + executor/runtime/spec/materialize/builder 改动测试全绿。
- 验收逐条：
  1. `run_symbol_subprocess` 新增 `python_executable` 参数且默认 `sys.executable`（向后兼容）：grep 签名 + 跑既有 executor 测试不回归。
  2. 依赖安装模块（envdeps.py）：合成小 repo + 小依赖或 mock venv 验证建 venv+装依赖；装不动库跳过并记 reason（不卡死）。
  3. runtime `_call_source` 用同一 venv python（spec 存 venv/python 路径或 requirements）：验证 rollout 期 call_entrypoint 真实执行而非 import 报错。
  4. **契约 golden_status**：manifest.envs[].golden_status ∈ {real_value, weak_oracle:<reason>}（字段勿改名）；weak_oracle env 从正确率分母剔除、manifest/spec 标注。重点：装依赖后 golden 由 ModuleNotFoundError→真实返回值（小依赖样例）。
  5. 现有 pytest 全绿；README/mvp_usage 更新。
- 未覆盖风险关注：真实大依赖下载由 w5 执行，本 PR 单测应不依赖大网络；venv 缓存路径 .code2env_cache/venvs 须已 gitignore。

### task031 (w2, 根因B: rollout prompt 禁自造参数)
- 跑全量 pytest；确认 test_rollout.py 新增断言。
- 验收逐条：
  1. system/task prompt 含明确指示：call_entrypoint 不自造参数、留空用环境 fixture（断言关键句存在于 build_system_prompt 输出）。
  2. mock/ScriptedSolveChat 单测：不传 args 的 call_entrypoint 走 fixture 回退（runtime `_dispatch` arguments.get(args, spec.fixture.args)）、轨迹仍 qualified。
  3. 不破坏既有 rollout loop/parse/fallback；**RolloutResult 契约字段不变**（与我 task022 落盘 schema 一致：env_id/messages/steps/final/num_tool_call_rounds/qualified/... 字段名不漂移）。
  4. 现有 pytest 全绿；README/mvp_usage（如有）。
- 只动 rollout.py prompt 层，与 w1/w4 解耦——确认未越界改 runtime/executor/report。

### task033 (w4, 报告真实 correct 率)
- 跑全量 pytest；确认 test_report.py 新增合成 manifest+rollouts 用例。
- 验收逐条：
  1. 真实 correct 率 = correct/(可用 env=非 weak_oracle 的 rollout 数)；weak_oracle 单列计数、不入分母（对比基线 report.py `_summarize_rollouts` correct_rate=correct/total）。
  2. 装依赖前后对比段：golden error→real_value 数、各 repo smoke_ok 前后变化（尤其 flask 0→?）。
  3. **消费 w1 契约** manifest.envs[].golden_status（字段勿改名）；缺失时安全降级（不崩）。
  4. 保留原有指标（生成成功率/by_repo/合格率/平均 score/失败聚类）。
  5. 现有 pytest 全绿；README/mvp_usage 更新。
- 跨 PR 一致性：task033 读的 golden_status 取值集合须与 task030 写的一致（real_value | weak_oracle:<reason>）——若两 PR 取值/前缀不一致即为阻塞。

## 验证结果

### [Phase1] task031 (PR#17, 分支 ...worker_2/task031_..., 493e1dd) — APPROVE 建议, 无阻塞
- pytest tests/ = 90 passed(与自测一致); PromptFixtureGuidanceTest 4 passed; dry-run merge main=CLEAN + 临时 merge 后仍 90 passed。
- 1[PASS] system prompt 含 CALL_ENTRYPOINT_FIXTURE_GUIDANCE("do NOT invent...empty arguments {}")。
- 2[PASS] user message 回显 spec.fixture(build_initial_user_message 加 fixture 参数; None 时省略)。
- 3[PASS] 空 args call_entrypoint 走回退: 真跑得 arguments={}/ok/qualified/correct; 回退源 runtime.py:413-414(真 runtime 行为)。
- 4[PASS] 契约不漂移: 用我 task022 validate_conversation 校验真实 rollout 输出通过。
- 5[PASS] 代码仅改 rollout.py(+28); tests(+51)/docs(+7)/workspace。
- 加分: 对抗用例 test_fabricated_args_mismatch 证明自造 args→qualified 但 correct=False(根因B)。
- 未覆盖(非阻塞): 真实模型遵从率需 w5 放量验证, 本 PR 仅静态验证指示句+回退行为。
- 教训复用: 跨 worker 契约一致性可用自己模块的 validator 做交叉校验, 高效且权威。

### [Phase2] task033 (PR#20, 分支 ...worker_4/task033_..., ab3cc66) — APPROVE 建议, 无阻塞
- pytest tests/=91 passed; test_report.py 19 passed; merge main CLEAN + post-merge 91。
- 1[PASS] true_correct_rate=_rate(true_correct,usable=非weak); 手验 raw 2/3 vs true 1/2。
- 2[PASS] weak_oracle 单列 weak_oracle_excluded(手验=1)。
- 3[PASS] 消费 golden_status, 缺失→unknown 且**留分母**(never silently shrink); 取值 real_value 精确 + weak_oracle 前缀匹配。
- 4[PASS] --baseline-manifest 前后对比: golden error→real(手验=1) + 各 repo smoke before/after delta(flask 0→1); 无 baseline 安全降级。
- 5[PASS] 原指标全保留(correct 改标 raw 仍在)。
- 跨 PR 待核(记录): w4 读取 weak_oracle 用前缀匹配, 需 task030 写出形如 `weak_oracle:<reason>`(冒号分隔); 验 task030 时交叉核对两侧取值集合, 不一致→阻塞。

### 踩坑(流程)
- 验别人分支时 worker_3 自己的 status.md 会变成该分支上的旧副本(常是 main/已合并态), Stop hook 读当前分支的 status.md → 可能 Session 号不符。规避: 验证完务必 checkout 回自己 task 分支再结束回复, 并让 status.md Session 号 = checklist = 本轮预期。
