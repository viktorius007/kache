STATUS: DONE
COMMIT: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
CHANGED: 18 files
OPEN: 1
BLOCKERS: none
CONFIRMED: 1
LIMITS: Controlled handler/pipeline probes, not whole-Cargo throughput; real remote transport and ordinary writer-contention frequency unmeasured; Rust graph coverage partial and source-corroborated.
---

D5 remains confirmed as a condition-specific responsiveness defect. The new evidence extends reachability beyond a one-worker runtime: on a two-worker runtime, concurrent successful uploads can sweep the main store and one configured volume shard under independent GC locks, starving unrelated health work until real SQLite writers release. Multiple worktrees sharing one store do not, by themselves, produce additional full sweeps. The tested sixteen-worker pipelines stayed responsive. This is not a diagnosis of ordinary multi-worktree Cargo slowdown.

The investigation is complete; the defect is open for owner approval. No repair, installed-daemon/config/cache change, commit, issue, PR, or publication occurred. All prior experimental source/evidence was preserved. The new module lives only in investigation/multi_upload_gc.rs; its temporary registration was removed from src/daemon/tests.rs, restoring that file to its pre-dispatch state (the prior two-line post_upload_gc registration remains).

## Executed evidence

During the coordinator-granted quiet window, the already-built debug test binary ran four commands, without compilation. Raw commands, exit codes and durations are in [pipeline-executions.json](pipeline-executions.json).

- `measure_pipeline_gc_capacity --ignored --nocapture --test-threads=1`: PASS, 1 passed, 0 failed; 18 samples, 32 durable uploads each; 35.705 s including fixture setup.
- `two_async_workers_allow_health_while_main_and_shard_sweeps_wait_for_writers`: expected FAIL, 0 passed, 1 failed; health delayed **707.526 ms**, completing after writer release. [Red log](pipeline-red.log).
- `two_async_workers_allow_health_while_one_store_sweep_waits_for_a_writer`: PASS, 1 passed, 0 failed. This fixture discriminator removes the volume shard, keeping two runtime workers and 16 upload tasks. [Control log](pipeline-control.log).
- Original `a_post_upload_gc_sweep_allows_health_requests_while_a_writer_is_busy`: expected FAIL replayed, 0 passed, 1 failed; **1272.3 ms** health delay. [Replay log](baseline-red-replay.log). Prior optimized evidence remains untouched in verification.md and release-*.log/json.

Measurements use real Store/SQLite transactions, real durable upload-intent persistence and retirement, actual production `next_upload_job`/`run_upload_job`/`do_upload`, real eviction, and the actual health handler. The repository in-memory backend replaces only remote network transport. No GC/database operation is mocked. A separate thread supplies pre-persisted jobs to the bounded channel, as the worker side of startup replay; the server socket, full enqueue-buffer task and compiler process are not exercised. Setup is excluded from health latency. Main plus shard here means two separate indexed stores on the same host filesystem; a second physical volume is unnecessary for independent locks.

Each sample first lets one upload enter main-store GC. Peer jobs then run; for two-store samples the probe waits for a peer to enter shard GC too. Actual SQLite `BEGIN IMMEDIATE` writers remain held during the 400 ms observation window following health scheduling. All writers release before assertions/cleanup. Every sample ultimately completes all 32 jobs successfully, retires their durable intents, evicts the pressured-store victims and records GC results. The health handler touches no store DB, so health delay is executor starvation rather than its own SQLite lock wait.

| Async workers | Upload tasks | Pressured stores | Health before writer release | Median health latency (ms) | Range (ms) | Peer jobs finished before release, of 31 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 1 | 0/3 | 645.419 | 638.120–666.620 | 0 |
| 2 | 1 | 1 | 3/3 | 0.034 | 0.022–0.037 | 0 |
| 2 | 16 | 1 | 3/3 | 0.035 | 0.033–0.035 | 21–31 |
| 16 | 16 | 1 | 3/3 | 0.022 | 0.022–0.024 | 31 |
| 2 | 16 | 2 | 0/3 | 708.019 | 685.506–718.127 | 0 |
| 16 | 16 | 2 | 3/3 | 0.025 | 0.018–0.037 | 30 |

[Raw observations](pipeline-measurements.log), [structured summary](pipeline-summary.json), and [summary script](summarize-pipeline.py). These debug results establish ordering/progress and workload-specific observed latency. The artificially held writers do not estimate ordinary build contention frequency; three samples are not a general performance characterization. The 21–31 peer range is retained, not rounded into a claim that every peer always finishes in the window. The separate control's exact 31-peer assertion passed once and is a measurement-specific assertion, not a recommended future performance gate.

## Realistic scope and severity drivers

A real successful PUT is required; remote-disabled, readonly, suppressed, failed and remote-already-present branches do not reach the call. `do_upload` calls inline pressure GC at src/daemon.rs:4344. The equivalent GC-hint path uses the blocking pool (6718–6725). Production runs `max(s3_concurrency,1)` background upload tasks (7384–7437), defaulting to 16 (src/config.rs:1815–1827), independently of Tokio's async worker count. The daemon uses Tokio's default runtime count (src/daemon.rs:7224–7227). A constrained core allocation or `TOKIO_WORKER_THREADS` override is reachable; see [Tokio Builder documentation](https://docs.rs/tokio/latest/tokio/runtime/struct.Builder.html#method.worker_threads).

A store's full sweep holds its GC lock and releases the daemon Store mutex before eviction. Another upload skips that store's held lock. With shards, the next upload can skip main GC and enter a shard sweep under another lock. The observed two-store/two-worker failure is therefore not the previously assumed daemon-wide one-sweep limit: the limit is per store. It still does not prove that two stores exhaust an idle sixteen-worker daemon. Synchronous preliminary store opens/filesystem work elsewhere are outside the exclusive-lock bound.

Inline GC also occupies a background upload task until completion. With one configured upload task and two async workers, health progressed but none of the 31 peer uploads completed before writer release. With 16 upload tasks, peers progressed while one or two upload tasks swept. This proves an upload-queue occupancy cost under these settings, without converting it into a Cargo makespan claim.

Rust wrapper publication synchronously persists a durable intent before its fire-and-forget socket request (src/wrapper.rs:4952 → src/wrapper/remote.rs:27 → src/daemon.rs:8853). That persistence takes the same GC lock (724–778). Thus a later compile can wait on an active sweep even after an offloading fix; this is a separate durability-lock cost. The daemon enqueue response does not wait for that job's remote PUT or post-upload maintenance (4045–4047). No end-to-end Cargo benchmark was performed.

Operational impact is delayed health/lifecycle and other runnable async work under constrained/exhausted executor capacity, plus reduced upload-slot availability. Remote publication succeeded and all fixture jobs/victims completed correctly; no data-loss or cache-corruption claim is admitted. The prior report found no remote configured in the checked user setup; this run did not refresh real user config, and does not present D5 as the cause of current local-only builds.

## Fix design for later approval

Reuse the existing coalesced GC-hint scheduler after successful PUT/key-presence publication/intent retirement. Post-upload GC should request the same blocking-pool sweep, sharing the pending claim and unwind-safe release, rather than enqueueing an independent sweep per upload. Keep the sweep's cross-process per-store locks, pressure trigger, backoff, disk-recovery checks and reporting. Give the async upload chain Arc-capable receivers so the task owns the daemon lifetime; mechanically adapt direct test callers. This avoids duplicating the eviction algorithm or constructing another daemon just for GC.

That design lets an upload task finish while opportunistic maintenance runs separately. The existing one-worker regression and the new two-worker/two-store regression should both become green, with eventual eviction/reporting observed separately. Check overlap coalescing and later-hint admission, startup replay, durable retirement and shutdown. A bare `block_in_place` is less suitable because it still occupies the upload task and panics on current-thread runtimes; [Tokio 1.53.1 documentation](https://docs.rs/tokio/1.53.1/tokio/task/fn.block_in_place.html). Running blocking tasks cannot be aborted; retain the daemon's existing bounded runtime shutdown behavior ([spawn_blocking documentation](https://docs.rs/tokio/1.53.1/tokio/task/fn.spawn_blocking.html), src/daemon.rs:7231–7242). No fix was implemented or red-to-green repair claim made.

[Full reachability and fix notes](scope-and-fix-design.md).

## Proof, coverage and reproduction

The red oracle is writer-release ordering for an independent health response, not a speed threshold, source spelling, or log count. Actual upload success, durable retirement, victim eviction and GC recording prevent missing-remote/skipped-sweep/error-path vacuity. The discriminator changes only fixture store count: two workers/two stores fails; two workers/one store passes. Original one-worker proof was replayed on unchanged baseline production code. The proposed module is report-only; the old regression remains exactly as supplied by the coordinator.

Run from this worktree:

```sh
python3 investigation/replay-pipeline.py red      # expected exit 101 on baseline
python3 investigation/replay-pipeline.py control  # observed exit 0
python3 investigation/replay-pipeline.py measure  # ignored measurement, observed exit 0
python3 investigation/summarize-pipeline.py
```

The replay script verifies the pinned SHA and an unchanged production scope, temporarily registers the report-only test module, clears compiler wrappers, uses clang, bounds Cargo jobs to two, then removes its own registration. The final production scope hashes equal baseline: [production-source-check.json](production-source-check.json). Debug target reuse compiled only the test crate in 1m20s; existing caches were approximately 2.4 GiB debug and 905 MiB release before this run. No new dependency/baseline build was needed. Rebuilding from no cache requires that normal repository build footprint; logs and source remain in the worktree.

Structural exploration used codebase-memory project `Users-viktor-Developer-github-kache-investigations-coordinator`, indexed at the pinned baseline. Positive trace: `do_upload` → `maybe_evict_after_upload`, with inbound production roots `handle_upload` and `run_upload_job`. Rust semantic coverage is partial (binding oracle, expanded calls and implementation relationships unavailable), so relevant wiring/source was checked directly. No exhaustive graph-only absence claim is made. [Graph status](graph-status.log), [trace](graph-trace.log), [coverage](graph-coverage.log), [bounded ledger](coverage-ledger.json).

Scope reviewed: successful upload and terminal early returns; actual worker receiver/replay scheduling; main/shard pressure driver and GC-lock lifetimes; shared pressure/backoff/disk-recovery dispatch; wrapper durable publication; shutdown behavior relevant to offloading. Cleared/dismissed in findings.json: automatic starvation from many worktrees sharing one store; inference of ordinary sixteen-worker Cargo throughput loss; D5 as a demonstrated local-only cause; offloading eliminating all compiler/GC lock wait. Reopen conditions are recorded. Whole daemon/store integrity, real remote saturation (#327), crash recovery correctness, real service latency, large realistic artifact mixes and whole-Cargo makespan are outside this focused investigation.

Production-code shape checks have no new production diff. No commit gate/mutation coverage claim is made; no local cargo-mutants was run, as AGENTS.md assigns it to CI. The only observed failing tests are expected defect proofs. The machine-readable contract contains one admitted open finding with full source and red output, plus four evidence-backed dismissals: [findings.json](findings.json).
