# intern_code2env_dev - personal knowledge base

<!-- METADATA:SESSION=4 -->

---

## Knowledge entries

- code2env repo uses `main` as the default branch even though some playbook examples still mention `master`; use `main` for PR targets and sync commands unless the remote changes.
- The first runnable code2env MVP is dependency-free and uses JSON EnvSpec plus standard-library AST/subprocess/runtime components.
- Generated env packages should copy filtered source into `source/` and add both `source` and `source/src` to Python import paths to support common package layouts.
- Initial scoring path uses exact match against the pinned source function output as the golden answer.
- Kimi endpoint config is available in this environment at `/work-agents/endpoints.txt`; do not commit endpoint secrets, and prefer redacted provenance in generated JSONL summaries.
- Targeted selection improves candidate quality by excluding static risk flags before LLM review; `requires_instance` and `possible_side_effect` were useful first filters for requests/rich.
- Materializing EnvSpec drafts with explicit JSON fixtures before build gives a clean checkpoint: fixture, golden answer, and runtime smoke failures can be debugged separately.
- Some otherwise good candidates need non-JSON fixture adapters; Flask `find_app_by_string` requires a Python `ModuleType` with an app or factory, so it should not be forced through JSON-only args.
