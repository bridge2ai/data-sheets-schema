"""U1 #4354, 2026-11-06: bounded offline check launcher, quiet-window aware.
Inputs: command args; outputs: scratch log. Denies socket connections and native
executables in Python children via audit hooks; never installs dependencies.
"""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
if LOCK.exists():
    raise SystemExit('Quiet window active; no check started')
name, *command = sys.argv[1:]
env = dict(os.environ)
for key in list(env):
    if key.endswith('_API_KEY') or key in ('ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'):
        del env[key]
env['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'scripts/adhoc/native_u1_offline'), str(ROOT / 'src'), str(ROOT)))
env['PYTHONPYCACHEPREFIX'] = str(SCRATCH / 'pycache')
env['TMPDIR'] = str(SCRATCH)
with (SCRATCH / (name + '.log')).open('w') as log:
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
    log.write(f'\nU1_CHECK_EXIT={code}\n')
print(f'{name}: exit {code}; log {SCRATCH / (name + ".log")}')
raise SystemExit(code)
