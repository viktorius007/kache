#!/usr/bin/env python3
"""Replay a lease marker captured from an exited production test runner."""
import argparse, json, os, pathlib, subprocess, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_BIN = "/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache"
CHILD = """#!/usr/bin/env python3
import fcntl, json, os, pathlib
held = 0
for slot in pathlib.Path(os.environ['KACHE_FIXTURE_CACHE']).joinpath('scheduler/permits').glob('*'):
    with slot.open('r') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            held += 1
print(json.dumps({'held':held, 'marker':os.environ.get('KACHE_TEST_LEASE')}))
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', default=DEFAULT_BIN)
    parser.add_argument('--clear-control', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='stale-lease-', dir=ROOT / 'investigation') as scratch:
        directory = pathlib.Path(scratch)
        cache, home = directory / 'cache', directory / 'home'
        cache.mkdir(); home.mkdir()
        config = directory / 'config.toml'
        config.write_text('[cache]\nlocal_store = "' + str(cache) + '"\nauto_gc = false\n')
        child = directory / 'fixture-0123456789abcdef'
        child.write_text(CHILD); child.chmod(0o755)
        env = {key:value for key,value in os.environ.items() if not key.startswith(('KACHE_', 'KUNOBI_', 'ACTIONS_', 'CARGO_', 'RUST_', 'NEXTEST_'))}
        env.update({'HOME':str(home), 'XDG_CONFIG_HOME':str(home / 'config'), 'KACHE_CONFIG':str(config), 'KACHE_STORE':str(cache), 'KACHE_LOCAL_ONLY':'1', 'KACHE_FIXTURE_CACHE':str(cache), 'RUSTC_WRAPPER':''})
        def run(current):
            proc = subprocess.run([args.binary, 'test-runner', str(child), '--test-threads', '1'], cwd=directory, env=current, capture_output=True, text=True, timeout=15)
            assert proc.returncode == 0, proc.stderr
            return json.loads(proc.stdout)
        initial = run(env)
        assert initial['held'] >= 1 and initial['marker'], 'positive control must observe actual OS permit lock while runner is alive'
        marker = pathlib.Path(initial['marker'])
        import fcntl
        with marker.open('r') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not args.clear_control:
            env['KACHE_TEST_LEASE'] = initial['marker']
        second = run(env)
        evidence = {'control':args.clear_control, 'initial':initial, 'marker_released_before_second':True, 'second':second}
        output = ROOT / 'investigation' / ('stale_lease_control.json' if args.clear_control else 'stale_lease_red.json')
        output.write_text(json.dumps(evidence, indent=2) + '\n')
        print(json.dumps(evidence, indent=2), flush=True)
        assert second['held'] >= 1, 'STALE_LEASE_BYPASS: a released marker from an exited test runner suppresses all production scheduler permits'
        print('CONTROL_PASS: fresh runner acquires permits')
if __name__ == '__main__':
    main()
