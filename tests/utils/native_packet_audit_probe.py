"""G13 audit canary, 2026-11-12: invoke safe attempted effects, expect denial.
Inputs explicit output/action. Output stdout only. No native executable path.
"""
import importlib.util
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
    else:
        raise ValueError(action)
except module.OfflineViolation as exc:
    print('DENIED '+str(exc))
else:
    raise AssertionError('effect unexpectedly allowed')
