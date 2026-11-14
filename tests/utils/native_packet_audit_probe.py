"""G13 audit canary, 2026-11-12: invoke safe attempted effects, expect denial.
Inputs explicit output/action. Output stdout only. No native executable path.
"""
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
path=Path(__file__).resolve().parents[2]/'scripts/build_native_canary_packet.py'
spec=importlib.util.spec_from_file_location('packet',path)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
out=Path(sys.argv[1]); action=sys.argv[2]
module.offline_guard(out)
try:
    if action=='process':
        subprocess.run([sys.executable,'--version'],check=True)
    elif action=='network':
        socket.socket()
    elif action=='write':
        (out.parent/'outside').write_text('must not exist')
    elif action=='symlink':
        (out/'link').symlink_to(out.parent/'outside')
    elif action in ('manifest-fd', 'other-fd', 'chmod-fd', 'truncate-fd'):
        path = out / ('other.json' if action == 'other-fd' else 'environment-manifest.json')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
        try:
            if action == 'chmod-fd':
                os.fchmod(fd, 0o600)
            elif action == 'truncate-fd':
                os.ftruncate(fd, 0)
            else:
                with os.fdopen(fd, 'wb', closefd=False) as stream:
                    stream.write(b'isolated descriptor canary\n')
        finally:
            os.close(fd)
        if action == 'manifest-fd':
            assert path.read_bytes() == b'isolated descriptor canary\n'
            assert path.stat().st_mode & 0o777 == 0o444
            print('ALLOWED exact manifest descriptor')
            raise SystemExit(0)
    elif action == 'outside-fd':
        # /dev/null is already outside the output and needs no mutable fixture.
        with open(os.devnull, 'rb') as stream:
            os.fdopen(stream.fileno(), 'wb', closefd=False)
    else:
        raise ValueError(action)
except module.OfflineViolation as exc:
    print('DENIED '+str(exc))
else:
    raise AssertionError('effect unexpectedly allowed')
