STATUS: READY
COMMIT: 27525c27865026aa5943a36cb7e32d4dfd1b664b
CHANGED: 5 files
OPEN: 0
BLOCKERS: none
---

Test-only commit: d7f83a05a094c4e9a7c2cb570b0bf6a1092b095e. Production fix commit: 27525c27865026aa5943a36cb7e32d4dfd1b664b. Both branch directly from 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9; no sibling change is included. The owned worktree is clean. The production commit adds four lines to the existing shared dep-info prefix transform and bumps CACHE_KEY_VERSION 32→33. Generated markers now carry a NUL prefix unavailable to real filenames; expansion removes it before compiler-facing dep-info is materialized. Existing ambiguous entries get different cache keys.

The two focused regression tests failed at exact restored-dependency assertions on untouched baseline production source (logs/red.log). After repair, the store suite passed: 570 unit tests, 2 pre-existing ignored; 5 property tests; two one-test integration suites; one isolated telemetry child. The full workspace gate `env CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/restoration-literal-marker/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check` exited 0 at the final tip (logs/gate.log), including formatting, clippy, resource-guard checks and all workspace tests. The legacy-v32 pack test also failed with baseline production, then passed with the precise incompatible-schema error and no published output (logs/schema-red.log and logs/schema-green.log). CI owns mutation testing; no local cargo-mutants run was performed.

The previous full gate (logs/gate-second.log) and its exact sandbox integration retry (logs/fallback-retry.log) failed in an existing denied-server fallback assertion outside this diff. The native policy control passed. A subsequent exact compiled test passed unchanged against both the proven baseline binary and the restored final binary, including denied and allowed assertions (logs/sandbox-exact-baseline-control.json). The final binary bytes were restored in finally and its SHA-256 was rechecked. Standalone lsof and CLI diagnostic results are in logs/sandbox-discovery-diagnostic.json; they do not establish the cause of the intermittent failures. No timeout, oracle or unrelated source change was made. The final full gate result above was obtained after these controls.

The regression oracle preserves literal dependency tokens and environment values exactly while independently relocating actual producer roots to consumer roots. Exact restored text also excludes private NUL bytes. Existing encoded-fixture tests were updated to the new private representation without weakening their compiler-facing behavior assertions. Details are in verification-notes.md. No new helper, abstraction, visibility change, test hook, suppression or unrelated cleanup was introduced. Root independently reviews and publishes; no PR has been pushed by this agent.

Original investigation source, fixtures and red evidence remain unchanged. delivery.json contains the branch, both commits, baseline, commands, logs, changed files and short PR title/body for root publication.
