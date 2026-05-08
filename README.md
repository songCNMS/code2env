# code2env

`code2env` turns Python code blocks into runnable tool-based environments for agentic RL experiments.

## MVP Quickstart

Scan a local repository:

```bash
python -m code2env scan /path/to/python/repo --top-k 10 --json
```

Draft an environment spec for a selected symbol:

```bash
python -m code2env draft /path/to/python/repo \
  --symbol package.module:function_name \
  --fixture-json '{"args": [1, 2], "kwargs": {}}' \
  --output /tmp/env_spec.json
```

Build a standalone package and run a smoke trajectory:

```bash
python -m code2env build /tmp/env_spec.json --output-dir /tmp/generated_envs
python -m code2env smoke /tmp/generated_envs/<env_id>
```

The generated runtime exposes `inspect_task`, `call_entrypoint`, optional `call_helper`, and `submit_answer` tools. The default scorer uses exact match against the pinned source function output.
