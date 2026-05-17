# Problem And Goals

## Problem

The code-to-env direction asks how to turn real software into trainable, evaluable, and reproducible agent environments.

The problem is broader than wrapping one function as one tool. A useful environment should preserve enough of the source repo, package, or service behavior for an agent to make meaningful decisions, while still making execution safe, deterministic enough to score, and portable enough for RL training and evaluation.

In the current code2env MVP, this starts from Python repositories: scan candidate functions, ask an LLM to screen and describe suitable tasks, draft an `EnvSpec`, materialize fixtures and golden answers, build an `EnvPackage`, and smoke-test the runtime. The planning schema should keep that concrete pipeline in view, while leaving room for richer repo/package/service environments beyond JSON-callable functions.

## Inputs

- Source units: local repos, GitHub repos, Python packages, service modules, or selected source snapshots pinned to a commit or version.
- Code targets: functions, methods, classes, modules, workflows, APIs, CLI entrypoints, or service operations that can become agent tasks.
- Context signals: source spans, signatures, docstrings, call/helper structure, tests, examples, README/API docs, dependency metadata, and risk flags.
- Task guidance: human-written goals, LLM-generated task descriptions, candidate-selection records, or review annotations.
- Fixtures and state: JSON arguments, object or module adapters, files, temporary directories, service mocks, seeds, and other bounded initial state.
- Runtime constraints: network/filesystem/subprocess policy, timeouts, dependency limits, package layout, and allowed side effects.

Inputs should be bounded enough to reproduce execution and review provenance. Inputs that require live external services, private credentials, uncontrolled network calls, or unpinned mutable state are outside the initial scope unless replaced by safe adapters.

## Outputs

- Candidate records: structured JSONL rows with repo metadata, file/function location, static signals, LLM suitability, task description, risk flags, and provenance.
- Environment specs: reviewable `EnvSpec` files describing source, task, tools, runtime limits, fixtures, reward policy, golden answer, and provenance.
- Runnable packages: portable `EnvPackage` directories containing filtered source, `env_spec.json`, manifest metadata, fixtures or adapters, and runtime entrypoints.
- Evaluation artifacts: smoke reports, trajectories, tool-call logs, submitted answers, scores, failures, and blocker notes.
- Dataset or registry entries: versioned references to generated environments that downstream training or evaluation systems can load.

## Downstream Users / Tasks

- Env builders use the schema to decide what code can become a safe, useful environment and what metadata must be reviewed before release.
- RL researchers use generated environments for agentic RL training, rollout collection, offline evaluation, and ablation studies.
- Agent developers use trajectories and failure reports to improve models, prompts, tool-use policies, and debugging behavior.
- Benchmark maintainers use candidate records, EnvSpecs, and smoke reports to curate reproducible suites across repos and packages.
- Runtime integrators use EnvPackages or adapters to connect code2env outputs to Gym-like systems, GEM-style environments, or other training stacks.

## Goals

- Build environments from real repo/package/service behavior rather than synthetic tasks alone.
- Keep every generated environment reproducible through pinned source, explicit fixtures, runtime constraints, and recorded provenance.
- Make tasks trainable by exposing meaningful tools, state, observations, rewards, and termination behavior.
- Make tasks evaluable by producing stable oracles, golden answers, smoke tests, trajectories, and score breakdowns.
- Support human review at each boundary: candidate selection, task wording, fixture design, tool surface, reward policy, and blocker classification.
- Separate source understanding from runtime execution: LLMs may help select and describe tasks, but execution truth should come from pinned source, tests, or controlled oracles.
- Provide a path from lightweight MVP function environments to richer package/service environments with adapters for objects, files, mocks, and service state.
