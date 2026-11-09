"""Offline PR5531 fix-A command evidence, quiet-window guard and 3600s deadline.

Inputs: label and command argv. Outputs: scratch-pr5531-fix logs. 2026-11-08.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'

def main():
    label, *command = sys.argv[1:]
    SCRATCH.mkdir(exist_ok=True)
    while LOCK.exists():
        print('Quiet window active; waiting 60 seconds.', flush=True)
        time.sleep(60)
    env = dict(os.environ, PYTHONPATH=f'{ROOT}/src:{ROOT}',
               TMPDIR=str(SCRATCH), PYTHONDONTWRITEBYTECODE='1')
    started = time.monotonic()
    with (SCRATCH / f'{label}.log').open('w') as log:
        log.write(repr(command) + '\n'); log.flush()
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        while child.poll() is None:
            if LOCK.exists() or time.monotonic() - started > 3600:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
                log.write('\nSTOPPED: quiet lock or 3600-second deadline\n')
                return 124
            time.sleep(2)
        print(f'{label}: exit {child.returncode}; {time.monotonic()-started:.1f}s', flush=True)
        return child.returncode

if __name__ == '__main__':
    sys.exit(main())
