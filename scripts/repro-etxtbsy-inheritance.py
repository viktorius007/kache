import errno, os, shutil, subprocess, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix='titan-etxtbsy-') as directory:
    executable = Path(directory) / 'program'
    shutil.copyfile('/usr/bin/true', executable)
    executable.chmod(0o755)
    writer = os.open(executable, os.O_WRONLY)
    ready_read, ready_write = os.pipe()
    release_read, release_write = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(ready_read); os.close(release_write)
        os.write(ready_write, b'held')
        os.read(release_read, 1)
        os.close(writer)
        os._exit(0)
    os.close(ready_write); os.close(release_read)
    assert os.read(ready_read, 4) == b'held'
    os.close(writer)
    try:
        subprocess.run([str(executable)], check=True)
    except OSError as error:
        assert error.errno == errno.ETXTBSY, error
        print('Confirmed: the original writer is closed, but its forked child keeps exec blocked with ETXTBSY.')
    else:
        raise AssertionError('expected inherited writer to prevent execution')
    os.write(release_write, b'x')
    os.waitpid(child, 0)
    subprocess.run([str(executable)], check=True)
    print('After the inherited writer closes, the identical inode executes successfully. No timing window used.')
