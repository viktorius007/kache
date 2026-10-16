import concurrent.futures,json,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
rows=json.loads((root/'root-replay-manifest.json').read_text())
groups={}
for row in rows:groups.setdefault(row['owner'],[]).append(row)
def run_group(items):
 results=[]
 for row in items:
  case=Path(row['case']); fixture=root/'root-replay'/('envelope-'+case.stem)
  fixture.mkdir(exist_ok=True)
  for d in ['home','cargo','cache','runtime','tmp']:(fixture/d).mkdir(exist_ok=True)
  config=fixture/'config.toml';config.write_text('[cache]\nlocal_only = true\ndaemon_publish = false\n')
  env={k:v for k,v in os.environ.items() if not k.startswith(('KACHE_','CARGO_','RUSTC_'))}
  env.update(HOME=str(fixture/'home'),CARGO_HOME=str(fixture/'cargo'),RUSTUP_HOME='/Users/viktor/.rustup',KACHE_CONFIG=str(config),KACHE_HOST_CONFIG=str(fixture/'absent-host.toml'),KACHE_CACHE_DIR=str(fixture/'cache'),KACHE_RUNTIME_DIR=str(fixture/'runtime'),TMPDIR=str(fixture/'tmp'),RUSTC_WRAPPER='')
  log=case.with_suffix('.log')
  try:
   run=subprocess.run(['python3',str(root/'replay-gate.py'),str(case),'--output',str(log)],cwd=root.parent,env=env,capture_output=True,text=True,timeout=600)
   verdict=json.loads(run.stdout) if run.stdout.strip() else {'error':run.stderr,'gate_exit':run.returncode}
  except Exception as error:verdict={'error':str(error)}
  record={**row,**verdict}
  case.with_suffix('.verdict.json').write_text(json.dumps(record,indent=2))
  print(row['owner'],case.stem,verdict.get('verdict',verdict),flush=True);results.append(record)
 return results
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 results=[r for group in pool.map(run_group,groups.values()) for r in group]
(root/'root-replay-results.json').write_text(json.dumps(results,indent=2))
