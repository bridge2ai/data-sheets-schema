#!/usr/bin/env python3
# Purpose: offline pytest checks for the #5364 timing refresh, 2026-10-31.
# Inputs: installed Python/dependencies, pytest args. Outputs: execution and node IDs.
# Run with Python -S -B: no site hooks or bytecode writes in borrowed dependencies.
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fairscape', required=True, type=Path)
    parser.add_argument('--rootdir-cwd', action='store_true',
                        help='Keep nested synthetic collections rooted in their own cwd inside this checkout')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    opt = parser.parse_args()
    assert sys.flags.no_site and sys.dont_write_bytecode
    output = opt.output.resolve()
    assert output.is_relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=False)
    prefix = Path(sys.executable).parent.parent
    version = f'python{sys.version_info.major}.{sys.version_info.minor}'
    project_paths = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts'),
                     str(opt.fairscape.resolve())]
    sites = [str(prefix / 'lib' / version / 'site-packages')]
    if (prefix / 'pyvenv.cfg').exists():
        sys.prefix = sys.exec_prefix = str(prefix)
        if 'include-system-site-packages = true' in (prefix / 'pyvenv.cfg').read_text():
            sites.append(str(Path(sys.base_prefix) / 'lib' / version / 'site-packages'))
    sys.path[:0] = project_paths + sites
    for key in list(os.environ):
        if key.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_')) or key.endswith(
                ('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN')) or key in {
                'CLAUDE_CODE_OAUTH_TOKEN', 'D4D_INSTALL_TESTS', 'RECEIPTS_V5_INSTRUMENT'}:
            os.environ.pop(key)
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
        PYTEST_PLUGINS='xdist.plugin', PYTEST_ADDOPTS='--rootdir=.' if opt.rootdir_cwd else '',
        PIP_NO_INDEX='1', UV_OFFLINE='1',
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', GIT_NO_LAZY_FETCH='1',
        GIT_OPTIONAL_LOCKS='0', PYTHONPATH=os.pathsep.join(project_paths),
        TMPDIR=str(output), PYTHONPYCACHEPREFIX=str(output / 'pycache'))

    def offline(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
            raise RuntimeError('offline timing check forbids network access')
        if event == 'subprocess.Popen' and Path(os.fsdecode(args[0])).name in {
                'gh', 'curl', 'wget', 'ssh', 'claude', 'codex'}:
            raise RuntimeError('offline timing check forbids live commands')

    sys.addaudithook(offline)
    os.chdir(ROOT)
    args = opt.args[1:] if opt.args[:1] == ['--'] else opt.args
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(output / 'cases'), *args]
    metadata = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        python=sys.version, executable=sys.executable, args=args, python_argv=sys.orig_argv,
        platform=sys.platform, child_pythonpath=project_paths,
        pytest_addopts=os.environ['PYTEST_ADDOPTS'],
        launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        timings_sha256=hashlib.sha256((ROOT / 'utils/ci_test_durations.json').read_bytes()).hexdigest(),
        lock_sha256=hashlib.sha256((ROOT / 'poetry.lock').read_bytes()).hexdigest(),
        network_scope='No parent socket calls; child processes retain the filesystem/network sandbox.',
        dependencies={name: importlib.metadata.version(name) for name in sorted({
            d.metadata['Name'] for d in importlib.metadata.distributions()})})
    import pytest

    class Collection:
        def pytest_collection_finish(self, session):
            (output / 'nodeids.json').write_text(json.dumps([i.nodeid for i in session.items], indent=2) + '\n')

    start = time.monotonic()
    code = int(pytest.main(args, plugins=[Collection()]))
    metadata.update(returncode=code, seconds=time.monotonic() - start)
    (output / 'execution.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
