STATUS: READY
COMMIT: 21381a061bba7f7d864a11d46f6d05885046fd30
CHANGED: src/daemon.rs; src/daemon/tests.rs
OPEN: none
BLOCKERS: none
---

Three demand checks that expire waiting for local request permits previously opened the shared read breaker without issuing a backend request. A later valid remote hit remained suppressed after all permits were released. The repair stops reporting that local queue error as a backend failure and leaves the existing breaker permit drop behavior intact, including abandoned half-open probes.

The test-only commit `59aecbbd9647ad34a2a85fce5145bf39df3fcac3` fails at the recovery assertion (expected a hit, received a miss). The production fix commit `21381a061bba7f7d864a11d46f6d05885046fd30` makes the same test pass. The test reuses the existing valid entry pack and daemon fixtures; no production helper or test hook was added. The source-backed graph lookup confirmed those existing fixtures.

Validation: the focused regression passed; the actual backend timeout/transient failure control passed; all 39 remote resilience tests passed; the stalled backend restore deadline control passed. Final-tip `just check` exited 0, covering formatting, Clippy, resource guard checks and the full workspace suite. The main binary suite passed 4,382 tests with 14 existing ignores. Logs are `red.log`, `green.log`, `backend-controls.log` and `gate.log`.

Only cost002 is repaired. The measured cost001 request scheduling policy is excluded. The worktree is clean and contains the requested separate test and fix commits.
