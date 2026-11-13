"""2026-11-13 codex197: interrupt only the superseded owned stage coordinator.

Input: saved exact attempt03 build-reference command. Output: PID/create-time
identity and interrupt proof in owned scratch. Coordinator SIGINT invokes its
existing descendant cleanup and held-outcome publication; never signals by name.
"""
import json
from pathlib import Path
import signal
import time
import psutil

E = Path(__file__).resolve().parents[3]
S = E / 'scratch-h3-resume-matrix-20261113'
declaration = json.loads((S / 'attempt03/build-reference-command.json').read_bytes())
matches = []
for process in psutil.process_iter(['pid', 'cmdline', 'create_time']):
    try:
        if process.info['cmdline'] == declaration['command'] and process.cwd() == declaration['cwd']:
            matches.append(process)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue
if len(matches) != 1:
    raise RuntimeError('expected exactly one original owned stage coordinator')
process = matches[0]
identity = dict(pid=process.pid, create_time=process.create_time(), command=process.cmdline(), cwd=process.cwd())
with (S / 'superseded-interrupt.json').open('x') as stream:
    json.dump(dict(reason='bounds continuation barrier added; fresh cohort required', identity=identity, signal='SIGINT'), stream, indent=2)
assert process.create_time() == identity['create_time'] and process.cmdline() == declaration['command']
process.send_signal(signal.SIGINT)
for _ in range(50):
    if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
        break
    time.sleep(0.5)
outcome = E / 'scratch-h3-gate-refinements-20261113/tests/final-format-06/stages/build-reference/outcome.json'
result = json.loads(outcome.read_bytes())
assert result['status'] == 'held' and not result['observed_surviving_pids']
with (S / 'superseded-interrupt-readback.json').open('x') as stream:
    json.dump(dict(identity=identity, outcome=result), stream, indent=2)
print(json.dumps(dict(status=result['status'], surviving_pids=result['observed_surviving_pids'], evidence=str(outcome))))
