import os,subprocess,sys,tempfile
from pathlib import Path
p=Path(tempfile.mkdtemp(prefix='kache-e1-',dir='/tmp'))
(p/'home').mkdir()
(p/'config.toml').write_text('[cache]\nprefetch_enabled=false\n')
e=os.environ.copy()
for key in list(e):
 if key.startswith('KACHE_'): del e[key]
e.update(HOME=str(p/'home'),KACHE_CONFIG=str(p/'config.toml'),KACHE_CACHE_DIR=str(p/'cache'),KACHE_HOST_CONFIG='',KACHE_LOG_FILE='off',TMPDIR=str(p),RUSTUP_HOME=os.environ.get('RUSTUP_HOME','/Users/viktor/.rustup'),CARGO_HOME=os.environ.get('CARGO_HOME','/Users/viktor/.cargo'),CARGO_TARGET_DIR='/Users/viktor/Developer/github/kache-prs/ephemeral-ci-001/target')
args=['python3','/Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py',*sys.argv[2:]]
with Path(sys.argv[1]).open('w') as log:
 result=subprocess.run(args,env=e,stdout=log,stderr=subprocess.STDOUT)
print('EXIT',result.returncode,'LOG',sys.argv[1],flush=True)
sys.exit(result.returncode)
