# Store metadata, blobs, hash memos, atomic publication and restore policy

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 37; bytes: 1338473.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- metadata-store-publication: 30 paths, 32824 text lines; subdivide into the listed contiguous file sections when needed.
- targets-recovery-and-maintenance: 7 paths, 2251 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace entry and blob lifecycle through metadata validation, hash memoization, SQLite/index state, staged writes, atomic publication, failed restore, entry deletion and blob reclamation.
- Review reflink/hardlink/copy choices, carrier leases, reader/writer mutation isolation, executable bits, readonly stores, cross-volume fallback, symlinks, concurrent processes and crash/partial-write ordering.
- Trace target cleanup, deduplication, seeding, liveness and recovery so user files and active artifacts remain safe; distinguish measured physical space from logical counters.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- store-import-publish: consult remote-daemon; kache-format validators + kache-store imported entries ↔ remote_pack/remote_backend; verify sizes/names/hashes before publication
- target-cargo-incremental: consult cargo-build; target liveness/cleanup/seeding ↔ Cargo build dirs/incremental/out-dir aliases; active readers and persistent artifacts

## Sampling declarations

- APFS can run locally; Linux/Windows reflink, cgroup and file permission paths require platform-specific source review and declared runtime limits.
- Crash/failure injection and multi-process interleavings are sampled, with exact chosen cut points recorded.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `crates/kache-format/Cargo.toml` (config-or-delivery-collateral; 568 bytes; 19 text lines)
- `crates/kache-format/README.md` (contract-doc-or-ci; 1164 bytes; 24 text lines)
- `crates/kache-format/src/lib.rs` (source-or-script; 15555 bytes; 344 text lines)
- `crates/kache-format/tests/compatibility.rs` (test-or-fixture; 1814 bytes; 49 text lines)
- `crates/kache-format/tests/fixtures/entry-v31.json` (test-or-fixture; 548 bytes; 27 text lines)
- `crates/kache-store/Cargo.toml` (config-or-delivery-collateral; 1845 bytes; 57 text lines)
- `crates/kache-store/README.md` (contract-doc-or-ci; 1414 bytes; 30 text lines)
- `crates/kache-store/examples/bench-cc-memos.rs` (source-or-script; 4883 bytes; 131 text lines)
- `crates/kache-store/src/atomic.rs` (source-or-script; 22792 bytes; 650 text lines)
- `crates/kache-store/src/blob_drift.rs` (source-or-script; 6383 bytes; 177 text lines)
- `crates/kache-store/src/blob_validation.rs` (source-or-script; 1928 bytes; 56 text lines)
- `crates/kache-store/src/cc_memo.rs` (source-or-script; 51912 bytes; 1299 text lines)
- `crates/kache-store/src/config.rs` (source-or-script; 858 bytes; 33 text lines)
- `crates/kache-store/src/eviction.rs` (source-or-script; 29282 bytes; 660 text lines)
- `crates/kache-store/src/eviction_evidence.rs` (source-or-script; 6570 bytes; 182 text lines)
- `crates/kache-store/src/eviction_evidence/tests.rs` (test-or-fixture; 10062 bytes; 279 text lines)
- `crates/kache-store/src/file_hash.rs` (source-or-script; 75411 bytes; 1897 text lines)
- `crates/kache-store/src/filesystem.rs` (source-or-script; 10552 bytes; 309 text lines)
- `crates/kache-store/src/index_compaction.rs` (source-or-script; 12636 bytes; 334 text lines)
- `crates/kache-store/src/lib.rs` (source-or-script; 937 bytes; 32 text lines)
- `crates/kache-store/src/link.rs` (source-or-script; 200525 bytes; 5015 text lines)
- `crates/kache-store/src/markers.rs` (source-or-script; 20888 bytes; 548 text lines)
- `crates/kache-store/src/opcounts.rs` (source-or-script; 11104 bytes; 283 text lines)
- `crates/kache-store/src/sharing.rs` (source-or-script; 11070 bytes; 325 text lines)
- `crates/kache-store/src/store.rs` (source-or-script; 286418 bytes; 6568 text lines)
- `crates/kache-store/src/store/tests.rs` (test-or-fixture; 455414 bytes; 13183 text lines)
- `crates/kache-store/src/test_support.rs` (source-or-script; 3125 bytes; 79 text lines)
- `crates/kache-store/tests/byte_counters.rs` (test-or-fixture; 3063 bytes; 116 text lines)
- `crates/kache-store/tests/staged_publication.rs` (test-or-fixture; 2669 bytes; 80 text lines)
- `crates/kache-store/tests/thread_store_counters.rs` (test-or-fixture; 1064 bytes; 38 text lines)
- `src/cache_fs.rs` (source-or-script; 31295 bytes; 773 text lines)
- `src/compiler_store.rs` (source-or-script; 5036 bytes; 158 text lines)
- `src/opcounts.rs` (source-or-script; 12718 bytes; 344 text lines)
- `src/store_view.rs` (source-or-script; 6923 bytes; 218 text lines)
- `src/store_view/tests.rs` (test-or-fixture; 15386 bytes; 393 text lines)
- `tests/eviction_evidence_test.rs` (test-or-fixture; 2047 bytes; 52 text lines)
- `tests/readonly_store_test.rs` (test-or-fixture; 12614 bytes; 313 text lines)
