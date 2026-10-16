import os, pathlib, subprocess, tempfile, json, shutil
root = pathlib.Path(__file__).resolve().parent.parent
case = pathlib.Path(tempfile.mkdtemp(prefix='diagnostic-', dir=root))
kache = '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
rustc = subprocess.check_output(['rustup','which','rustc'], text=True).strip()
(case/'config.toml').write_text('[cache]\nauto_gc = false\ndaemon_publish = false\n')
(case/'home').mkdir(); (case/'out').mkdir()
(case/'lib.rs').write_text('pub fn answer() -> u32 { let unused = 1; 42 }\n')
env = {k:v for k,v in os.environ.items() if not k.startswith(('KACHE_', 'CARGO_', 'RUSTC_'))}
env.update(HOME=str(case/'home'), XDG_CONFIG_HOME=str(case/'home'), KACHE_CONFIG=str(case/'config.toml'), KACHE_HOST_CONFIG=str(case/'absent-host.toml'), KACHE_CACHE_DIR=str(case/'cache'), KACHE_PROGRESS='off', KACHE_AUTO_GC='0', KACHE_DAEMON_PUBLISH='0', KACHE_DEFERRED_DISCOVERY='0', RUSTC_WRAPPER='')
args=[rustc, '--crate-name','format_probe','--crate-type','rlib','--emit=link,metadata,dep-info','lib.rs','--out-dir',str(case/'out')]
def run(label, argv):
 p=subprocess.run(argv, cwd=case, env=env, capture_output=True, text=True,timeout=30)
 (case/(label+'.stdout')).write_text(p.stdout); (case/(label+'.stderr')).write_text(p.stderr)
 print(label, 'exit=',p.returncode,'stderr=',repr(p.stderr[:180]))
 assert p.returncode == 0
 return p
run('human_cold',[kache]+args+['--error-format=human'])
for p in (case/'out').iterdir(): p.unlink()
cached=run('json_warm',[kache]+args+['--error-format=json'])
fresh=run('json_direct',args+['--error-format=json'])
(case/'invocation.json').write_text(json.dumps({'case':str(case),'rustc':rustc,'cache_entries':[str(p) for p in (case/'cache').rglob('meta.json')]},indent=2))
print('CASE',case)
assert fresh.stderr.lstrip().startswith('{'), 'control rustc did not emit JSON'
assert cached.stderr.lstrip().startswith('{'), 'CACHE_DIAGNOSTIC_FORMAT: --error-format=json replayed human diagnostics'
