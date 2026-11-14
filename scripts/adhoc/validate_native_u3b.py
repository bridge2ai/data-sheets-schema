"""Offline U3-B test launcher, 2026-11-07.

Inputs: pytest arguments; outputs: scratch logs. Enforces the quiet lock,
network denial, credential removal, at most two workers and a 3600 s deadline
(7200 s only for the authorized serial api-round3-ordered invocation).
No native agent executable is launched. Serves the U3-B review packet.
"""
import os
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import signal
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3b'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
if LOCK.exists():
    raise SystemExit('Quiet window active; do not start tests. Poll no sooner than 60 s.')
name, *args = sys.argv[1:]
workers = '2'
if args[:1] == ['--workers']:
    workers, args = args[1], args[2:]
    if workers not in ('0', '2'):
        raise SystemExit('Only zero or two workers are permitted')
if args[:1] == ['--output-dir']:
    SCRATCH, args = Path(args[1]).resolve(), args[2:]
    if not SCRATCH.is_relative_to(ROOT.parent / 'scratch-native-u3b'):
        raise SystemExit('Evidence directory must be inside assigned scratch')
test_root = ROOT
if args[:1] == ['--tree']:
    test_root = Path(args[1]).resolve()
    args = args[2:]
if any(arg.startswith('-n') or arg.startswith('--numprocesses') for arg in args):
    raise SystemExit('Worker count is fixed by this launcher')
deadline = 3600
if name == 'api-round3-ordered':
    # One-run exception authorized by the 2026-11-07T20:50Z lead ruling.
    if workers != '0' or test_root != ROOT:
        raise SystemExit('Round 3 exception requires the assigned tree and serial order')
    deadline = 7200
env = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY') and k not in
       {'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'}}
env.update(PYTHONPATH=os.pathsep.join((str(test_root / 'src'), str(test_root), str(ROOT / 'scripts/adhoc'))),
           PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(SCRATCH), GIT_NO_LAZY_FETCH='1')
env['U3B_EVENT_LOG'] = str(SCRATCH / (name + '.events.jsonl'))
if name.startswith('parity-'):
    env['U1_PARITY_OUTPUT'] = str(SCRATCH / name)
SCRATCH.mkdir(parents=True, exist_ok=True)
if (SCRATCH / (name + '.log')).exists():
    raise SystemExit('Refusing to overwrite existing run evidence')
profile = '(version 1)(allow default)(deny network*)'
profile += '(deny process-exec (regex #"/(claude|codex|gemini|agy)$"))'
for executable in ('claude', 'codex', 'gemini', 'agy'):
    found = shutil.which(executable)
    if found:
        profile += '(deny process-exec (literal ' + json.dumps(str(Path(found).resolve())) + '))'
cmd = ['/usr/bin/sandbox-exec', '-p', profile,
       str(PYTHON), '-m', 'pytest', '-p', 'native_u3b_test_events', '-n', workers,
       '-o', 'cache_dir=' + str(SCRATCH / 'pytest-cache'),
       '--basetemp=' + str(SCRATCH / (name + '-tmp')), *args]
with (SCRATCH / (name + '.log')).open('w') as log:
    started = time.monotonic()
    wall_started = time.time()
    log.write(json.dumps({'command': cmd, 'cwd': str(test_root),
                          'start_utc': datetime.now(timezone.utc).isoformat(),
                          'deadline_seconds': deadline, 'network': 'OS denied',
                          'source_sha256': {str(p.relative_to(test_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((test_root / 'src/data_sheets_schema').glob('*.py'))}}) + '\n')
    log.flush()
    child = subprocess.Popen(cmd, cwd=test_root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        while child.poll() is None:
            remaining = min(deadline - (time.monotonic() - started),
                            deadline - (time.time() - wall_started))
            if remaining <= 0:
                raise subprocess.TimeoutExpired(cmd, deadline)
            try:
                child.wait(timeout=min(1, remaining))
            except subprocess.TimeoutExpired:
                continue
        result = child.returncode
        if time.time() - wall_started >= deadline:
            result = 124  # A child finishing during suspend is not a bounded pass.
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        result = 124
    log.write(f'\nU3B_EXIT={result}; elapsed_seconds={time.monotonic() - started:.3f}; '
              f'wall_seconds={time.time() - wall_started:.3f}\n')
for artifact in (SCRATCH / (name + '-tmp')).rglob('cpu-smoke*.json'):
    destination = SCRATCH / (name + '-' + artifact.name)
    if destination.exists():
        raise SystemExit('Duplicate smoke evidence')
    shutil.copyfile(artifact, destination)
    assert destination.read_bytes() == artifact.read_bytes() and destination.stat().st_size
print(f'{name}: exit {result}; {SCRATCH / (name + ".log")}')
raise SystemExit(result)
