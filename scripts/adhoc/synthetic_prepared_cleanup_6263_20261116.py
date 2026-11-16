"""Purpose: offline regression worker for issue 6263, 2026-11-16.

Inputs: repository root and scratch directory. Outputs: child PID and cleanup
marker in scratch. Runs only a synthetic Python child through real transport.
"""
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

root, scratch = map(Path, sys.argv[1:])
sys.path[:0] = [str(root / 'src'), str(root / 'notes/matched_cborg_2026-09-13'),
               str(root / 'notes/matched_cborg_2026-09-13/native_controls')]
from data_sheets_schema import native_prepared_worker as worker
from data_sheets_schema.native_execution import _signals
from run_native_canary import execute_child

ipc = scratch / 'ipc'
binding = dict(registration_raw=b'regression', attempt=scratch / 'attempt', max_age_seconds=60)
raw = worker.publish_prepared(ipc, **binding, source_sha256='a' * 64,
                              environment_sha256='b' * 64)
with _signals([]):
    worker.wait_proceed(ipc, prepared_raw=raw, **binding)
    attempt = scratch / 'attempt'
    attempt.mkdir()
    instruction = scratch / 'instruction'
    instruction.write_text('synthetic')
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: None)
    try:
        execute_child([sys.executable, '-I', '-c',
            'import os,time,pathlib; pathlib.Path("child.pid").write_text(str(os.getpid())); time.sleep(60)'],
            proxy=proxy, instruction=instruction, attempt=attempt, cwd=scratch,
            env=dict(os.environ), deadline_seconds=60, verify_launch=lambda: None)
    finally:
        (scratch / 'cleanup-completed').write_text('transport cleanup returned')
