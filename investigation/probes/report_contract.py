#!/usr/bin/env python3
"""Untouched baseline black-box report contract probes, fixture state only."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile

BASELINE = '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['redact-bypass-root', 'skip-reason'])
    parser.add_argument('--kache', default=BASELINE)
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parents[1] / 'evidence'
    evidence.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='observability-', dir=evidence) as tmp:
        fixture = Path(tmp)
        runtime = fixture / 'runtime'
        runtime.mkdir()
        home = fixture / 'home'
        home.mkdir()
        config = fixture / 'config.toml'
        config.write_text('[cache]\n')
        host_config = fixture / 'host.toml'
        host_config.write_text('[cache]\n')
        env = {key: value for key, value in os.environ.items() if not key.startswith(('KACHE_', 'CARGO_'))}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'), KACHE_CONFIG=str(config),
                   KACHE_HOST_CONFIG=str(host_config), KACHE_CACHE_DIR=str(fixture / 'cache'),
                   KACHE_RUNTIME_DIR=str(runtime), KACHE_PROGRESS='0')
        event = dict(ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     crate_name='fixture', root='/private/customer-secret/workspace', version='1',
                     result='passthrough', elapsed_ms=1234, size=0, schema=26,
                     passthrough_reason='unsupported|fixture flag', exit_code=0)
        if args.case == 'skip-reason':
            event.update(result='skipped', passthrough_reason='', skip_reason='admission-threshold')
        (runtime / 'events.jsonl').write_text(json.dumps(event) + '\n')
        argv = [args.kache, 'stats', '--format', 'json']
        if args.case == 'redact-bypass-root':
            argv += ['--redact']
        proc = subprocess.run(argv, env=env, cwd=fixture, capture_output=True, text=True, timeout=20)
        (evidence / (args.case + '.stdout.json')).write_text(proc.stdout)
        (evidence / (args.case + '.stderr.txt')).write_text(proc.stderr)
        assert proc.returncode == 0, f'fixture command failed: {proc.returncode}: {proc.stderr}'
        report = json.loads(proc.stdout)
        row = report['bypass']['slowest'][0]
        if args.case == 'redact-bypass-root':
            assert report['traceEvents'][0]['args']['root'] == 'redacted', 'redaction control did not run'
            print('CONTROL traceEvents root is redacted', flush=True)
            print('OBSERVED bypass root = ' + row['root'], flush=True)
            assert row['root'] == 'redacted', 'REDACT_BYPASS_ROOT_LEAK: bypass.slowest root survived --redact'
        else:
            assert report['summary']['skipped'] == 1, 'skipped event control did not run'
            print('CONTROL summary skipped is 1', flush=True)
            print('OBSERVED skip reason = ' + row['reason'], flush=True)
            assert row['reason'] == 'admission-threshold', 'SKIP_REASON_LOST: recorded admission-threshold became unknown'

if __name__ == '__main__':
    main()
