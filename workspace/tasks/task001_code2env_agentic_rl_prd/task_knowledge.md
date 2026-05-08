# task001_code2env_agentic_rl_prd Knowledge

<!-- METADATA:SESSION=2 -->

## Writing Rule

Record durable task-specific decisions, constraints, and implementation notes here. Keep entries concise and update when new information would help future sessions.

## Entries

- The repo default branch is `main`; the idle playbook examples mention `master`, so task work uses `main` as the target branch.
- Initial PRD corpus is based on shallow clones of fastapi, flask, scrapy, rich, and requests under `/tmp/code2env_corpus`; external repos should not be committed into code2env.
- MVP implementation intentionally uses only the Python standard library and JSON EnvSpec files to keep the first runnable loop dependency-free.
- Common Python `src/` layouts are handled by adding both the packaged source root and `source/src` to the executor import path.
