STATUS: DONE
COMMIT: 9e469c9a6e319339c9a3146461a2fcfc2e12c8f4
CHANGED: 3 files
OPEN: CI mutation testing and independent root review
BLOCKERS: none
---

`handle_remote_check_started_at` now scopes the existing singleflight coordinator to the validated expected entry directory. A same-key hit includes publication into the requesting store, so another configured store runs its own import instead of receiving the first store's answer. Equivalent requests for the same store still coalesce. The bounded coordinator, inner download guard, request deadlines and import path are retained.

The deliberately red test-only commit is `4a1a2994b86eb43d114cafe74608d17323f95b76`; the production fix commit is `9e469c9a6e319339c9a3146461a2fcfc2e12c8f4`. Both start from `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Only `src/daemon.rs`, `src/daemon/tests.rs` and `src/remote_resilience.rs` changed, and the worktree is clean. [delivery.json](delivery.json) carries exact commit, body and gate references for root publication.

| Criterion | Executed proof |
| --- | --- |
| Each same-key remote hit must commit to its own requested store | [red.log](red.log): hit responses occurred but the follower store had no committed row; the named assertion failed on unchanged production, 0 passed/1 failed |
| Main and shard destinations publish regardless of leader order | [green.log](green.log): the new two-store regression passed both orders and checked committed rows plus exact fixture artifact bytes |
| Same-store singleflight survives equivalent wire requests | [green.log](green.log): the strengthened one-GET coalescing control passed with explicit main shard_dir and a dot-component entry-directory alias |
| Direct restore without remote listing remains correct | [green.log](green.log): existing unknown/positive/stale-miss knowledge controls passed |
| Full local gate at fixed tip | [gate.log](gate.log): `CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check` exited 0 at `9e469c9a6e319339c9a3146461a2fcfc2e12c8f4` |

The targeted direct-restore suite passed all 3 tests. Full workspace summaries are in [gate-summary.txt](gate-summary.txt). The final gate includes workspace/fuzz formatting, workspace/all-targets clippy with warnings denied, test-resource guard checks and workspace tests. The bounded build wrapper used two Cargo/test threads and an exclusive private target. CI owns mutation testing; no local mutants invocation or publication occurred.

[oracle-notes.md](oracle-notes.md) records overlap, independent expectations, alias controls and reuse searches. The existing network double blocks a real in-flight GET; production validation, singleflight, download joining, extraction and Store publication remain exercised. The readiness handshake and one follower poll make the overlap deterministic. Store rows and exact artifact bytes establish the publication contract independently of response booleans, meta.json files or GET counts. Fixtures introduce no process-global state, live cloud calls, host configuration or new production visibility.

The saved original [cross-shard-singleflight.case.json](../../cross-shard-singleflight.case.json), [probe_remote_validation.py](../../probe_remote_validation.py), concurrent/reverse/socket execution transcripts and sequential/same-store controls remain unchanged. They proved the false hit through real socket requests, including reversed leadership. This delivery reused that evidence without repeating the audit. Fixture setup corrections are preserved in [fixture-compile-error.log](fixture-compile-error.log) and [fixture-artifact-path-error.log](fixture-artifact-path-error.log); neither is counted as the behavioral red proof.

Shape review: graph search found existing direct-restore tests and backend helpers and they are reused. No new production function, type, trait, variant, module or duplicate validator is introduced. The production diff changes the coordinator key from String to native PathBuf with a borrowed Path claim parameter, adapts its existing primitive tests mechanically, and passes the validated destination without lossy conversion. It documents the publication invariant; no unrelated refactor. The new regression remains below 100 lines inside the existing private test module. Path validation precedes the claim, so identity is based on the daemon's destination rather than raw wire spelling. Windows execution and mutation discrimination remain CI responsibilities. The first full gate failed in the unchanged macOS sandbox-preflight fixture; the focused test passed and the required full gate was rerun without source changes. [gate-attempt1.log](gate-attempt1.log), [sandbox-focused.log](sandbox-focused.log) and [gate-diagnostics.md](gate-diagnostics.md) preserve the failure and the unconfirmed precise cause. Root's independent review and CI lanes remain required before landing.
