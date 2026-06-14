# task032_qa_session3_fixes - Task Knowledge

<!-- METADATA:SESSION=1 -->

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
