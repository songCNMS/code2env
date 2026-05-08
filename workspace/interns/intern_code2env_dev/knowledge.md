# intern_code2env_dev - personal knowledge base

<!-- METADATA:SESSION=2 -->

---

## Knowledge entries

- code2env repo uses `main` as the default branch even though some playbook examples still mention `master`; use `main` for PR targets and sync commands unless the remote changes.
- The first runnable code2env MVP is dependency-free and uses JSON EnvSpec plus standard-library AST/subprocess/runtime components.
- Generated env packages should copy filtered source into `source/` and add both `source` and `source/src` to Python import paths to support common package layouts.
- Initial scoring path uses exact match against the pinned source function output as the golden answer.
