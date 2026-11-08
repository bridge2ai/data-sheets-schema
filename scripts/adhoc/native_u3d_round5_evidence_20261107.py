#!/usr/bin/env python3
"""U3-D N1-N5 evidence and red mutation copies, 2026-11-07.

Inputs: assigned D tree, retained Round 3 regression roster, local Git objects.
Outputs: new scratch-only local clone, bounded offline runs, retained render
witnesses and evidence manifest. No remote operations or scratch commits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent / 'scratch-native-u3d'
START = '46e2f12b25bb848c5bb5474fbffb1281e59d015f'
COPY = BASE / 'round5-mutation-copy'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
FILES = (
    'src/data_sheets_schema/native_shared_phase.py',
    'tests/test_native_shared_phase.py', 'tests/test_native_shared_render.py',
    'tests/test_native_u3d_receipt_policy.py', 'tests/test_native_u3d_runner_evidence.py',
    'scripts/adhoc/run_native_u3d_tests_20261107.py',
    'scripts/adhoc/native_u3d_round5_evidence_20261107.py',
)
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}
MUTATIONS = {
    'n2': ('src/data_sheets_schema/cli/receipts.py',
           "\n                or (block.get('coverage_floor') or {}).get('state') == 'pending'", '',
           'tests/test_native_u3d_receipt_policy.py::test_strict_native_final_requires_completion_and_nonpending_floor[stored-pending]'),
    'n3': ('src/data_sheets_schema/native_shared_render.py',
           'Never use a stage or helper success as overall completion.',
           'Never use a stage or helper success as overall completioN.',
           'tests/test_native_shared_render.py::test_initial_and_final_receipt_commands_are_exact'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=cwd, env=ENV)


def scope():
    assert git('branch', '--show-current').decode().strip() == 'codex/native-u3d-integration-20261107'
    changed = set(git('diff', '--name-only', START).decode().splitlines())
    untracked = set(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
    assert changed | untracked <= set(FILES), (changed | untracked) - set(FILES)


def prepare():
    assert not COPY.exists()
    # One actual byte-copy canary before the local checkout and overlays.
    canary = BASE / 'round5-copy-canary.py'
    with canary.open('xb') as stream:
        stream.write((ROOT / FILES[0]).read_bytes())
    assert sha(canary) == sha(ROOT / FILES[0])
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--local',
                    '--shared', '--no-checkout', str(ROOT), str(COPY)], env=ENV, check=True)
    git('-c', 'core.hooksPath=/dev/null', 'checkout', '--detach', START, cwd=COPY)
    for name in FILES:
        (COPY / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, COPY / name)
        assert sha(ROOT / name) == sha(COPY / name)
    save(BASE / 'round5-copy.json', {'base': START, 'source': str(ROOT), 'copy': str(COPY),
        'files': {name: sha(ROOT / name) for name in FILES},
        'scope': 'local detached mutation copy, no scratch commits, protected bytes unchanged'})


def run(source, name, nodes):
    assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window active'
    return subprocess.call([str(PYTHON), '-S', '-P', '-B',
        str(source / 'scripts/adhoc/run_native_u3d_tests_20261107.py'),
        '--out', str(BASE / ('round5-' + name)), '--workers', '0', *nodes], cwd=source, env=ENV)


def mutation(name):
    relative, before, after, node = MUTATIONS[name]
    path = COPY / relative
    original = path.read_bytes()
    assert original == (ROOT / relative).read_bytes()
    assert original.count(before.encode()) == 1
    modified = original.replace(before.encode(), after.encode())
    save(BASE / ('round5-mutation-' + name + '.json'), {
        'path': relative, 'before_sha256': sha(path),
        'after_sha256': hashlib.sha256(modified).hexdigest(),
        'replace': before, 'with': after, 'node': node})
    try:
        path.write_bytes(modified)
        code = run(COPY, 'red-' + name, [node])
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert code == 1, ('expected assertion failure; inspect retained evidence', code)


def collect():
    result = {'base': START, 'head': git('rev-parse', 'HEAD').decode().strip(),
              'sources': {name: sha(ROOT / name) for name in FILES}, 'runs': {}}
    for planpath in sorted(BASE.glob('round5-*/plan.json')):
        directory = planpath.parent
        plan = json.loads(planpath.read_bytes())
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        assert outcome['cleanup_verified'] and outcome['worker']['source_origin_checks_passed']
        for key, name in [('tested_diff_sha256', 'tested.diff'),
                          ('tested_status_sha256', 'tested.status'),
                          ('tested_untracked_sha256', 'tested-untracked.json')]:
            assert plan[key] == sha(directory / name)
        suite = ET.parse(directory / 'pytest.xml').getroot()
        counts = [dict(item.attrib) for item in suite.iter('testsuite')]
        failures = [{'node': case.get('classname') + '::' + case.get('name'),
                     'message': failure.get('message')}
                    for case in suite.iter('testcase') for failure in case
                    if failure.tag in ('failure', 'error')]
        retained = directory / 'retained-render'
        for witness in sorted((directory / 'cases').rglob('render-digests.json')):
            dest = retained / witness.parent.name
            dest.mkdir(parents=True, exist_ok=True)
            for name in ('render-digests.json', 'normalized-receipt-render.json', 'new-instruction.txt'):
                source = witness.parent / name
                if source.exists():
                    shutil.copy2(source, dest / name)
                    assert sha(source) == sha(dest / name)
        result['runs'][directory.name] = {'counts': counts, 'failures': failures,
            'returncode': outcome['returncode'], 'seconds': outcome['seconds'],
            'evidence_sha256': {name: sha(directory / name) for name in
                ('plan.json', 'outcome.json', 'pytest-command.json', 'pytest.log', 'pytest.xml',
                 'tested.diff', 'tested.status', 'tested-untracked.json', 'network.json',
                 'origins-before.json', 'origins-after.json', 'subprocess-origins.json')},
            'retained_render_sha256': {str(p.relative_to(directory)): sha(p)
                                      for p in retained.rglob('*') if p.is_file()}}
    save(BASE / 'round5-evidence.json', result)
    print(json.dumps({name: {'counts': row['counts'], 'returncode': row['returncode']}
                      for name, row in result['runs'].items()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'n2', 'n3', 'green', 'focused', 'regressions', 'collect'))
    mode = parser.parse_args().mode
    assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'), 'quiet window active'
    scope()
    if mode == 'prepare':
        prepare()
    elif mode in MUTATIONS:
        mutation(mode)
    elif mode == 'green':
        raise SystemExit(run(ROOT, 'green', [entry[3] for entry in MUTATIONS.values()] +
                             ['tests/test_native_u3d_runner_evidence.py',
                              'tests/test_native_u3d_receipt_policy.py::test_actual_cli_no_receipt_strict_uses_recorded_expectation']))
    elif mode == 'focused':
        raise SystemExit(run(ROOT, 'focused', ['tests/test_native_shared_phase.py',
            'tests/test_native_initial_structure_mode.py', 'tests/test_native_u3d_receipt_policy.py',
            'tests/test_native_shared_render.py', 'tests/test_native_u3d_runner_evidence.py']))
    elif mode == 'regressions':
        args = json.loads((BASE / 'round3-regressions/pytest-command.json').read_bytes())['args']
        raise SystemExit(run(ROOT, 'regressions', [a for a in args if a.startswith('tests/')]))
    else:
        collect()


if __name__ == '__main__':
    main()
