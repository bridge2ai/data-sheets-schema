"""Verify #5157 offline; inputs: selected tests; outputs: scratch logs/JSON/XML.

2026-11-08. Uses the same bounded launcher for one-test canary and regression.
No provider or native-agent invocation is authorized by this helper.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5157'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'


def main():
    name, *tests = sys.argv[1:]
    if name not in {'canary', 'regression', 'canary-resume', 'regression-resume',
                    'fix-canary', 'fix-regression'} or not tests:
        raise SystemExit('Use a named canary/regression run followed by explicit test paths')
    if LOCK.exists():
        raise SystemExit(f'Quiet window active; no pytest started: {LOCK.read_text()}')
    destination = SCRATCH / name
    destination.mkdir(parents=True, exist_ok=False)
    temporary = destination / 'tmp'
    temporary.mkdir()
    env = {k: v for k, v in os.environ.items()
           if not k.endswith('_API_KEY') and k not in {
               'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
               'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'}}
    env.update(PYTHONPATH=f'{ROOT / "src"}:{ROOT}',
               PYTHONPYCACHEPREFIX=str(SCRATCH / 'pycache'),
               TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary))
    command = [sys.executable, '-m', 'pytest', *tests, '-q', '-n', '2',
               '-p', 'no:cacheprovider', '--basetemp', str(destination / 'basetemp'),
               '--junitxml', str(destination / 'pytest.xml')]
    metadata = {'command': command, 'cwd': str(ROOT), 'deadline_seconds': 3600,
                'python': sys.version, 'executable': sys.executable,
                'dependencies': {p: importlib.metadata.version(p)
                                 for p in ('pytest', 'pytest-xdist', 'anthropic')},
                'environment': {k: env[k] for k in (
                    'PYTHONPATH', 'PYTHONPYCACHEPREFIX', 'TMPDIR')}}
    (destination / 'command.json').write_text(json.dumps(metadata, indent=2) + '\n')
    started = time.monotonic()
    with (destination / 'pytest.log').open('w') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            code = 124
    result = {'exit_code': code, 'elapsed_seconds': time.monotonic() - started}
    (destination / 'outcome.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
