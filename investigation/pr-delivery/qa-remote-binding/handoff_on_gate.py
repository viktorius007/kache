import os, pathlib, select, subprocess, sys
D=pathlib.Path(__file__).resolve().parent
assert hasattr(select,'kqueue'), 'Handoff watcher requires macOS/BSD kqueue on this host'
exit_path=D/'gate-exit.txt'
queue=select.kqueue()
handles=[]
def watch(path):
    fd=os.open(path,os.O_RDONLY);handles.append(fd)
    event=select.kevent(fd,filter=select.KQ_FILTER_VNODE,flags=select.KQ_EV_ADD|select.KQ_EV_ENABLE|select.KQ_EV_CLEAR,fflags=select.KQ_NOTE_WRITE)
    queue.control([event],0,0)
watch(D)
file_watched=False
try:
    while True:
        if exit_path.exists():
            if not file_watched:
                watch(exit_path);file_watched=True
            value=exit_path.read_text().strip()
            if value:
                if value!='0':
                    print('FAIL_GATE '+str(exit_path)+' exit='+value,flush=True)
                    sys.exit(int(value))
                sys.exit(subprocess.call([sys.executable,str(D/'finalize.py')]))
        queue.control(None,1,None)
finally:
    for fd in handles:os.close(fd)
    queue.close()
