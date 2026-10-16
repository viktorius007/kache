# D5 verification: inline post-upload GC

Verified 2026-10-11 against upstream main `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9` on macOS/arm64.

The post-upload sweep still runs synchronously on an async runtime worker. A reachable single-worker fixture demonstrates delayed unrelated health work. Spare workers mask the responsiveness effect in the tested workloads. No whole-build throughput claim is made.

## Source and reachability

`Daemon::do_upload` calls `maybe_evict_after_upload` after a successful remote PUT (`src/daemon.rs:4344`). The helper calls `sweep_under_size_pressure` synchronously (`src/daemon.rs:6689–6690`). `handle_gc_hint` schedules that same sweep through `spawn_blocking` (`src/daemon.rs:6718–6722`). The production runtime uses Tokio's default worker count (`src/daemon.rs:7224–7227`), which follows available parallelism or `TOKIO_WORKER_THREADS`. One worker is therefore a reachable configuration, not an impossible future caller.

The codebase-memory index and positive inbound trace located the upload call. Rust semantic coverage is partial, so source was checked directly.

## Probe design

The isolated worktree is `/Users/viktor/Developer/github/kache-d5-investigation`. Only tests were added; production source is unchanged. The main clone and installed daemon were not modified.

The fixture uses the real Store, real SQLite transactions, real eviction, real upload handler and real health handler. Only remote transport uses the repository's in-memory backend; no GC or database work is mocked. The health handler avoids the store database, distinguishing executor starvation from normal database contention.

Controlled workload: one idle 200-byte entry over a 100-byte budget; hold an actual SQLite `BEGIN IMMEDIATE` writer for 250 ms after observing GC's initialized lock file. Schedule health on the same async runtime. Five samples per path/worker count.

Uncontended workload: 200 distinct idle 200-byte entries over the same budget, with no held writer or injected delay. Three samples per path/worker count. The small byte budget forces a sweep; entry count drives filesystem/database work. Setup is excluded from latency measurements.

Control path: the existing GC-hint handler, which offloads the identical pressure sweep. This is an existing production scheduling path, not an implementation of a proposed upload fix.

Measurements are handler scheduling plus execution latency, not socket round-trip latency or end-to-end compiler build time. Tiny, idle, reclaimable entries model metadata-heavy GC, not a large realistic compiler-artifact mix.

## Optimized measurements

Upstream release profile, sequential measurement tests; 48 samples total. Health latency is measured from scheduling unrelated health work after GC enters.

| Workload | Async workers | Path | Samples | Median health latency (ms) | Range (ms) | Median request duration (ms) |
|---|---:|---|---:|---:|---:|---:|
| uncontended_200_entries | 1 | hint | 3 | 0.021 | 0.018–0.023 | 0.075 |
| uncontended_200_entries | 1 | upload | 3 | 290.773 | 274.623–527.049 | 292.437 |
| uncontended_200_entries | 2 | hint | 3 | 0.020 | 0.018–0.033 | 0.065 |
| uncontended_200_entries | 2 | upload | 3 | 0.026 | 0.025–0.027 | 1603.970 |
| uncontended_200_entries | 16 | hint | 3 | 0.029 | 0.025–0.327 | 0.038 |
| uncontended_200_entries | 16 | upload | 3 | 0.022 | 0.021–0.022 | 303.541 |
| writer_250ms | 1 | hint | 5 | 0.008 | 0.007–0.012 | 0.030 |
| writer_250ms | 1 | upload | 5 | 468.692 | 454.636–481.220 | 470.216 |
| writer_250ms | 2 | hint | 5 | 0.009 | 0.007–0.010 | 0.028 |
| writer_250ms | 2 | upload | 5 | 0.011 | 0.007–0.013 | 467.223 |
| writer_250ms | 16 | hint | 5 | 0.008 | 0.007–0.014 | 0.024 |
| writer_250ms | 16 | upload | 5 | 0.007 | 0.006–0.011 | 467.933 |

For the 250 ms writer workload, one-worker upload health completed before writer release in 0/5 samples; the offloaded hint control did so in 5/5. Both paths did so in all two- and sixteen-worker samples. The natural workload uses no held writer.

The upload request itself also waits for inline GC, even with spare workers. This fixture measured its completion, but does not establish end-to-end Cargo throughput impact or an equivalent upload-vs-hint request comparison: those handlers have different response contracts.

Optimized regression execution also failed as expected: 0 passed, 1 failed, health latency 1228.1 ms. The two optimized measurement tests passed (48 samples), and the existing upload/eviction baseline passed. No production fix has been applied.

## Regression proof

Proposed behavior: unrelated async health work must progress while post-upload GC waits for a cache writer.

`a_post_upload_gc_sweep_allows_health_requests_while_a_writer_is_busy` holds a real writer for one second, schedules the actual upload, then schedules health after GC has entered. It asserts health completion before the writer is released, plus successful upload, actual victim eviction and GC reporting. The one-second timeout bounds the test; the key assertion is ordering relative to writer release, not a speed threshold or source spelling.

Final one-worker fixture on unchanged upstream production code: FAIL, health delayed 1230.6 ms. Varying only the fixture to two workers: PASS (1 passed, 0 failed). The one-worker fixture was restored and failed again. A mechanism such as offloading GC or allowing Tokio to replace a blocking worker can satisfy the assertion; the test does not require one exact API.

The regression is deliberately left failing in the isolated worktree because this task verifies a defect; it does not implement a production fix. The patch applies cleanly to the updated main clone and passes rustfmt checking.

## Coverage and oracle reasoning

Executed suite search: `upload.*(respons|progress|async|stall)|post.upload|maybe_evict_after_upload|runtime.*(block|respons)` in `src/daemon/tests.rs` and `tests/**/*.rs`.

Nearest GC test: `test_upload_triggered_eviction_respects_gc_lock` (`src/daemon/tests.rs:3110`) proves eviction skips an already-held GC lock and evicts after release, but never drives an async upload or observes another task's progress. `a_slow_upload_retirement_flush_does_not_block_other_uploads` (`src/daemon/tests.rs:14202`) covers a separate spool flush path, not post-upload GC.

Audience: remote-cache clients with constrained or exhausted async capacity. Failure cost: health/lifecycle responses and other runnable async work wait for synchronous GC. The small regression a future fix should catch is putting the sweep back inline in the upload handler.

Target: successful upload under due size pressure. Boundaries, backoff and already-held GC-lock behavior remain covered by existing tests. Concurrent writer timing is the actor that exposes this target. Store and upload success assertions establish reachability; releasing the writer before assertions prevents cleanup deadlock. Error upload branches are outside this focused target.

There is no vacuous success from a missing remote, skipped sweep or failed upload: those fail fixture assertions. The independent health response and writer-release ordering are the oracle; expectations are not derived from the implementation. Actual red-first execution is recorded; no production hand-mutation was used.

## Artifacts

- Test and measurement module: `/Users/viktor/Developer/github/kache-d5-investigation/src/daemon/tests/post_upload_gc.rs`
- Applyable patch: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/regression.patch`
- Red-first/final failure log: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/regression.log`
- Two-worker discriminator log: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/discriminator.log`
- Preliminary debug measurement log: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/debug-measurements.log`
- Optimized regression log: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/release-regression.log`
- Optimized summary: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/release-summary.json`
- Optimized measurement log: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/release-measurements.log`
- Summary script: `/Users/viktor/Developer/github/kache-d5-investigation/investigation/summarize.py`

Reproduce with compiler caching disabled and a temporary target directory:

```sh
cd /Users/viktor/Developer/github/kache-d5-investigation
RUSTC_WRAPPER= CARGO_TARGET_DIR=/private/tmp/kache-d5-target cargo test --locked --bin kache a_post_upload_gc_sweep_allows_health_requests_while_a_writer_is_busy -- --nocapture
RUSTC_WRAPPER= CARGO_TARGET_DIR=/private/tmp/kache-d5-release-target cargo test --release --locked --bin kache post_upload_gc::measure_ -- --ignored --nocapture --test-threads=1
python3 /Users/viktor/Developer/github/kache-d5-investigation/investigation/summarize.py /Users/viktor/Developer/github/kache-d5-investigation/investigation/release-measurements.log
```

## Interpretation

No measured delay with spare workers clears only those measured conditions. It does not erase the verified inline blocking or the measured single-worker latency. Conversely, the single-worker result does not prove a general sixteen-worker or concurrent-worktree throughput regression. At most one pressure sweep holds a store's GC lock, limiting how much capacity this mechanism alone occupies.

The user's checked configuration has no remote section, and launchd sets only `KACHE_LOG`. No current successful-remote-upload trigger was identified there. The finding is retained as a verified condition-specific issue, not a diagnosis of the user's current local-only builds.
