# task042_execute_v3_rerun - Task Knowledge

<!-- METADATA:SESSION=1 -->

## 记录规则

- 只记录本任务相关的事实、决策、踩坑和验证结果。
- 每条尽量一句话，避免重复 README 的完整内容。

## Knowledge Entries

1. 本 task 由 team_lead `intern_code2env_lead` 创建并分配给 worker `intern_code2env_worker_1`。
2. uv 兜底真机 bug 根因(实测更正)：非裸名 python3(uv 能解析 `--python python3`)，而是 `python -m venv` 失败前留半成品目录→`uv venv` 拒绝非空目录(exit 2)。fix=uv 兜底前 rmtree(venv_dir)。
3. 路径：v2 rollouts=/home/leisong/codes/work-agents/intern_code2env_coordinator/outputs/rollouts_v2；v2 manifest=intern_code2env_worker_5/outputs/phase3_v2/envs/manifest.json；v3 产物写 coordinator outputs/phase3_v3、rollouts_v3、report_v3(并存不覆盖 v1/v2)。
4. endpoints：/home/leisong/codes/work-agents/simpleCodeQA/endpoints.txt；gpt-5.5=https://xyzlapi.boyuerichdata.com/v1/(200 可达)，fallback gpt-oss-120b=http://127.0.0.1:39000/v1。
5. 语料 git URL：psf/requests、pallets/flask、Textualize/rich、pallets/click、pallets/jinja。
6. batch 只在结束时 print 一次 summary(无流式进度)；后台跑 + Monitor 守 PID/manifest.json。
7. probe：click(no_deps)build_ok 2、real_value1/weak_oracle1；flask(修后)deps installed。candidates_scanned 量大(click 511/flask 357)。
