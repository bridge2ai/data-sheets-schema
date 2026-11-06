# Purpose: offline bounded #5508 validation with the D92 quiet lock.
# Inputs: test paths or scan/collect mode. Outputs: scratch logs and execution JSON.
# Date: 2026-11-06. No provider or native executable is invoked by this driver.
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent/'scratch-native-u2'
LOCK = ROOT.parent/'plans/native_quiet_window.lock'
PYTHON = '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python'

def main():
    name, *paths = sys.argv[1:]
    source = OUT/'baseline' if name in ('replay', 'baseline-scan', 'baseline-tests') else ROOT
    if LOCK.exists():
        print('Quiet window active; no work started: '+LOCK.read_text(), flush=True)
        return 75
    env = {k: v for k, v in os.environ.items() if not (k.startswith(('ANTHROPIC_', 'OPENAI_', 'CBORG_', 'CLAUDE_')) or k.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN')))}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='',
               UV_OFFLINE='1', PIP_NO_INDEX='1', GIT_NO_LAZY_FETCH='1', TMPDIR=str(OUT),
               PYTHONPATH=os.pathsep.join([str(source/'src'), str(source), '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/fairscape_models']))
    if name == 'replay':
        env['NATIVE_U2_V1_REPLAY'] = str(OUT/'v1-replay')
    command = [PYTHON, '-B', '-m', 'pytest', '-o', 'addopts=', '-p', 'no:cacheprovider', '-q']
    if name == 'collect':
        command += ['tests', '--collect-only']
    elif name in ('scan', 'baseline-scan'):
        command = [PYTHON, '-B', '.claude/skills/d4d-generation-specificity-audit/scan.py', '--root', str(source), '--report', str(OUT/(name+'.md')), '--json', str(OUT/(name+'.json'))]
    else:
        command += ['-p', 'xdist.plugin', '-n', '2', *paths, '--junitxml='+str(OUT/(name+'.xml'))]
    start = time.monotonic()
    with (OUT/(name+'.log')).open('w') as stream:
        child = subprocess.Popen(command, cwd=source, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        (OUT/(name+'.pid')).write_text(str(child.pid)+'\n')
        try:
            while True:
                remaining = 3600 - (time.monotonic() - start)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, 3600)
                try:
                    code = child.wait(timeout=min(60, remaining))
                    break
                except subprocess.TimeoutExpired:
                    if LOCK.exists():
                        # Stop the whole test process group; never contend with U0.
                        os.killpg(child.pid, signal.SIGSTOP)
                        print('Paused for quiet window: '+LOCK.read_text(), flush=True)
                        while True:
                            if time.monotonic() - start >= 3600:
                                raise subprocess.TimeoutExpired(command, 3600)
                            time.sleep(60)
                            if not LOCK.exists():
                                break
                        os.killpg(child.pid, signal.SIGCONT)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            code = 124
    result = {'command': command, 'exit_code': code, 'seconds': time.monotonic()-start, 'deadline_seconds': 3600}
    (OUT/(name+'.execution.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return code

if __name__ == '__main__':
    raise SystemExit(main())
