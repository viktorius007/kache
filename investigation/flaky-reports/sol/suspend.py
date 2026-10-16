import subprocess,os,signal,time,re,sys
args=['env','KACHE_FLAKY_SUSPEND=1','./scripts/with-test-resources.sh','cargo','test','-p','kache','--bin','kache','test_wait_for_warming_blocks_then_signals','--','--test-threads=1','--nocapture']
print('INNER COMMAND: '+' '.join(args),flush=True)
p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
suspended=False
for line in p.stdout:
 print(line,end='',flush=True)
 m=re.search(r'FLAKY_SUSPEND_PID=(\d+)',line)
 if m:
  pid=int(m[1]);print('CONTROLLER stopping owned test PID '+str(pid),flush=True)
  os.kill(pid,signal.SIGSTOP)
  try:time.sleep(1.2)
  finally:os.kill(pid,signal.SIGCONT)
  print('CONTROLLER resumed owned test PID after 1.2 seconds',flush=True);suspended=True
rc=p.wait()
if not suspended:print('ERROR: never observed timing marker',flush=True);sys.exit(99)
sys.exit(rc)
