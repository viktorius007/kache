#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parent.parent
artifact = root / 'investigation'
base = pathlib.Path(os.environ.get('KACHE_INV_DEP_TARGET', '/private/tmp/kache-d5-release-target/release'))
overlay = artifact / 'overlay'
(overlay / 'src').mkdir(parents=True, exist_ok=True)
for source in (root / 'src').iterdir():
    destination = overlay / 'src' / source.name
    if source.name in ('main.rs', 'daemon.rs'):
        destination.write_bytes(source.read_bytes())
    elif not destination.exists():
        destination.symlink_to(source)
test_path = overlay / 'daemon-tests.rs'
tests = (root / 'src/daemon/tests.rs').read_text()
for source in ('entry-budget-test.rs', 'plan-deadline-test.rs'):
    tests += (artifact / source).read_text()
test_path.write_text(tests)
daemon_path = overlay / 'src/daemon.rs'
daemon_path.write_text(daemon_path.read_text().replace('mod tests;', f'#[path = "{test_path}"]\nmod tests;'))
for name in ('assets', 'tests', 'docs'):
    link = artifact / 'overlay' / name
    if not link.exists():
        link.symlink_to(root / name)
fingerprints = list((base / '.fingerprint').glob('kache-*/test-bin-kache.json'))
if len(fingerprints) != 1:
    raise RuntimeError(f'Expected one baseline test fingerprint: {fingerprints}')
fingerprint = json.loads(fingerprints[0].read_text())
launcher_dirs = [p for p in (base / 'build').glob('kache-*/out') if (p / 'build-script-launcher').exists()]
if len(launcher_dirs) != 1:
    raise RuntimeError(f'Expected one baseline launcher directory: {launcher_dirs}')
args = ['rustc', '--crate-name', 'kache', '--edition=2024', '--test', str(artifact / 'overlay/src/main.rs'), '-C', 'opt-level=0', '-C', 'debuginfo=0', '-C', 'codegen-units=4', '-C', 'lto=thin', '-L', f'dependency={base / "deps"}', '-o', str(artifact / 'pack-probe')]
for _, name, _, dep_fingerprint in fingerprint['deps']:
    if name == 'build_script_build':
        continue
    stem = 'opendal_core' if name == 'opendal' else name
    candidates = list((base / 'deps').glob(f'lib{stem}-*.rlib')) or list((base / 'deps').glob(f'lib{stem}-*.dylib'))
    if len(candidates) > 1:
        matching = []
        for p in candidates:
            suffix = p.stem.rsplit('-', 1)[1]
            for fp_dir in (base / '.fingerprint').glob(f'*-{suffix}'):
                for fp in fp_dir.glob('lib-*'):
                    if fp.suffix == '.json':
                        continue
                    if int.from_bytes(bytes.fromhex(fp.read_text().strip()), 'little') == dep_fingerprint:
                        matching.append(p)
        candidates = matching
    if len(candidates) != 1:
        raise RuntimeError(f'{name}: expected one prebuilt dependency, found {candidates}')
    args += ['--extern', f'{name}={candidates[0]}']
for out in (base / 'build').glob('*/out'):
    args += ['-L', f'native={out}']
env = os.environ.copy()
env.update(CARGO_PKG_VERSION='1.0.0', CARGO_MANIFEST_DIR=str(root), OUT_DIR=str(launcher_dirs[0]), RUSTC_WRAPPER='', HOST_CC='clang', HOST_CXX='clang++', CC='clang', CXX='clang++')
(artifact / 'rustc-command.json').write_text(json.dumps(args, indent=2))
with (artifact / 'build-probe.log').open('w') as log:
    result = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT)
print(f'BUILD_PROBE_EXIT: {result.returncode}')
if result.returncode:
    print((artifact / 'build-probe.log').read_text())
sys.exit(result.returncode)
