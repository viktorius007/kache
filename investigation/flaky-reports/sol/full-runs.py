import subprocess
for label,threads in [('R21',16),('R22',32),('R23',8),('R24',64),('R25',16),('R26',16)]:
 subprocess.run(['python3','/private/tmp/kache-flaky/sol/run.py',label,'./scripts/with-test-resources.sh','cargo','test','--workspace','--','--test-threads='+str(threads)])
