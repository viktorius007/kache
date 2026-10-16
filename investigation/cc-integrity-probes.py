#!/usr/bin/env python3
"""Real Apple-Clang black-box cache integrity probes against an unchanged baseline CLI."""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent
KACHE = '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
CLANG = '/usr/bin/clang'
parser = argparse.ArgumentParser()
parser.add_argument('case', choices=['epoch', 'has-include', 'header-swap', 'link-library'])
parser.add_argument('--discovery', default='1', choices=['0', '1'])
parser.add_argument('--control', action='store_true')
args = parser.parse_args()
fixture = ROOT / ('fixtures-' + args.case + '-' + args.discovery + ('-control' if args.control else ''))
shutil.rmtree(fixture, ignore_errors=True)
fixture.mkdir()
(fixture / 'config.toml').write_text('[cache]\ndaemon_publish = false\n')
env = {k: v for k, v in os.environ.items() if not k.startswith('KACHE_') and k not in ['OUT_DIR', 'RUSTC_WRAPPER', 'SOURCE_DATE_EPOCH']}
env.update(HOME=str(fixture / 'home'), KACHE_CACHE_DIR=str(fixture / 'cache'), KACHE_RUNTIME_DIR=str(fixture / 'cache'), KACHE_CONFIG=str(fixture / 'config.toml'), KACHE_HOST_CONFIG=str(fixture / 'no-host.toml'), KACHE_LOCAL_ONLY='1', KACHE_DAEMON_PUBLISH='0', KACHE_MIN_STORE_COMPILE_MS='0', KACHE_DEFERRED_DISCOVERY=args.discovery, KACHE_LOG='kache::wrapper=debug')
(fixture / 'home').mkdir()
commands = []

def command(argv, phase_env=env, check=True):
    result = subprocess.run(argv, cwd=fixture, env=phase_env, capture_output=True, text=True, timeout=30)
    commands.append(dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    (fixture / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    if check:
        assert result.returncode == 0, result.stderr
    return result

def header(value):
    return '#undef VALUE\n#define VALUE ' + str(value) + '\n'

def library(value):
    (fixture / 'value.c').write_text('int value(void) { return ' + str(value) + '; }\n')
    command([CLANG, '-c', 'value.c', '-o', 'value.o'])
    (fixture / 'libvalue.a').unlink(missing_ok=True)
    command(['/usr/bin/ar', 'rcs', 'libvalue.a', 'value.o'])

if args.case == 'epoch':
    source = '#include <stdio.h>\nint main(void) { puts(__DATE__ " " __TIME__); return 0; }\n'
elif args.case == 'has-include':
    source = '#if __has_include("optional.h")\n#include "optional.h"\n#else\n#define VALUE 1\n#endif\nint main(void) { return VALUE; }\n'
    if args.control:
        (fixture / 'optional.h').write_text('#define VALUE 1\n')
elif args.case == 'header-swap':
    source = '#include "a.h"\n#include "b.h"\nint main(void) { return VALUE; }\n'
    (fixture / 'a.h').write_text(header(1))
    (fixture / 'b.h').write_text(header(2))
else:
    source = 'int value(void);\nint main(void) { return value(); }\n'
    env['KACHE_CACHE_CC_LINKS'] = '1'
(fixture / 'unit.c').write_text(source)
if args.case == 'link-library':
    command([CLANG, '-c', 'unit.c', '-o', 'main.o'])
    library(1)
time.sleep(2.1)
rows = []
for phase in ['cold', 'warm', 'changed']:
    phase_env = env.copy()
    if args.case == 'epoch':
        phase_env['SOURCE_DATE_EPOCH'] = '946684800' if phase == 'changed' else '0'
    if phase == 'changed':
        if args.case == 'has-include':
            (fixture / 'optional.h').write_text('#define VALUE 2\n')
        elif args.case == 'header-swap':
            (fixture / 'a.h').write_text(header(2))
            (fixture / 'b.h').write_text(header(1 if not args.control else 3))
        elif args.case == 'link-library':
            library(2)
        time.sleep(2.1)
    if args.case == 'link-library':
        (fixture / 'app').unlink(missing_ok=True)
        argv = [KACHE, CLANG, 'main.o'] + (['libvalue.a'] if args.control else ['-L.', '-lvalue']) + ['-o', 'app']
    else:
        (fixture / 'unit.o').unlink(missing_ok=True)
        argv = [KACHE, CLANG, '-c', 'unit.c', '-o', 'unit.o']
    process = command(argv, phase_env)
    (fixture / (phase + '.stderr')).write_text(process.stderr)
    if args.case != 'link-library':
        command([CLANG, 'unit.o', '-o', 'app'], phase_env)
    run = command([str(fixture / 'app')], phase_env, check=False)
    events = [json.loads(line) for line in (fixture / 'cache/events.jsonl').read_text().splitlines()]
    actual = run.stdout.strip() if args.case == 'epoch' else run.returncode
    event = events[-1]
    row = dict(phase=phase, result=event.get('result'), key=event.get('cache_key'), actual=actual, compiler_runs=event.get('compiler_runs'))
    rows.append(row)
    print(json.dumps(row), flush=True)
if args.case == 'link-library':
    command([CLANG, 'main.o'] + (['libvalue.a'] if args.control else ['-L.', '-lvalue']) + ['-o', 'oracle-app'], phase_env)
else:
    command([CLANG, '-c', 'unit.c', '-o', 'oracle.o', f'-ffile-prefix-map={fixture}=/kache/cc-root'], phase_env)
    command([CLANG, 'oracle.o', '-o', 'oracle-app'], phase_env)
oracle = command([str(fixture / 'oracle-app')], phase_env, check=False)
expected = oracle.stdout.strip() if args.case == 'epoch' else oracle.returncode
print('DIRECT_ORACLE ' + str(expected), flush=True)
(fixture / 'observations.json').write_text(json.dumps(dict(baseline='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9', driver=CLANG, rows=rows, expected=expected), indent=2) + '\n')
assert rows[0]['result'] == 'miss', 'cold cache control did not miss'
assert rows[1]['result'] == 'local_hit', 'unchanged warm cache control did not hit'
assert rows[0]['actual'] == rows[1]['actual'], 'warm control changed output'
assert rows[-1]['actual'] == expected, f'CACHE_INTEGRITY_FAILURE: {args.case}: cached {rows[-1]["actual"]!r}, direct compiler expected {expected!r}; result={rows[-1]["result"]}'
print('PASS: cache result agrees with direct compiler')
