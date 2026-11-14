"""Plan U3-H cohorts from retained U3-G rosters and expanded registry readers.

2026-11-09, review P1/P2/P3 and D126. Inputs: explicit committed source root;
output: fresh JSON plan under u3h. No imports of project code or test execution.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EXEC = next(p for p in ROOT.parents if p.name == 'd4d-executions')
OUT = EXEC / 'scratch-native-u1u3/u3h'
RUNNER = 'scripts/adhoc/run_native_u3h_20261109.py'
ORDER = ('canary', 'd114', 'hooks', 'f2-core', 'registry', 'registry-shared',
         'f2-delegated', 'f2-specificity', 'u4b', 'parity-canary', 'parity')
READERS = (
    'test_api_launcher.py', 'test_api_playbook_context.py', 'test_pin_granularity.py', 'test_prompt_registry.py',
    'test_resources.py', 'test_shared_generation_assets.py',
    'test_shared_generation_resources.py', 'test_shared_generation_scope_context.py',
    'test_installed_wheel.py', 'test_generation_record_schema.py',
    'test_american_english_rule.py', 'test_agentic_provenance_completeness.py',
    'test_schema_straddle.py', 'test_historical_prompt_recovery.py',
)
GIT_ENV = dict(PATH='/usr/bin:/bin', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='',
    GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
    GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')


def source_identity(source):
    def git(*args):
        if os.path.lexists(EXEC / 'plans/native_quiet_window.lock'):
            raise RuntimeError('quiet window active')
        return subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c',
            'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-c',
            'protocol.allow=never', *args], cwd=source, env=GIT_ENV,
            capture_output=True, check=True, timeout=30).stdout.decode().strip()
    assert Path(git('rev-parse', '--show-toplevel')) == source
    assert not git('status', '--porcelain=v1', '--untracked-files=all'), 'source must be clean'
    return dict(commit=git('rev-parse', 'HEAD'), tree=git('rev-parse', 'HEAD^{tree}'))


def identity(path):
    assert path.resolve(strict=True) == path, 'selected file must be physical'
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=ROOT)
    p.add_argument('--label', required=True)
    p.add_argument('--cohorts', nargs='+', choices=ORDER, default=list(ORDER))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    source = a.source_root
    if os.path.lexists(EXEC / 'plans/native_quiet_window.lock'):
        raise SystemExit('quiet window active')
    assert source.is_absolute() and source.resolve(strict=True) == source
    assert source.is_relative_to(EXEC) and re.fullmatch('[a-z0-9-]+', a.label)
    assert len(set(a.cohorts)) == len(a.cohorts)
    pinned_source = source_identity(source)
    s = importlib.util.spec_from_file_location('u3h_rosters',
        ROOT / 'scripts/adhoc/plan_native_u3g_cohorts_20261109.py')
    g = importlib.util.module_from_spec(s)
    s.loader.exec_module(g)
    python = EXEC.parent / 'data-sheets-schema/.venv/bin/python'
    groups, identities = [], {}
    for name in ORDER:
        if name not in a.cohorts:
            continue
        if name == 'registry':
            row = dict(nodes=['tests/' + f for f in READERS])
        elif name == 'registry-shared':
            row = dict(nodes=sorted(str(f.relative_to(source))
                for f in (source / 'tests').glob('test_shared_generation_*.py')
                if f.name not in READERS))
        elif name == 'hooks':
            row = dict(nodes=['tests/test_native_u1_selector_refusals.py',
                              'tests/test_native_shared_selection.py'])
        else:
            row = g.roster(name, source)
        assert row['nodes']
        for node in row['nodes']:
            relative = node.split('::')[0]
            assert all(relative != excluded.split('::')[0] for excluded in g.EXCLUDED)
            identities[relative] = identity(source / relative)
        out = OUT / (a.label + '-' + name)
        env = {'U3F_PARITY': '1'} if name.startswith('parity') else {}
        groups.append(dict(name=name, **row, cwd=str(source), out=str(out), environment=env,
            argv=[str(python), '-S', '-P', '-B', str(source / RUNNER), '--out', str(out),
                  '--workers', '2', *row['nodes']]))
    result = dict(kind='native_u3h_offline_cohort_plan', version=1,
        source_root=str(source), source_commit=pinned_source['commit'],
        source_tree=pinned_source['tree'], source_clean=True,
        runner=identity(source / RUNNER),
        planner=identity(Path(__file__).resolve()), cohorts=groups,
        selected_test_file_identities=identities, workers=2,
        test_deadline_seconds=3200, independent_cutoff_seconds=3250,
        excluded_public_completion_nodes=list(g.EXCLUDED),
        installed_wheel='Included, not opted in: its network installation remains unavailable offline.',
        scope='Sequential named cohorts, with overlaps; not a whole-repository unique-test count.')
    assert source_identity(source) == pinned_source, 'source moved during planning'
    assert a.output.is_absolute() and a.output.resolve() == a.output
    assert a.output.parent == OUT
    with a.output.open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(dict(plan=str(a.output), groups=[r['name'] for r in groups])))


if __name__ == '__main__':
    main()
