#!/usr/bin/env python3
"""Process-level fallback, cancellation and disable controls using real rustc."""
import json
import shutil
from pathlib import Path
from contract_probes import FIX, RAW, KACHE, TOOLCHAIN, command, environment


def main():
    path = FIX / 'fallback'
    if path.exists():
        shutil.rmtree(path)
    env = environment('fallback')
    env['KACHE_CACHE_EXECUTABLES'] = '0'
    source = path / 'main.rs'
    source.write_text('fn main(){println!("direct-result");}\n')
    wrapper = path / 'fallback'
    marker = path / 'fallback-ran'
    args = [KACHE, TOOLCHAIN / 'rustc', '--crate-name', 'fallback_fixture', '--crate-type', 'bin', source, '--out-dir', path]
    env['KACHE_FALLBACK'] = str(wrapper)
    for code in [42, 130, 143]:
        wrapper.write_text(f'#!/bin/sh\nprintf invoked > "{marker}"\nprintf fallback-diagnostic >&2\nexit {code}\n')
        wrapper.chmod(0o755)
        binary = path / 'fallback_fixture'
        binary.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
        command(args, path, env, f'fallback-exit-{code}', 0 if code == 42 else code)
        assert marker.read_text() == 'invoked', 'fallback must run before its exit result is evaluated'
        if code == 42:
            assert command([binary], path, env, 'fallback-direct-result').strip() == 'direct-result'
        else:
            assert not binary.exists(), f'cancellation {code} must not retry direct compiler'
    env['KACHE_FALLBACK'] = str(path / 'missing-fallback')
    command(args, path, env, 'fallback-missing')
    assert command([path / 'fallback_fixture'], path, env, 'fallback-missing-run').strip() == 'direct-result'
    env['KACHE_FALLBACK'] = str(wrapper)
    env['KACHE_DISABLED'] = '1'
    marker.unlink()
    command(args, path, env, 'disabled-no-fallback')
    assert not marker.exists(), 'KACHE_DISABLED must invoke rustc directly without fallback'
    assert command([path / 'fallback_fixture'], path, env, 'disabled-direct-run').strip() == 'direct-result'
    print('PASS fallback failure and spawn failure recover with direct result; 130/143 do not retry; disabled skips fallback')


if __name__ == '__main__':
    main()
