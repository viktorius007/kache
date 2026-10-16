import os,pathlib,subprocess,tempfile
CONTROL='--control' in __import__('sys').argv
BASE=pathlib.Path(__file__).resolve().parents[2]
BINARY='/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
with tempfile.TemporaryDirectory(prefix='env-comment-',dir='/private/tmp') as tmp:
 root=pathlib.Path(tmp); home=root/'home'; ch=home/'.cargo'; ch.mkdir(parents=True); config=ch/'config.toml'; original='[env] # host settings\nUSER_SETTING = "preserved"\n'; original=original.replace('[env] # host settings','[env]') if CONTROL else original; config.write_text(original); kc=root/'kache.toml'; kc.write_text('')
 env={k:v for k,v in os.environ.items() if not k.startswith(('KACHE_','CARGO_','RUSTC_','XDG_')) and k not in ('OUT_DIR','RUSTFLAGS')}; env.update(HOME=str(home),CARGO_HOME=str(ch),KACHE_CONFIG=str(kc),KACHE_HOST_CONFIG='',KACHE_CACHE_DIR=str(root/'cache'),KACHE_RUNTIME_DIR=str(root/'runtime'),KACHE_DAEMON_PUBLISH='0')
 p=subprocess.run([BINARY,'init','--yes','--no-shell','--no-service'],cwd=root,env=env,capture_output=True,timeout=30)
 
 if CONTROL: subprocess.run([BINARY,'daemon','stop'],cwd=root,env=env,capture_output=True,timeout=30)
 print('INIT_EXIT',p.returncode,flush=True); print(p.stdout.decode(),p.stderr.decode(),flush=True); print('CONFIG_UNCHANGED',config.read_text()==original,flush=True)
 assert p.returncode==0, 'VALID_COMMENTED_ENV_REJECTED: init must configure valid Cargo TOML with a commented env table'
