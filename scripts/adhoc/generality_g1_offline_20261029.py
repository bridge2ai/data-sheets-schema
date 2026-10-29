#!/usr/bin/env python3
# Purpose: isolated offline G1 checks; inputs: module/script and arguments.
# Outputs: selected check stdout/artifacts; generality F2-F19, 2026-10-29.
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
if not sys.flags.no_site:
    raise SystemExit('Invoke with python -S; site/.pth initialization is forbidden')
venv = Path(sys.executable).parent.parent
site = venv / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
sys.prefix = sys.exec_prefix = str(venv)
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.path.append(str(site))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                  PIP_NO_INDEX='1', UV_OFFLINE='1', GIT_NO_LAZY_FETCH='1')
for key in ('ANTHROPIC_API_KEY', 'CBORG_API_KEY', 'OPENAI_API_KEY'):
    os.environ.pop(key, None)

def offline(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        raise RuntimeError('G1 offline checks forbid network: ' + event)

sys.addaudithook(offline)
target, *args = sys.argv[1:]
if target == 'python':
    target, *args = args
    if target == '-m':
        target, *args = args
sys.argv = [target, *args]
if target.endswith('.py'):
    runpy.run_path(target, run_name='__main__')
elif target in {'gen-linkml', 'gen-project', 'd4d'}:
    from importlib.metadata import entry_points
    raise SystemExit(next(iter(entry_points(group='console_scripts', name=target))).load()())
else:
    runpy.run_module(target, run_name='__main__', alter_sys=True)
