# Related Work

## EP140: Zhang Xiaojun Interview With Yao Shunyu

Source: Zhang Xiaojun Podcast EP140. Public pages and excerpts: [Xiaoyuzhou](https://www.xiaoyuzhoufm.com/episode/6a00aa051b7bd50295dfe41d), [Apple Podcasts](https://podcasts.apple.com/cn/podcast/140-%E5%AF%B9%E5%A7%9A%E9%A1%BA%E5%AE%87%E7%9A%844%E5%B0%8F%E6%97%B6%E8%AE%BF%E8%B0%88-%E8%AF%B7%E5%85%81%E8%AE%B8%E6%88%91%E5%B0%8F%E7%96%AF%E4%B8%80%E4%B8%8B-%E5%9C%A8anthropic%E5%92%8Cgemini%E8%AE%AD%E6%A8%A1%E5%9E%8B-%E6%8A%80%E6%9C%AF%E9%A2%84%E6%B5%8B-%E8%8B%B1%E9%9B%84%E4%B8%BB%E4%B9%89%E5%B7%B2%E8%BF%87%E5%8E%BB/id1634356920?i=1000767107736), [Podwise](https://podwise.ai/dashboard/episodes/7949463), [Scripod](https://scripod.com/episode/qz1rzztces6go9w5odxb2tdl), and a public excerpt reposted from `语言即世界language is world` on [发现AI](https://www.faxai.cn/archives/6724).

This note only keeps points directly relevant to code-to-env / code2env planning.

## Anthropic: Coding RL And Environment Feedback

Original phrases:

- "回馈信号足够清晰"
- "把简单的事儿做的比谁都干净"
- "回归信号清晰，数据充分"

Value for code2env:

- Coding is useful as an RL target because the environment can return tests, logs, runtime errors, traces, and final correctness.
- The hard part is less about fancy wrappers and more about making the execution path clean: stable fixtures, reliable reward, reproducible runs, and clear failure labels.

## Anthropic: Agentic Coding Scale-Up

Original phrase:

- "制备各种各样的环境和data"

Value for code2env:

- Environment construction and data construction are linked. Candidate selection, adapter design, materialization, smoke tests, and failure reports should be explicit pipeline stages.

## Infrastructure And Evaluation

Original phrases:

- "基础设施真的是很重要"
- "算法设计...依赖于你的基础设施"

Value for code2env:

- Related work points to infra/eval as part of the method, not just support code. EnvSpec should record runtime constraints, oracle source, dependency assumptions, and evaluator provenance.

## Long-Horizon Experiment Loops

Original phrase:

- "不仅能写这个code，还能跑这个实验"

Value for code2env:

- Keep this only as a boundary marker: code2env should eventually support plan, run, observe, diagnose, and retry loops, not just one-shot function calls.

## Implications For code2env Schema

- Add environment feedback quality: tests, traces, logs, errors, final oracle.
- Add task horizon: single-call, short tool sequence, long-context, long-horizon loop.
- Add fixture/adapter fields: JSON args, files, modules, object instances, service mocks, persistent state.
- Add evaluation provenance: pinned source, tests, golden traces, human review, controlled service simulation.
