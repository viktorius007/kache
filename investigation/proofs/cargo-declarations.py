"""Tiny real-Cargo audit probes; all writable state is disposable and isolated."""
import json,os,pathlib,subprocess,tempfile,time,sys
BASE=pathlib.Path(__file__).resolve().parents[2]
BINARY='/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
INCREMENTAL='--incremental' in sys.argv
DIRECT='--direct' in sys.argv
sysroot=pathlib.Path(subprocess.check_output(['/opt/homebrew/opt/rustup/bin/rustc','--print','sysroot'],text=True).strip())
CARGO=str(sysroot/'bin/cargo'); RUSTC=str(sysroot/'bin/rustc')
with tempfile.TemporaryDirectory(prefix='kache-cargo-',dir='/private/tmp') as tmp:
 root=pathlib.Path(tmp); pkg=root/'pkg'; (pkg/'src').mkdir(parents=True); home=root/'home'; (home/'.cargo').mkdir(parents=True)
 cfg=root/'kache.toml'; cfg.write_text('[cache]\nbuild_script_hermetic = false\n')
 (pkg/'Cargo.toml').write_text('[package]\nname = "declared-app"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n'+('[dependencies]\npm = { path = "pm" }\n' if INCREMENTAL else ''))
 (pkg/'input').write_text('stable')
 directive='cargo:rerun-if-env-changed=APP_MODE' if INCREMENTAL else '  cargo:rerun-if-env-changed=APP_MODE  '
 (pkg/'build.rs').write_text('fn main() { println!("cargo:rerun-if-changed=input"); println!("'+directive+'"); std::fs::write(std::path::Path::new(&std::env::var("OUT_DIR").unwrap()).join("value"),std::env::var("APP_MODE").unwrap()).unwrap(); }')
 (pkg/'src/main.rs').write_text('fn main() { print!("{}", '+('pm::bake!()' if INCREMENTAL else 'include_str!(concat!(env!("OUT_DIR"),"/value"))')+'); }')
 if INCREMENTAL:
  (pkg/'pm/src').mkdir(parents=True); (pkg/'pm/Cargo.toml').write_text('[package]\nname="pm"\nversion="0.1.0"\nedition="2021"\n[lib]\nproc-macro=true\n')
  (pkg/'pm/src/lib.rs').write_text('extern crate proc_macro; #[proc_macro] pub fn bake(_: proc_macro::TokenStream) -> proc_macro::TokenStream { format!("{:?}",std::env::var("APP_MODE").unwrap()).parse().unwrap() }')
 env={k:v for k,v in os.environ.items() if not k.startswith(('KACHE_','CARGO_','RUSTC_','XDG_')) and k not in ('OUT_DIR','RUSTFLAGS')}; env.update(HOME=str(home),CARGO_HOME=str(home/'.cargo'),KACHE_CONFIG=str(cfg),KACHE_HOST_CONFIG='',KACHE_CACHE_DIR=str(root/'cache'),KACHE_RUNTIME_DIR=str(root/'runtime'),KACHE_DAEMON_PUBLISH='0',KACHE_DAEMON_IDLE_TIMEOUT='1',CARGO_TARGET_DIR=str(root/'target'),CARGO_INCREMENTAL='1' if INCREMENTAL else '0',KACHE_CACHE_EXECUTABLES='1',RUSTC=RUSTC,RUSTC_WRAPPER='' if DIRECT else BINARY,HOST_CC='clang',HOST_CXX='clang++',CC='clang',CXX='clang++')
 if INCREMENTAL: env['KACHE_INCREMENTAL_CRATES']='declared_app'
 print('VERSIONS',subprocess.check_output([CARGO,'-V'],text=True).strip(),subprocess.check_output([RUSTC,'-V'],text=True).strip(),flush=True)
 time.sleep(.2); outputs=[]
 try:
  for mode in ['first','second']:
   env['APP_MODE']=mode
   result=subprocess.run([CARGO,'build','--offline','-j','1'],cwd=pkg,env=env,capture_output=True,timeout=45)
   print('BUILD',mode,'EXIT',result.returncode,'STDERR',result.stderr.decode(),flush=True); assert result.returncode==0
   output=subprocess.check_output([str(root/'target/debug/declared-app')],text=True); outputs.append(output)
  print('OUTPUTS',outputs,flush=True)
  log=root/'runtime/events.jsonl'
  if log.exists():
   events=[json.loads(s) for s in log.read_text().splitlines()]; print('EVENTS',json.dumps([{k:e.get(k) for k in ['crate_name','result','cache_key','passthrough_reason','incremental_policy']} for e in events]),flush=True)
  if INCREMENTAL:
   managed=list((root/'target/debug/incremental.kache-auto').rglob('query-cache.bin'))
   print('MANAGED_QUERY_CACHES',[str(path.relative_to(root)) for path in managed],flush=True)
   assert managed, 'SEAM_FIXTURE_NOT_MANAGED: expected private rustc query cache'
  assert outputs==['first','second'], 'STALE_CARGO_DECLARATION_OUTPUT: changed declared environment must produce second output, got '+repr(outputs)
 finally:
  if not DIRECT: subprocess.run([BINARY,'daemon','stop'],cwd=root,env=env,capture_output=True,timeout=20)
