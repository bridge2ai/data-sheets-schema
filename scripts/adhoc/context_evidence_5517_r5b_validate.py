"""PR #5532, 2026-11-08: bounded offline validation and scratch evidence.

Inputs: pytest arguments. Outputs: log/XML/basetemp under scratch-5517.
Refuse a quiet-window lock; terminate only this process group at 3600 seconds.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-5517'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
if LOCK.exists():
    raise SystemExit('Quiet window active; no test started: ' + LOCK.read_text())
label, *arguments = sys.argv[1:]
env = dict(os.environ, TMPDIR=str(OUT), PYTHONDONTWRITEBYTECODE='1',
           PYTHONPYCACHEPREFIX=str(OUT / 'pycache'), PYTHONPATH=str(ROOT / 'src')+os.pathsep+str(ROOT))
for key in tuple(env):
    if key.endswith('_API_KEY') or key in {'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
                                          'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'}:
        env.pop(key)
command = [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider',
           '--basetemp='+str(OUT / (label+'-temp')), '--junitxml='+str(OUT / (label+'.xml')),
           *arguments]
with (OUT / (label+'.log')).open('x') as log:
    log.write(repr(command)+'\n')
    log.flush()
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        result = process.wait(timeout=3600)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        result = 124
print(label, 'exit', result)
raise SystemExit(result)
