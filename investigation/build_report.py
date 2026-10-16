#!/usr/bin/env python3
"""Package hydration investigation evidence without modifying production."""
import datetime
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
worktree = root.parent
raw = root / 'raw'
sha = (raw / 'baseline-sha.txt').read_text().strip()
binary = '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
run = {'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'commit': sha, 'model': 'inherited', 'mode': 'production-readiness', 'slice': 'bulk-sync-hydration'}
patch = ''
for name in ['ci_probe.py', 'gate_case.py']:
    source = (root / name).read_text().splitlines()
    patch += f'diff --git a/investigation/{name} b/investigation/{name}\nnew file mode 100644\n--- /dev/null\n+++ b/investigation/{name}\n@@ -0,0 +1,{len(source)} @@\n'
    patch += ''.join('+' + line + '\n' for line in source)
(root / 'red-tests.patch').write_text(patch)
records = []
cases = []
for n, case in enumerate(['residue', 'concurrent'], 1):
    fid = f'qa-ci-hydration-{n:03}'
    assertion = 'sync must complete hydration after extraction residue; got 23 committed entries, expected 24' if case == 'residue' else 'concurrent sync must hydrate all entries without import errors'
    case_record = {'id': fid, 'argv': ['python3', 'investigation/gate_case.py', case, '--binary', binary], 'workdir': str(worktree), 'timeout_seconds': 180, 'expected_failure_regex': 'AssertionError: ' + assertion, 'assertion_regex': 'AssertionError: ' + assertion}
    cases.append(case_record)
    record = {'id': fid, 'kind': 'finding', 'run': run, 'category': 'defect', 'domain': 'code', 'status': 'open', 'duplicates_prior_lead': f'ephemeral-ci-{n:03}', 'proof': {'red_test': patch, 'name': 'bulk_hydration_recovers_extraction_residue' if n == 1 else 'concurrent_bulk_hydration_commands_succeed', 'fails_on': sha, 'output': (raw / f'gate-{case}.log').read_text(), 'gate_case': case_record}}
    if n == 1:
        record.update(summary='Bulk sync exits successfully while leaving an extracted but uncommitted entry unavailable.', scenario='Generated valid 24-entry remote; copy one authentic extracted entry to its final store directory without index registration; sync --pull --all reports pull 23 and exits 0; local-only clean-target build records 23 local hits and one compiler run, while clean control records 24 hits and zero compiler runs.', evidence=[{'path':'src/cli.rs','lines':'7633-7641,7722-7728','point':'Both skip decisions test entry directory existence, not committed-store visibility.'},{'path':'src/remote_layout.rs','lines':'776-794','point':'Extraction publishes the final directory before CLI import.'},{'path':'crates/kache-store/src/store.rs','lines':'2418-2434','point':'Local availability requires meta.json and committed SQLite row.'},{'path':'investigation/raw/residue.json','lines':'all','point':'Clean=24 committed rows; residue=23 before build; external consequence is one extra compiler run.'}], trace='Commands::Sync -> cli::sync -> sync_inner/V3Remote -> sync_with_client existence filter -> omitted residue key -> wrapper contains check fails -> compilation.', authority={'source':'src/cli.rs:7440; production crash-recovery failure mode', 'quote':'Synchronize the local cache with its remote: pull missing artifacts, push new ones.'}, severity='Persistent L1 after interruption or copied crash residue silently loses a bulk prewarm entry. Recompilation matters for ephemeral/local-only/unavailable-remote builds. No wrong output or source-data loss demonstrated; native on-demand recovery was not tested.', oracle='Expected 24 derives from the 24 generated source crates and successfully committed seed, independently checked by a clean pull and clean-target local-hit events. Discriminator changes only extracted residue presence; clean arm is green and residue arm is red on untouched source.')
    else:
        record.update(summary='Independent supported jobs sharing a cache race extraction/import and fail healthy bulk-sync commands.', scenario='Four sync --pull --all clients use one generated shared store and distinct fixture runtimes; all three initial groups and all three standalone replay groups include failures on valid data. Initial exits [1,0,1,0], [0,1,0,0], [1,1,1,1]; final committed count 24 in each group.', evidence=[{'path':'docs/remote-cache/ci.mdx','lines':'136','point':'Concurrent jobs may share a persistent local store with distinct runtimes.'},{'path':'src/cli.rs','lines':'7722-7740','point':'Check, extraction and filesystem import have no shared claim in this seam.'},{'path':'src/remote_layout.rs','lines':'776-785','point':'Publication removes/replaces a shared final directory.'},{'path':'crates/kache-store/src/store.rs','lines':'2947-3050','point':'Read/hash/move filesystem operations precede database transaction.'},{'path':'investigation/raw/concurrent.json','lines':'all','point':'Three groups include failed commands; final counts 24.'}], trace='Four Commands::Sync processes -> shared check -> overlapping v3 extraction/replacement -> import reads/hashes/moves disappearing/changing files -> fail counters -> nonzero sync exits.', authority={'source':'docs/remote-cache/ci.mdx:136', 'quote':'Concurrent jobs may share a persistent local store, but each job should have a distinct KACHE_RUNTIME_DIR for sockets, locks, event logs, and session state.'}, severity='Healthy CI prewarming can fail jobs when independent jobs share trusted persistent L1. Exact interleavings are scheduler-sensitive. Final row counts recovered to 24; no permanent content corruption or native daemon/CLI race was established.', oracle='Every legitimate command should succeed on the 24-entry valid remote; clean sequential pull proves validity. Distinct runtimes preserve supported topology and actual filesystem/SQLite I/O preserve the risk. The red gate requires all four zero exits and 24 entries, and is not a timing assertion.')
    records.append(record)
records.extend([
 {'id':'qa-ci-hydration-d001','kind':'dismissal','run':run,'category':'defect','domain':'code','summary':'Complete warm hydration still downloads all entry packs in this fixture.','checked':'Five completed loopback cold/warm pairs, same generated remote and already committed stores.','closed_by':{'tier':1,'citation':'investigation/raw/loopback.json and loopback.http.jsonl','point':'Every warm sync made exactly one LIST, zero pack GETs; each preceding cold sync committed all 24 rows.'},'reopens_if':'An already committed complete store downloads those packs in a supported repeated workload.','status':'dismissed'},
 {'id':'qa-ci-hydration-d002','kind':'dismissal','run':run,'category':'defect','domain':'code','summary':'Healthy complete hydration fails to produce local-only reusable cache hits for the generated libraries.','checked':'Five clean-target builds after clean bulk pulls plus the residue clean control.','closed_by':{'tier':1,'citation':'investigation/raw/measurements.json, restore-*.events.jsonl and residue.json','point':'Each clean-target run recorded all 24 local hits and zero compiler runs.'},'reopens_if':'An independently seeded clean valid fixture with matching cache keys compiles one of these units despite complete hydration.','status':'dismissed'}])
(root / 'findings.json').write_text(json.dumps(records,indent=2))
(root / 'cases.json').write_text(json.dumps(cases,indent=2))
summary = json.loads((raw / 'measurement-summary.json').read_text())
rows = []
for family, keys in [('filesystem', ['cold_sync_s','warm_sync_s','warm_clean_target_build_s']),('loopback_20ms',['cold_sync_s','warm_sync_s'])]:
    for key in keys:
        values = summary[family][key]
        rows.append(f"| {family} {key} | 5 | {values['median']:.3f} | {values['min']:.3f}–{values['max']:.3f} |")
report = '''STATUS: DONE
COMMIT: none
CHANGED: COUNT
OPEN: 2 unresolved confirmed baseline defects
BLOCKERS: none
CONFIRMED: 2
LIMITS: macOS/APFS, shared debug CLI, generated 24-library workload; no cloud/CI fleet, release-binary or native-daemon results.
---

The two prior hydration findings reproduce independently on untouched main `SHA`. They are validations of `ephemeral-ci-001` and `ephemeral-ci-002`, not two additional unique defects. Production source and the committed test suite are unchanged. Five-run filesystem and five-run loopback measurements also completed inside a quiet window granted by root; all measurement commands succeeded.

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
ROWS

All ten cold syncs commit 24 entries. All five clean-target builds produce 24 local hits and zero compiler runs, each recording 19,094,680 reflinked bytes on this APFS host. Structured per-unit event timings are sums across concurrent workers and must not be treated as a wall-time phase decomposition. The build wall time includes Cargo and dep-info work. `raw/measurement-summary.json` also includes means and sample standard deviations; raw durations, command outputs and all event logs are saved.

Each loopback cold sync makes **25 HTTP requests: one LIST plus 24 V3 pack GETs**, transferring 6,411,683 response-body bytes total (6,405,216 pack bytes plus 6,467 listing bytes). Each warm sync makes **one LIST, zero pack GETs**, transferring 6,467 response-body bytes. All five pairs have the same counts/bytes, corroborated by `raw/loopback.http.jsonl`. Counts exclude request/header transport overhead. This measures the current per-entry bulk path on this fixture; it does not measure namespace/shard pack publication, request reduction from an alternative implementation, AWS costs or CI fleet performance. No latency threshold or baseline/repair comparison exists here, so these costs are measurements, not a third admitted defect.

Source exposes extraction hashing followed by ordinary import hashing and separate Store opens/registration per entry. The timings above do not identify the dominant cost or quantify an optimization. Do not infer a cloud speedup from comparing filesystem and delayed HTTP transports.

## Replay and oracle

Gate-ready `cases.json` has argv, workdir, timeout_seconds, expected_failure_regex and assertion_regex for each finding. `gate_case.py` regenerates and seeds its own fixture before running each red assertion:

```bash
python3 investigation/gate_case.py residue --binary BINARY
python3 investigation/gate_case.py concurrent --binary BINARY
```

Both are expected exit-1 baseline tests and have already executed with the displayed assertion identities. Full test source is `ci_probe.py` plus `gate_case.py`, and embedded as the complete `red-tests.patch` in both JSON proofs. The residue discriminator varies only extracted/uncommitted presence: clean is green and residue is red. The independent oracle is the 24 generated crates and committed seed plus externally observable compilation events. The concurrency test widens to real processes, filesystem and SQLite because mocking those seams would remove the risk; distinct runtimes preserve the supported shared-store layout. Sequential control proves the generated remote is valid. A missing binary/compiler or unrelated setup failure does not match either expected assertion regex.

Timing replay is:

```bash
python3 investigation/ci_probe.py prepare
python3 investigation/ci_probe.py seed --binary BINARY
python3 investigation/ci_probe.py measure --binary BINARY
python3 investigation/ci_probe.py loopback --binary BINARY
```

Coordinate a quiet window again before timing. `raw/provenance.json` records the host, Python, binary SHA-256 and source hashes; `raw/baseline-version.stdout` records the debug CLI version. Absolute fixture paths affect generated keys/compression, so gate fixtures have slightly different remote byte sizes; the reported timings consistently use the original fixture.

## Coverage, dismissals and verification limits

The bounded scope maps CLI sync -> configuration/store open -> V3 listing/planning -> download/extraction publication -> import -> committed-store visibility -> local-only restore. Actors sampled are one sequential client, four concurrent CLI processes, fixture crash residue and filesystem/loopback remote I/O. CLI selectors beyond --all, interruption at other phases, disk-full/GC, malicious remote content, native daemon recovery and other workloads were not exercised.

Graph project `Users-viktor-Developer-github-kache-investigations-coordinator` is ready, indexed 2026-10-11T05:36:35Z. Graph search located sync_with_client, import_restored_entry and contains; inbound trace resolves sync_inner. Rust semantics are partial: missing binding oracle, expanded calls and impl relationships; 127,041 unresolved call candidates / 193,239 references, nine partial parses, 17 intentionally unindexed files including .cargo. These are graph diagnostic counts, not missed production bugs. `raw/graph-*.txt` preserves queries' outcomes. Source directly corroborates every cited production edge and skip/publication/import predicate; no exhaustive call-graph claim is made.

Two evidence-cited dismissals in findings.json cover repeated warm pack downloads and loss of reuse after healthy complete pulls, strictly for this generated fixture. No cloud/CI fleet acceptance, release performance, byte-integrity guarantee after concurrency or general no-regression claim follows. No production fix, known-failing committed suite test, whole-repo suite or mutation run was performed. The repository forbids local mutants; this investigation asks for behavioral evidence only. Production diff is empty (`raw/production-diff.txt`), and source hashes are saved. Standards Size/Existence/Shape/Comments have no production diff to review; the scratch helpers reuse the earlier lead and existing loopback server. The task is DONE because its requested independent red validations and repeated local measurements are complete; the baseline contains two open defects.
'''
report = report.replace('SHA', sha).replace('ROWS', '\n'.join(rows)).replace('BINARY', binary)
(root / 'report.md').write_text(report)
changed = subprocess.check_output(['git','ls-files','--others','--exclude-standard'], cwd=worktree, text=True).splitlines()
count = len([p for p in changed if p != 'investigation/brief.md'])
(root / 'report.md').write_text(report.replace('COUNT', str(count)))
(root / 'ledger.json').write_text(json.dumps({'commit':sha,'mode':'production-readiness','reviewed_scope':'CLI bulk sync hydration; generated filesystem and loopback remote; final local-only cache reuse','reviewed_files':['src/main.rs','src/cli.rs','src/config.rs','src/cache_remote.rs','src/remote_layout.rs','crates/kache-store/src/store.rs','docs/remote-cache/ci.mdx'],'coverage':'bounded source and executed cases; partial Rust graph; not whole-file audit','limits':['native daemon','cloud/CI fleet','release performance','adversarial remote','full crash/cancellation lifecycle','postrace byte integrity']},indent=2))
print('PASS investigation evidence packaged')
