# Ephemeral-CI investigation map

Baseline: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. Authority: upstream issues #810/#811 and baseline docs/remote-cache/ci.mdx. No production repair. The review scope is the cold/warm sync-to-build seam plus node-local store/runtime selection, not whole-file approval of every named source file.

Entry points and traces examined:

- src/main.rs::run_cli (Sync match) → src/cli.rs::sync → sync_inner → sync_with_client → cache_remote::V3Remote → RemoteLayout::download_entry_observed → extract_entry_pack_until → ArtifactStore::import_restored_entry/import_downloaded_entry → committed index.
- Local Rust wrapper lookup → ArtifactStore::get → contains (metadata plus committed row) → restore; structured wrapper events are the external oracle for next-build misses/compiler invocations.
- Config::load_resolved → sanitize_trust_domain/isolate_cache_dir_for_trust_domain → cache/store/index location; runtime-directory separation and documented node-cache mount prerequisite.
- Daemon::handle_remote_check_leader and join_inflight_download read in full for the on-demand recovery distinction: metadata is a wake-up hint; commitment is checked; leader downloads/replaces/imports. No executed native daemon fallback claim.
- V3 extraction integrity path read in full (limits, path/link refusals, schema, streamed hashes, destructive publication); import_downloaded_entry and import_verified_restored_entries read in full (rehash, new-blob fsync, SQLite publication). Pack catalog selection/publication belongs to the other investigator and is not audited here.

Actors/invariants: independent jobs/CLI processes, process death between extraction and index registration, local filesystem directory replacement, SQLite commitment, ambient labels/config, node mount access. Existing directories are not committed entries; different runtimes must still coordinate writes to the shared store; cache content validation remains necessary before restoration.

Graph: coordinator baseline index ready, Rust semantic_partial (binding/expanded calls/impl edges unavailable); 17 files excluded including .cargo, 9 partial mostly Helm. Graph queries located symbols and inbound sync edge; direct source corroborates each cited production edge. No negative call-graph claim based on incomplete edges.

Executed slices: 24-real-library seed and v3 push, clean versus crash-equivalent extraction residue, next clean-target local-only Rust build, three groups of four simultaneous bulk sync clients with distinct runtimes, valid/invalid/case-variant trust labels, prepared local request/byte and cold/warm timing probes (not executed: coordinator subsequently instructed report-only completion).

Sampling limits: synthetic 24 crates on macOS/APFS using a debug baseline binary; no ARC deployment, Linux mount topology, AWS network, real fork job, forced kernel disk-full, global GC/reservation sweep, daemon restart stress, publisher, or five-run large production job. Same-principal filesystem access demonstrates label non-ACL behavior, not a break of the documented no-node-mount security boundary. Correctness findings come from production CLI execution; no modified production source or mock import layer.

Final execution limit: the coordinator’s final instruction explicitly prohibited further tests, benchmark or compiler commands. Planned five-run filesystem and loopback timing modes remain in ci_probe.py but were not run. The seed/residue durations are incidental debug/local setup observations collected without a quiet window and do not support a cold/warm speedup claim. Four-client corrected concurrency groups used distinct runtimes; initial two-client shared-runtime logs are preserved separately.
