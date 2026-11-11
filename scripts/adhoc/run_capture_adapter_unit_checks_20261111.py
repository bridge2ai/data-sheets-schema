#!/usr/bin/env python3
"""Capture-adapter unit evidence, 2026-11-11; source-only integration task.

Inputs: this sparse checkout and existing dependency Python. Outputs: fresh
external logs/JUnit/sandbox/deadline evidence. Fixed selections: one cheap
canary, affected synthetic cases, and entry-fixture repair verification.
Reuses D76 supervisor; no native fixture,
private composition, environment/corpus copy, provider or new process framework.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-capture-adapter-20261111'
TEST = 'tests/test_native_wp1_capture_recheck.py'
CANARY = TEST + '::test_fixed_route_never_becomes_timing_acceptance'


def main():
    began = time.monotonic()
    if sys.argv[1:] not in (['canary'], ['affected'], ['entry-repair']):
        raise ValueError('only the fixed unit selections are allowed')
    mode = sys.argv[1]
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('dependency Python -S -P -B required')
    if os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'):
        raise ValueError('quiet window occupied')
    if mode != 'canary':
        prior = json.loads((BASE / 'canary/result.json').read_bytes())
        if prior.get('passed') is not True:
            raise ValueError('verified unit canary required first')
    out = BASE / mode
    out.mkdir(parents=True, exist_ok=False)
    for name in ('home', 'tmp'):
        (out / name).mkdir()
    dependency = Path(sys.executable).absolute().parent.parent / 'lib/python3.13/site-packages'
    if not dependency.is_dir() or dependency.resolve() != dependency:
        raise ValueError('existing physical dependency site required')
    profile = out / 'offline.sb'
    profile.write_text('(version 1)\n(allow default)\n(deny network*)\n'
        '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n'
        '(deny file-write* (require-all (require-not (subpath ' + json.dumps(str(out)) + '))'
        ' (require-not (literal "/dev/null")) (require-not (literal "/dev/tty"))))\n')
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(out / 'home'),
        TMPDIR=str(out / 'tmp'), PYTHONPATH=os.pathsep.join(map(str, (ROOT, ROOT / 'src', dependency))),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='', PYTHONDONTWRITEBYTECODE='1',
        PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONPYCACHEPREFIX=str(out / 'unused-pycache'),
        GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null', GIT_NO_LAZY_FETCH='1',
        GIT_ALLOW_PROTOCOL='', UV_OFFLINE='1', PIP_NO_INDEX='1')
    guard_path = ROOT / 'scripts/adhoc/d76_process_deadline_20261102.py'
    spec = importlib.util.spec_from_file_location('capture_unit_deadline', guard_path)
    guard = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = guard
    spec.loader.exec_module(guard)
    selection = [CANARY] if mode == 'canary' else [TEST, '-k', 'not test_fixed_route_never_becomes_timing_acceptance']
    if mode == 'entry-repair':
        selection = [TEST + '::test_both_entry_layers_check_canary_before_launch']
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), sys.executable, '-S', '-P', '-B',
        '-m', 'pytest', '-q', '-o', 'addopts=', '-p', 'no:cacheprovider',
        '--basetemp', str(out / 'cases'), '--junitxml', str(out / 'pytest.xml'), *selection]
    (out / 'plan.json').write_text(json.dumps(dict(command=command, environment=env,
        limit_seconds=30, cleanup_reserve_seconds=20,
        scope='30s acceptance budget; existing D76 cleanup, no independent outer hard alarm'), indent=2) + '\n')
    with (out / 'pytest.log').open('xb') as stream:
        result = guard.run(command, cwd=ROOT, env=env, evidence=out / 'deadline',
                           stream=stream, seconds=max(0.1, 10 - (time.monotonic() - began)))
    elapsed = time.monotonic() - began
    xml = out / 'pytest.xml'
    root = ET.parse(xml).getroot() if xml.is_file() else ET.Element('missing')
    cases = list(root.iter('testcase'))
    passed = (result.returncode == 0 and not result.expired and elapsed <= 30 and bool(cases)
              and not any(list(root.iter(tag)) for tag in ('failure', 'error', 'skipped'))
              and (mode != 'canary' or len(cases) == 1 and cases[0].get('name') == CANARY.split('::')[1]))
    (out / 'result.json').write_text(json.dumps(dict(passed=passed, tests=len(cases),
        elapsed_seconds=elapsed, limit_seconds=30, returncode=result.returncode,
        expired=result.expired, scope='Synthetic adapter units only; no genuine capture/native acceptance.'),
        indent=2) + '\n')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
