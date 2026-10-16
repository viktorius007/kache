#!/usr/bin/env python3
"""Isolated baseline CLI hydration probes; no host config or daemon service writes."""
import argparse
import json
import os
from pathlib import Path
import random
import shutil
import sqlite3
import sys
import subprocess
import time

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / 'fixture'
RAW = ROOT / 'raw'


def run(argv, env, name, cwd=None):
    start = time.perf_counter()
    result = subprocess.run(argv, cwd=cwd or FIXTURE / 'workspace', env=env,
                            capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    (RAW / (name + '.stdout')).write_text(result.stdout)
    (RAW / (name + '.stderr')).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f'{argv}: exit {result.returncode}: {result.stderr}')
    return elapsed


def environment(binary, cache, config, runtime, local_only=False, domain=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('KACHE_', 'GITHUB_', 'GITLAB_', 'CI_', 'RUSTC_WRAPPER'))}
    home = FIXTURE / 'home'
    home.mkdir(parents=True, exist_ok=True)
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / 'config'),
               KACHE_HOST_CONFIG='', KACHE_CONFIG=str(config),
               KACHE_CACHE_DIR=str(cache), KACHE_RUNTIME_DIR=str(runtime),
               KACHE_ADAPTIVE_INCREMENTAL='0', CARGO_INCREMENTAL='0',
               KACHE_DEFERRED_DURABILITY='0', KACHE_LOG_FILE='off',
               RUSTC_WRAPPER=str(binary), KACHE_OUT_DIR_ALIAS='0',
               CARGO_TARGET_DIR=str(FIXTURE / 'workspace' / 'target'))
    env['CARGO_HOME'] = os.environ.get('CARGO_HOME', '/Users/viktor/.cargo')
    env['RUSTUP_HOME'] = os.environ.get('RUSTUP_HOME', '/Users/viktor/.rustup')
    if local_only:
        env['KACHE_LOCAL_ONLY'] = '1'
    if domain is not None:
        env['KACHE_TRUST_DOMAIN'] = domain
    return env


def count(cache):
    path = cache / 'index.db'
    if not path.exists():
        return 0
    with sqlite3.connect(path) as db:
        return db.execute('SELECT COUNT(*) FROM entries WHERE committed=1').fetchone()[0]


def event_summary(runtime, name):
    source = runtime / 'events.jsonl'
    events = [json.loads(line) for line in source.read_text().splitlines()]
    shutil.copyfile(source, RAW / (name + '.events.jsonl'))
    results = {}
    for event in events:
        results[event['result']] = results.get(event['result'], 0) + 1
    return {'results': results, **{key: sum(event.get(key, 0) for event in events) for key in ['compiler_runs', 'restored_bytes', 'reflinked_bytes', 'hardlinked_bytes', 'copied_bytes', 'restore_ms', 'key_ms', 'startup_ms', 'lookup_ms', 'dep_info_ms', 'elapsed_ms']}}


def remove_target():
    path = FIXTURE / 'workspace' / 'target'
    if path.exists():
        shutil.rmtree(path)


def prepare():
    workspace = FIXTURE / 'workspace'
    workspace.mkdir(parents=True, exist_ok=True)
    members = []
    for n in range(24):
        name = f'fixture{n:02}'
        members.append(name)
        package = workspace / name
        (package / 'src').mkdir(parents=True, exist_ok=True)
        (package / 'Cargo.toml').write_text(f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2024"\n')
        (package / 'src' / 'data.bin').write_bytes(random.Random(n).randbytes(256 * 1024))
        (package / 'src' / 'lib.rs').write_text('pub static DATA: &[u8] = include_bytes!("data.bin");\npub fn value() -> u8 { DATA[0] }\n')
    (workspace / 'Cargo.toml').write_text('[workspace]\nresolver="3"\nmembers=' + json.dumps(members) + '\n')
    (FIXTURE / 'local.toml').write_text('[cache]\ncache_executables=false\nprefetch_enabled=false\n')
    remote = FIXTURE / 'remote'
    remote.mkdir(exist_ok=True)
    (FIXTURE / 'remote.toml').write_text('[cache]\nprefetch_enabled=false\n[cache.remote]\ntype="filesystem"\npath=' + json.dumps(str(remote)) + '\nprefix="fixture"\n')


def seed(binary):
    cache = FIXTURE / 'seed'
    env = environment(binary, cache, FIXTURE / 'local.toml', FIXTURE / 'seed-runtime', True)
    remove_target()
    duration = run(['cargo', 'build', '--workspace', '-j', '2'], env, 'seed-build')
    env = environment(binary, cache, FIXTURE / 'remote.toml', FIXTURE / 'sync-runtime')
    push = run([str(binary), 'sync', '--push', '--all'], env, 'seed-push')
    entries = sorted((cache / 'store').glob('*/meta.json'))
    if len(entries) != 24:
        raise AssertionError(f'fixture expected 24 cache entries, got {len(entries)}')
    info = {'seed_build_s': duration, 'seed_push_s': push, 'entries': len(entries),
            'logical_bytes': sum(json.loads(p.read_text())['files'][i]['size']
                                 for p in entries for i in range(len(json.loads(p.read_text())['files']))),
            'remote_bytes': sum(p.stat().st_size for p in (FIXTURE / 'remote').rglob('*') if p.is_file()),
            'remote_files': len([p for p in (FIXTURE / 'remote').rglob('*') if p.is_file()])}
    (RAW / 'fixture.json').write_text(json.dumps(info, indent=2))
    print('PASS fixture seed', json.dumps(info), flush=True)


def residue(binary):
    key = next((FIXTURE / 'seed' / 'store').glob('*/meta.json')).parent.name
    outcomes = []
    for label, with_residue in [('clean', False), ('extracted-residue', True)]:
        cache = FIXTURE / ('residue-' + label)
        if cache.exists():
            shutil.rmtree(cache)
        if with_residue:
            entry = cache / 'store' / key
            entry.mkdir(parents=True)
            # Exact production crash window: extraction publishes metadata and files,
            # then CLI opens Store and starts import; kill before that registration.
            source = FIXTURE / 'seed' / 'store' / key / 'meta.json'
            meta = json.loads(source.read_text())
            shutil.copyfile(source, entry / 'meta.json')
            for item in meta['files']:
                blob = FIXTURE / 'seed' / 'store' / 'blobs' / item['hash'][:2] / item['hash']
                shutil.copyfile(blob, entry / item['name'])
        env = environment(binary, cache, FIXTURE / 'remote.toml', FIXTURE / ('runtime-' + label))
        elapsed = run([str(binary), 'sync', '--pull', '--all'], env, 'residue-' + label)
        outcomes.append({'arm': label, 'entries': count(cache), 'duration_s': elapsed, 'key': key})
    (RAW / 'residue.json').write_text(json.dumps(outcomes, indent=2))
    assert outcomes[0]['entries'] == 24, 'clean control must import all fixture entries'
    for outcome in outcomes:
        label = outcome['arm']
        cache = FIXTURE / ('residue-' + label)
        runtime = FIXTURE / ('residue-build-runtime-' + label)
        if runtime.exists():
            shutil.rmtree(runtime)
        remove_target()
        env = environment(binary, cache, FIXTURE / 'local.toml', runtime, True)
        run(['cargo', 'build', '--workspace', '-j', '2'], env, 'residue-build-' + label)
        outcome['build_events'] = event_summary(runtime, 'residue-build-' + label)
    (RAW / 'residue.json').write_text(json.dumps(outcomes, indent=2))
    assert outcomes[1]['entries'] == 24, f"sync must complete hydration after extraction residue; got {outcomes[1]['entries']} committed entries, expected 24"
    print('PASS residue recovered')


def measure(binary):
    rows = []
    for n in range(5):
        cache = FIXTURE / f'bench-{n}'
        if cache.exists():
            shutil.rmtree(cache)
        runtime = FIXTURE / f'bench-runtime-{n}'
        if runtime.exists():
            shutil.rmtree(runtime)
        env = environment(binary, cache, FIXTURE / 'remote.toml', runtime)
        cold = run([str(binary), 'sync', '--pull', '--all'], env, f'cold-{n}')
        assert count(cache) == 24
        warm = run([str(binary), 'sync', '--pull', '--all'], env, f'warm-{n}')
        remove_target()
        localenv = environment(binary, cache, FIXTURE / 'local.toml', runtime, True)
        build = run(['cargo', 'build', '--workspace', '-j', '2'], localenv, f'restore-{n}')
        row = {'run': n, 'cold_sync_s': cold, 'warm_sync_s': warm, 'warm_clean_target_build_s': build,
               'entries': count(cache), 'build_events': event_summary(runtime, f'restore-{n}')}
        rows.append(row)
        (RAW / 'measurements.json').write_text(json.dumps(rows, indent=2))
        print('PASS measurement', json.dumps(row), flush=True)


def trust(binary):
    base = FIXTURE / 'domains'
    results = []
    for domain in ['trusted-A', 'trusted-B', 'invalid/domain', 'Trusted-A']:
        runtime = FIXTURE / ('trust-runtime-' + domain.replace('/', '_'))
        env = environment(binary, base, FIXTURE / 'remote.toml', runtime, domain=domain)
        run([str(binary), 'sync', '--pull', '--all'], env, 'trust-' + domain.replace('/', '_'))
        scoped = base / domain
        results.append({'domain': domain, 'base_entries': count(base), 'scoped_entries': count(scoped),
                        'scoped_exists': scoped.exists()})
    # A path label is not an OS access-control boundary. Domains in the same mount
    # are directly accessible to this same OS principal without consulting Kache.
    results.append({'same_os_principal_reads_sibling_index': (base / 'trusted-B' / 'index.db').read_bytes()[:16] == b'SQLite format 3\0',
                    'case_variants_samefile': os.path.samefile(base / 'Trusted-A', base / 'trusted-A')})
    (RAW / 'trust.json').write_text(json.dumps(results, indent=2))
    print('PASS trust characterization', json.dumps(results), flush=True)


def loopback(binary):
    # Reuse baseline read-only S3 fixture: real HTTP/OpenDAL parsing, bounded latency;
    # it does not model AWS bandwidth, auth policy, availability or routing.
    sys.path.insert(0, str(ROOT.parent / 'scripts'))
    from prefetch_remote import ReadOnlyRemote
    http_log = RAW / 'loopback.http.jsonl'
    if http_log.exists():
        http_log.unlink()
    rows = []
    with ReadOnlyRemote(FIXTURE / 'remote', 20, http_log) as server:
        config = FIXTURE / 'loopback.toml'
        config.write_text('[cache]\nprefetch_enabled=false\n[cache.remote]\ntype="s3"\nbucket="qualification"\nregion="us-east-1"\nendpoint=' + json.dumps(server.endpoint) + '\nprefix="fixture"\n')
        for n in range(5):
            cache = FIXTURE / f'http-bench-{n}'
            runtime = FIXTURE / f'http-runtime-{n}'
            if cache.exists():
                shutil.rmtree(cache)
            env = environment(binary, cache, config, runtime)
            env.update(KACHE_S3_ACCESS_KEY='qualification', KACHE_S3_SECRET_KEY='qualification')
            before = len(http_log.read_text().splitlines()) if http_log.exists() else 0
            cold = run([str(binary), 'sync', '--pull', '--all'], env, f'http-cold-{n}')
            assert count(cache) == 24
            aftercold = [json.loads(line) for line in http_log.read_text().splitlines()][before:]
            warm = run([str(binary), 'sync', '--pull', '--all'], env, f'http-warm-{n}')
            afterwarm = [json.loads(line) for line in http_log.read_text().splitlines()][before + len(aftercold):]
            row = {'run': n, 'cold_sync_s': cold, 'warm_sync_s': warm,
                   'cold_http_requests': len(aftercold), 'cold_http_body_bytes': sum(x['body_bytes'] for x in aftercold),
                   'warm_http_requests': len(afterwarm), 'warm_http_body_bytes': sum(x['body_bytes'] for x in afterwarm),
                   'cold_pack_gets': sum('/v3/packs/' in x['path'] and x['method'] == 'GET' for x in aftercold),
                   'warm_pack_gets': sum('/v3/packs/' in x['path'] and x['method'] == 'GET' for x in afterwarm)}
            rows.append(row)
            (RAW / 'loopback.json').write_text(json.dumps(rows, indent=2))
            print('PASS loopback measurement', json.dumps(row), flush=True)


def concurrent(binary):
    rows = []
    for trial in range(3):
        cache = FIXTURE / f'concurrent-{trial}'
        if cache.exists():
            shutil.rmtree(cache)
        env = environment(binary, cache, FIXTURE / 'remote.toml', FIXTURE / f'concurrent-runtime-{trial}')
        handles = []
        processes = []
        for arm in range(4):
            env = environment(binary, cache, FIXTURE / 'remote.toml', FIXTURE / f'concurrent-runtime-{trial}-{arm}')
            out = open(RAW / f'concurrent-{trial}-{arm}.stdout', 'w')
            err = open(RAW / f'concurrent-{trial}-{arm}.stderr', 'w')
            handles.extend([out, err])
            processes.append(subprocess.Popen([str(binary), 'sync', '--pull', '--all'], cwd=FIXTURE / 'workspace', env=env, stdout=out, stderr=err))
        codes = [process.wait() for process in processes]
        for handle in handles:
            handle.close()
        rows.append({'trial': trial, 'exit_codes': codes, 'entries': count(cache)})
        (RAW / 'concurrent.json').write_text(json.dumps(rows, indent=2))
    print('RESULT concurrent sync', json.dumps(rows), flush=True)
    assert all(row['exit_codes'] == [0, 0, 0, 0] and row['entries'] == 24 for row in rows), 'concurrent sync must hydrate all entries without import errors'


parser = argparse.ArgumentParser()
parser.add_argument('mode', choices=['prepare', 'seed', 'residue', 'measure', 'trust', 'concurrent', 'loopback'])
parser.add_argument('--binary', type=Path)
args = parser.parse_args()
RAW.mkdir(parents=True, exist_ok=True)
if args.mode == 'prepare':
    prepare()
else:
    if args.binary is None or not args.binary.is_file():
        parser.error('--binary must name the built untouched baseline')
    globals()[args.mode](args.binary.resolve())
