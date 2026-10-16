# Outstanding Kache findings

The complete current tracker is [Kache issue tracker](/Users/viktor/Developer/github/kache-investigations/coordinator/investigation/issue-tracker.md). It marks every audited item as a confirmed bug, measured cost, external tool gap or unproven lead.

Verified on 2026-10-11 against upstream main `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`.

## D5: Post-upload garbage collection blocks an async worker

Status: **Confirmed bug — fix. Medium impact.** Unresolved; no dedicated upstream issue has been filed. The runtime conditions describe exposure, not uncertainty about the demonstrated bug.

After a successful remote upload, `Daemon::do_upload` calls `self.maybe_evict_after_upload()` synchronously (`src/daemon.rs:4344`). Its call to `sweep_under_size_pressure` (`src/daemon.rs:6689–6690`) runs filesystem and database work on an async worker. The existing GC-hint path offloads the same sweep with `spawn_blocking` (`src/daemon.rs:6718–6722`).

### Measured impact

Optimized upstream release profile, real SQLite/store/eviction and upload/health handlers, repository in-memory remote transport. The probe measures handler scheduling and execution, rather than full builds or network round trips.

| Workload | Async workers | Median health latency: upload sweep | Median health latency: offloaded hint sweep |
|---|---:|---:|---:|
| SQLite writer held for 250 ms (5 samples per path) | 1 | 468.692 ms | 0.008 ms |
| Same writer workload | 2 | 0.011 ms | 0.009 ms |
| Same writer workload | 16 | 0.007 ms | 0.008 ms |
| 200 reclaimable entries, no held writer (3 samples per path) | 1 | 290.773 ms | 0.021 ms |
| Same uncontended workload | 2 | 0.026 ms | 0.020 ms |
| Same uncontended workload | 16 | 0.022 ms | 0.029 ms |

The regression requires unrelated health work to finish before a held SQLite writer is released. It fails on unchanged upstream code: 1228.1 ms health latency in the optimized build. Changing only the fixture to two workers passes in the debug build. This demonstrates starvation of a constrained executor without requiring one particular fix API. Successful upload and actual eviction are also asserted.

A one-worker runtime is reachable through Tokio's available-parallelism default or `TOKIO_WORKER_THREADS=1`. Spare workers mask the health delay in these measurements. Each store permits only one pressure sweep under its GC lock, so this does not prove that multiple worktrees alone exhaust a normal multiworker daemon. Upload completion itself also waits for inline GC; whole-build throughput was not measured.

No remote configuration was found in this machine's checked user/system/launchd configuration, so this is not an established cause of slowdowns in current local-only builds. Negative results in spare-worker workloads do not refute the observed single-worker defect.

### Reproduction and evidence

[Verification report](verification.md), [test-only patch](regression.patch), [optimized measurements](release-measurements.log), and [summary data](release-summary.json).

The main clone remains clean and equal to the checked upstream main. Test additions remain isolated in `/Users/viktor/Developer/github/kache-d5-investigation`; no production fix or installed-binary update was made. The regression is deliberately failing until a fix satisfies the progress requirement.
