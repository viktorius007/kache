#!/usr/bin/env python3
"""Green controls for rejected Cargo edits and supported native passthrough."""
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
BASELINE = Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')


def main():
    with tempfile.TemporaryDirectory(prefix='guards-', dir=ROOT) as fixture:
        home = Path(fixture)
        cargo_home = home / '.cargo'
        cargo_home.mkdir()
        config = cargo_home / 'config.toml'
        before = '[build] # existing config\njobs = 2\n'
        config.write_text(before)
        kache_config = home / 'kache.toml'
        kache_config.write_text('[cache]\nlocal_only = true\nauto_gc = false\n')
        source = home / 'input.c'
        source.write_text('#define HELLO 42\nHELLO\n')
        env = dict(HOME=str(home), CARGO_HOME=str(cargo_home), SHELL='/bin/bash',
                   PATH='/usr/bin:/bin:/usr/sbin:/sbin', KACHE_CONFIG=str(kache_config),
                   KACHE_HOST_CONFIG='', KACHE_CACHE_DIR=str(home / 'cache'),
                   KACHE_RUNTIME_DIR=str(home / 'runtime'), KACHE_LOG='off', KACHE_LOG_FILE='off',
                   KACHE_LOG_FILE_PATH=str(home / 'log'))
        def run(args):
            argv = [str(BASELINE), *[str(x) for x in args]]
            result = subprocess.run(argv, cwd=home, env=env, text=True, capture_output=True, timeout=20)
            return dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        guarded = run(['init', '--yes', '--no-service', '--no-shell'])
        observations = dict(guarded=guarded, before=before, after=config.read_text(), native=[])
        for form in [['cc', '-E', source], ['-E', source]]:
            for disabled in ['0', '1']:
                env['KACHE_DISABLED'] = disabled
                result = run(form)
                result['disabled'] = disabled
                observations['native'].append(result)
        (ROOT / 'config-guards-evidence.json').write_text(json.dumps(observations, indent=2) + '\n')
        assert guarded['returncode'] != 0 and config.read_text() == before, 'CONFIG_GUARD_FAILED: wrapper editor must reject its invalid output without saving'
        assert all(x['returncode'] == 0 and '42' in x['stdout'] for x in observations['native'][:2]), 'DIRECT_CC_FAILED: documented compiler-prefixed preprocessing must work with caching on or off'
        print('CONFIG_GUARDS_PASS: rejected invalid wrapper edit preserves config; kache cc -E works with caching on or off')


if __name__ == '__main__':
    main()
