import json, os, pathlib, socket, subprocess, time
BIN = os.environ.get('KACHE_AUDIT_BINARY', '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
ROOT = pathlib.Path(__file__).resolve().parent

def isolated_env(d, config):
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('KACHE_', 'AWS_', 'GITHUB_', 'GITLAB_', 'CI_', 'CARGO_')) or key in ('CI', 'RUSTC_WRAPPER'):
            env.pop(key, None)
    env.update(HOME=str(d/'home'), KACHE_CONFIG=str(config), KACHE_LOG='kache=debug', KACHE_LOG_FILE='off', RUSTC_WRAPPER='')
    return env

def config(d, name, remote=True, volumes=False):
    base=d/name; base.mkdir(); cache=base/'cache'; cache.mkdir(); runtime=base/'runtime'; runtime.mkdir()
    cfg=base/'config.toml'
    text='[cache]\nignore_env = true\nlocal_store = '+json.dumps(str(cache))+'\nruntime_dir = '+json.dumps(str(runtime))+'\nprefetch_enabled = false\nremote_key_listing = false\n'
    if volumes:
        shard=base/'shard'; shard.mkdir()
        text+='[cache.volumes]\n'+json.dumps(str(d/'volume'))+' = '+json.dumps(str(shard))+'\n'
    if remote: text+='[cache.remote]\ntype = "filesystem"\npath = '+json.dumps(str(d/'remote'))+'\nprefix = "artifacts"\n'
    cfg.write_text(text)
    return base, isolated_env(d,cfg)

def ipc(base, request):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10);client.connect(str(base/'runtime'/'daemon.sock'))
        client.sendall((json.dumps(request)+'\n').encode())
        return json.loads(client.makefile('rb').readline())

def start(base,env):
    logfile=(base/'daemon.log').open('wb')
    process=subprocess.Popen([BIN,'daemon','run'],env=env,cwd=base,stdout=logfile,stderr=logfile)
    for _ in range(250):
        if (base/'runtime'/'daemon.sock').exists(): return process,logfile
        if process.poll() is not None: raise AssertionError('fixture daemon exited: '+(base/'daemon.log').read_text())
        time.sleep(.02)
    process.terminate();process.wait(timeout=10);logfile.close()
    raise AssertionError('fixture daemon socket did not appear')

def stop(base,handle):
    process,logfile=handle
    try:
        if process.poll() is None:
            try: ipc(base,'shutdown')
            except (OSError,ValueError): pass
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.terminate();process.wait(timeout=10)
    finally: logfile.close()

def run(args,env,cwd):
    p=subprocess.run(args,env=env,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    print('argv:',args,'exit:',p.returncode,flush=True)
    if p.stdout: print('stdout:',p.stdout.decode(errors='replace'),flush=True)
    if p.stderr: print('stderr:',p.stderr.decode(errors='replace'),flush=True)
    assert p.returncode==0, 'fixture command failed'
    return p
