#!/usr/bin/env python3
"""Run untouched APT publisher against a local object-store boundary fixture."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='apt-order-', dir=ROOT / 'investigation') as scratch:
    scratch = Path(scratch)
    local = scratch / 'repo'
    remote = scratch / 'remote'
    tools = scratch / 'bin'
    tools.mkdir()
    (scratch / 'home/.config/rclone').mkdir(parents=True)
    (scratch / 'home/.config/rclone/rclone.conf').write_text('[r2]\n')
    (local / 'dists/unstable').mkdir(parents=True)
    (local / 'pool/main/k/kache').mkdir(parents=True)
    (remote / 'dists/unstable').mkdir(parents=True)
    (remote / 'dists/unstable/Packages').write_text('Package: kache\nFilename: pool/old.deb\n')
    (remote / 'pool').mkdir()
    (remote / 'pool/old.deb').write_bytes(b'old existing package')
    (local / 'dists/unstable/Packages').write_text('Package: kache\nFilename: pool/main/k/kache/new.deb\n')
    (local / 'dists/unstable/InRelease').write_text('new signed metadata fixture\n')
    (local / 'pool/main/k/kache/new.deb').write_bytes(b'new package fixture')
    fake = tools / 'rclone'
    fake.write_text('''#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
op, source, target = sys.argv[1:4]
remote = pathlib.Path(os.environ['PROBE_REMOTE'])
with open(os.environ['PROBE_LOG'], 'a') as log:
    log.write(json.dumps(sys.argv[1:4])+'\\n')
relative = target.split('/kache/apt/', 1)[1]
destination = remote / relative
if op == 'copy' and relative == 'pool/' and os.environ['PROBE_FAIL_POOL'] == '1':
    print('injected object-store failure during package upload', file=sys.stderr)
    sys.exit(9)
if op in ('sync', 'copy'):
    if op == 'sync' and destination.exists(): shutil.rmtree(destination)
    shutil.copytree(source, destination, dirs_exist_ok=True)
else:
    raise SystemExit('unexpected boundary operation')
''')
    fake.chmod(0o755)
    env = os.environ.copy()
    env.update(PATH=str(tools)+os.pathsep+env['PATH'], HOME=str(scratch / 'home'),
               R2_ACCESS_KEY_ID='fixture', R2_SECRET_ACCESS_KEY='fixture',
               R2_ACCOUNT_ID='fixture', R2_BUCKET='fixture', APT_CHANNEL='unstable',
               APT_REPO_DIR=str(local), PROBE_FAIL_POOL='0' if '--healthy' in sys.argv else '1', PROBE_REMOTE=str(remote), PROBE_LOG=str(scratch/'calls.jsonl'))
    result = subprocess.run(['/bin/bash', str(ROOT/'scripts/apt/publish.sh')],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    print('publish_exit='+str(result.returncode))
    print('boundary_calls='+ (scratch/'calls.jsonl').read_text().strip().replace('\n','; '))
    index = (remote / 'dists/unstable/Packages').read_text()
    filename = next(line.split(': ',1)[1] for line in index.splitlines() if line.startswith('Filename: '))
    package_exists = (remote / filename).exists()
    print('PUBLIC_INDEX_FILENAME='+filename)
    print('PUBLIC_PACKAGE_EXISTS='+str(package_exists))
    assert result.returncode == (0 if '--healthy' in sys.argv else 9), 'failure injection must reach package upload'
    assert package_exists, 'APT publication integrity: live index points at absent package after pool upload failure'
