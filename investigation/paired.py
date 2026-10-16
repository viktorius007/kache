#!/usr/bin/env python3
"""Isolated paired cache-restoration and profiler-overhead investigation."""
import argparse
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / 'fixture'
CARGO = shutil.which('cargo')
RUSTC = subprocess.check_output(['rustup', 'which', 'rustc'], text=True).strip()


def fixture(files):
    workspace = FIXTURE / 'subject'
    workspace.mkdir(parents=True, exist_ok=True)
    members = [f'unit{i:02}' for i in range(24)]
    (workspace / 'Cargo.toml').write_text('[workspace]\nresolver = "3"\nmembers = ' + json.dumps(members) + '\n[profile.dev]\ndebug = 0\nincremental = false\n')
    for index, member in enumerate(members):
        crate = workspace / member
        (crate / 'src').mkdir(parents=True, exist_ok=True)
        (crate / 'Cargo.toml').write_text(f'[package]\nname = "{member}"\nversion = "0.1.0"\nedition = "2024"\n')
        (crate / 'src/lib.rs').write_text(f'pub fn answer() -> usize {{ {index} }}\n')
    docs = workspace / 'docs'
    if docs.exists():
        shutil.rmtree(docs)
    docs.mkdir()
    for index in range(files):
        (docs / f'page{index:05}.md').write_text(f'# Fixture page {index}\n' + 'documentation content\n' * 4)
    (workspace / 'README.md').write_text('# Original documentation\n')
    lock = 'version = 4\n' + ''.join(f'\n[[package]]\nname = \"{member}\"\nversion = \"0.1.0\"\n' for member in members)
    (workspace / 'Cargo.lock').write_text(lock)
    return workspace


def environment(arm, store, target, profile=None, trace=None):
    home = FIXTURE / 'homes' / arm
    home.mkdir(parents=True, exist_ok=True)
    config = home / 'config.toml'
    config.write_text('[cache]\nauto_gc = false\ndaemon_publish = false\ninput_predictions = true\n')
    cargo_home = FIXTURE / 'cargo-home'
    cargo_home.mkdir(exist_ok=True)
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('KACHE_', 'HOTPATH_', 'CARGO_', 'RUSTFLAGS', 'RUSTC_WRAPPER'))}
    clean.update(HOME=str(home), XDG_CONFIG_HOME=str(home), CARGO_HOME=str(cargo_home), RUSTUP_HOME=os.environ.get('RUSTUP_HOME', str(Path.home()/'.rustup')), RUSTC=RUSTC,
                 RUSTC_WRAPPER=str(ROOT/'bin'/arm), CARGO_TARGET_DIR=str(target), CARGO_BUILD_JOBS='4', CARGO_INCREMENTAL='0', KACHE_CONFIG=str(config), KACHE_HOST_CONFIG='', KACHE_CACHE_DIR=str(store), KACHE_RUNTIME_DIR=str(store), KACHE_EVENT_ROOT=str(FIXTURE/'subject'), KACHE_INPUT_PREDICTIONS='1', KACHE_VERIFY_INPUT_PREDICTIONS='off', KACHE_AUTO_GC='0', KACHE_DAEMON_PUBLISH='0', HOST_CC='clang', HOST_CXX='clang++', CC='clang', CXX='clang++')
    if profile:
        clean.update(HOTPATH_OUTPUT_FORMAT='json', HOTPATH_REPORT='functions-timing', HOTPATH_FUNCTIONS_LIMIT='0', HOTPATH_METRICS_SERVER_OFF='1', HOTPATH_FUNCTIONS_NAME_DEPTH='0')
    if trace:
        clean['KACHE_PHASE_TRACE_DIR'] = str(trace)
    return clean


def build(arm, store, target, label, profile=False, trace=False):
    if target.exists():
        shutil.rmtree(target)
    trace_path = ROOT/'raw'/f'{label}-traces' if trace else None
    env = environment(arm, store, target, profile, trace_path)
    log_path = ROOT/'raw'/f'{label}.log'
    offsets = {path: len(path.read_text().splitlines()) for path in store.glob('**/events.jsonl')}
    if profile:
        profile_path = ROOT/'raw'/f'{label}-hotpath'
        profile_path.mkdir(parents=True, exist_ok=True)
        env['KACHE_HOTPATH_DIR'] = str(profile_path)
    start = time.perf_counter()
    with log_path.open('w') as log:
        result = subprocess.run([CARGO, 'build', '--workspace', '--offline', '-j', '4'], cwd=FIXTURE/'subject', env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    elapsed = time.perf_counter() - start
    if result.returncode:
        raise RuntimeError(f'{label} failed ({result.returncode}): see {log_path}')
    events = []
    for path in store.glob('**/events.jsonl'):
        for line in path.read_text().splitlines()[offsets.get(path, 0):]:
            events.append(json.loads(line))
    return {'arm': arm, 'seconds': elapsed, 'label': label, 'events': events, 'log': str(log_path.relative_to(ROOT)), 'loadavg': os.getloadavg()}


def restore_snapshot(snapshot, store):
    if store.exists():
        shutil.rmtree(store)
    shutil.copytree(snapshot, store)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', type=int, default=4000)
    parser.add_argument('--samples', type=int, default=6)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    workspace = fixture(args.files)
    if args.prepare_only:
        print('DONE prepared fixture', workspace)
        return
    # TreeStamp::SETTLE is two seconds; fixture writes must settle before warm seeds.
    time.sleep(2.1)
    records = []
    for arm in ['v1', 'main-disabled']:
        store = FIXTURE/'stores'/arm
        if store.exists(): shutil.rmtree(store)
        for seed in range(2):
            records.append(build(arm, store, FIXTURE/'target', f'{args.files}-{arm}-seed{seed}'))
        snapshot = FIXTURE/'snapshots'/arm
        if snapshot.exists(): shutil.rmtree(snapshot)
        shutil.copytree(store, snapshot)
    for workload in ['unchanged', 'documentation-edit']:
        for sample in range(args.samples):
            order = ['v1', 'main-disabled'] if sample % 2 == 0 else ['main-disabled', 'v1']
            for arm in order:
                desired = '# Original documentation\n' if workload=='unchanged' else '# Edited documentation\n'
                if workload == 'documentation-edit' or (workspace/'README.md').read_text() != desired:
                    (workspace/'README.md').write_text(desired)
                store = FIXTURE/'stores'/arm
                restore_snapshot(FIXTURE/'snapshots'/arm, store)
                item = build(arm, store, FIXTURE/'target', f'{args.files}-{workload}-{sample}-{arm}')
                item.update(workload=workload, sample=sample, files=args.files)
                records.append(item)
                (ROOT/'raw'/f'paired-{args.files}.json').write_text(json.dumps({'host':platform.platform(), 'rustc':subprocess.check_output([RUSTC,'--version'],text=True).strip(), 'records':records},indent=2))
    # Re-prime the unchanged stamp after the documentation workload rewrote README.
    (workspace/'README.md').write_text('# Original documentation\n')
    time.sleep(2.1)
    store = FIXTURE/'stores'/'main-disabled'
    restore_snapshot(FIXTURE/'snapshots'/'main-disabled', store)
    records.append(build('main-disabled', store, FIXTURE/'target', f'{args.files}-control-prime'))
    shutil.rmtree(FIXTURE/'snapshots'/'main-disabled')
    shutil.copytree(store, FIXTURE/'snapshots'/'main-disabled')
    # Enabled/disabled paired controls reuse the same main seed and data.
    for sample in range(3):
        for arm in (['main-disabled','main-enabled'] if sample%2==0 else ['main-enabled','main-disabled']):
            if (workspace/'README.md').read_text() != '# Original documentation\n':
                (workspace/'README.md').write_text('# Original documentation\n')
            store = FIXTURE/'stores'/arm
            restore_snapshot(FIXTURE/'snapshots'/'main-disabled', store)
            item=build(arm,store,FIXTURE/'target',f'{args.files}-overhead-{sample}-{arm}',profile=arm=='main-enabled')
            item.update(workload='overhead', sample=sample, files=args.files)
            records.append(item)
    store = FIXTURE/'stores'/'main-disabled'
    restore_snapshot(FIXTURE/'snapshots'/'main-disabled', store)
    item = build('main-disabled', store, FIXTURE/'target', f'{args.files}-trace-only-main-disabled', trace=True)
    item.update(workload='phase-trace', files=args.files)
    records.append(item)
    (workspace/'README.md').write_text('# Edited documentation\n')
    store = FIXTURE/'stores'/'main-enabled'
    restore_snapshot(FIXTURE/'snapshots'/'main-disabled', store)
    item = build('main-enabled', store, FIXTURE/'target', f'{args.files}-documentation-profile-main-enabled', profile=True, trace=True)
    item.update(workload='documentation-profile', files=args.files)
    records.append(item)
    (ROOT/'raw'/f'paired-{args.files}.json').write_text(json.dumps({'host':platform.platform(), 'rustc':subprocess.check_output([RUSTC,'--version'],text=True).strip(), 'records':records},indent=2))
    print('DONE', ROOT/'raw'/f'paired-{args.files}.json')


if __name__ == '__main__':
    main()
