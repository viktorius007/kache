#!/usr/bin/env python3
"""Red public-contract test: implicit Rust bin must respect cache_executables=0."""
import json
from pathlib import Path
import shutil
import sys
from contract_probes import FIX, RAW, KACHE, TOOLCHAIN, command, environment, events


def main():
    path = FIX / 'default-bin-policy'
    if path.exists():
        shutil.rmtree(path)
    env = environment('default-bin-policy')
    env['KACHE_CACHE_EXECUTABLES'] = '0'
    env['KACHE_FALLBACK'] = str(path / 'fallback-wrapper')
    source = path / 'main.rs'
    source.write_text('fn main(){println!("{}",cfg!(fallback_was_used));}\n')
    fallback = Path(env['KACHE_FALLBACK'])
    fallback.write_text('#!/bin/sh\ncompiler="$1"\nshift\nexec "$compiler" "$@" --cfg fallback_was_used\n')
    fallback.chmod(0o755)
    base = [KACHE, TOOLCHAIN / 'rustc', '--crate-name', 'default_bin_fixture', source, '--out-dir', path]
    command(base + ['--crate-type', 'bin'], path, env, 'default-bin-explicit-control')
    control = command([path / 'default_bin_fixture'], path, env, 'default-bin-explicit-run').strip()
    assert control == 'true', f'explicit bin must use the configured fallback: {control!r}'
    (path / 'default_bin_fixture').unlink()
    command(base, path, env, 'default-bin-implicit')
    observed = command([path / 'default_bin_fixture'], path, env, 'default-bin-implicit-run').strip()
    records = events(env)
    filename = 'default-bin-policy-control-events.json' if '--negative-control' in sys.argv else 'default-bin-policy-events.json'
    (RAW / filename).write_text(json.dumps(records, indent=2))
    print(f'CONTROL explicit --crate-type bin: fallback runtime output={control}', flush=True)
    print(f'OBSERVED omitted --crate-type: fallback runtime output={observed}', flush=True)
    if '--negative-control' in sys.argv:
        assert observed == 'false', 'manufactured control must reject an incorrect claimed defect'
        print('MANUFACTURED CONTROL: rejected incorrect claim that implicit bin already uses fallback')
        return
    assert observed == 'true', 'executable caching disabled must route default-bin rustc invocation through fallback; expected true, observed '+observed


if __name__ == '__main__':
    main()
