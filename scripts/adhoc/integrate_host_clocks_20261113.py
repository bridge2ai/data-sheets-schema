#!/usr/bin/env python3
"""Issue 6046: add host start/end hooks around the existing cleanup boundary.
Input/output: own worktree orchestration source; no execution. 2026-11-13.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/'src/data_sheets_schema/native_execution_orchestration.py'
s=p.read_text();start='    with _signals(signals):\n'
assert s.count(start)==1
s=s.replace(start,'    from . import native_host_power as host_power\n    host_power.start_run(attempt)\n'+start)
first=s.index('            pending_error = sys.exc_info()[1]\n',s.index('    host_power.start_run(attempt)'))
last=s.index('        try:\n            # Cleanup failure',first)
body=s[first:last]
s=s[:first]+'            with host_power.finishing_run(attempt):\n'+''.join('    '+line if line.strip() else line for line in body.splitlines(keepends=True))+s[last:]
p.write_text(s)
