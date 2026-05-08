# task004_fixture_golden_envpackage_smoke Knowledge

<!-- METADATA:SESSION=1 -->

## Writing Rule

Record durable task-specific decisions, constraints, and implementation notes here. Keep entries concise and update when new information would help future sessions.

## Entries

- Input EnvSpec drafts are expected under `/work-agents/intern_code2env_dev/outputs/task003_targeted_selection/env_specs/`.
- Flask `find_app_by_string` likely needs non-JSON module/app fixtures or an adapter before it can run in the current JSON-only runtime.
- `materialize_env_spec` fills `fixture` and optionally computes `golden_answer` through `run_symbol_subprocess` with network and subprocess calls disabled.
- The passing task004 JSON fixtures are:
  - `requests.auth:_basic_auth_str`: `{"args": ["user", "pass"], "kwargs": {}}`
  - `requests.models:RequestEncodingMixin._encode_params`: `{"args": [{"q": "hello world", "tag": ["a", "b"]}], "kwargs": {}}`
  - `rich._wrap:divide_line`: `{"args": ["hello world", 5], "kwargs": {}}`
  - `rich.pretty:traverse`: `{"args": [[1, {"a": 2}]], "kwargs": {}}`
- `flask.cli:find_app_by_string` is blocked because it requires a Python `ModuleType` containing a Flask app or factory; this needs an adapter fixture type beyond JSON args.
- Fixture smoke report is `/work-agents/intern_code2env_dev/outputs/task004_fixture_smoke/fixture_smoke_report.md`; machine-readable report is `/work-agents/intern_code2env_dev/outputs/task004_fixture_smoke/fixture_smoke_report.json`.
