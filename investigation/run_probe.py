"""Build an isolated crate root, execute controls/red probes, preserve exact replay results."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import time

here = Path(__file__).resolve().parent
root = here.parent
parser = argparse.ArgumentParser()
parser.add_argument('--no-build', action='store_true')
parser.add_argument('--test')
args = parser.parse_args()
env = os.environ.copy()
env.update(RUSTC_WRAPPER='', HOST_CC='clang', HOST_CXX='clang++', CC='clang', CXX='clang++',
           CARGO_BUILD_JOBS='2', CARGO_TARGET_DIR=str(here/'target'), KACHE_HOST_CONFIG='')
if not args.no_build:
    subprocess.run(['python3', str(here/'prepare_harness.py')], cwd=root, check=True)
    with (here/'build-replay.log').open('w') as log:
        subprocess.run(['cargo', 'test', '--manifest-path', str(here/'Cargo.toml'), '--bin',
                        'permit-probe', 'remote_permits_probe', '--no-run'], cwd=root,
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
binaries = [p for p in (here/'target/debug/deps').glob('permit_probe-*') if p.is_file() and os.access(p, os.X_OK)]
binary = max(binaries, key=lambda p: p.stat().st_mtime)
names = ['remote_permits_probe_measure', 'remote_permits_probe_default_budget',
         'remote_permits_probe_small_hit_survives_large_demand',
         'remote_permits_probe_recovery_after_queue_timeout']
if args.test:
    if args.test not in names: parser.error('unknown probe name')
    names = [args.test]
results = []
for name in names:
    command = [str(binary), 'remote_permits_probe::'+name, '--exact', '--nocapture', '--test-threads=1']
    start = time.monotonic()
    result = subprocess.run(command, cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    (here/'evidence'/f'{name}.log').write_text(result.stdout)
    record = dict(name=name, command=command, exit_code=result.returncode,
                  seconds=round(time.monotonic()-start, 3), output=result.stdout)
    results.append(record)
    print(json.dumps({k: v for k, v in record.items() if k not in ['output', 'command']}), flush=True)
destination = here/'evidence/replay.json'
if args.test and destination.exists():
    existing = json.loads(destination.read_text())
    existing = [r for r in existing if r['name'] != args.test]
    results = existing + results
destination.write_text(json.dumps(results, indent=2)+'\n')
