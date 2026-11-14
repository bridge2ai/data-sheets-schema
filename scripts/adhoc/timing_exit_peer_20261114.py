"""Issue 6239 offline exit peer, 2026-11-14.
Input: existing scratch directory. Output: timing sidecar after delayed handoff.
"""
from pathlib import Path
import sys
import time
from data_sheets_schema import native_pre_dispatch_timing as timing

original = timing.Trace.flush
def delayed(self):
    time.sleep(.1)
    original(self)
timing.Trace.flush = delayed
with timing.scope(b'exit-peer'):
    timing.bind({'attempt_directory': str(Path(sys.argv[1]) / 'attempt')})
    timing.record('last operation')
