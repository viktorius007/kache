#!/usr/bin/env python3
"""Bound concurrent builds and gates; each writer keeps a private Cargo target."""
import fcntl,os,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
if sys.platform == 'darwin' and sys.argv[1:3] == ['just', 'check']:
 for key in ('HOME', 'TMPDIR'):
  value=os.environ.get(key,'')
  if value == '/private/tmp' or value.startswith('/private/tmp/'):
   sys.exit(f'{key} uses protected /private prefix; use the same directory through /tmp without resolving its path')
test_threads=os.environ.get('KACHE_PR_TEST_THREADS','2')
if test_threads not in ('1','2'):sys.exit('KACHE_PR_TEST_THREADS must be 1 or 2')
held=[]
exclusive=os.environ.get('KACHE_PR_EXCLUSIVE_GATE')=='1'
if exclusive:
 if sys.argv[1:] != ['just','check']:sys.exit('Exclusive reservation requires just check')
 for n in range(3):
  fd=(root/('build-slot-'+str(n)+'.lock')).open('a')
  fcntl.flock(fd,fcntl.LOCK_EX);held.append(fd)
else:
 while not held:
  for n in range(3 if sys.argv[1:3] == ['just', 'check'] else 4):
   fd=(root/('build-slot-'+str(n)+'.lock')).open('a')
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(fd);break
   except BlockingIOError:fd.close()
  if not held:time.sleep(2)
env=os.environ.copy()
env.update(RUSTC_WRAPPER='',KACHE_TEST_USE_CARGO_BIN_EXE='1',CARGO_BUILD_JOBS='2',RUST_TEST_THREADS=test_threads,HOST_CC='clang',HOST_CXX='clang++',CC='clang',CXX='clang++')
try:sys.exit(subprocess.call(sys.argv[1:],env=env))
finally:
 for fd in held:fd.close()
