STATUS: READY
COMMIT: 91132248be1015dd43013328cae3f834a0356ff9
CHANGED: src/daemon.rs; src/daemon/tests.rs
OPEN: none
BLOCKERS: none
---

The packed reader previously extracted and batch-imported every sibling in a selected pack despite the configured per-plan entry limit. The fix reserves slots for admitted candidates, including their v3 fallback, and admits opportunistic siblings only while allowance remains. Already-present/inflight siblings are skipped before spending allowance; zero remains unlimited.

Test-only commit `a0497d10a45fa2bdd6542dacbc7a858c1ced8eed` is deliberately red: limit one produced three committed Store hits. Fix commit `91132248be1015dd43013328cae3f834a0356ff9` passes the same observable Store oracle. The requested key sorts after both siblings, preventing opportunistic entries from displacing it. The fixture also exercises limit two, unlimited mode, and a warm sibling followed by a cold sibling. Existing Store/valid-pack/catalog helpers were reused following the focused graph search (seven budget/claim/Store fixture hits); no new production helper or test hook was added.

The packed-prefetch filter passed seven tests, and corruption and traversal fallback controls both passed. Final-tip `just check` exited 0 with default two Cargo/test threads, normal toolchain HOME/TMPDIR, ambient KACHE_RUNTIME_DIR unset, and the worktree's exclusive COW target. Every workspace check ran; no test was skipped or weakened. Source is clean and only the two specified commits follow baseline `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`.

The first two complete gates failed at the unchanged macOS sandbox-preflight fixture (`tests/fallback_recovery_test.rs:320`). That fixture passed both a targeted Cargo retry and an exact saved workspace-binary control, then passed in the final complete gate. `gate-initial.log`, `gate-second.log`, `gate-retry-control.log`, and `workspace-sandbox-control.log` preserve the evidence. The native probe is best-effort with a 200ms lsof bound, but the logs do not identify which probe returned unknown; the precise intermittent failure cause remains unconfirmed. An attempted one-thread shell command failed before checks started and is retained as `gate-shell-options-error.log`; it is not counted as a gate or behavioral proof.

Original `entry-budget-test.rs`, red/control logs, saved pack proof binary, and other investigation evidence are untouched. This delivery repairs only the packed entry-budget finding; the plan-deadline fix is assigned separately on its own baseline branch. Dispatch was recorded under the coordinator queue lock.
