import ctypes,hashlib,json,os,pathlib,shutil,socket,subprocess,tempfile,time
DELIVERY=pathlib.Path(__file__).resolve().parent
WORKTREE=pathlib.Path('/Users/viktor/Developer/github/kache-prs/restoration-literal-marker')
BASELINE=pathlib.Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
expected='45840941809ca7c45622027f84d2c653c737e7ff35d375cfbf355b619456120f'
assert hashlib.sha256(BASELINE.read_bytes()).hexdigest()==expected
case=pathlib.Path(tempfile.mkdtemp(prefix='sandbox-discovery-',dir=WORKTREE/'target'))
denied=case/'denied';allowed=case/'allowed';denied.mkdir();allowed.mkdir()
source=case/'listener.c';server=case/'sccache'
source.write_text('''#include <arpa/inet.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>
int main(int argc,char **argv){if(argc!=2)return 2;int fd=socket(AF_INET,SOCK_STREAM,0);struct sockaddr_in addr={0};addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);addr.sin_port=htons(atoi(argv[1]));if(bind(fd,(struct sockaddr *)&addr,sizeof(addr))!=0)return 3;if(listen(fd,16)!=0)return 4;for(;;)pause();}
''')
subprocess.run(['/usr/bin/cc',source,'-o',server],check=True)
listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];listener.close()
profile=f'(version 1)(allow default)(deny file-write* (subpath "{denied.resolve()}"))'
child=subprocess.Popen(['/usr/bin/sandbox-exec','-p',profile,server,str(port)])
record=dict(case=str(case),baseline_sha256=expected,final_sha256=hashlib.sha256((WORKTREE/'target/debug/kache').read_bytes()).hexdigest(),commands=[],fixture_scope='Same listener/profile, assembler passthrough compiler and failing sccache scripts as fallback_recovery_test; recreated outside the Rust harness to expose discovery diagnostics.')
try:
 deadline=time.monotonic()+30
 while True:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.1):break
  except OSError:
   assert time.monotonic()<deadline,'listener not ready'
   time.sleep(.01)
 lib=ctypes.CDLL('/usr/lib/libsandbox.dylib');check=lib.sandbox_check;check.restype=ctypes.c_int
 no_report=ctypes.c_int.in_dll(lib,'SANDBOX_CHECK_NO_REPORT').value
 record['policy']={'pid':child.pid,'sandboxed':check(child.pid,None,0),'denied_create':check(child.pid,b'file-write-create',1|no_report,str(denied.resolve()).encode()),'allowed_create':check(child.pid,b'file-write-create',1|no_report,str(allowed.resolve()).encode())}
 for _ in range(4):
  argv=['/usr/sbin/lsof','-nP','-a','-i',f'TCP@127.0.0.1:{port}','-sTCP:LISTEN','-Fp']
  start=time.monotonic();out=subprocess.run(argv,capture_output=True,text=True,timeout=10)
  record['commands'].append(dict(argv=argv,elapsed_ms=round((time.monotonic()-start)*1000,2),exit=out.returncode,stdout=out.stdout,stderr=out.stderr))
 for fixture in [denied,allowed]:
  cc=fixture/'cc';fallback=fixture/'sccache';(fixture/'input.s').write_text('')
  cc.write_text('#!/bin/sh\nprintf "direct\\n" >> "$TEST_CALLS"\nprintf complete-object > "$TEST_OBJECT"\n')
  fallback.write_text('#!/bin/sh\nprintf "fallback\\n" >> "$TEST_CALLS"\nprintf partial > "$TEST_OBJECT"\necho "fallback compiler error" >&2\nexit 42\n')
  cc.chmod(0o755);fallback.chmod(0o755)
  for label,binary in [('baseline',BASELINE),('final',WORKTREE/'target/debug/kache')]:
   for path in [fixture/'calls',fixture/'object.o']:
    if path.exists():path.unlink()
   env=os.environ.copy();env.update(KACHE_CONFIG=str(fixture/'absent.toml'),KACHE_HOST_CONFIG='',KACHE_CACHE_DIR=str(fixture/'cache'),KACHE_BASE_DIR=str(fixture),KACHE_FALLBACK=str(fallback),KACHE_CACHE_EXECUTABLES='false',KACHE_REMOTE='',TEST_CALLS=str(fixture/'calls'),TEST_OBJECT=str(fixture/'object.o'),SCCACHE_SERVER_PORT=str(port))
   env.pop('KACHE_DISABLED',None);env.pop('SCCACHE_SERVER_UDS',None)
   argv=[str(binary),str(cc),'-xassembler-with-cpp','-c','input.s','-o','object.o']
   start=time.monotonic();out=subprocess.run(argv,cwd=fixture,env=env,capture_output=True,text=True,timeout=30)
   record['commands'].append(dict(label=label,fixture=fixture.name,argv=argv,elapsed_ms=round((time.monotonic()-start)*1000,2),exit=out.returncode,stdout=out.stdout,stderr=out.stderr,calls=(fixture/'calls').read_text()))
finally:
 child.terminate();child.wait(timeout=5)
 (DELIVERY/'logs/sandbox-discovery-diagnostic.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
