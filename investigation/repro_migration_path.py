#!/usr/bin/env python3
"""Doctor migration must leave Cargo pointing to an executable wrapper."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib

BASELINE = Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
CARGO = Path('/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/cargo')
ROOT = Path(__file__).resolve().parent


def run(argv, env, cwd):
    result = subprocess.run([str(a) for a in argv], env=env, cwd=cwd, text=True,
                            capture_output=True, timeout=30)
    return dict(argv=[str(a) for a in argv], returncode=result.returncode,
                stdout=result.stdout, stderr=result.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, default=ROOT / 'migration-path-evidence.json')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='migration-', dir=ROOT) as fixture:
        home = Path(fixture)
        cargo_home = home / '.cargo'
        cargo_home.mkdir()
        binary_dir = home / 'bin'
        binary_dir.mkdir()
        (binary_dir / 'kache').symlink_to(BASELINE)
        # Keep the migration from observing or stopping the user's sccache.
        (binary_dir / 'pgrep').write_text('#!/bin/sh\nexit 1\n')
        (binary_dir / 'pgrep').chmod(0o755)
        old_dir = home / 'old-wrapper'
        old_dir.mkdir()
        old_wrapper = old_dir / 'sccache'
        old_wrapper.write_text('#!/bin/sh\nexec "$@"\n')
        old_wrapper.chmod(0o755)
        config = cargo_home / 'config.toml'
        config.write_text('[build]\nrustc-wrapper = ' + json.dumps(str(old_wrapper)) + '\n')
        project = home / 'project'
        (project / 'src').mkdir(parents=True)
        (project / 'Cargo.toml').write_text('[package]\nname="migration-audit"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
        (project / 'src/lib.rs').write_text('pub fn value() -> u32 { 42 }\n')
        kache_config = home / 'kache.toml'
        kache_config.write_text('[cache]\nlocal_only = true\nauto_gc = false\n')
        env = dict(HOME=str(home), CARGO_HOME=str(cargo_home), SHELL='/bin/bash',
                   PATH=str(binary_dir) + ':' + str(CARGO.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
                   XDG_CONFIG_HOME=str(home / '.config'), KACHE_CONFIG=str(kache_config),
                   KACHE_HOST_CONFIG='', KACHE_CACHE_DIR=str(home / 'cache'),
                   KACHE_RUNTIME_DIR=str(home / 'runtime'), KACHE_LOG='off', KACHE_LOG_FILE='off',
                   KACHE_LOG_FILE_PATH=str(home / 'kache.log'), RUSTC=str(CARGO.with_name('rustc')),
                   RUSTUP_HOME='/Users/viktor/.rustup')
        before = config.read_text()
        before_cargo = run([CARGO, 'check', '--offline', '--target-dir', home / 'target-before'], env, project)
        assert before_cargo['returncode'] == 0, 'CONTROL_FAILED: old absolute wrapper must work: ' + str(before_cargo)
        migration = run([BASELINE, 'doctor', '--fix'], env, project)
        after = config.read_text()
        chosen = tomllib.loads(after)['build']['rustc-wrapper']
        after_cargo = run([CARGO, 'check', '--offline', '--target-dir', home / 'target-after'], env, project)
        observations = dict(before=before, after=after, before_cargo=before_cargo,
                            migration=migration, after_cargo=after_cargo,
                            configured_wrapper=chosen, wrapper_exists=Path(chosen).is_file())
        args.evidence.write_text(json.dumps(observations, indent=2) + '\n')
        assert after_cargo['returncode'] == 0, (
            'MIGRATION_WRAPPER_BROKEN: doctor --fix rewrote an absolute sccache wrapper path to a nonexistent kache path;\n'
            + after_cargo['stderr'])


if __name__ == '__main__':
    main()
