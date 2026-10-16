#!/usr/bin/env python3
"""Exercise public Rust contracts on an untouched baseline CLI in fixture homes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
KACHE = Path(os.environ.get('AUDIT_KACHE', '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'))
TOOLCHAIN = Path('/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin')
FIX = ROOT / 'fixtures'
RAW = ROOT / 'raw'


def command(argv, cwd, env, name, expected=0):
    p = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    result = dict(argv=list(map(str, argv)), workdir=str(cwd), returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    (RAW / (name + '.json')).write_text(json.dumps(result, indent=2))
    assert p.returncode == expected, f'{name}: expected exit {expected}, observed {p.returncode}: {p.stderr}'
    return p.stdout


def environment(group):
    home = FIX / group / 'home'
    home.mkdir(parents=True, exist_ok=True)
    conf = home / 'config.toml'
    conf.write_text('[cache]\nlocal_only = true\nadaptive_incremental = false\nseed_new_targets = false\nexplain_miss = true\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('KACHE_', 'CARGO_', 'RUSTC_', 'RUSTFLAGS', 'CLIPPY_'))}
    env.update(HOME=str(home), CARGO_HOME=str(home / 'cargo'), RUSTUP_HOME='/Users/viktor/.rustup', RUSTC=str(TOOLCHAIN / 'rustc'),
               RUSTC_WRAPPER=str(KACHE), KACHE_CONFIG=str(conf), KACHE_HOST_CONFIG='', KACHE_CACHE_DIR=str(home / 'store'),
               KACHE_RUNTIME_DIR=str(home / 'runtime'), KACHE_SOCKET_PATH=str(home / 'runtime' / 'absent.sock'),
               KACHE_LOG='warn', KACHE_PROGRESS='verbose', HOST_CC='clang', HOST_CXX='clang++', CC='clang', CXX='clang++')
    return env


def project(path, source, build=None):
    (path / 'src').mkdir(parents=True)
    (path / 'Cargo.toml').write_text('[package]\nname="contract-fixture"\nversion="0.1.0"\nedition="2021"\n[workspace]\n[features]\nchanged=[]\n')
    (path / 'src/main.rs').write_text(source)
    if build:
        (path / 'build.rs').write_text(build)
        (path / 'input.txt').write_text('first')


def build(path, env, name, extra=()):
    command([TOOLCHAIN / 'cargo', 'build', '--offline', '--target-dir', path / 'target', *extra], path, env, name)
    return command([path / 'target/debug/contract-fixture'], path, env, name + '-run').strip()


def events(env):
    return [json.loads(line) for p in Path(env['KACHE_RUNTIME_DIR']).rglob('*.jsonl') for line in p.read_text().splitlines() if line.strip()]


def relocation():
    env = environment('relocation')
    source = 'fn main(){println!("{} {}", env!("AUDIT_VALUE"), cfg!(feature="changed"));}\n'
    a, b = FIX / 'relocation/a', FIX / 'relocation/b'
    project(a, source)
    project(b, source)
    env['AUDIT_VALUE'] = 'original'
    assert build(a, env, 'relocation-cold') == 'original false'
    assert build(b, env, 'relocation-warm') == 'original false'
    shutil.rmtree(b / 'target')
    env['AUDIT_VALUE'] = 'updated'
    assert build(b, env, 'relocation-env-change') == 'updated false', 'compile-time environment changes must invalidate cached output'
    shutil.rmtree(b / 'target')
    assert build(b, env, 'relocation-feature-change', ['--features', 'changed']) == 'updated true', 'feature changes must invalidate cached output'
    records = events(env)
    (RAW / 'relocation-events.json').write_text(json.dumps(records, indent=2))
    assert any(e.get('result') == 'local_hit' and e.get('root') == str(b) and e.get('crate_name') == 'contract_fixture' and e.get('compiler_runs') == 0 and e.get('size', 0) > 0 for e in records), 'second checkout must exercise a real cache restore'
    print('PASS relocation output, compile-time env invalidation and feature invalidation')


def manifest_path():
    env = environment('manifest-path')
    source = 'fn main(){println!("{}",env!("CARGO_MANIFEST_DIR"));}\n'
    for tree in ['a', 'b']:
        path = FIX / 'manifest-path' / tree
        project(path, source)
        actual = build(path, env, 'manifest-' + tree)
        assert actual == str(path), f'runtime manifest path must equal current checkout: {actual}'
    (RAW / 'manifest-events.json').write_text(json.dumps(events(env), indent=2))
    print('PASS runtime manifest path remains checkout-local')


def build_script():
    env = environment('build-script')
    source = 'fn main(){println!("{}",include_str!(concat!(env!("OUT_DIR"),"/generated.txt")));}\n'
    script = '''fn main(){
println!("cargo:rerun-if-changed=input.txt");
println!("cargo:rerun-if-env-changed=AUDIT_SCRIPT_VALUE");
let out=std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap());
let input=std::fs::read_to_string("input.txt").unwrap();
let value=std::env::var("AUDIT_SCRIPT_VALUE").unwrap_or_else(|_| "unset".into());
std::fs::write(out.join("generated.txt"),format!("{}:{}",input,value)).unwrap();
}\n'''
    env['AUDIT_SCRIPT_VALUE'] = 'old'
    for tree in ['a', 'b']:
        path = FIX / 'build-script' / tree
        project(path, source, script)
        assert build(path, env, 'script-' + tree) == 'first:old'
    path = FIX / 'build-script/b'
    shutil.rmtree(path / 'target')
    (path / 'input.txt').write_text('second')
    assert build(path, env, 'script-input-change') == 'second:old', 'declared input changes must invalidate build-script run and Rust artifacts'
    shutil.rmtree(path / 'target')
    env['AUDIT_SCRIPT_VALUE'] = 'new'
    assert build(path, env, 'script-env-change') == 'second:new', 'declared environment changes must invalidate build-script run and Rust artifacts'
    records = events(env)
    (RAW / 'script-events.json').write_text(json.dumps(records, indent=2))
    assert any(e.get('result') == 'local_hit' and e.get('crate_name') == 'build_script_run' for e in records), 'canonical script fixture must exercise a cached build-script run'
    print('PASS build-script relocation, declared-file invalidation and declared-env invalidation')


def main():
    RAW.mkdir(exist_ok=True)
    assert KACHE.is_file(), KACHE
    if FIX.exists():
        shutil.rmtree(FIX)
    relocation()
    manifest_path()
    build_script()
    print('ALL PUBLIC-CONTRACT PROBES PASSED')


if __name__ == '__main__':
    main()
