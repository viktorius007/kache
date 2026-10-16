STATUS: DONE
COMMIT: none
CHANGED: 79 files
OPEN: 2 unresolved findings
BLOCKERS: none
CONFIRMED: 2
LIMITS: Debug baseline; 24 synthetic real Rust libraries; macOS/APFS; no quiet five-run benchmark, AWS/ARC test, native daemon lifecycle stress, or production repair.
---

# Ephemeral CI cache reuse investigation

Reviewed untouched upstream main `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. The coordinator’s final instruction narrowed completion to saved behavioral evidence and explicitly prohibited further tests, benchmarks or compiler commands. The five-run cold/warm and loopback request-count modes are prepared in `investigation/ci_probe.py` but **unexecuted**. This report does not claim #810’s production performance acceptance criteria are met.

Two defects were executed through the production CLI: incomplete bulk hydration after crash residue, and concurrent bulk-sync command failures. Neither establishes incorrect compiled artifacts or permanent source-data loss. Production source remains unchanged; the final task is an investigation, not a repaired implementation. All data/config/store operations used generated fixtures in this worktree.

## Fixture and reproducible evidence

The coordinator built the untouched baseline debug CLI at `/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache` (exit 0). The fixture contains 24 actual Rust workspace library crates, each with a deterministic 256 KiB `include_bytes!` payload. Its successful initial build populated 24 entries. A standalone filesystem-remote push produced **48 files totaling 6,412,193 bytes**; local entry metadata accounted for **19,103,368 logical artifact bytes**. These are measured inventory sizes, not AWS transport measurements. Raw data is in `raw/fixture.json`, `seed.log`, and per-command stdout/stderr.

Incidental seed observations were 2.595 s for the initial fixture build and 0.445 s for push. The final saved residue controls took 1.802 s and 1.541 s for their bulk pulls. Those were debug/local correctness setup runs without a coordinated quiet window. Comparing them would be invalid: the residue arm intentionally hydrates one fewer entry, and other agents were building. They do not establish speedup, request overhead, or dominant phase costs.

Reproduction from this worktree (each test resets its own generated stores):

```bash
RUSTC_WRAPPER= HOST_CC=clang HOST_CXX=clang++ CC=clang CXX=clang++ \
  CARGO_TARGET_DIR=investigation/target cargo build --locked -j 2 --bin kache
python3 investigation/ci_probe.py prepare
python3 investigation/ci_probe.py seed --binary investigation/target/debug/kache
python3 investigation/ci_probe.py residue --binary investigation/target/debug/kache
python3 investigation/ci_probe.py concurrent --binary investigation/target/debug/kache
```

`residue` and `concurrent` are expected red tests on the baseline. Run them separately; the residue assertion exits 1. The full runnable source is embedded in both finding JSON proof records. The script isolates HOME, config, host-config selection, cache and runtime paths; it disables adaptive incremental behavior and does not install a daemon service. The disposable fixture occupied about 214 MiB at the earlier recorded inventory point; an abandoned own build target occupied 346 MiB. Five-run extra fixtures were not created.

## Confirmed: bulk hydration ignores uncommitted extracted entries

`ephemeral-ci-001`. Both the plan filter at `src/cli.rs:7633-7641` and the in-flight recheck at `7722-7728` use directory existence as availability. V3 extraction publishes that directory before index import (`src/remote_layout.rs:776-794`). Local consumers require a committed SQLite row (`ArtifactStore::contains`, `crates/kache-store/src/store.rs:2418-2434`).

The fixture copied one authentic extracted entry’s metadata and artifacts into its final store directory with no index registration, representing death between extraction publication and import. The same valid remote imports cleanly in the control. On the residue arm, bulk sync exits 0, prints `Plan: pull 23 artifacts`, and finishes with **23 committed entries rather than 24**. The independent red assertion is:

```text
AssertionError: sync must complete hydration after extraction residue; got 23 committed entries, expected 24
```

The subsequent clean-target local-only Cargo build proves the external consequence. The control recorded **24 local hits and zero compiler runs**; residue recorded **23 local hits, one miss and one compiler run**. Structured events are saved as `raw/residue-build-*.events.jsonl`; `raw/residue.json` contains the summarized outcomes. Successful copies/reflinks do not hide the absent entry.

This affects persistent L1 disks after interruption, cache snapshots carrying extraction residue, and bulk prewarming followed by a local-only or unavailable-remote build. The source trace shows native on-demand daemon handling checks committed state and performs its own download/import. That distinction is source evidence, not an executed daemon recovery test. Scope the defect to bulk sync and its downstream lost prewarming, not every cache read path.

The smallest demonstrated correctness improvement is to use committed-store visibility in both CLI skip decisions and recover/re-download an uncommitted extraction. This is a proposed change only; no repair or regression test was inserted into production/the committed suite.

## Confirmed: independent jobs race bulk extraction/import

`ephemeral-ci-002`. Four clients ran `sync --pull --all` against one isolated shared cache, each with a distinct runtime directory as documented for concurrent jobs. All remote objects were the valid seed fixture. Three groups produced these process exits:

| Group | Four exit codes | Final committed entries |
| --- | --- | --- |
| 0 | 1, 1, 0, 1 | 24 |
| 1 | 1, 1, 1, 1 | 24 |
| 2 | 0, 0, 0, 1 | 24 |

Logs show missing downloaded metadata, artifact rename failures and a concurrent cleanup reporting `Directory not empty`. The red assertion requires all legitimate commands to exit 0 and the known 24 entries to be present. All three corrected groups failed that command-reliability contract. Sequential clean pull is the valid-data control.

The source seam is a per-process existence check followed by unclaimed extraction into a shared directory (`src/cli.rs:7722-7740`), whose publication removes/replaces the directory (`src/remote_layout.rs:776-785`), while another importer hashes and moves files before opening its database transaction (`store.rs:2947-3007,3023-3050`). Atomic database registration does not serialize those preceding filesystem operations.

This can fail a CI prewarming step on a healthy remote; `--allow-partial` would suppress the command failure, not serialize the race. The corrected supported-layout groups all ended at 24 rows, so this report does **not** claim persistent corruption from those groups. Initial two-client shared-runtime evidence had one failed group with 23 rows and two green groups; its logs are preserved under `raw/initial-sharedruntime-*` as secondary evidence. Exact keys and interleavings are scheduling sensitive. A replay can pass a group; the saved failure and three corrected red groups demonstrate the defect, not a deterministic scheduler.

A safe concurrency improvement needs a shared ownership/claim mechanism spanning existence validation, extraction and import across every cooperating publisher. Merely replacing `exists()` with `contains()` fixes the residue decision but does not fix concurrent destructive publication. Native cross-daemon/CLI races were not tested here.

## Current cold-path costs and improvement opportunity

The current CLI bulk path builds a V3Remote and uses per-entry v3 downloads (`src/cli.rs:7500-7524,7730-7740`). Source implies one entry-pack GET for each missing listed entry; the 24-entry fixture therefore needs 24 pack downloads, while an already hydrated store skips them. Actual HTTP request counts were **not** measured: the prepared loopback mode was not executed. This must not be presented as a measured AWS request reduction.

The source exposes two concrete local-work costs worth testing after the functional fixes: extraction hashes artifacts while streaming them to disk (`remote_layout.rs:621-775`), then ordinary v3 import rereads/re-hashes them (`store.rs:2997-3007`); CLI opens a new Store and commits each entry separately (`cli.rs:7736-7740`, `store.rs:3050-3105`). New blobs are fsynced before publication (`store.rs:3023-3036`). Existing packed-prefetch plumbing has a stream-verified witness and batch importer that avoids the second content read and amortizes transaction registration (`store.rs:3206-3382`). Reusing that proven seam for eligible v3 hydration is a bounded performance experiment. It must preserve the byte-validation and cross-process publication guarantees. No speedup or phase dominance was measured, so it is an opportunity rather than an admitted performance defect.

The larger request-count improvement in #810 requires published manifest/namespace/shard packs. The reader already exists in this baseline; publisher/catalog investigation is owned by another investigator. This report does not assign publication work, prove corrupt-pack fallback, or credit unexecuted pack behavior. Node-local persistence can avoid repeated artifact hydration in trusted pools, but representative five-run cold/warm ARC measurements remain outstanding.

## L1 lifecycle and isolation characterization

Valid labels `trusted-A` and `trusted-B` selected separate directories, each populated with 24 entries; the unscoped base initially had zero. `invalid/domain` fell back to the base and populated 24 entries, matching the explicit documented fallback. On this case-insensitive APFS volume, `Trusted-A` and `trusted-A` referred to the **same directory**. The same OS principal could read its sibling fixture index directly. Those are concrete operational hazards, not evidence that a supported untrusted ARC job has the node-cache mount.

[Current #811](https://github.com/kunobi-ninja/kache/issues/811) requires isolation tests proving untrusted jobs receive no node-cache mount/socket/credentials. Baseline CI docs say: “Do not mount that disk or export KACHE_TRUST_DOMAIN on public or fork jobs.” The implementation adds a path-safe directory label (`src/config.rs:4263-4305`); it supplies no ACL or container admission mechanism. Deployment must enforce the no-mount boundary, separate trust pools, and canonical unique labels. This investigation did not inspect real ARC manifests, permission identities, fork admission or credentials and therefore does not claim that deployment criterion passed or failed. Invalid-label fallback and case variants must not be mistaken for strict namespace rejection or a secrecy boundary.

Runtime directories belong on job scratch storage; the persistent store belongs on the trusted node disk. Documentation says concurrent jobs can share a store with distinct runtimes and that uploads need draining before an ephemeral runner disappears. The corrected bulk-sync race remains despite separate runtimes. Daemon restart/drain, GC, reservation and disk-pressure stress were not executed; other investigators own broader store/eviction details.

## Coverage and evidence limits

`coverage.md` inventories the entry points, actors, invariants and sampled source methods. The coordinator graph was ready but Rust semantic call/impl coverage was partial; 17 files including .cargo were excluded and nine parses were partial, mostly Helm. Graph search located symbols and the inbound production Sync edge; direct source corroborated every cited edge. There is no whole-file or whole-codebase correctness claim.

Primary authority was saved from the current GitHub API in `raw/issue-810.json` and `raw/issue-811.json`, with readable copies. Findings and meaningful dismissals are in `findings.json`. Planned five-run filesystem/loopback measurements, representative Linux ARC/S3 behavior, hardlink/cross-mount copy costs and native daemon lifecycle probes are unexecuted. The incidental debug/local durations and inventory bytes cannot validate #810’s 90% request reduction, ≤10% extra bytes, or before/after five-run acceptance requirements.
