import argparse, fcntl, hashlib, json, os, pathlib, sqlite3, subprocess, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent.parent
BIN = pathlib.Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
HASH = pathlib.Path('/Users/viktor/Developer/github/kache-investigations/audit-filesystem-targets/investigation/probes/blake3-file')
CARGO = pathlib.Path('/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/cargo')
RUSTC = CARGO.with_name('rustc')
parser = argparse.ArgumentParser()
parser.add_argument('case', choices=['corrupt', 'valid', 'ends', 'split-clean', 'same-clean', 'split-share', 'same-share'])
args = parser.parse_args()
root = pathlib.Path(tempfile.mkdtemp(prefix=args.case+'-', dir=HERE))
print('FIXTURE '+str(root), flush=True)
for name in ['home', 'cargo-home', 'cache', 'runtime', 'tmp', 'project']:
    (root/name).mkdir()
config = root/'config.toml'
config.write_text('[cache]\nlocal_store = '+json.dumps(str(root/'cache'))+'\nruntime_dir = '+json.dumps(str(root/'runtime'))+'\nauto_gc = false\nauto_share_target_files = false\n')
env = {key: os.environ[key] for key in ['PATH', 'LANG'] if key in os.environ}
env.update(HOME=str(root/'home'), CARGO_HOME=str(root/'cargo-home'), RUSTUP_HOME='/Users/viktor/.rustup', RUSTC=str(RUSTC), RUSTC_WRAPPER='', RUSTC_WORKSPACE_WRAPPER='', KACHE_CONFIG=str(config), KACHE_HOST_CONFIG=str(root/'absent-host.toml'), KACHE_CACHE_DIR=str(root/'cache'), KACHE_RUNTIME_DIR=str(root/'runtime'), KACHE_NO_DAEMON='1', TMPDIR=str(root/'tmp'), TMP=str(root/'tmp'), TEMP=str(root/'tmp'), HOST_CC='clang', HOST_CXX='clang++', CC='clang', CXX='clang++')
for key in ['HOME','CARGO_HOME','KACHE_CONFIG','KACHE_HOST_CONFIG','KACHE_CACHE_DIR','KACHE_RUNTIME_DIR','TMPDIR','TMP','TEMP']:
    assert pathlib.Path(env[key]).resolve().is_relative_to(HERE), key
assert json.loads(config.read_text().split('local_store = ')[1].splitlines()[0]) == env['KACHE_CACHE_DIR']
assert json.loads(config.read_text().split('runtime_dir = ')[1].splitlines()[0]) == env['KACHE_RUNTIME_DIR']
print('ISOLATION '+json.dumps({key:env[key] for key in ['HOME','CARGO_HOME','RUSTUP_HOME','KACHE_CONFIG','KACHE_HOST_CONFIG','KACHE_CACHE_DIR','KACHE_RUNTIME_DIR','TMPDIR']}), flush=True)
(root/'environment.json').write_text(json.dumps(env,indent=2))
seq = 0
def run(argv, cwd=None, check=True, timeout=40):
    global seq
    seq += 1
    wd = cwd or root
    print('COMMAND '+json.dumps({'argv':list(map(str,argv)), 'workdir':str(wd), 'timeout_seconds':timeout}), flush=True)
    result = subprocess.run(list(map(str,argv)), cwd=wd, env=env, text=True, capture_output=True, timeout=timeout)
    (root/f'command-{seq}.log').write_text(result.stdout+'\nSTDERR\n'+result.stderr+'\nEXIT '+str(result.returncode)+'\n')
    print(result.stdout, result.stderr, 'EXIT '+str(result.returncode), flush=True)
    if check:
        assert result.returncode == 0, 'SETUP_COMMAND_FAILED '+str(argv)
    return result

def share(target, apply):
    argv=[BIN, 'targets', 'share', '--json']
    if apply:
        argv.append('--apply')
    argv.append(target)
    result=run(argv)
    data=json.loads(result.stdout)
    return data['data'] if 'data' in data else data

def seed_blob(target, body, mutate=None):
    dest=target/'debug/deps/libprobe.rlib'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    share(target, False)
    dbpath=root/'cache/index.db'
    assert dbpath.is_file(), 'FIXTURE_INDEX_ABSENT'
    with sqlite3.connect(dbpath) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='blobs'").fetchone(), 'FIXTURE_BLOBS_TABLE_ABSENT'
    digest=run([HASH,dest]).stdout.strip()
    blob=root/'cache/store/blobs'/digest[:2]/digest
    blob.parent.mkdir(parents=True, exist_ok=True)
    stored=bytearray(body)
    if mutate is not None:
        stored[mutate] ^= 0xff
    blob.write_bytes(stored)
    with sqlite3.connect(dbpath) as db:
        db.execute('INSERT OR REPLACE INTO blobs(hash,size,refcount) VALUES(?,?,1)',(digest,len(body)))
    (root/'cache/target-dedup.db').unlink()
    return dest, digest, bytes(stored)

if args.case in ['corrupt','valid','ends']:
    target=root/'target'
    body=bytes(range(256))*512
    offset={'corrupt':len(body)//2,'valid':None,'ends':0}[args.case]
    dest,digest,stored=seed_blob(target,body,offset)
    before=dest.stat().st_ino
    report=share(target,True)
    observed=dest.read_bytes()
    print('OBSERVATION '+json.dumps({'hash':digest,'good_sha256':hashlib.sha256(body).hexdigest(),'observed_sha256':hashlib.sha256(observed).hexdigest(),'target_is_good':observed==body,'target_equals_blob':observed==stored,'inode_before':before,'inode_after':dest.stat().st_ino,'report':report}),flush=True)
    if args.case=='valid':
        assert report['replaced']==1 and observed==body, 'VALID_CLONE_CONTROL_FAILED'
    elif args.case=='ends':
        assert report['replaced']==0 and observed==body, 'ENDS_REJECTION_CONTROL_FAILED'
    else:
        assert observed==body, 'DEDUP_CORRUPTION: sharing replaced a valid target artifact with a blob corrupted in its middle'
    print('ASSERTION_PASS '+args.case,flush=True)
else:
    project=root/'project'
    target=project/'target'
    split=args.case.startswith('split-')
    artifacts=root/'artifacts' if split else target
    (project/'src').mkdir()
    (project/'src/lib.rs').write_text('pub fn answer() -> u64 { 42 }\n')
    (project/'Cargo.toml').write_text('[package]\nname="coordination-probe"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
    gate=root/'release'
    started=root/'build-script-started'
    (project/'build.rs').write_text('fn main() {\nstd::fs::write('+json.dumps(str(started))+', b"started").unwrap();\nwhile !std::path::Path::new('+json.dumps(str(gate))+').exists() {std::thread::sleep(std::time::Duration::from_millis(20));}\nprintln!("cargo:rerun-if-changed=build.rs");\n}\n')
    argv=[CARGO,'build','--offline','--target-dir',artifacts]
    if split:
        argv.extend(['--config','build.build-dir='+json.dumps(str(target))])
    log=(root/'cargo-live.log').open('w')
    print('LIVE_COMMAND '+json.dumps({'argv':list(map(str,argv)), 'workdir':str(project), 'timeout_seconds':90}),flush=True)
    proc=subprocess.Popen(list(map(str,argv)),cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+60
        while not started.exists():
            assert proc.poll() is None, 'CARGO_EXITED_BEFORE_BUILD_GATE'
            assert time.monotonic()<deadline, 'CARGO_BUILD_GATE_TIMEOUT'
            time.sleep(.05)
        locks=[]
        for base in set([target,artifacts]):
            for lock in base.rglob('.cargo*lock'):
                with lock.open('rb') as fd:
                    try:
                        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        held=False
                        fcntl.flock(fd,fcntl.LOCK_UN)
                    except BlockingIOError:
                        held=True
                locks.append({'path':str(lock.relative_to(root)),'held':held})
        print('CARGO_LOCKS '+json.dumps(locks),flush=True)
        assert proc.poll() is None, 'CARGO_NOT_LIVE_AT_PROBE'
        if split:
            assert any(x['path'].endswith('target/debug/.cargo-build-lock') and x['held'] for x in locks), 'SPLIT_BUILD_LOCK_NOT_HELD'
            assert not any(x['path'].startswith('project/target/') and x['path'].endswith('/.cargo-lock') and x['held'] for x in locks), 'UNEXPECTED_INTERMEDIATE_LEGACY_LOCK'
        else:
            assert any(x['path'].endswith('/.cargo-lock') and x['held'] for x in locks), 'LEGACY_LOCK_NOT_HELD'
        if args.case.endswith('clean'):
            result=run([BIN,'clean','--json','--yes',project],cwd=project)
            data=json.loads(result.stdout)
            print('OBSERVATION '+json.dumps({'cargo_alive':proc.poll() is None,'target_exists':target.is_dir(),'report':data}),flush=True)
            assert target.is_dir(), 'SPLIT_CLEAN_DURING_CARGO: clean removed intermediate target while real Cargo held .cargo-build-lock'
        else:
            body=bytes(range(256))*512
            dest,digest,stored=seed_blob(target,body)
            before=dest.stat().st_ino
            report=share(target,True)
            print('OBSERVATION '+json.dumps({'cargo_alive':proc.poll() is None,'inode_before':before,'inode_after':dest.stat().st_ino,'report':report}),flush=True)
            assert dest.stat().st_ino==before and report['replaced']==0, 'SPLIT_SHARE_DURING_CARGO: share replaced an intermediate artifact while real Cargo held .cargo-build-lock'
        print('ASSERTION_PASS '+args.case,flush=True)
    finally:
        gate.write_text('release')
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        log.close()
        print('CARGO_FINAL_EXIT '+str(proc.returncode),flush=True)
        print((root/'cargo-live.log').read_text(),flush=True)
