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
HARNESS = ROOT / 'investigation/target/debug/kache-scenario'
KACHE = Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
healthy = '--healthy' in sys.argv
with tempfile.TemporaryDirectory(prefix='verify-timeout-', dir=ROOT / 'investigation') as tmp:
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
        assert elapsed >= 1.25, 'fixture must really run past its declared deadline'
        assert result.returncode != 0, 'Verify timeout contract: executable exceeded timeout_s=1 but harness passed'
