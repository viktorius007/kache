STATUS: DONE
COMMIT: e8df9b2a6e6165de82592d73c711ddf1219c768f
CHANGED: 2 files
OPEN: 0
BLOCKERS: none
---
Test commit: f7ac6de9daa755c03da05996e4120f689ed35213 (deliberately red, separately requested).
Fix commit: e8df9b2a6e6165de82592d73c711ddf1219c768f.
Independent untouched production baseline: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. E1 source and original artifacts remain at their separately tested tip; only this agent's private target is reused sequentially. Queue dispatch was recorded before execution.

The saved concurrent hydration proof is ported to `concurrent_bulk_sync_clients_hydrate_shared_store_without_errors`. Clean valid-pack and already-committed pulls each commit all 24 entries; then three fresh node-local stores each receive four barrier-started real CLI processes with distinct runtime directories. Every command must exit successfully and each store must have all 24 committed entries. Before repair, the first trial fails at the exit-status assertion after native import move, missing-file and file-size-mismatch errors (red.log). Production is unchanged for that red. After repair, all twelve overlapping commands and both controls pass (green.log). Native extraction, integrity validation and import are exercised; no mock replaces this seam.

The production fix holds the existing cross-process StoreLock for the cache through bulk sync planning, extraction and import. Another CLI sync therefore cannot replace or consume the same extracted files before import completes. Waiting happens before the current-thread async runtime starts. The persisted lock file and release reuse the existing OS-lock RAII guard; waiting processes must subsequently acquire and finish, covering release between clients.

Size/Existence/Shape/Comments: no new production function, type, dependency or abstraction; the existing public StoreLock is reused. The fix adds eight lines to sync plus its import, and the 93-line regression is under the 100-line test ceiling. Its comment states why the critical section is necessary. Only src/cli.rs and tests/filesystem_remote_test.rs change.

Tradeoff and scope: overlapping bulk sync commands against one local cache serialize, including push-only/dry-run commands; per-command transfer concurrency and separate caches retain their existing concurrency. This fixes the confirmed concurrent CLI bulk-sync trigger. It does not claim native daemon publication coordination, which does not take this CLI lock. The E1 directory-existence repair is not bundled here.

Final full `just check` exited 0 at unchanged e8df9b2a6e6165de82592d73c711ddf1219c768f. It includes the new concurrent regression, all filesystem remote controls and the unchanged native sandbox fixture. The log records 5,892 passed, 0 failed and 16 existing ignored tests across 76 targets. Coordinator build-slot reserved all three full-gate slots while root held the focused slot. The driver retained normal toolchain HOME/TMPDIR, isolated Kache config/cache and per-CLI fixtures, baseline profile environment, one libtest thread and this agent's private target. No warmup, oracle edits or skips were added. The worktree is clean. Root was notified immediately to resume held workers.

Earlier gates stopped on the unchanged macOS fallback sandbox fixture. Temporary adapter diagnostics confirmed its lsof lookup exceeded the existing 200ms deadline; the patch/trace were saved then reverted to exact HEAD. Global temporary HOME/TMPDIR overrides were corrected per coordinator controls; intermittent lookup timing persisted under load, including with the exact workspace test artifact. A coordinator-managed quiet full gate passed without source changes. Detailed failed logs, controls and environmental diagnosis remain in gate-environment.md; final reservation command/env/exactSHA and result are in exclusive-gate.txt.

Author verification is complete. No local mutation run; CI owns that gate. Root owns independent review, draft publication and CI follow-up. Original investigation proofs remain preserved.
