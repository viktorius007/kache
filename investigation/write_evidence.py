"""Persist bounded source/graph coverage and reproducible review records."""
import datetime
import hashlib
import json
import pathlib
import re
import subprocess

WORKDIR = pathlib.Path(__file__).resolve().parent.parent
ROOT = WORKDIR/'investigation'
PROJECT = 'Users-viktor-Developer-github-kache-investigations-coordinator'
BINARY = pathlib.Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')

def capture(argv, file):
    result = subprocess.run(argv, cwd=WORKDIR, capture_output=True, text=True, timeout=30)
    (ROOT/file).write_text('$ '+json.dumps(argv)+'\nexit: '+str(result.returncode)+'\n'+result.stdout+'\nSTDERR:\n'+result.stderr)
    assert result.returncode == 0, (argv, result.stderr)
    return result.stdout


def save(file, value):
    (ROOT/file).write_text(json.dumps(value, indent=2)+'\n')


def main():
    sha = capture(['git', 'rev-parse', 'HEAD'], 'baseline-head.txt').strip()
    diff = capture(['git', 'diff', '--name-only', 'HEAD', '--', 'src', 'crates', 'Cargo.toml', 'Cargo.lock'], 'production-diff.txt')
    assert not diff.strip(), 'BASELINE_PRODUCTION_CHANGED'
    coordinator = capture(['git', '-C', str(BINARY.parent.parent.parent), 'diff', '--name-only', 'HEAD', '--', 'src', 'crates', 'Cargo.toml', 'Cargo.lock'], 'coordinator-production-diff.txt')
    assert not coordinator.strip(), 'COORDINATOR_PRODUCTION_CHANGED'
    capture(['codebase-memory-mcp', 'cli', 'list_projects'], 'graph-projects.txt')
    capture(['codebase-memory-mcp', 'cli', 'index_status', '--project', PROJECT, '--diagnostics', 'summary'], 'graph-index-status.txt')
    capture(['codebase-memory-mcp', 'cli', 'trace_path', '--project', PROJECT, '--function-name', 'handle_remote_check_started_at', '--direction', 'inbound', '--depth', '1', '--limit', '10', '--include-evidence', 'true', '--format', 'json'], 'graph-request-trace.txt')
    bounds = {'src/cache_remote.rs': [[1, 457]], 'src/wrapper/remote.rs': [[1, 81]],
              'src/remote_layout.rs': [[1, 234], [399, 451], [462, 481], [639, 809]],
              'src/daemon.rs': [[448, 475], [985, 1096], [1408, 1500], [4481, 4949], [4960, 4980], [8640, 8730], [9050, 9120]],
              'crates/kache-store/src/store.rs': [[2438, 2560], [2940, 3130], [3200, 3260]],
              'src/config.rs': [[645, 653], [1530, 1590]],
              'docs/remote-cache/overview.mdx': [[40, 48]],
              'docs/getting-started/configuration.mdx': [[7, 78]]}
    excerpts = []
    for path, ranges in bounds.items():
        lines = (WORKDIR/path).read_text().splitlines()
        for start, end in ranges:
            end = min(end, len(lines))
            excerpts.append('\n'+path+':'+str(start)+'-'+str(end)+'\n')
            excerpts.extend(str(i)+': '+lines[i-1]+'\n' for i in range(start, end+1))
    (ROOT/'source-evidence.txt').write_text(''.join(excerpts))
    save('coverage.json', {'project': PROJECT, 'baseline': sha, 'source_ranges': bounds,
                          'full_files_read': ['src/cache_remote.rs', 'src/wrapper/remote.rs'],
                          'scope': 'two exact restore/request scheduling seams; bounded methods in larger modules',
                          'graph_limits': ['Rust semantic_partial: binding_oracle_unavailable, expanded_calls_unavailable, impl_relationships_unavailable', '127041 unresolved calls; 193239 unresolved references; no exhaustive caller absence claim'],
                          'runtime_limits': ['macOS aarch64 baseline debug CLI; fixture directory stores share a physical volume', 'loopback GET transport only; no cloud credential, provider consistency, live registry, Linux or Windows claim', 'no extra dependency/baseline builds, full suite, mutation run, workload frequency measurement or production repairs']})
    save('provenance.json', {'baseline_sha': sha, 'binary': str(BINARY), 'binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(),
                             'binary_size': BINARY.stat().st_size, 'production_diff': [], 'coordinator_production_diff': [],
                             'rustc': '/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc',
                             'fixture_isolation': 'Every CLI child gets explicit fixture HOME/KACHE_CONFIG/KACHE_CACHE_DIR/KACHE_RUNTIME_DIR/CARGO_HOME/TMPDIR/TMP/TEMP inside investigation; real RUSTUP_HOME retained; no ambient environment inherited; effective paths asserted through daemon stats before operations.'})
    cases = [('remote-binding', 'binding', 'swap', 'WRONG_REMOTE_BINDING', 'source returns 11 but restored valid artifact returns 29'),
             ('cross-shard-singleflight', 'shards', 'concurrent', 'SHARD_SINGLEFLIGHT_FALSE_HIT', 'both requests report found but a requested store has no committed entry')]
    for filename, probe, mode, assertion, detail in cases:
        save(filename+'.case.json', {'argv': ['python3', str(ROOT/'probe_remote_validation.py'), probe, mode],
             'workdir': str(WORKDIR), 'timeout_seconds': 60, 'expected_exit_code': 1,
             'expected_failure_regex': 'AssertionError: '+assertion+': '+detail, 'assertion_regex': assertion})
    commands = []
    for probe, mode, exit_code in [('binding', 'valid', 0), ('shards', 'sequential', 0), ('binding', 'swap', 1), ('shards', 'concurrent', 1), ('shards', 'reverse', 1), ('shards', 'same-store', 0), ('binding', 'corrupt', 0), ('shards', 'sockets', 1)]:
        log = probe+'-'+mode+'.execution.txt'
        commands.append({'argv': ['python3', 'investigation/probe_remote_validation.py', probe, mode], 'workdir': str(WORKDIR), 'timeout_seconds': 60, 'observed_exit': exit_code, 'raw_log': log})
    save('commands.json', commands)
    support = (ROOT/'probe_support.py').read_text()
    probe = (ROOT/'probe_remote_validation.py').read_text()
    standalone = support+'\n'+re.sub(r'from probe_support import \(.*?\)\n', '', probe, flags=re.S)
    common = {'run': {'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'commit': sha, 'model': 'inherited-parent', 'mode': 'production-readiness', 'slice': 'remote-entry-identity-and-cross-shard-requests'}}
    finding1 = dict(common, id='qa-remote-binding', kind='finding', category='defect', domain='code',
        summary='Exact remote restore accepts a valid pack for another cache key and silently restores an incorrect compiler output.',
        scenario='Generate normal packs for the same fixture crate returning 11 (key A) and 29 (key B), then loopback GET of A serves the complete unmodified B pack. The wrapper requests A, imports metadata naming B under A, restores the rlib, and a directly compiled consumer prints 29 while source returns 11.',
        evidence=[{'path': 'src/remote_layout.rs', 'lines': '147-234,719-740', 'point': 'download_entry_observed calls extract_entry_pack_until(..., None); cache_key/crate comparisons run only with an expected binding.'},
                  {'path': 'crates/kache-store/src/store.rs', 'lines': '2947-3105,2445-2553', 'point': 'import validates artifact fields and hashes then commits under requested cache_key; get returns parsed metadata without comparing meta.cache_key to the requested key.'},
                  {'path': 'investigation/binding-swap.execution.txt', 'lines': '32-62', 'point': 'Requested A, imported metadata key B, requested_committed True, wrapper RemoteHit, observed consumer value 29, exact red assertion.'}],
        trace='rustc wrapper -> wrapper::remote::acquire_entry -> send_remote_check -> real daemon RemoteCheck -> handle_remote_check_started_at/leader -> V3Remote.download_entry -> RemoteLayout.download_entry_observed -> extractor without expected identity -> Store.import_restored_entry/import_downloaded_entry(A) -> Store.get(A) -> wrapper restores B rlib -> directly compiled consumer prints 29',
        authority={'source': 'cache integrity failure mode; generated independent source/consumer oracle', 'quote': 'pub fn value() -> u32 { 11 }'},
        proof={'red_test': standalone, 'test_files': {'investigation/probe_support.py': support, 'investigation/probe_remote_validation.py': probe}, 'name': 'binding swap', 'fails_on': sha, 'output': 'AssertionError: WRONG_REMOTE_BINDING: source returns 11 but restored valid artifact returns 29', 'case': 'remote-binding.case.json',
               'oracle_reasoning': 'Consumer expectation 11 is defined by generated source, independent of cached metadata or hash code. Only endpoint object mapping changes: valid A green, complete B under A red, malformed pack safe fallback green. No production edits.'},
        severity='Compiler-result integrity: silent successful build returns wrong behavior and commits the wrong generation under the requested key. Reaches normal exact remote restore on trusted remote object misrouting/accidental substitution; no forged metadata or malicious-writer isolation claim. Runtime witness is one same-crate rlib on macOS; frequency and other artifact types were not measured.', status='open')
    finding2 = dict(common, id='qa-cross-shard-singleflight', kind='finding', category='defect', domain='code',
        summary='Concurrent same-key remote checks for distinct configured stores reuse the leader hit even though the follower store receives no entry.',
        scenario='A fresh daemon has main and configured shard stores. Two valid same-key requests target their respective entry directories. Both replies say found=true but only the leader store commits the entry. Reversing request order reverses the populated store; independent socket clients reproduce it.',
        evidence=[{'path': 'src/daemon.rs', 'lines': '4481-4533,4968-4980,8698-8712', 'point': 'The real socket dispatcher accepts RemoteCheck and BatchRemoteCheck; validation resolves each store before remote_checks.claim(&req.key); followers return leader Response verbatim.'},
                  {'path': 'src/daemon.rs', 'lines': '4809-4842', 'point': 'Only the leader downloads and imports into cache_dir selected for its request.'},
                  {'path': 'investigation/shards-concurrent.execution.txt', 'lines': '24-42', 'point': 'Both results found=true; main committed True, shard committed False; exact red assertion.'},
                  {'path': 'investigation/shards-reverse.execution.txt', 'lines': '24-42', 'point': 'Reversed leader gives main committed False, shard committed True.'},
                  {'path': 'investigation/shards-sockets.execution.txt', 'lines': '24-42', 'point': 'Independent RemoteCheck socket requests also return found=true while shard has no row.'}],
        trace='Two compiler/client stores -> valid shard_dir and entry_dir -> real socket RemoteCheck (or batch join_all) -> handle_remote_check_started_at -> key-only singleflight -> leader imports its chosen store -> follower receives same hit without its own import -> wrapper Store.get(follower key) returns None -> safe compile fallback (source inference)',
        authority={'source': 'src/daemon.rs:997-1003 RemoteCheckRequest shard_dir contract', 'quote': 'Volume-shard cache dir to import into.'},
        proof={'red_test': standalone, 'test_files': {'investigation/probe_support.py': support, 'investigation/probe_remote_validation.py': probe}, 'name': 'shards concurrent', 'fails_on': sha, 'output': 'AssertionError: SHARD_SINGLEFLIGHT_FALSE_HIT: both requests report found but a requested store has no committed entry', 'case': 'cross-shard-singleflight.case.json',
               'oracle_reasoning': 'Requests independently name two destination stores; SQLite read-only queries require a committed row for each. Sequential distinct-store control is green; concurrent same-store control is green; concurrent distinct-store and reverse-order fixtures are red. Separate sockets reproduce without the batch helper. Neither logs nor mere file presence are the hit oracle.'},
        severity='Cache reuse/concurrency and protocol correctness: follower compiler waits for a remote hit, then safely compiles because its own store lacks the entry. Affects overlapping identical keys across configured stores served by one daemon. No compiler corruption or data-loss claim from this scheduling defect; both fixture stores share one physical volume and actual recompilation cost/frequency were not measured.', status='open')
    dismissals = [dict(common, id='qa-malformed-pack-control', kind='dismissal', checked='Serve non-zstd bytes at the exact valid requested pack key.', closed_by={'tier': 1, 'citation': 'binding-corrupt.execution.txt: PASS binding-corrupt, consumer prints 11; binding-corrupt.cold.daemon.log: remote download failed: Unknown frame descriptor'}, reopens_if='A structurally invalid pack can publish or influence compiler output; artifact corruption beyond this malformed-frame fixture was not exhaustively sampled.', status='dismissed'),
                 dict(common, id='qa-same-store-dedup-control', kind='dismissal', checked='Two concurrent requests for the identical key and identical destination store.', closed_by={'tier': 1, 'citation': 'shards-same-store.execution.txt: two found=true replies, main committed True, PASS shards-same-store'}, reopens_if='Same-store followers claim a hit without the shared committed row or under different cancellation/replacement schedules.', status='dismissed'),
                 dict(common, id='qa-sequential-shard-control', kind='dismissal', checked='The same generated key imported into main and shard in sequential RemoteCheck operations.', closed_by={'tier': 1, 'citation': 'shards-sequential.execution.txt: both found=true, main committed True, shard committed True, PASS'}, reopens_if='Import fails without overlapping same-key requests or with a different native-volume backend.', status='dismissed'),
                 dict(common, id='qa-shard-false-hit-corruption-limit', kind='dismissal', checked='Whether the observed cross-shard false reply alone causes a wrong restored compiler artifact.', closed_by={'tier': 2, 'citation': 'src/wrapper/remote.rs:66 requires store.get(cache_key).ok()??; crates/kache-store/src/store.rs:2450 returns None without a committed row; no wrong artifact is supplied by the missing-store witness.'}, reopens_if='A wrapper consumes a leader artifact without reloading its own store, or another race leaves a wrong committed follower entry.', status='dismissed'),
                 dict(common, id='qa-hostile-writer-isolation-scope', kind='dismissal', checked='Treating entry substitution as proof of promised isolation from an authorized malicious remote writer.', closed_by={'tier': 4, 'citation': 'docs/remote-cache/overview.mdx:47-48', 'quote': 'Only give write access to jobs and people you trust to produce those outputs.'}, reopens_if='A signed/authenticated-entry or hostile-writer boundary is promised; the admitted binding defect remains a trusted-domain wrong-object integrity result.', status='dismissed')]
    for dismissal in dismissals:
        dismissal.update(category='defect', domain='code', summary=dismissal['checked'])
    save('findings.json', [finding1, finding2]+dismissals)
    print('Evidence saved; confirmed findings: 2; dismissals: 5; production diff: empty.')


if __name__ == '__main__':
    main()
