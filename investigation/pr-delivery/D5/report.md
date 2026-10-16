STATUS: READY
COMMIT: 5e6317398b7442759c362929bad76e70d83b90bf
CHANGED: src/daemon.rs; src/daemon/tests.rs; src/daemon/tests/post_upload_gc.rs
OPEN: Independent root review and CI mutation lane follow delivery.
BLOCKERS: None
---

Successful PUTs called a synchronous pressure sweep on the async worker. The fix invokes the existing coalesced handle_gc_hint blocking-pool scheduler; Arc receivers retain the daemon for background maintenance. The unchanged sweep still owns size thresholds, backoff, gc.lock, shard cleanup and statistics. The removed synchronous forwarding helper had no remaining production consumer; its maintenance controls now call the underlying sweep directly and retain every assertion.

Scope preservation: src/daemon.rs:6713 clones the same Arc<Daemon>; run_hinted_sweep at :6721 invokes the same sweep_under_size_pressure at :6738 as the former upload helper. No Config is reconstructed and job.entry_dir never determines sweep scope. Main store maintenance uses self.config; configured volume shards retain their own Config, gc.lock, size budget, backoff and GC report. Existing size_pressure_sweeps_each_shard_with_its_own_budget_and_backoff (:3474), size_pressure_leaves_a_shard_whose_gc_lock_is_held (:3515), and gc_skips_a_missing_shard_and_still_sweeps_the_main_store (:3445) preserve those controls. The ported successful-upload regression observes actual main-store eviction and gc_stats.json after offload.

Test-only commit: bea0aa8a5fcb4f2eae7ffcbeff658816642b38d3 (intentionally red as requested).
Fix commit: 5e6317398b7442759c362929bad76e70d83b90bf.

Evidence:
- Ported only the saved responsiveness regression, without ignored measurements. red.log: one failure at the health-before-writer-release assertion, observed 1304.0 ms. green.log: one passed, zero failed. Both use the same single-worker fixture.
- Oracle: src/daemon/tests/post_upload_gc.rs:94 requires an unrelated health request to complete while real SQLite BEGIN IMMEDIATE remains held and GC has reached its lock. The upload must succeed, GC statistics must appear and the actual victim must be absent afterward; merely skipping maintenance cannot pass.
- Existing fixture discriminator reused from ../../discriminator.log (original investigation): adding a second async worker makes the unfixed fixture pass; restored single-worker baseline fails in ../../baseline-red-replay.log at 1272.3 ms. No workload matrix was repeated.
- Mock remote backend replaces network transfer only. Store, SQLite writer, pressure sweep, file locks and runtime scheduling are real isolated fixture state.
- Controls retained: test_upload_triggered_eviction_respects_gc_lock; upload_triggered_eviction_records_its_run; upload_triggered_eviction_waits_out_the_auto_gc_backoff; upload_triggered_eviction_starts_one_byte_above_the_shared_trigger; upload_triggered_eviction_clears_the_backoff_once_the_store_fits; gc_hints_coalesce_while_a_sweep_is_pending; shard pressure controls.

Commands (all builds passed through build-slot.py, private CARGO_TARGET_DIR=/private/tmp/kache-pr-d5-target, KACHE_RUNTIME_DIR unset):
- cargo test -p kache a_post_upload_gc_sweep_allows_health_requests_while_a_writer_is_busy -- --nocapture (red exit 101, green exit 0).
- just check at final commit (exit 0; gate.log): formatting, Clippy -D warnings, resource guard and workspace tests passed. 5892 tests passed across 76 result summaries; 16 ignored tests. Main/shard pressure controls and new responsiveness regression all passed.

Diff review: existing scheduler reused; no new production function, task queue, pending flag, runtime, error type, public module or suppression. No additional nesting or complexity; existing large upload function changes only receiver and maintenance call. New test helper is 84 lines and isolates all filesystem/runtime state. Existing codebase graph trace in ../../graph-trace.log established the upload call chain; source fallback confirmed existing scheduler and all affected consumers. Comments explain the lock observation and releasing the writer before assertions. Scope excludes the separately measured release feature cost.

AGENTS.md assigns changed-line mutation testing to CI and forbids local cargo-mutants. Root performs independent review before publishing; CI remains outstanding.
