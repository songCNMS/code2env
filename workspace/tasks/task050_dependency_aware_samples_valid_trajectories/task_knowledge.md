# task050_dependency_aware_samples_valid_trajectories - Task Knowledge

<!-- METADATA:SESSION=8 -->

## Knowledge Entries

1. Task050 is a data-generation and dependency-aware rerun task, not a quality
   gate relaxation task. Accepted records must meet the same strict predicates
   as task049.
2. The main accepted-data run must not pass `--no-install-deps`; if a worker uses
   no-install mode for a cheap audit, it must be clearly labeled as audit-only
   and not the accepted-data run.
3. If accepted_count stays below 3, the blocker breakdown is an acceptance
   deliverable and must distinguish dependency installation, system dependency,
   package metadata/import path, CLI/stdout envelope, untyped/unsupported
   params, side-effect sandbox, and helper-argument synthesis blockers.
4. Because dependency installation can be expensive and flaky, targeted reruns of
   task049 dependency-likely blockers are preferred before broad full-sample
   runs.
5. The task050 dedicated venv cache path is
   `/home/leisong/codes/work-agents/intern_code2env_lead/outputs/session25_dependency_aware_samples/task050_dependency_aware_samples_valid_trajectories/venv_cache/`.
6. First accepted-data batch must omit `--no-install-deps`; install failures
   should be captured as dependency blockers rather than silently converted into
   weak-oracle accepted records.
7. Lead requires the formal acceptance mailbox before validation/audit can rely
   on worker_1's plan; include PR/head, product-code expectation, first commands,
   venv cache, artifact paths, no-`--no-install-deps` guarantee, and blockers.
8. Before a ready-for-validation report, PR #37 must be synced to latest
   `origin/main` and GitHub must show a clean merge state; lead task-history
   metadata commits can dirty the PR even when product code is unchanged.
9. Empty artifact directories are not evidence for task050 readiness. The owner
   report must include generated JSONL/summary files, dependency manifest or
   equivalent command evidence, focused predicate output, accepted count, and
   blocker breakdown when accepted_count is below 3.
10. For heartbeat reporting, verify the batch PID is still alive and the log path
    has an explicit start marker before reporting option A. An empty log and
    missing manifest from a wrapper that already exited must be reported as a
    failed launch, not as an active accepted-data run.
11. A batch `strict_usable` record is not accepted for task050 until fresh
    trace-mode evidence also proves helper_calls_successful,
    helper_trace_valid, all_source_tool_returns_ok, final_correct, and every
    source helper plus call_entrypoint return `ok=true`.
12. An empty accepted JSONL is valid blocked-data evidence only when paired with
    summary JSON/MD, rollout proof for rejected strict usable candidates,
    focused validator output, no weak-oracle confirmation, and a categorized
    blocker breakdown for accepted_count below 3.
13. Formal handoff must name the exact PR head after metadata pushes; otherwise
    worker_2 cannot validate the intended artifact set against a stable owner
    revision.
14. If the mailbox API returns stored but lead does not see unread mail, resend
    with a new client_message_id and a concise payload under the mailbox content
    limit, then record the delivered message id in task history.
15. After independent validation PASS and lead merge authorization, only
    completion/status metadata should be changed before self-merge; product code
    remains frozen at the validated scope.
