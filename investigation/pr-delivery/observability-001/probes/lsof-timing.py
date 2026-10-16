#!/usr/bin/env python3
import json,os,socket,subprocess,time
from pathlib import Path
with socket.socket() as listener:
    listener.bind(('127.0.0.1',0)); listener.listen(1); port=listener.getsockname()[1]
    argv=['/usr/sbin/lsof','-nP','-a','-i','TCP@127.0.0.1:'+str(port),'-sTCP:LISTEN','-Fp']
    rows=[]
    for sample in range(3):
        start=time.monotonic(); result=subprocess.run(argv,capture_output=True,text=True,timeout=10)
        rows.append({'sample':sample,'elapsed_ms':(time.monotonic()-start)*1000,'exit':result.returncode,'stdout':result.stdout,'expected_pid':os.getpid()})
    Path(__file__).resolve().parents[1].joinpath('evidence/lsof-timing.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(rows,indent=2))
