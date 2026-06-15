# task049_samples_valid_helper_trajectories - Task Knowledge

<!-- METADATA:SESSION=0 -->

## Knowledge Entries

1. For task049, trace completeness alone is not enough. Accepted records must
   prove helper-call success and all source tool returns ok, not just
   `entrypoint_after_helpers`.
2. Accepted records must retain nested `subfunction_trace` fields for
   compatibility even if summary/export also flattens flags.
3. If fewer than 5 valid records are found, the blocker breakdown is part of
   the deliverable, not a residual note.
4. The task may use prior Session20 archive extraction and Session24 dependency
   context, but any dependency on coordinator-only paths must be documented in
   the summary.
