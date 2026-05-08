# task001_code2env_agentic_rl_prd

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_dev -->

## Background

code2env needs a product-level design for turning existing Python code into an environment that can interact with agentic RL training. The environment should start from a task description inferred from complex functions, expose tools mapped to key function steps or sub-functions, and score execution outcomes based on runtime behavior.

## Goals

- Define the code-to-env workflow from repository ingestion to task/tool/reward generation.
- Specify major modules, data contracts, and implementation phases.
- Include a practical source-corpus strategy using high-star Python repositories as initial code blocks.
- Produce a PRD that can guide subsequent implementation tasks.

## Acceptance

- A PRD document is added under `docs/`.
- The PRD covers task description generation, tool extraction, environment runtime, scoring/reward, data storage, evaluation, and rollout.
- The PRD includes a staged implementation path with milestones and risks.
- The task metadata is updated when the task is accepted.
