# task020_batch_generation_pipeline - D1 批量生成 pipeline + fixture 自动合成 (≥100 EnvPackage)

<!-- METADATA:STATUS=InProgress,ASSIGNEE=intern_code2env_worker_1 -->

## 背景

Session2 目标:规模化生成100环境供 gpt-5.5 多轮 rollout 验证。复用现有 scan/select/draft/materialize/build(cli.py/spec.py/builder.py/materialize.py/ingest.py)。语料用 shallow clone 的 requests/flask/rich/click/jinja2(不够再加 poetry),clone 到 .code2env_cache(已 gitignore, 勿提交外部 repo 源码)。ingest_repo(repo,cache_dir=) 已支持 clone 到 .code2env_cache/repos。Session1 已让每个 env 产 3-8 语义工具(spec.py)。

## 任务目标

新增 code2env batch 命令(及 batch.py 模块):跨上述 repo 批量 scan→挑候选→draft→build,自动合成 fixture,产出 ≥100 个成功 build 的 EnvPackage(每个含 env_spec.json+语义tools+golden),并写一份 gen manifest.json。'100 env'按成功 draft+build 计,不强求 smoke 通过(smoke 失败记原因)。fixture 自动合成:优先选参数类型简单(str/int/list/dict/无必填/全有默认值)的候选函数,或内置默认 fixture 策略;无法合成 fixture 的候选跳过并记原因。

## 实现说明

落点:新增 code2env/batch.py + cli.py 加 batch 子命令(子命令实现尽量放 batch.py,cli.py 仅加 subparser+dispatch 一行,减少与 w2/w3 的 cli.py 冲突面)。fixture 合成可用 ast 注解+默认值:str->''或'x',int->0或1,list->[],dict->{},bool->False;优先无必填参数或全默认值的函数;risk_flags 含 requires_instance/possible_side_effect 的降权或跳过。[gen manifest 契约] {generated_at, repos:[...], summary:{candidates_scanned,draft_ok,build_ok,smoke_ok,skipped_no_fixture,by_repo:{repo:{build_ok,smoke_ok}}}, envs:[{env_id,repo,symbol,file,line_start,line_end,fixture:{ok,strategy,value:{args,kwargs},reason},draft_ok,build_ok,smoke_ok,smoke_fail_reason,spec_path,package_path}], skipped:[{symbol,repo,reason}]}. 此 manifest 是 w4 报告与 w5 放量的输入,字段勿改名。本 PR 阶段用少量 env 跑通即可,放量到100由 w5 执行。完成 mailbox 回报 intern_code2env_lead PR# 与自测,等 tester(w5) 验证与 lead review。

## 验收标准

- 新增 code2env batch 命令:输入 repo 列表+目标数量+输出目录,批量产出 EnvPackage 与 manifest.json;build_ok 计数可达目标(放量时≥100)
- fixture 自动合成:基于候选函数签名(args/defaults_count/类型注解)合成简单类型 fixture;无法合成的跳过并在 manifest.skipped 记 reason
- gen manifest.json 严格符合契约(见 details):envs[]含 env_id/repo/symbol/file/fixture{ok,strategy,value,reason}/draft_ok/build_ok/smoke_ok/smoke_fail_reason/spec_path/package_path; summary 含 by_repo 与各计数; skipped[]
- 外部 repo 源码与生成产物均不进 git(clone 到 .code2env_cache, 生成物到 --output-dir 默认 gitignore 目录或 coordinator outputs 绝对路径);单测用小型临时/合成 repo 不依赖网络
- 补单测(fixture 合成策略/跳过原因/manifest 结构/小规模 batch 闭环);现有 pytest tests/ 全绿;更新 README.md/docs/mvp_usage.md

## 分配信息

- Team：code2env
- Team lead：intern_code2env_lead
- Worker：intern_code2env_worker_1
- 分配方式：team_lead 创建本 task 文档后，通知 worker 接受该 task。
