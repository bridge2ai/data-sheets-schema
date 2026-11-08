"""Audit retained R9-3 evidence and source scope, 2026-11-08.

Inputs: Round 6 JSON/JUnit, local Git objects. Output: scratch summary JSON.
Read-only except the new summary; no network, native launch, or cleanup.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3a-r6'
CASES = ('MA', 'MB', 'MC', 'MD', 'ME', 'MF', 'MG', 'MI', 'MJ', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP')


def sha(path):
    raw = path.read_bytes()
    assert raw
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT,
        env={'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
             'GIT_CONFIG_SYSTEM': '/dev/null', 'TMPDIR': str(SCRATCH)}, timeout=60).decode().strip()


def run(directory, root=ROOT):
    plan = json.loads((directory / 'plan.json').read_bytes())
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    assert plan['workers'] <= 2 and plan['deadline_seconds'] == 3600
    assert plan['source_root'] == str(root)
    assert plan['environment']['PYTHONPATH'] == str(root / 'src') + ':' + str(root)
    assert plan['scratch_root'] == str(SCRATCH)
    assert outcome['cleanup_verified'] and not outcome['forced_cleanup']
    assert not outcome['observed_surviving_pids'] and not outcome['observation_errors']
    assert outcome['worker']['source_origin_checks_passed'] and outcome['seconds'] < 3600
    assert json.loads((directory / 'network.json').read_bytes())['network_bind_denied']
    nodes = list(ET.parse(directory / 'pytest.xml').getroot().iter('testcase'))
    counts = {'tests': len(nodes), 'failures': sum(n.find('failure') is not None for n in nodes),
              'errors': sum(n.find('error') is not None for n in nodes),
              'skipped': sum(n.find('skipped') is not None for n in nodes)}
    assert nodes
    names = ('plan.json', 'outcome.json', 'pytest.xml', 'pytest.log', 'network.json',
             'origins-before.json', 'origins-after.json', 'subprocess-origins.json')
    return {'directory': str(directory), 'source_commit': plan['source_commit'],
            'seconds': outcome['seconds'], 'returncode': outcome['returncode'],
            'counts': counts, 'sha256': {name: sha(directory / name) for name in names}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-run', required=True)
    args = parser.parse_args()
    assert not git('status', '--porcelain'), 'committed clean source required'
    final = run(SCRATCH / args.final_run)
    assert final['source_commit'] == git('rev-parse', 'HEAD')
    c_run = run(SCRATCH / 'c-real', SCRATCH / 'c-source')
    for item in (final, c_run):
        assert item['returncode'] == 0
        assert not any(item['counts'][k] for k in ('failures', 'errors', 'skipped'))
    mutations = {}
    for case in CASES:
        directory = SCRATCH / 'mutations' / case
        result = json.loads((directory / 'result.json').read_bytes())
        assert result['status'] == 'killed'
        baseline, mutant = run(directory / 'baseline'), run(directory / 'mutant')
        assert baseline['returncode'] == 0 and mutant['returncode'] == 1
        assert mutant['counts']['failures'] and not mutant['counts']['errors']
        assert not baseline['counts']['errors'] and not baseline['counts']['failures']
        assert git('rev-parse', result['base'] + '^{tree}') == git('rev-parse', result['restored_commit'] + '^{tree}')
        mutations[case] = {'baseline': baseline, 'mutant': mutant, 'result_sha256': sha(directory / 'result.json')}
    source = 'src/data_sheets_schema/native_execution_registration_v2.py'
    assert git('diff', '--name-only', 'a6edb1c2d', 'HEAD', '--', 'src') == source
    summary = {'head': git('rev-parse', 'HEAD'), 'source_sha256': sha(ROOT / source),
        'final': final, 'c_integration': c_run, 'mutations': mutations,
        'c_snapshot_sha256': sha(SCRATCH / 'c-snapshot.json'),
        'scope': 'R9-3 runtime capture identity; not native or full C/D admission'}
    with (SCRATCH / 'final-summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'head': summary['head'], 'final': final['counts'],
        'c_integration': c_run['counts'], 'mutations': len(mutations),
        'summary_sha256': sha(SCRATCH / 'final-summary.json')}))


if __name__ == '__main__':
    main()
