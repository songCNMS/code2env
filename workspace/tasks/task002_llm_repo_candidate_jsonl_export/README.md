# task002_llm_repo_candidate_jsonl_export

<!-- METADATA:STATUS=Completed,ASSIGNEE=intern_code2env_dev -->

## Background

code2env already has a runnable MVP that can scan Python repositories and rank function candidates with static analysis. The next requirement is to use a specified LLM endpoint to further screen candidate files/functions according to the PRD and generate task-oriented descriptions suitable for environment construction.

## Goals

- Add a CLI flow that accepts a repository and exports a JSONL file of selected function candidates.
- Use static analysis to gather candidate file paths, function locations, signatures, metrics, and source snippets.
- Call a specified LLM model to decide whether each candidate is suitable and to generate a concrete task-style description.
- Support Kimi or other endpoint-configured models for debugging through the local endpoint configuration.

## Acceptance

- A command can run on a local repo and write JSONL records containing file path, function symbol, line range, static metrics, LLM suitability decision, task description, tool suggestions, and provenance.
- The LLM client reads endpoint configuration from a local file or environment variables without committing secrets.
- The command supports a deterministic mock/offline mode for tests.
- Tests cover JSONL generation, LLM response parsing, fallback behavior, and CLI execution.
