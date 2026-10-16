"""Fixture-only baseline CLI helpers; no dependency builds or production edits."""
import contextlib
import hashlib
import http.server
import json
import os
import pathlib
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
BIN = '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
RUSTC = '/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'
RUSTUP_HOME = os.environ.get('RUSTUP_HOME', '/Users/viktor/.rustup')


def fixture_env(base, cfg, sock):
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
           'HOME': str(base/'home'), 'CARGO_HOME': str(base/'cargo'),
           'RUSTUP_HOME': RUSTUP_HOME, 'TMPDIR': str(base/'tmp'),
           'TMP': str(base/'tmp'), 'TEMP': str(base/'tmp'),
           'KACHE_CONFIG': str(cfg), 'KACHE_HOST_CONFIG': '',
           'KACHE_CACHE_DIR': str(base/'cache'), 'KACHE_RUNTIME_DIR': str(base/'runtime'),
           'KACHE_SOCKET_PATH': str(sock), 'KACHE_LOG': 'kache=debug',
           'KACHE_LOG_FILE': 'off', 'RUSTC_WRAPPER': '',
           'KACHE_S3_ACCESS_KEY': 'fixture-key', 'KACHE_S3_SECRET_KEY': 'fixture-secret',
           'AWS_EC2_METADATA_DISABLED': 'true',
           'AWS_CONFIG_FILE': str(base/'home'/'aws-config'),
           'AWS_SHARED_CREDENTIALS_FILE': str(base/'home'/'aws-credentials'),
           'HOST_CC': 'clang', 'HOST_CXX': 'clang++', 'CC': 'clang', 'CXX': 'clang++'}
    for name in ['HOME', 'CARGO_HOME', 'TMPDIR', 'TMP', 'TEMP', 'KACHE_CONFIG',
                 'KACHE_CACHE_DIR', 'KACHE_RUNTIME_DIR', 'KACHE_SOCKET_PATH']:
        assert pathlib.Path(env[name]).resolve().is_relative_to(ROOT), (name, env[name])
    return env


def configure(fixture, name, endpoint=None, volumes=False):
    base = fixture/name
    for directory in ['home', 'cargo', 'tmp', 'cache', 'runtime', 'shard']:
        (base/directory).mkdir(parents=True, exist_ok=True)
    sock = ROOT/('s'+uuid.uuid4().hex[:6])
    assert len(str(sock).encode()) < 104
    cfg = base/'config.toml'
    text = ('[cache]\nlocal_store = '+json.dumps(str(base/'cache'))+
            '\nruntime_dir = '+json.dumps(str(base/'runtime'))+
            '\nprefetch_enabled = false\nremote_key_listing = false\nremote_readonly = '+
            ('true' if endpoint else 'false')+'\n')
    if volumes:
        text += '[cache.volumes]\n'+json.dumps(str(fixture/'volume'))+' = '+json.dumps(str(base/'shard'))+'\n'
    if endpoint:
        text += '[cache.remote]\ntype = "s3"\nbucket = "fixture"\nprefix = "artifacts"\nendpoint = '+json.dumps(endpoint)+'\nregion = "us-east-1"\n'
    else:
        text += '[cache.remote]\ntype = "filesystem"\npath = '+json.dumps(str(fixture/'remote'))+'\nprefix = "artifacts"\n'
    cfg.write_text(text)
    return base, fixture_env(base, cfg, sock)


def run(args, env, cwd):
    result = subprocess.run(args, env=env, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=45)
    print('argv:', json.dumps(args), 'cwd:', str(cwd), 'exit:', result.returncode, flush=True)
    if result.stdout:
        print('stdout:', result.stdout.decode(errors='replace'), flush=True)
    if result.stderr:
        print('stderr:', result.stderr.decode(errors='replace'), flush=True)
    assert result.returncode == 0, 'FIXTURE_COMMAND_FAILED: '+repr(args)
    return result


def ipc(env, request):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(10)
        client.connect(env['KACHE_SOCKET_PATH'])
        client.sendall((json.dumps(request)+'\n').encode())
        line = client.makefile('rb').readline()
        assert line, 'EMPTY_DAEMON_REPLY'
        return json.loads(line)


@contextlib.contextmanager
def daemon(base, env, log_name):
    log_path = ROOT/(log_name+'.daemon.log')
    with log_path.open('wb') as log:
        process = subprocess.Popen([BIN, 'daemon', 'run'], env=env, cwd=base,
                                   stdout=log, stderr=log)
        print('daemon_argv:', json.dumps([BIN, 'daemon', 'run']), 'env:', json.dumps(env, sort_keys=True), flush=True)
        try:
            for _ in range(250):
                if pathlib.Path(env['KACHE_SOCKET_PATH']).exists():
                    break
                assert process.poll() is None, 'DAEMON_EXITED: '+log_path.read_text()
                time.sleep(.02)
            else:
                raise AssertionError('DAEMON_START_TIMEOUT')
            reply = ipc(env, {'stats': {'include_entries': False, 'sort_by': None, 'event_hours': None}})
            eff = reply['stats']['effective_config']
            for field, var in [('cache_dir', 'KACHE_CACHE_DIR'), ('runtime_dir', 'KACHE_RUNTIME_DIR'),
                               ('config_path', 'KACHE_CONFIG'), ('socket_path', 'KACHE_SOCKET_PATH')]:
                assert eff[field] == env[var], ('RESOLVED_PATH_MISMATCH', field, eff[field], env[var])
            assert eff['remote_error'] is None and eff['remote_description'], eff
            print('asserted_effective_config:', json.dumps(eff, sort_keys=True), flush=True)
            yield
        finally:
            if process.poll() is None:
                try:
                    print('shutdown_reply:', ipc(env, 'shutdown'), flush=True)
                except (OSError, ValueError, AssertionError) as error:
                    print('shutdown_error:', repr(error), flush=True)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=10)
            print('daemon_exit:', process.returncode, flush=True)
            for artifact in ROOT.glob(pathlib.Path(env['KACHE_SOCKET_PATH']).name+'*'):
                artifact.unlink(missing_ok=True)


class Endpoint:
    """Loopback S3 object GET double preserves the real transport and extraction seam."""
    def __init__(self, objects, delay=0):
        self.objects, self.delay, self.requests = objects, delay, []
        owner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                key = self.path.split('?', 1)[0]
                payload = owner.objects.get(key)
                owner.requests.append({'path': key, 'status': 200 if payload is not None else 404,
                                       'bytes': len(payload) if payload is not None else 0})
                if owner.delay:
                    time.sleep(owner.delay)
                self.send_response(200 if payload is not None else 404)
                self.send_header('Content-Length', str(len(payload) if payload is not None else 0))
                self.send_header('ETag', '"fixture-object"')
                self.end_headers()
                if payload is not None:
                    self.wfile.write(payload)
            def log_message(self, format, *args):
                print('loopback_http:', format % args, flush=True)
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.url = 'http://127.0.0.1:'+str(self.server.server_port)
    def __enter__(self):
        self.thread.start()
        return self
    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        print('endpoint_requests:', json.dumps(self.requests, sort_keys=True), flush=True)


def compiler_args(fixture):
    return [BIN, RUSTC, '--crate-name', 'fixture', '--crate-type', 'rlib',
            '--emit', 'link,dep-info', '-C', 'metadata=audit', '-C', 'extra-filename=-audit',
            '--out-dir', str(fixture/'out'), str(fixture/'fixture.rs')]


def seed(fixture, log_name, two_entries=False):
    for directory in ['remote', 'out', 'volume']:
        (fixture/directory).mkdir()
    args = compiler_args(fixture)
    base, env = configure(fixture, 'seed')
    keys = []
    with daemon(base, env, log_name+'.seed'):
        for value in ([11, 29] if two_entries else [11]):
            (fixture/'fixture.rs').write_text('pub fn value() -> u32 { '+str(value)+' }\n')
            run(args, env, fixture)
            metas = list((base/'cache'/'store').glob('*/meta.json'))
            new = [p for p in metas if json.loads(p.read_text())['cache_key'] not in keys]
            assert len(new) == 1, 'SEED_NOT_CACHED_DISTINCTLY'
            key = json.loads(new[0].read_text())['cache_key']
            keys.append(key)
            run([BIN, 'sync', '--push'], env, fixture)
    objects = {}
    for key in keys:
        file = fixture/'remote'/'artifacts'/'v3'/'packs'/'fixture'/(key+'.tar.zst')
        assert file.is_file(), 'SEED_PACK_MISSING: '+str(file)
        payload = file.read_bytes()
        objects['/fixture/artifacts/v3/packs/fixture/'+key+'.tar.zst'] = payload
        print('seed_pack:', key, 'bytes:', len(payload), 'sha256:', hashlib.sha256(payload).hexdigest(), flush=True)
    return keys, objects


def committed(base, key, shard=False):
    cache = base/('shard' if shard else 'cache')
    db = cache/'index.db'
    if not db.exists():
        return False
    with sqlite3.connect('file:'+str(db)+'?mode=ro', uri=True) as connection:
        row = connection.execute('SELECT committed FROM entries WHERE cache_key=?', (key,)).fetchone()
        return row is not None and row[0] == 1


def fixture_directory():
    return tempfile.TemporaryDirectory(prefix='f-', dir=ROOT)
