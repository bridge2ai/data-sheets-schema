#!/usr/bin/env python3
"""Audit Round 5 saved tests/mutations for the P2 review, 2026-11-07.

Inputs: scratch-native-u3a-r5 JSON/JUnit and this worktree's Git objects.
Output: a new --out evidence summary under that scratch directory. No test,
network or provider execution; no source edits or deletions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3a-r5'
CASES = ('MA', 'MB', 'MC', 'MD', 'ME', 'MF', 'MG', 'MI', 'MJ', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP')


def sha(path):
    raw = path.read_bytes()
    assert raw
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args], cwd=ROOT,
        env={'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
             'GIT_CONFIG_SYSTEM': '/dev/null'}, timeout=30).decode().strip()


def run(directory):
    plan = json.loads((directory / 'plan.json').read_bytes())
    outcome = json.loads((directory / 'outcome.json').read_bytes())
    assert plan['workers'] <= 2 and plan['deadline_seconds'] == 3600
    assert plan['source_root'] == str(ROOT)
    assert plan['environment']['PYTHONPATH'] == str(ROOT / 'src') + ':' + str(ROOT)
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
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--final-run', required=True)
    args = parser.parse_args()
    assert args.out.parent == SCRATCH and not args.out.exists()
    final = run(SCRATCH / args.final_run)
    assert final['returncode'] == 0
    assert not any(final['counts'][key] for key in ('failures', 'errors', 'skipped'))
    result = {'head': git('rev-parse', 'HEAD'), 'final': final, 'mutations': []}
    for case in CASES:
        directory = SCRATCH / 'mutations' / case
        value = json.loads((directory / 'result.json').read_bytes())
        assert value['status'] == 'killed'
        control, mutant = run(directory / 'baseline'), run(directory / 'mutant')
        assert control['returncode'] == 0 and not control['counts']['failures']
        assert mutant['returncode'] == 1 and mutant['counts']['failures']
        for entry in (control, mutant):
            assert not entry['counts']['errors'] and not entry['counts']['skipped']
        assert mutant['source_commit'] == value['mutant_commit']
        assert git('rev-parse', control['source_commit'] + '^{tree}') == git('rev-parse', value['base'] + '^{tree}')
        assert git('rev-parse', value['restored_commit'] + '^{tree}') == git('rev-parse', value['base'] + '^{tree}')
        result['mutations'].append({'case': case, 'result_sha256': sha(directory / 'result.json'),
                                    'baseline': control, 'mutant': mutant})
    result['changed_paths'] = git('diff', '--name-only', '26a8632d9', 'HEAD').splitlines()
    result['source_sha256'] = {path: sha(ROOT / path) for path in result['changed_paths']}
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'summary': str(args.out), 'sha256': sha(args.out), 'final': final['counts'],
                      'mutations': len(result['mutations'])}, sort_keys=True))


if __name__ == '__main__':
    main()
