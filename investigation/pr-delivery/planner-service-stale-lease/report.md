STATUS: DONE
COMMIT: f58c9ed2fee7338a6a1af9e53ef13152d1dd37ae
CHANGED: 2 files
OPEN: CI mutation testing and independent root review
BLOCKERS: none
---

`lease_covers` now requires an exclusively held marker lock in this scheduler's canonical test directory. The existing `slot_is_held` probe supplies the native lock observation. An inherited path from an exited test owner therefore takes ordinary admission after its marker and slots are released. Missing or unprobeable markers also take ordinary admission. Active leases retain nested test and compiler reuse; scheduling limits and the lease format are unchanged.

The deliberately red test-only commit is `3a17e158873fbe875e7e348adff989e01d4f3b9d`; the production fix commit is `f58c9ed2fee7338a6a1af9e53ef13152d1dd37ae`. Both start from `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Only `src/scheduler.rs` and `src/test_runner.rs` changed, and the worktree is clean. [delivery.json](delivery.json) carries exact commits, body and gate references; [dispatch.json](dispatch.json) records the author handoff from the unavailable original investigator.

| Criterion | Executed proof |
| --- | --- |
| Admission resumes after the inherited lease owner exits | [red.log](red.log): after live-owner controls and independent proof of marker release, the stale keyless request held zero slots where one was required; named assertion failed on untouched production |
| Preserve live nested reuse | [green.log](green.log): real child-held lease keeps two slots while parent keyed/keyless requests add none and runner planning is Exec |
| Restore each consumer's admission | [green.log](green.log): stale keyless and keyed guards each hold one real permit; runner planning is exactly Schedule with Fixed(1) |
| Preserve scheduler directory and symlink boundaries | [green.log](green.log): existing path controls now use actually held marker locks and continue to pass |
| Preserve admitted limits and ordinary runner plans | [green.log](green.log): scheduler and test-runner unit suites pass; [gate.log](gate.log) includes existing nested CLI integration and bounded-pool controls |
| Full gate at fixed tip | [gate.log](gate.log): `CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/qa-remote-binding/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check` exited 0 at `f58c9ed2fee7338a6a1af9e53ef13152d1dd37ae` |

Targeted suite summaries: `test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4396 filtered out; finished in 0.01s
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4396 filtered out; finished in 0.31s
test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 4396 filtered out; finished in 0.22s
test result: ok. 85 passed; 0 failed; 4 ignored; 0 measured; 4308 filtered out; finished in 0.90s
test result: ok. 16 passed; 0 failed; 0 ignored; 0 measured; 4381 filtered out; finished in 0.00s`. Full workspace test summaries are in [gate-summary.txt](gate-summary.txt). The final gate includes workspace/fuzz formatting, workspace/all-targets clippy with warnings denied, test-resource guard checks and workspace tests. The build wrapper used an exclusive private target and two Cargo/test threads. CI owns mutation testing; no local mutants invocation or publication occurred.

[oracle-notes.md](oracle-notes.md) records independent expectations, the real process/OS-lock seam, live observations saved before owner exit, and cleanup. The ignored fixture is explicitly selected and runs under the ordinary regression on every platform; the regular test uses a fixed pool and avoids host-CPU skip conditions. New tests share no process-global state, live cloud, host config, new production visibility or mutable live cache. The owner has exited and all slots are independently free before stale assertions, so the red test leaves no helper running.

The original [stale-lease-replay.json](../../stale-lease-replay.json), [stale_lease_red.json](../../stale_lease_red.json), [stale_lease_control.json](../../stale_lease_control.json) and [stale_test_lease.py](../../probes/stale_test_lease.py) remain unchanged. They proved the bypass through the real baseline CLI test-runner; this delivery ports that process-lifetime behavior to the existing scheduler/runner seams without repeating the audit.

Shape review: graph queries found existing slot_is_held and process fixture helpers, which are reused. The repair adds no production function, type, trait, variant, module or duplicate validator and makes no unrelated lease redesign. The existing lease predicate stays below 100 lines; the new regular regression is 83 lines. Existing tests that previously named unlocked/nonexistent markers now acquire marker locks to establish their live-lease premise, retaining their original outcome assertions. Root's independent review, cross-platform execution and CI mutation lanes remain required before landing.
