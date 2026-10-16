#!/usr/bin/env python3
"""Baseline CLI must preserve valid Cargo configuration during rustdoc setup."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib

BASELINE = Path('/Users/viktor/Developer/github/kache-prs/cargo-build-001/target/debug/kache')
CARGO = Path('/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/cargo')
RUSTC = CARGO.with_name('rustc')
ROOT = Path(__file__).resolve().parent


def run(argv, env, cwd):
    result = subprocess.run([str(a) for a in argv], env=env, cwd=cwd, text=True,
                            capture_output=True, timeout=30)
    return dict(argv=[str(a) for a in argv], returncode=result.returncode,
                stdout=result.stdout, stderr=result.stderr)


def exercise(name, header):
    with tempfile.TemporaryDirectory(prefix='rustdoc-' + name + '-', dir='/tmp') as fixture, \
         tempfile.TemporaryDirectory(prefix='kcr-', dir='/tmp') as runtime:
        home = Path(fixture)
        cargo_home = home / '.cargo'
        cargo_home.mkdir()
        config = cargo_home / 'config.toml'
        config.write_text(header + '\nrustc-wrapper = "kache"\n[env]\n'
                          'HOST_CC = "clang"\nHOST_CXX = "clang++"\n'
                          'CC_KNOWN_WRAPPER_CUSTOM = "kache"\n')
        project = home / 'project'
        (project / 'src').mkdir(parents=True)
        (project / 'Cargo.toml').write_text('[package]\nname="rustdoc-audit"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
        (project / 'src/lib.rs').write_text('pub fn value() -> u32 { 42 }\n')
        binary_dir = home / 'bin'
        binary_dir.mkdir()
        (binary_dir / 'kache').symlink_to(BASELINE)
        kache_config = home / 'kache.toml'
        kache_config.write_text('[cache]\nlocal_only = true\ndaemon_idle_timeout_secs = 15\n'
                                'auto_gc = false\nauto_clean_orphaned_targets = false\n'
                                'auto_clean_unused_units_days = 0\nseed_new_targets = false\n')
        env = dict(HOME=str(home), CARGO_HOME=str(cargo_home), SHELL='/bin/bash',
                   PATH=str(binary_dir) + ':' + str(CARGO.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
                   XDG_CONFIG_HOME=str(home / '.config'), XDG_CACHE_HOME=str(home / '.cache'),
                   KACHE_CONFIG=str(kache_config), KACHE_HOST_CONFIG='',
                   KACHE_CACHE_DIR=str(home / 'cache'), KACHE_RUNTIME_DIR=runtime,
                   KACHE_SOCKET_PATH=str(Path(runtime) / 'daemon.sock'),
                   KACHE_LOG='off', KACHE_LOG_FILE='off', KACHE_LOG_FILE_PATH=str(home / 'kache.log'),
                   RUSTC=str(RUSTC), RUSTC_WRAPPER='', RUSTUP_HOME='/Users/viktor/.rustup')
        before = config.read_text()
        tomllib.loads(before)
        before_cargo = run([CARGO, 'metadata', '--no-deps', '--format-version=1', '--offline'], env, project)
        assert before_cargo['returncode'] == 0, before_cargo
        # Installation and startup target only this fixture, with no login service.
        setup = None
        try:
            setup = run([BASELINE, 'init', '--yes', '--no-service'], env, project)
            after = config.read_text()
            try:
                parsed = tomllib.loads(after)
                error = None
                configured = parsed.get('build', {}).get('rustdoc')
            except tomllib.TOMLDecodeError as exc:
                error = str(exc)
                configured = None
            after_cargo = run([CARGO, 'metadata', '--no-deps', '--format-version=1', '--offline'], env, project)
        finally:
            stop = run([BASELINE, 'daemon', 'stop'], env, project)
        return dict(name=name, before=before, after=after, before_cargo=before_cargo,
                    setup=setup, after_cargo=after_cargo, parse_error=error,
                    rustdoc=configured, cleanup=stop)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, default=ROOT / 'rustdoc-config-evidence.json')
    args = parser.parse_args()
    observations = [exercise('plain', '[build]'), exercise('comment', '[build] # Existing compiler configuration')]
    args.evidence.write_text(json.dumps(observations, indent=2) + '\n')
    control, commented = observations
    assert all(x['setup']['returncode'] == 0 for x in observations), 'CONTROL_FAILED: both init invocations must report success'
    assert control['parse_error'] is None and control['rustdoc'], 'CONTROL_FAILED: plain Cargo table must configure rustdoc'
    assert control['after_cargo']['returncode'] == 0, 'CONTROL_FAILED: plain Cargo table must remain usable'
    assert commented['parse_error'] is None and commented['after_cargo']['returncode'] == 0, (
        'RUSTDOC_CONFIG_CORRUPTED: init appended duplicate [build] to a valid commented table; '
        + str(commented['parse_error']) + '\n' + commented['after_cargo']['stderr'])


if __name__ == '__main__':
    main()
