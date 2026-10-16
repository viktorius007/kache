#!/usr/bin/env python3
"""A bounded late executable must fail the baseline fixture timeout contract."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
HARNESS = Path('/Users/viktor/Developer/github/kache-prs/contract-bin-001/target/debug/kache-scenario')
KACHE = Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
healthy = '--healthy' in sys.argv
with tempfile.TemporaryDirectory(prefix='verify-timeout-', dir='/tmp') as tmp:
    scratch = Path(tmp)
    scenario = scratch / 'scenarios/e2e-timeout'
    (scenario / 'source').mkdir(parents=True)
    (scenario / 'source/marker').write_text('bounded verify fixture\n')
    (scenario / 'scenario.toml').write_text('''name = "e2e-timeout"
tags = ["suite:e2e"]
[source]
kind = "fixture"
path = "source"
[commands]
build = "true"
clean = "true"
[verify]
run = "sleep ''' + ('0.05' if healthy else '1.25') + '''; printf ok"
timeout_s = 1
expected_stdout_contains = ["ok"]
''')
    (scratch / 'home').mkdir()
    (scratch / 'config.toml').write_text('[cache]\nignore_env = false\nlocal_only = true\nscheduler = false\ndaemon_publish = false\nauto_gc = false\n')
    env = {key: value for key, value in os.environ.items() if not key.startswith('KACHE_') and key not in ('RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER')}
    env.update(HOME=str(scratch/'home'), XDG_CONFIG_HOME=str(scratch/'home'),
               KACHE_CONFIG=str(scratch/'config.toml'), KACHE_HOST_CONFIG='',
               KACHE_RUNTIME_DIR=str(scratch/'runtime'), KACHE_FALLBACK='off')
    start = time.monotonic()
    result = subprocess.run([str(HARNESS), '--kache', str(KACHE), '--scenarios', str(scratch/'scenarios'), '--select', 'suite:e2e', '--out', str(scratch/'results.json')],
                            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=25)
    print(result.stdout, end='')
    elapsed = time.monotonic() - start
    data = json.loads((scratch/'results.json').read_text())
    print('HARNESS_EXIT='+str(result.returncode))
    print('ELAPSED_SECONDS='+str(round(elapsed,3)))
    print('RESULTS='+json.dumps([{'name':f['name'],'status':f['status'],'phases':[{'phase':p['phase'],'status':p['status'],'verify':p.get('verify')} for p in f['phases']]} for f in data['fixtures']], sort_keys=True))
    if healthy:
        assert result.returncode == 0, 'within-deadline executable must pass'
    else:
        assert data['fixtures'][0]['status'] == 'fail', 'deadline failure must be recorded'
        assert len(data['fixtures'][0]['phases']) == 1, 'deadline failure must short circuit later phases'
        assert 'timed out after 1 seconds' in data['fixtures'][0]['phases'][0]['verify']['failure_reason'], 'deadline must have a distinct failure reason'
        assert result.returncode != 0, 'late executable must fail the harness'
