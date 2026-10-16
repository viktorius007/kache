STATUS: READY
COMMIT: b8d8f0513597f60de190f56395f5317238ff01f2
CHANGED: src/daemon.rs; src/daemon/tests.rs
OPEN: none
BLOCKERS: none
---

The saved delayed-catalog proof was ported into the repository suite without repeating the audit or benchmarks. A valid catalog starts before a one-second dispatch deadline and takes 1.5 seconds to return. The test observes transport admission directly and committed Store availability: no packed or fallback request may start after expiry. Controls cover a fast valid hit, a pack already started before expiry that completes afterward, zero disabling the deadline, and a dispatch already expired before admission.

A second regression occupies every speculative gate permit. A one-second plan must stop waiting before its ten-second restore timeout, with no remote request dispatched. Both tests failed at their behavioral assertions on the pinned baseline: one late request versus zero, and the queued plan still pending at the three-second observation bound. The test-only commit deliberately preserves those reds as requested.

The fix reuses RemoteDeadline to measure admission from the original dispatch. Packed gate and shared request-permit waits use the earlier plan/restore deadline, followed by an explicit admission check. Packed network transfers retain the restore timeout, permitting already-started work to finish. The fallback coordinator keeps the remaining dispatch deadline rather than resetting its allowance after the packed phase. Existing direct-helper controls pass disabled plan deadlines; no new production helper or remote-backend hook was added.

Builds use the assigned private COW target and the coordinator build-slot wrapper. Original proof binaries/evidence and sibling PR targets remain preserved. Only the assigned source/tests and delivery artifacts were modified. Full-gate HOME/TMPDIR retain their normal toolchain values, with ambient KACHE_RUNTIME_DIR unset and CLI fixture isolation retained.

The packed-prefetch suite passed all eight tests, including both new regressions. Existing corrupted-pack fallback, per-entry traversal fallback, and v3 zero-disabled deadline controls also passed. The test-only commit is 7f002434667bef82d4e9b809eeb298acd682523f; the fix commit is b8d8f0513597f60de190f56395f5317238ff01f2. The complete unchanged-tip just check exited 0 through the build-slot wrapper with KACHE_PR_TEST_THREADS=1, including formatting, clippy with warnings denied, and every workspace test. No skip annotations or test exclusions were introduced. The earlier focused test waited behind the coordinator’s exclusive gate and slot-three reservation; no duplicate build was launched.

The branch fix/pack-prefetch-plan-deadline is independently based on 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. The final worktree is clean and contains two commits. Red logs record Cargo exit 101 at each behavioral assertion; green, controls, and final gate each exited 0. No benchmark was rerun and no throughput claim is made.
