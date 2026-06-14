# Code2Env MVP Usage

This MVP implements the PRD path as a runnable standard-library pipeline:

```text
scan -> draft -> build -> smoke
```

## Commands

```bash
python -m code2env scan /path/to/repo --top-k 10 --json
```

`scan` parses Python files with `ast`, ranks functions by line count, branch count, call count, helper calls, docstring quality, and side-effect risk. It also reports a `Test files` count: test modules (`tests/`/`test/` directories, `test_*.py`, `*_test.py`, `conftest.py`) are mined separately into `RepoSnapshot.test_files` for the TestLinkIndex and are excluded from the ranked source corpus.

The indexer's `build_test_link_index(snapshot, candidates)` links each candidate to its tests, fixtures, and golden-data files (by import reference, name similarity, and fixture usage), recording the `evidence` and a `confidence` per link.

```bash
python -m code2env draft /path/to/repo \
  --symbol package.module:function_name \
  --fixture-json '{"args": [], "kwargs": {}}' \
  --output /tmp/env_spec.json
```

`draft` creates an `EnvSpec` with task text, tool specs, fixture, provenance, and an exact-match golden answer computed from the pinned source function. The `provenance.task_sources` list always holds at least two diverse sources — a `source_span` and a `signature` — plus any `test_link` / `fixture` / `golden` artifacts found by the TestLinkIndex. When no test artifacts are linked, `provenance.test_link_status` is `"no_test_links_found"` and a `degradation` note records that grounding fell back to signature-level evidence.

```bash
python -m code2env build /tmp/env_spec.json --output-dir /tmp/generated_envs
```

`build` copies a filtered Python source snapshot into the env package so the runtime no longer depends on the original repo checkout path.

```bash
python -m code2env smoke /tmp/generated_envs/<env_id> --json
```

`smoke` runs a scripted trajectory:

1. `call_entrypoint` with the fixture.
2. `submit_answer` with the serialized result.
3. Score by exact match against the golden source output.

Before building a draft EnvSpec, materialize it with a concrete JSON fixture:

```bash
python -m code2env materialize /tmp/env_spec_draft.json \
  --fixture-json '{"args": ["hello"], "kwargs": {}}' \
  --output /tmp/env_spec.json
```

## Runtime Tools

- `inspect_task`: returns task, fixture, source metadata, and allowed helpers.
- `call_entrypoint`: executes the selected function in an isolated Python subprocess.
- `call_helper`: optional, executes same-module top-level helper functions discovered from the entrypoint call graph.
- `submit_answer`: ends the episode and scores the submitted payload by exact match.

The runtime API is available as `code2env.runtime.Code2Env` with `reset`, `step`, `evaluate`, and `close`.
