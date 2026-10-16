STATUS: DONE
COMMIT: none
CHANGED: 178
OPEN: 2 unresolved confirmed baseline defects
BLOCKERS: none
CONFIRMED: 2
LIMITS: macOS/APFS, shared debug CLI, generated 24-library workload; no cloud/CI fleet, release-binary or native-daemon results.
---

The two prior hydration findings reproduce independently on untouched main `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. They are validations of `ephemeral-ci-001` and `ephemeral-ci-002`, not two additional unique defects. Production source and the committed test suite are unchanged. Five-run filesystem and five-run loopback measurements also completed inside a quiet window granted by root; all measurement commands succeeded.

## Fixture and isolation

`ci_probe.py` generates 24 real Rust libraries with a deterministic 256 KiB payload per crate. The original independent fixture seed committed 24 entries; filesystem remote inventory was 48 files / 6,412,152 bytes, and metadata described 19,103,368 logical bytes. Generated data was compiled by Cargo `-j 2` using the shared baseline CLI, with adaptive incremental and Cargo incremental disabled. These are workload sizes, not transmitted AWS bytes.

Every CLI child and wrapped compiler inherits asserted fixture-only HOME, KACHE_CONFIG, KACHE_CACHE_DIR, KACHE_RUNTIME_DIR, CARGO_HOME, TMPDIR, TMP and TEMP. RUSTUP_HOME preserves the installed toolchain. Remote credentials and Kache/CI overrides are removed; loopback uses fabricated credentials. `KACHE_HOST_CONFIG=''` disables host config and builds run local-only, so no daemon service is installed. Path assertions execute before child operations and save canonical resolved config/store/index paths in `raw/isolation.jsonl`; source corroboration is `src/config.rs:1539,1567,3015,3917`. `raw/commands.jsonl` saves argv, cwd and relevant isolation variables. No user stores, credentials or external services are used.

The fixture-only CARGO_HOME improves the isolation of the earlier lead script, which used the real cargo home. No extra Kache build was needed. Generated binary stores remain disposable and ignored by git; all source, raw logs, structured outcomes, provenance, excerpts and replay cases are retained in investigation/. Each gate replay recreates its own separate generated fixture.

## Confirmed completeness failure

`qa-ci-hydration-001` (`ephemeral-ci-001`). The clean pull commits 24 entries and its local-only clean-target build produces 24 local hits / zero compiler runs. The residue arm copies one authentic extracted metadata+artifact directory without committing it in SQLite, matching the source publication-before-import crash seam. Sync exits 0 after planning only 23 downloads and leaves 23 committed rows; its local-only build records 23 local hits / one compiler run. This is a silent lost-prewarming result, not incorrect compiled output.

`src/cli.rs:7633-7641` skips any existing directory during planning and `7722-7728` repeats that predicate in flight. `src/remote_layout.rs:776-794` publishes the extracted directory before `cli.rs:7736-7740` imports it. A local consumer requires committed state (`crates/kache-store/src/store.rs:2418-2434`), so directory presence cannot establish availability. This affects persistent L1 after interruption and cache snapshots carrying extraction residue; local-only/unavailable-remote builds must compile again. On-demand native daemon recovery is outside these executed tests.

Both the initial independent test and self-contained gate replay exit 1 with `AssertionError: sync must complete hydration after extraction residue; got 23 committed entries, expected 24`. Logs are `raw/residue-test.log`, `raw/gate-residue.log`, outcomes `raw/residue.json` and `gate-raw-residue/residue.json`, with all event files saved. The smallest proposed decision change is committed-store visibility at both skip points plus recovery of uncommitted extraction; no repair was made.

## Confirmed concurrent-command failure

`qa-ci-hydration-002` (`ephemeral-ci-002`). Four clients use the same generated cache and distinct runtimes, matching `docs/remote-cache/ci.mdx:136`. Initial groups have exits `[1,0,1,0]`, `[0,1,0,0]`, `[1,1,1,1]`; separate self-contained replay groups have `[1,1,1,1]`, `[0,1,1,0]`, `[0,1,1,0]`. Each group ends at 24 committed rows. Every group contains failed sync commands against the valid remote. Scheduling changes which key and command fail; this is a race, not a deterministic scheduler.

Failure logs include missing artifact files, artifact move failures, removal/republication failure and one content hash mismatch where the importer read empty content during the race. Sequential clean pulls and all ten cold measurement pulls succeed on the same valid generated inputs. The source seam is the existence check, unclaimed download/publication, then import at `src/cli.rs:7722-7740`; publication removes/replaces the final directory at `remote_layout.rs:776-785`; import reads, hashes and moves files before the SQLite transaction (`store.rs:2947-3050`). The transaction protects index registration but does not serialize those preceding operations. The report does not establish persistent artifact corruption; row counts alone are not a byte-integrity proof.

The gate replay exits 1 with `AssertionError: concurrent sync must hydrate all entries without import errors`. Raw command logs are under `raw/concurrent-*.stdout/.stderr` and `gate-raw-concurrent/`; group results are `raw/concurrent.json` and `gate-raw-concurrent/concurrent.json`. `--allow-partial` could suppress failure, but does not serialize publication. A shared claim must span extraction and import across cooperating processes. Native daemon/CLI races remain unsampled.

## Measured local costs

Five fresh stores per transport were hydrated and then synced again warm. In the filesystem arm, each warm hydrated store served a clean-target local-only Cargo build. Loopback runs use the repository's read-only S3 fixture copied to `investigation/prefetch_remote.py`: real OpenDAL/HTTP parsing, 20 ms server response delay, generated object files, fabricated credentials, no AWS. The fixture does not model network bandwidth, authentication policy, retries, route latency or cloud/fleet scheduling. Root coordinated a quiet window; unrelated host background work cannot be excluded. OS filesystem caches were not flushed, so “cold” means empty Kache store, not cold disk/page cache.

| Operation | n | Median seconds | Observed range seconds |
| --- | --- | --- | --- |
| filesystem cold_sync_s | 5 | 1.124 | 1.050–1.325 |
| filesystem warm_sync_s | 5 | 0.045 | 0.043–0.055 |
| filesystem warm_clean_target_build_s | 5 | 1.186 | 1.114–1.322 |
| loopback_20ms cold_sync_s | 5 | 1.440 | 1.409–1.442 |
| loopback_20ms warm_sync_s | 5 | 0.073 | 0.068–0.079 |

All ten cold syncs commit 24 entries. All five clean-target builds produce 24 local hits and zero compiler runs, each recording 19,094,680 reflinked bytes on this APFS host. Structured per-unit event timings are sums across concurrent workers and must not be treated as a wall-time phase decomposition. The build wall time includes Cargo and dep-info work. `raw/measurement-summary.json` also includes means and sample standard deviations; raw durations, command outputs and all event logs are saved.

Each loopback cold sync makes **25 HTTP requests: one LIST plus 24 V3 pack GETs**, transferring 6,411,683 response-body bytes total (6,405,216 pack bytes plus 6,467 listing bytes). Each warm sync makes **one LIST, zero pack GETs**, transferring 6,467 response-body bytes. All five pairs have the same counts/bytes, corroborated by `raw/loopback.http.jsonl`. Counts exclude request/header transport overhead. This measures the current per-entry bulk path on this fixture; it does not measure namespace/shard pack publication, request reduction from an alternative implementation, AWS costs or CI fleet performance. No latency threshold or baseline/repair comparison exists here, so these costs are measurements, not a third admitted defect.

Source exposes extraction hashing followed by ordinary import hashing and separate Store opens/registration per entry. The timings above do not identify the dominant cost or quantify an optimization. Do not infer a cloud speedup from comparing filesystem and delayed HTTP transports.

## Replay and oracle

Gate-ready `cases.json` has argv, workdir, timeout_seconds, expected_failure_regex and assertion_regex for each finding. `gate_case.py` regenerates and seeds its own fixture before running each red assertion:

```bash
python3 investigation/gate_case.py residue --binary /Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache
python3 investigation/gate_case.py concurrent --binary /Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache
```

Both are expected exit-1 baseline tests and have already executed with the displayed assertion identities. Full test source is `ci_probe.py` plus `gate_case.py`, and embedded as the complete `red-tests.patch` in both JSON proofs. The residue discriminator varies only extracted/uncommitted presence: clean is green and residue is red. The independent oracle is the 24 generated crates and committed seed plus externally observable compilation events. The concurrency test widens to real processes, filesystem and SQLite because mocking those seams would remove the risk; distinct runtimes preserve the supported shared-store layout. Sequential control proves the generated remote is valid. A missing binary/compiler or unrelated setup failure does not match either expected assertion regex.

Timing replay is:

```bash
python3 investigation/ci_probe.py prepare
python3 investigation/ci_probe.py seed --binary /Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache
python3 investigation/ci_probe.py measure --binary /Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache
python3 investigation/ci_probe.py loopback --binary /Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache
```

Coordinate a quiet window again before timing. `raw/provenance.json` records the host, Python, binary 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9-256 and source hashes; `raw/baseline-version.stdout` records the debug CLI version. Absolute fixture paths affect generated keys/compression, so gate fixtures have slightly different remote byte sizes; the reported timings consistently use the original fixture.

## Coverage, dismissals and verification limits

The bounded scope maps CLI sync -> configuration/store open -> V3 listing/planning -> download/extraction publication -> import -> committed-store visibility -> local-only restore. Actors sampled are one sequential client, four concurrent CLI processes, fixture crash residue and filesystem/loopback remote I/O. CLI selectors beyond --all, interruption at other phases, disk-full/GC, malicious remote content, native daemon recovery and other workloads were not exercised.

Graph project `Users-viktor-Developer-github-kache-investigations-coordinator` is ready, indexed 2026-10-11T05:36:35Z. Graph search located sync_with_client, import_restored_entry and contains; inbound trace resolves sync_inner. Rust semantics are partial: missing binding oracle, expanded calls and impl relationships; 127,041 unresolved call candidates / 193,239 references, nine partial parses, 17 intentionally unindexed files including .cargo. These are graph diagnostic counts, not missed production bugs. `raw/graph-*.txt` preserves queries' outcomes. Source directly corroborates every cited production edge and skip/publication/import predicate; no exhaustive call-graph claim is made.

Two evidence-cited dismissals in findings.json cover repeated warm pack downloads and loss of reuse after healthy complete pulls, strictly for this generated fixture. No cloud/CI fleet acceptance, release performance, byte-integrity guarantee after concurrency or general no-regression claim follows. No production fix, known-failing committed suite test, whole-repo suite or mutation run was performed. The repository forbids local mutants; this investigation asks for behavioral evidence only. Production diff is empty (`raw/production-diff.txt`), and source hashes are saved. Standards Size/Existence/Shape/Comments have no production diff to review; the scratch helpers reuse the earlier lead and existing loopback server. The task is DONE because its requested independent red validations and repeated local measurements are complete; the baseline contains two open defects.
