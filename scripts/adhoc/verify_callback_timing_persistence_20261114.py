"""Issue 6233, 2026-11-14: verify supplemental callback timing persistence.

Input: a completed or active diagnostic case directory. Output: verification JSON.
Optional --append-closed appends explicitly tagged measurements produced after
the controller closed its timing writer; requires the launcher exit-status file.
Existing bytes are preserved. Never repairs malformed historical timing files.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

case = Path(sys.argv[1]).resolve(strict=True)
rows = [json.loads(line) for line in (case / 'callback-cpu.jsonl').read_text().splitlines()]
assert rows
attempts = {row['timing_directory'] for row in rows}
assert len(attempts) == 1
target = Path(attempts.pop()) / 'host-controller-timing.jsonl'
assert target.is_file() and not target.is_symlink()
before = target.read_bytes()
host_rows = [json.loads(line) for line in before.splitlines()]
fields = ('work', 'event_type', 'tool', 'tool_use_id', 'line', 'calls',
          'thread_cpu', 'process_cpu', 'wall', 'records', 'unwound', 'cprofile_enabled')


def key(row):
    return row['work'], row['event_type'], row['line'], row['tool_use_id']


expected = {key(row): row for row in rows}
assert len(expected) == len(rows)
present = {}
for row in host_rows:
    if row.get('boundary') not in ('callback_cpu', 'callback_cpu_after_close'):
        continue
    identity = key(row)
    assert identity not in present and identity in expected
    assert all(row[field] == expected[identity][field] for field in fields)
    present[identity] = row
missing = [row for row in rows if key(row) not in present]
appended = 0
if '--append-closed' in sys.argv:
    # The shell writes this only after the Python process has exited, including
    # its non-daemon workers. It is not a production acceptance document.
    assert (case / 'exit-status.txt').is_file(), 'launcher has not recorded process exit'
    int((case / 'exit-status.txt').read_text())
    fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        for row in missing:
            supplement = {'boundary': 'callback_cpu_after_close',
                          'recorded_after_process_exit': True,
                          'recorded_wall_ns': time.time_ns(),
                          **{field: row[field] for field in fields}}
            raw = (json.dumps(supplement, sort_keys=True) + '\n').encode()
            assert os.write(fd, raw) == len(raw)
            appended += 1
    finally:
        os.close(fd)
after = target.read_bytes()
assert after.startswith(before), 'existing timing bytes changed'
verified = {}
for raw in after.splitlines():
    row = json.loads(raw)
    if row.get('boundary') not in ('callback_cpu', 'callback_cpu_after_close'):
        continue
    identity = key(row)
    assert identity in expected and identity not in verified
    assert all(row[field] == expected[identity][field] for field in fields)
    verified[identity] = row
result = {'independent_rows': len(rows), 'matching_controller_rows_before': len(present),
          'missing_before': len(missing), 'explicit_after_close_supplements': appended,
          'matching_controller_rows_after': len(verified),
          'fully_persisted': set(verified) == set(expected),
          'controller_path': str(target),
          'before_sha256': hashlib.sha256(before).hexdigest(),
          'after_sha256': hashlib.sha256(after).hexdigest()}
(case / 'timing-persistence-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
