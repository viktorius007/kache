import os, pathlib, subprocess, tempfile, json
root = pathlib.Path(__file__).resolve().parent.parent
case = pathlib.Path(tempfile.mkdtemp(prefix='emit-destination-', dir=root))
kache = '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
rustc = subprocess.check_output(['rustup','which','rustc'], text=True).strip()
(case/'config.toml').write_text('[cache]\nauto_gc = false\ndaemon_publish = false\n')
(case/'home').mkdir(); (case/'out').mkdir()
(case/'lib.rs').write_text('pub fn answer() -> u32 { 42 }\n')
env = {k:v for k,v in os.environ.items() if not k.startswith(('KACHE_', 'CARGO_', 'RUSTC_'))}
env.update(HOME=str(case/'home'), XDG_CONFIG_HOME=str(case/'home'), KACHE_CONFIG=str(case/'config.toml'), KACHE_HOST_CONFIG=str(case/'absent-host.toml'), KACHE_CACHE_DIR=str(case/'cache'), KACHE_PROGRESS='off', KACHE_AUTO_GC='0', KACHE_DAEMON_PUBLISH='0', KACHE_DEFERRED_DISCOVERY='0', RUSTC_WRAPPER='')
base=[rustc, '--crate-name','emit_probe','--crate-type','rlib','lib.rs','--out-dir',str(case/'out'),'--error-format=json','--json=artifacts']
def run(label, wrapped, destination):
 argv=([kache] if wrapped else [])+base+['--emit=metadata='+str(destination)]
 p=subprocess.run(argv, cwd=case, env=env, capture_output=True, text=True,timeout=30)
 (case/(label+'.stdout')).write_text(p.stdout); (case/(label+'.stderr')).write_text(p.stderr)
 print(label, 'exit=',p.returncode,'destination_exists=',destination.exists())
 assert p.returncode == 0, p.stderr
 return destination.exists()
first=case/'out/first.rmeta'; second=case/'out/second.rmeta'
assert run('cold',True,first), 'cold control missing output'
for p in (case/'out').iterdir(): p.unlink()
warm_exists=run('warm',True,second)
warm_files=[p.name for p in (case/'out').iterdir()]
for p in (case/'out').iterdir(): p.unlink()
assert run('direct',False,second), 'direct control missing requested destination'
(case/'invocation.json').write_text(json.dumps({'case':str(case),'rustc':rustc,'warm_files':warm_files,'warm_destination_exists':warm_exists},indent=2))
print('CASE',case,'warm_files=',warm_files)
assert warm_exists, 'CACHE_EMIT_DESTINATION: hit failed to materialize requested --emit=metadata path'
