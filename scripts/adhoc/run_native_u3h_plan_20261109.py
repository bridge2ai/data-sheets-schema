"""Run U3-H's immutable explicit plan sequentially, 2026-11-09.

Input: planner JSON and named groups. Output: persisted bounded offline runs.
Reuses U3-G's saved-probe canary verifier; no provider/native execution.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EXEC = next(p for p in ROOT.parents if p.name == 'd4d-executions')
OUT = EXEC / 'scratch-native-u1u3/u3h'
GIT_ENV = dict(PATH='/usr/bin:/bin', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='',
    GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
    GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')


def verify_source(plan):
    source = Path(plan['source_root'])
    def git(*args):
        if os.path.lexists(EXEC / 'plans/native_quiet_window.lock'):
            raise RuntimeError('quiet window active')
        return subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c',
            'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-c',
            'protocol.allow=never', *args], cwd=source, env=GIT_ENV,
            capture_output=True, check=True, timeout=30).stdout.decode().strip()
    assert plan['source_clean'] is True
    assert Path(git('rev-parse', '--show-toplevel')) == source
    assert git('rev-parse', 'HEAD') == plan['source_commit'], 'planned source HEAD moved'
    assert git('rev-parse', 'HEAD^{tree}') == plan['source_tree'], 'planned source tree changed'
    assert not git('status', '--porcelain=v1', '--untracked-files=all'), 'planned source is dirty'
    for relative, expected in plan['selected_test_file_identities'].items():
        assert relative.startswith('tests/') and '..' not in Path(relative).parts
        path = source / relative
        assert path.resolve(strict=True) == path and str(path) == expected['path']
        raw = path.read_bytes()
        assert len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'], \
            'planned test bytes changed: ' + relative
    runner = source / 'scripts/adhoc/run_native_u3h_20261109.py'
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == plan['runner']['sha256']


def verify_run_source(folder, plan):
    """A valid old canary never certifies another clean commit at the same path."""
    assert folder.resolve(strict=True) == folder and folder.parent == OUT
    actual = json.loads((folder / 'plan.json').read_bytes())
    assert actual['source_root'] == plan['source_root']
    assert actual['source_commit'] == plan['source_commit'], 'canary/run belongs to another source'
    stable = json.loads((folder / 'source-stability.json').read_bytes())
    assert stable['unchanged'] is True
    for state in (stable['before'], stable['after']):
        assert state['head'] == plan['source_commit'] and not state['status']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('groups', nargs='+')
    a = p.parse_args()
    assert a.plan.resolve(strict=True) == a.plan and a.plan.parent == OUT
    plan_raw = a.plan.read_bytes()
    plan = json.loads(plan_raw)
    assert plan['kind'] == 'native_u3h_offline_cohort_plan'
    source = Path(plan['source_root'])
    assert source.resolve(strict=True) == source and source.is_relative_to(EXEC)
    verify_source(plan)
    runner = source / 'scripts/adhoc/run_native_u3h_20261109.py'
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == plan['runner']['sha256']
    s = importlib.util.spec_from_file_location('u3h_canary_verifier',
        ROOT / 'scripts/adhoc/run_native_u3g_plan_20261109.py')
    g = importlib.util.module_from_spec(s)
    s.loader.exec_module(g)
    groups = {r['name']: r for r in plan['cohorts']}
    assert len(set(a.groups)) == len(a.groups) and set(a.groups) <= groups.keys()
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', LANG='en_US.UTF-8',
        GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null',
        GIT_CONFIG_SYSTEM='/dev/null', PYTHONDONTWRITEBYTECODE='1')
    for name in a.groups:
        if os.path.lexists(EXEC / 'plans/native_quiet_window.lock'):
            raise SystemExit('quiet window active; no next cohort')
        row = groups[name]
        assert a.plan.read_bytes() == plan_raw, 'plan changed during execution'
        verify_source(plan)
        out = Path(row['out'])
        assert out.resolve() == out and out.parent == OUT and not out.exists()
        if name != 'canary':
            verify_run_source(Path(groups['canary']['out']), plan)
            print(json.dumps({'canary': g.canary(Path(groups['canary']['out']))}), flush=True)
        if name == 'parity':
            folder = Path(groups['parity-canary']['out'])
            verify_run_source(folder, plan)
            o = json.loads((folder / 'outcome.json').read_bytes())
            assert o['returncode'] == 0 and o['cleanup_verified']
            files = list((folder / 'parity').glob('*.txt'))
            assert len(files) == 1
            assert files[0].read_bytes() == (EXEC / 'scratch-native-u1u3/parity2-canary-baseline/parity' / files[0].name).read_bytes()
        assert row['argv'][1:5] == ['-S', '-P', '-B', str(runner)]
        assert row['cwd'] == str(source)
        assert row['argv'][5:] == ['--out', str(out), '--workers', '2', *row['nodes']]
        assert all(node.split('::', 1)[0] in plan['selected_test_file_identities'] for node in row['nodes'])
        assert row['environment'] == ({'U3F_PARITY': '1'} if name.startswith('parity') else {})
        print(json.dumps(dict(start=name, out=str(out))), flush=True)
        r = subprocess.run(row['argv'], cwd=source, env={**env, **row['environment']})
        if r.returncode not in (0, 1):
            raise SystemExit(r.returncode)
        o = json.loads((out / 'outcome.json').read_bytes())
        assert o['cleanup_verified'] and o['seconds'] < 3300
        assert o['worker']['source_origin_checks_passed'] is True
        verify_source(plan)
        verify_run_source(out, plan)
        if name == 'canary':
            print(json.dumps({'canary': g.canary(out)}), flush=True)
        print(json.dumps(dict(finished=name, returncode=r.returncode)), flush=True)


if __name__ == '__main__':
    main()
