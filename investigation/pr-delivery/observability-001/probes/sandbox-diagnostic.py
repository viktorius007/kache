import ctypes,json,os,socket,subprocess,tempfile,time
from pathlib import Path
A=Path('/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/pr-delivery/observability-001')
with tempfile.TemporaryDirectory(prefix='obs-sandbox-',dir='/private/tmp') as tmp:
 root=Path(tmp);denied=root/'denied';denied.mkdir();source=root/'listener.c';server=root/'sccache'
 source.write_text('#include <arpa/inet.h>\n#include <stdlib.h>\n#include <sys/socket.h>\n#include <unistd.h>\nint main(int argc,char **argv){int fd=socket(AF_INET,SOCK_STREAM,0);struct sockaddr_in addr={0};addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);addr.sin_port=htons(atoi(argv[1]));if(bind(fd,(struct sockaddr *)&addr,sizeof(addr)))return 3;if(listen(fd,16))return 4;for(;;)pause();}\n')
 subprocess.run(['/usr/bin/cc',str(source),'-o',str(server)],check=True)
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 child=subprocess.Popen(['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny file-write* (subpath "'+str(denied)+'"))',str(server),str(port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  deadline=time.monotonic()+5
  while True:
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.1):break
   except OSError:
    if time.monotonic()>deadline:raise RuntimeError('sandbox listener did not become ready')
    time.sleep(.01)
  rows=[]
  for sample in range(3):
   start=time.monotonic();out=subprocess.run(['/usr/sbin/lsof','-nP','-a','-i','TCP@127.0.0.1:'+str(port),'-sTCP:LISTEN','-Fp'],capture_output=True,text=True,timeout=10)
   rows.append({'elapsed_ms':(time.monotonic()-start)*1000,'exit':out.returncode,'stdout':out.stdout,'stderr':out.stderr})
  lib=ctypes.CDLL('/usr/lib/libsandbox.dylib');check=lib.sandbox_check;check.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int];check.restype=ctypes.c_int
  no_report=ctypes.c_int.in_dll(lib,'SANDBOX_CHECK_NO_REPORT').value
  native={'sandboxed':check(child.pid,None,0),'denies_create':check(child.pid,b'file-write-create',1|no_report,ctypes.c_char_p(os.fsencode(denied))),'denies_data':check(child.pid,b'file-write-data',1|no_report,ctypes.c_char_p(os.fsencode(denied)))}
  result={'pid':child.pid,'server':str(server),'port':port,'lsof':rows,'native_policy':native}
  (A/'evidence/sandbox-diagnostic.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:
  child.kill();child.communicate()
