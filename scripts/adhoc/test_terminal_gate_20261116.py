"""Terminal-gate assignment isolated test runner, 2026-11-16.

Inputs: physical dependency site, scratch directory, test nodes.
Outputs: isolated environment and nonempty JUnit/log evidence. No native calls.
"""
import os
from pathlib import Path
import subprocess
import sys
import venv

root = Path(__file__).resolve().parents[2]
scratch, dependencies = map(Path, sys.argv[1:3])
scratch.mkdir(parents=True, exist_ok=True)
env = scratch.parent / 'test-venv'
if not env.exists():
    venv.EnvBuilder(with_pip=False, symlinks=True).create(env)
    site = env / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    (site / 'paths.pth').write_text('\n'.join(map(str, (root / 'src', root, dependencies))) + '\n')
    (site / 'sitecustomize.py').write_text('import socket\ndef deny(*args, **kwargs):\n    raise RuntimeError("network denied in focused fixture tests")\nsocket.socket.connect = deny\nsocket.create_connection = deny\n')
run_env = dict(os.environ, PYTHONPATH=str(root / 'src'), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONDONTWRITEBYTECODE='1')
command = [str(env / 'bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
           '--basetemp', str(scratch / 'tmp'), '--junitxml', str(scratch / 'results.xml'), *sys.argv[3:]]
with (scratch / 'pytest.log').open('w') as out:
    result = subprocess.run(command, cwd=root, env=run_env, stdout=out, stderr=subprocess.STDOUT)
print((scratch / 'pytest.log').read_text())
assert (scratch / 'results.xml').stat().st_size > 0
raise SystemExit(result.returncode)
