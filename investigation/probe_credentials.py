import json, os, pathlib, socket, subprocess, tempfile, time, sys
BIN = "/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache"
ROOT = pathlib.Path(__file__).resolve().parent
def main():
    with tempfile.TemporaryDirectory(prefix="kache-rd-", dir="/private/tmp") as td:
        d=pathlib.Path(td); (d/"home").mkdir(); (d/"cache").mkdir()
        helper=d/"helper.py"
        helper.write_text("import pathlib,time,os\np=pathlib.Path("+repr(str(d))+ ")\n(p/'helper.pid').write_text(str(os.getpid()))\ntime.sleep(4)\n(p/'survived').write_text('credential child still active')\nprint('{\"Version\":1,\"AccessKeyId\":\"test\",\"SecretAccessKey\":\"test\"}')\n")
        aws=d/"aws.conf"
        aws.write_text('[profile audit]\ncredential_process = '+sys.executable+' '+str(helper)+'\n')
        config=d/"config.toml"
        config.write_text('[cache]\nlocal_store = '+json.dumps(str(d/"cache"))+'\nruntime_dir = '+json.dumps(str(d))+ '\nprefetch_enabled = false\nremote_key_listing = false\nremote_restore_timeout_secs = 1\n[cache.remote]\ntype = "s3"\nbucket = "fixture"\nendpoint = "http://127.0.0.1:9"\nprofile = "audit"\n')
        env=dict(os.environ)
        for k in list(env):
            if k.startswith(('KACHE_', 'AWS_', 'GITHUB_', 'GITLAB_', 'CI_')) or k in ['CI','RUSTC_WRAPPER']: env.pop(k,None)
        env.update(HOME=str(d/"home"),KACHE_CONFIG=str(config),KACHE_LOG='kache=debug',KACHE_LOG_FILE='off',AWS_CONFIG_FILE=str(aws),AWS_SHARED_CREDENTIALS_FILE=str(d/"missing-credentials"),RUSTC_WRAPPER='')
        daemon=subprocess.Popen([BIN,'daemon','run'],env=env,cwd=d,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            path=d/'daemon.sock'
            for _ in range(200):
                if path.exists(): break
                if daemon.poll() is not None: raise RuntimeError(daemon.communicate())
                time.sleep(.02)
            key='a'*64
            s=socket.socket(socket.AF_UNIX);s.settimeout(8);s.connect(str(path))
            start=time.monotonic();s.sendall((json.dumps({'remote_check':{'key':key,'crate_name':'fixture','entry_dir':str(d/'cache'/'store'/key),'deadline_ms':1000}})+'\n').encode())
            reply=s.makefile('rb').readline();elapsed=time.monotonic()-start;s.close()
            print('remote_check:',reply.decode().strip(),'elapsed:',round(elapsed,3),flush=True)
            print('helper_started:',(d/'helper.pid').exists(),flush=True)
            time.sleep(4.5)
            survived=(d/'survived').exists()
            print('helper_survived_cancelled_remote_operation:',survived,flush=True)
            assert not survived, 'CREDENTIAL_CHILD_SURVIVED: cancelled remote operation left credential helper running'
        finally:
            try:
                s=socket.socket(socket.AF_UNIX);s.settimeout(5);s.connect(str(d/'daemon.sock'));s.sendall(b'"shutdown"\n');s.close()
            except OSError: pass
            try: out,err=daemon.communicate(timeout=10)
            except subprocess.TimeoutExpired: daemon.terminate();out,err=daemon.communicate(timeout=10)
            (ROOT/'probe_credentials.daemon.log').write_bytes(out+err)
if __name__ == '__main__': main()
