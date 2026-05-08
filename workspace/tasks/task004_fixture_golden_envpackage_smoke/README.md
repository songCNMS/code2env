# task004_fixture_golden_envpackage_smoke

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_dev -->

## Background

Task003 produced five EnvSpec drafts from selected candidate JSONL rows. The next step is to determine which selected candidates can run with JSON-serializable fixtures, compute golden answers from source code, build EnvPackages, and smoke-test them.

## Goals

- Inspect the five EnvSpec drafts generated under `outputs/task003_targeted_selection/env_specs/`.
- Design JSON fixtures for candidates that can be invoked by the current runtime.
- Materialize EnvSpecs with fixtures and golden answers.
- Build standalone EnvPackages and run scripted smoke tests.
- Record pass/fail results and blockers for candidates that need adapters or richer fixture support.

## Acceptance

- A fixture/golden report is generated under the intern outputs directory.
- Runnable candidates have materialized EnvSpec JSON files with golden answers.
- Runnable candidates have built EnvPackage directories and smoke-test results.
- Non-runnable candidates have concrete blocker notes.
- Task metadata is updated on the PR branch.
