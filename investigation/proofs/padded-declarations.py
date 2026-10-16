import os,pathlib,subprocess,tempfile,time,json
CONTROL='--control' in __import__('sys').argv
BASE=pathlib.Path(__file__).resolve().parents[2]
BINARY='/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
with tempfile.TemporaryDirectory(prefix='padded-',dir=BASE/'investigation') as tmp:
 root=pathlib.Path(tmp); pkg=root/'pkg'; pkg.mkdir(); unit=root/'target/debug/build/pkg-1234567890abcdef'; unit.mkdir(parents=True); out=unit/'out'; out.mkdir(); cfg=root/'config.toml'; cfg.write_text('[cache]\nbuild_script_hermetic = false\n')
 (pkg/'input').write_text('stable'); real=unit/'build-script-build.kache-real'; real.write_text('#!/bin/sh\nprintf "cargo:rerun-if-changed=input\\n  cargo:rerun-if-env-changed=APP_MODE  \\n"\nprintf "%s" "$APP_MODE" > "$OUT_DIR/value"\n'); 
 if CONTROL: real.write_text(real.read_text().replace('  cargo:rerun-if-env-changed=APP_MODE  ', 'cargo:rerun-if-env-changed=APP_MODE'))
 real.chmod(0o755)
 env={k:v for k,v in os.environ.items() if not k.startswith(('KACHE_','CARGO_','RUSTC_')) and k not in ('OUT_DIR','RUSTFLAGS')}; env.update(HOME=str(root/'home'),CARGO_HOME=str(root/'home/.cargo'),KACHE_CONFIG=str(cfg),KACHE_HOST_CONFIG='',KACHE_CACHE_DIR=str(root/'cache'),KACHE_RUNTIME_DIR=str(root/'cache'),KACHE_DAEMON_PUBLISH='0',KACHE_BUILD_SCRIPT_PATH=str(unit/'build-script-build'),OUT_DIR=str(out),CARGO_MANIFEST_DIR=str(pkg),CARGO_PKG_NAME='pkg',TARGET='aarch64-apple-darwin',HOST='aarch64-apple-darwin',PROFILE='debug')
 time.sleep(.2)
 outputs=[]
 for mode in ['first','second']:
  env['APP_MODE']=mode
  p=subprocess.run([BINARY],cwd=pkg,env=env,capture_output=True,timeout=30)
  print('RUN',mode,'exit',p.returncode,'stdout',p.stdout.decode(),'stderr',p.stderr.decode(),flush=True)
  assert p.returncode==0
  outputs.append((out/'value').read_text())
  (out/'value').unlink()
 print('OUTPUTS',outputs,flush=True)
 print('EVENTS',(root/'cache/events.jsonl').read_text(),flush=True)
 assert outputs == ['first','second'], 'STALE_BUILD_SCRIPT_ENV: expected second generated output, got '+repr(outputs)
