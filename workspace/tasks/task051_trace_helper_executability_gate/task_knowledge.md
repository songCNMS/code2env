# task051_trace_helper_executability_gate - Task Knowledge

<!-- METADATA:SESSION=3 -->

## Knowledge Entries

1. Task050 proved that `final_correct=true` plus `helper_trace_complete=true`
   still cannot be accepted when helper source returns fail. Task051 should
   reject or skip such helpers before trace rollout rather than weakening gates.
2. Transitive helper side effects matter for trace helper exposure:
   `get_github_latest_version -> fetch_json -> urllib.request.Request/urlopen`
   must make `get_github_latest_version` non-executable in sandboxed strict
   helper mode even if the direct helper itself has no direct risk flags.
3. The task050 strict env target is
   `code2env.scripts.check-versions.check_language_version.21a74cc9.v1`; its
   before evidence is failed docker/github helper source returns.
4. Acceptance should distinguish three helper sets: candidate semantic helpers,
   sandbox-safe dedicated helpers, and strict executable trace helpers. The
   strict accepted-data path should count only executable helpers toward the
   min-helper threshold.
5. For task050 `scripts.check-versions:check_language_version`, direct-network
   `get_alpine_latest_version` remains sandbox provenance, while the strict
   trace candidate set should focus on the previous three required helpers:
   `get_current_version_from_csv`, `get_docker_latest_version`, and
   `get_github_latest_version`. Docker/GitHub must be rejected as executable
   helpers because they transitively call `fetch_json -> Request/urlopen`; docker
   should also record unavailable `image` and `tag_filter` fixture mappings.
