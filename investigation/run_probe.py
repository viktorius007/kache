#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
mode = sys.argv[1]
root = pathlib.Path(tempfile.mkdtemp(prefix=mode+'-', dir=HERE/'fixtures')).resolve()
env = os.environ.copy()
for key, suffix in {'HOME':'home','KACHE_CONFIG':'config.toml','KACHE_CACHE_DIR':'cache','KACHE_RUNTIME_DIR':'runtime','CARGO_HOME':'cargo-home','TMPDIR':'tmp','TMP':'tmp','TEMP':'tmp'}.items():
    env[key] = str(root/suffix)
    if key != 'KACHE_CONFIG': (root/suffix).mkdir(exist_ok=True)
(root/'config.toml').write_text('cache_dir = '+json.dumps(str(root/'cache'))+'\n')
env['FIXTURE_ROOT']=str(root)
env['RUSTC_WRAPPER']=''
env['KACHE_AUTO_START']='0'
env['KACHE_VERIFY_RESTORES']='always'
argv=[str(HERE/'bin'/'transaction_probe'),mode]
print(json.dumps({'argv':argv,'workdir':str(HERE.parent),'fixture':str(root),'env':{k:env[k] for k in ['HOME','KACHE_CONFIG','KACHE_CACHE_DIR','KACHE_RUNTIME_DIR','CARGO_HOME','RUSTUP_HOME','TMPDIR','TMP','TEMP'] if k in env}},indent=2),flush=True)
result=subprocess.run(argv,env=env,cwd=HERE.parent,timeout=30)
sys.exit(result.returncode)
