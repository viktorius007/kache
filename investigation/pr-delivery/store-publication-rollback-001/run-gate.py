#!/usr/bin/env python3
"""Run this PR's gate with generated short fixture paths and a private target."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

DELIVERY = Path(__file__).resolve().parent
WORKTREE = Path('/Users/viktor/Developer/github/kache-prs/store-publication-rollback-001')
# Keep the standard /tmp spelling: macOS scan tests reject /private paths.
created = Path(tempfile.mkdtemp(prefix='ksr-', dir='/private/tmp'))
FIXTURE = Path('/tmp') / created.name
env = os.environ.copy()
for key, suffix in {
    'HOME': 'h', 'KACHE_CONFIG': 'config.toml', 'KACHE_CACHE_DIR': 'c',
    'TMPDIR': 't', 'TMP': 't', 'TEMP': 't',
}.items():
    env[key] = str(FIXTURE / suffix)
    if key != 'KACHE_CONFIG':
        (FIXTURE / suffix).mkdir(exist_ok=True)
# Runtime follows each generated cache, including caches overridden by tests.
env.pop('KACHE_RUNTIME_DIR', None)
env['RUSTUP_HOME'] = os.environ.get('RUSTUP_HOME', '/Users/viktor/.rustup')
env['CARGO_HOME'] = '/Users/viktor/.cargo'
env['CARGO_TARGET_DIR'] = str(WORKTREE / 'tmp/pr-target')
env['RUSTC_WRAPPER'] = ''
(FIXTURE / 'config.toml').write_text('cache_dir = ' + json.dumps(env['KACHE_CACHE_DIR']) + '\n')
argv = [
    'python3',
    '/Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py',
    *(sys.argv[1:] or ['just', 'check']),
]
stem = 'environment-validation' if sys.argv[1:] else 'gate'
record = {
    'argv': argv, 'workdir': str(WORKTREE), 'fixture': str(FIXTURE),
    'runtime_isolation': 'default runtime follows generated cache or per-test cache override',
    'env': {key: env.get(key) for key in [
        'HOME', 'KACHE_CONFIG', 'KACHE_CACHE_DIR', 'KACHE_RUNTIME_DIR',
        'TMPDIR', 'TMP', 'TEMP', 'RUSTUP_HOME', 'CARGO_HOME', 'CARGO_TARGET_DIR',
        'RUSTC_WRAPPER',
    ]},
}
(DELIVERY / (stem + '-command.json')).write_text(json.dumps(record, indent=2) + '\n')
print('RUNNING isolated ' + ' '.join(argv[2:]) + ': ' + str(FIXTURE), flush=True)
with (DELIVERY / (stem + '.log')).open('w') as log:
    result = subprocess.run(argv, cwd=WORKTREE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
record['exit_code'] = result.returncode
(DELIVERY / (stem + '-command.json')).write_text(json.dumps(record, indent=2) + '\n')
print(('PASS ' if result.returncode == 0 else 'FAIL ') + ' '.join(argv[2:]) + ' exit=' + str(result.returncode), flush=True)
sys.exit(result.returncode)
