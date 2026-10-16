import os,sys,subprocess,json,time
from pathlib import Path
root='/private/tmp/kache-flaky/sol'
label=sys.argv[1]; args=sys.argv[2:]
load=subprocess.check_output(['sysctl','-n','vm.loadavg'],text=True).strip()
env=os.environ.copy();env['CARGO_TARGET_DIR']=root+'/target';env['TMPDIR']='/tmp/kache-flaky/sol/t';os.makedirs(env['TMPDIR'],exist_ok=True)
row={'id':label,'command':args,'load':load,'start':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'threads':next((x.split('=')[1] for x in args if x.startswith('--test-threads=')), 'default')}
print(json.dumps(row),flush=True)
with open(root+'/logs/'+label+'.log','w') as log:
 log.write(json.dumps(row)+'\n');log.flush()
 p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,env=env)
row['exit']=p.returncode;row['end']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
with open(root+'/runs.jsonl','a') as f:f.write(json.dumps(row)+'\n')
print(json.dumps(row),flush=True)
