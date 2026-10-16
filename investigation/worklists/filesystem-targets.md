# Filesystem primitives, target lifetime, reclamation and recovery

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 29; bytes: 706529.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- filesystem-primitives: 13 paths, 3900 text lines; subdivide into the listed contiguous file sections when needed.
- targets-recovery-and-maintenance: 16 paths, 15185 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace entry and blob lifecycle through metadata validation, hash memoization, SQLite/index state, staged writes, atomic publication, failed restore, entry deletion and blob reclamation.
- Review reflink/hardlink/copy choices, carrier leases, reader/writer mutation isolation, executable bits, readonly stores, cross-volume fallback, symlinks, concurrent processes and crash/partial-write ordering.
- Trace target cleanup, deduplication, seeding, liveness and recovery so user files and active artifacts remain safe; distinguish measured physical space from logical counters.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- store-fs-target-isolation: consult store-core; kache-fs clone/copy/identity and target lifetime/reclamation ↔ store publication/link/carrier leases and blob references

## Sampling declarations

- APFS can run locally; Linux/Windows reflink, cgroup and file permission paths require platform-specific source review and declared runtime limits.
- Crash/failure injection and multi-process interleavings are sampled, with exact chosen cut points recorded.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `crates/kache-fs/Cargo.toml` (config-or-delivery-collateral; 980 bytes; 38 text lines)
- `crates/kache-fs/LICENSE` (license-or-lock-collateral; 10760 bytes; 190 text lines)
- `crates/kache-fs/README.md` (contract-doc-or-ci; 1746 bytes; 32 text lines)
- `crates/kache-fs/src/apfs.rs` (source-or-script; 28728 bytes; 834 text lines)
- `crates/kache-fs/src/apfs_values.rs` (source-or-script; 2661 bytes; 75 text lines)
- `crates/kache-fs/src/copy.rs` (source-or-script; 13638 bytes; 371 text lines)
- `crates/kache-fs/src/extents.rs` (source-or-script; 6147 bytes; 193 text lines)
- `crates/kache-fs/src/fallback.rs` (source-or-script; 2558 bytes; 91 text lines)
- `crates/kache-fs/src/identity.rs` (source-or-script; 6350 bytes; 210 text lines)
- `crates/kache-fs/src/ledger.rs` (source-or-script; 4575 bytes; 157 text lines)
- `crates/kache-fs/src/lib.rs` (source-or-script; 44443 bytes; 1245 text lines)
- `crates/kache-fs/src/linux.rs` (source-or-script; 7647 bytes; 242 text lines)
- `crates/kache-fs/src/staging.rs` (source-or-script; 8389 bytes; 222 text lines)
- `docs/deduplication.mdx` (contract-doc-or-ci; 5027 bytes; 68 text lines)
- `src/blob_heal.rs` (source-or-script; 30760 bytes; 869 text lines)
- `src/disk_recovery.rs` (source-or-script; 9084 bytes; 252 text lines)
- `src/index_compact.rs` (source-or-script; 28966 bytes; 849 text lines)
- `src/link_probe.rs` (source-or-script; 25268 bytes; 675 text lines)
- `src/maintenance.rs` (source-or-script; 11037 bytes; 290 text lines)
- `src/prestage.rs` (source-or-script; 35941 bytes; 913 text lines)
- `src/target_cleanup.rs` (source-or-script; 85190 bytes; 2111 text lines)
- `src/target_dedup.rs` (source-or-script; 81142 bytes; 2330 text lines)
- `src/target_liveness.rs` (source-or-script; 75938 bytes; 2059 text lines)
- `src/target_seed.rs` (source-or-script; 87717 bytes; 2280 text lines)
- `src/target_seed/placement.rs` (source-or-script; 10140 bytes; 309 text lines)
- `src/target_use.rs` (source-or-script; 7512 bytes; 216 text lines)
- `src/unit_prune.rs` (source-or-script; 55057 bytes; 1415 text lines)
- `src/volume_gc.rs` (source-or-script; 6733 bytes; 175 text lines)
- `src/worktree_discovery.rs` (source-or-script; 12395 bytes; 374 text lines)
