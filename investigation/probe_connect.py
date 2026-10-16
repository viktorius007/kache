import json, os, pathlib, socket, subprocess, tempfile, time
BIN = "/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache"
ROOT = pathlib.Path(__file__).resolve().parent
def main():
    with tempfile.TemporaryDirectory(prefix="kache-rd-", dir="/private/tmp") as td:
        d=pathlib.Path(td);(d/"home").mkdir();(d/"cache").mkdir()
        config=d/'config.toml'
        config.write_text('[cache]\nlocal_store = '+json.dumps(str(d/'cache'))+'\nruntime_dir = '+json.dumps(str(d))+'\nprefetch_enabled = false\n')
        env=dict(os.environ)
        for k in list(env):
            if k.startswith(('KACHE_', 'AWS_', 'GITHUB_', 'GITLAB_', 'CI_')) or k in ['CI','RUSTC_WRAPPER']: env.pop(k,None)
        env.update(HOME=str(d/'home'),KACHE_CONFIG=str(config),KACHE_LOG_FILE='off',RUSTC_WRAPPER='')
        listener=socket.socket(socket.AF_UNIX);listener.bind(str(d/'daemon.sock'));listener.listen(1)
        clients=[]
        for _ in range(128):
            client=socket.socket(socket.AF_UNIX);client.settimeout(.05)
            try: client.connect(str(d/'daemon.sock'));clients.append(client)
            except (TimeoutError, BlockingIOError): client.close();break
        print('backlog_filled_connections:',len(clients),flush=True)
        assert clients, 'fixture must establish backlog connections'
        start=time.monotonic()
        blocked=False
        try:
            proc=subprocess.run([BIN,'stats','--format','json'],env=env,cwd=d,capture_output=True,timeout=7)
            (ROOT/'probe_connect.command.log').write_bytes(proc.stdout+proc.stderr)
        except subprocess.TimeoutExpired as e:
            blocked=True;(ROOT/'probe_connect.command.log').write_bytes((e.stdout or b'')+(e.stderr or b''))
        finally:
            listener.close()
            for c in clients: c.close()
        print('stats_blocked_past_7s:',blocked,'elapsed:',round(time.monotonic()-start,3),flush=True)
        assert not blocked, 'IPC_CONNECT_UNBOUNDED: stats blocks on connect beyond its five-second response budget'
if __name__ == '__main__': main()
