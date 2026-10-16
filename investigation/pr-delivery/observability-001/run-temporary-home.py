#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path
ROOT=Path('/Users/viktor/Developer/github/kache-prs/observability-001')
ART=Path(__file__).resolve().parent
FIX=Path('/tmp/kache-observability-001-gate')
(FIX/'home').mkdir(parents=True,exist_ok=True)
(FIX/'config.toml').write_text('')
(FIX/'host.toml').write_text('')
env=os.environ.copy()
for key in list(env):
    if key.startswith(('KACHE_', 'CARGO_')) or key in ('RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER'):
        env.pop(key)
env.update(HOME=str(FIX/'home'),XDG_CONFIG_HOME=str(FIX/'home/.config'),RUSTUP_HOME='/Users/viktor/.rustup',CARGO_HOME='/Users/viktor/.cargo',CARGO_TARGET_DIR='/Users/viktor/Developer/github/kache-prs/observability-003/target',KACHE_CONFIG=str(FIX/'config.toml'),KACHE_HOST_CONFIG='',KACHE_CACHE_DIR=str(FIX/'cache'))
log=ART/sys.argv[1]
argv=['python3','/Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py']+sys.argv[2:]
with log.open('w') as output:
    result=subprocess.run(argv,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT)
print('EXIT '+str(result.returncode)+' LOG '+str(log),flush=True)
print(log.read_text()[-7000:],flush=True)
sys.exit(result.returncode)
