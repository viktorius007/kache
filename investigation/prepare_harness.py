from pathlib import Path
import re
import shutil
root = Path(__file__).resolve().parent.parent
out = root/'investigation'
manifest = (root/'Cargo.toml').read_text()
start = manifest.index('[workspace]')
end = manifest.index('[dependencies]')
manifest = manifest[:start]+'[workspace]\n\n[[bin]]\nname = "permit-probe"\npath = "harness.rs"\n\n'+manifest[end:]
manifest = re.sub(r'path = "crates/', 'path = "../crates/', manifest)
manifest = manifest.replace('rust-version = "1.95"', 'rust-version = "1.95"\nbuild = "../build.rs"')
(out/'Cargo.toml').write_text(manifest)
source_dir = out/'source'
source_dir.mkdir(exist_ok=True)
for child in (root/'src').iterdir():
    if child.name != 'main.rs':
        target = source_dir/child.name
        if not target.exists(): target.symlink_to(child)
for name in ['assets', 'tests', 'test-projects', 'launcher']:
    target = out/name
    if not target.exists(): target.symlink_to(root/name)
source = (root/'src/main.rs').read_text()
source += '\n#[cfg(test)]\n#[path = "../remote_permits_probe.rs"]\nmod remote_permits_probe;\n'
(source_dir/'main.rs').write_text(source)
manifest = manifest.replace('path = "harness.rs"', 'path = "source/main.rs"')
(out/'Cargo.toml').write_text(manifest)
tests = (root/'src/daemon/tests.rs').read_text()
fixture = tests[tests.index('pub(super) fn test_config'):tests.index('\nfn test_cache_key')]
fixture = fixture.replace('pub(super) fn test_config', 'fn test_config')
(out/'config_fixture.rs').write_text(fixture)

shutil.copyfile(root/'Cargo.lock', out/'Cargo.lock')
