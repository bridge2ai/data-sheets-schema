#!/usr/bin/env python3
# Purpose: retain Wave7 #5212/#5162 controls, failures, fixes and real canary artifacts.
# Inputs: completed offline validation roots and one native profile; output: compact packet.
# Refs #5212 / #5162; 2026-10-29. Originals remain read-only; no test/provider calls.
"""Archive actual bytes and source attestations without embedding large inventories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import preserve_wave5_validation_20261028 as compact

ROOT = Path(__file__).resolve().parents[2]
MERGE = 'c119d58ddf18cc7c4a77bc8293d09335ab24f921'
ORIGINAL = 'fc3417be63b55c579c48df13fb54ae33437a3977'
PROTECTED_SHA = '8c799066df941dd80d65ffdc23eee225f875383e046bbc1f88656f9897d01e47'
CANARY_NODE = 'test_actual_cli_scope_delivery_regate_and_completed_replay'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular evidence file required: ' + str(path))
    raw = path.read_bytes()
    if not raw:
        raise ValueError('nonempty evidence file required: ' + str(path))
    return raw


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=dict(os.environ, GIT_NO_LAZY_FETCH='1')).stdout


def summarize(root):
    outcome = json.loads(read(root / 'outcome.json'))
    plan = json.loads(read(root / 'plan.json'))
    assert outcome['source_unchanged'] and outcome['selection_complete']
    assert read(root / 'source-before.json') == read(root / 'source-after.json')
    assert json.loads(read(root / 'source-before.json'))['head'] == plan['head']
    assert git('rev-parse', plan['head'] + '^{commit}').decode().strip() == plan['head']
    read(root / 'origins-before.json')
    read(root / 'origins-after.json')
    rows, identities = [], set()
    for case in ET.fromstring(read(root / 'pytest.xml')).iter('testcase'):
        identity = (case.get('classname'), case.get('name'))
        assert identity not in identities
        identities.add(identity)
        failure = next((case.find(tag) for tag in ('failure', 'error', 'skipped')
                        if case.find(tag) is not None), None)
        rows.append({'module': identity[0], 'name': identity[1],
                     'status': failure.tag if failure is not None else 'passed',
                     'seconds': float(case.get('time', '0')),
                     'message': failure.get('message') if failure is not None else None})
    counts = {state: sum(row['status'] == state for row in rows)
              for state in ('passed', 'failure', 'error', 'skipped')}
    assert counts['passed'] == sum(outcome['passed_cases_by_module'].values())
    assert counts['failure'] + counts['error'] == len(outcome['invalid_junit_cases'])
    assert counts['skipped'] == len(outcome['skipped'])
    return {'root': str(root), 'head': plan['head'], 'base': plan['base'],
            'counts': counts, 'outcome': outcome,
            'failures': [row for row in rows if row['status'] != 'passed'],
            'slowest_cases': sorted(rows, key=lambda row: row['seconds'], reverse=True)[:5],
            'outcome_sha256': sha(read(root / 'outcome.json')),
            'junit_sha256': sha(read(root / 'pytest.xml'))}


def main(roots, canary, profile, output):
    assert not output.exists() and canary in roots
    summaries = [summarize(root) for root in roots]
    selected = next(row for row in summaries if row['root'] == str(canary))
    assert selected['head'] == ORIGINAL
    assert selected['counts'] == {'passed': 1, 'failure': 0, 'error': 0, 'skipped': 0}
    assert json.loads(read(canary / 'plan.json'))['test_node'] == CANARY_NODE
    assert sha(read(ROOT / 'src/data_sheets_schema/shared_generation.py')) == PROTECTED_SHA
    assert git('diff', '--binary', MERGE, 'HEAD', '--', 'src/', 'data/', '.claude/') == b''
    output.mkdir(parents=True)
    compact.preserve(roots, output / 'validation')
    extra = output / 'extra_evidence'
    extra.mkdir()
    copied = []

    def retain(source, destination):
        raw = read(source)
        with destination.open('xb') as stream:
            stream.write(raw)
        assert read(destination) == read(source)
        copied.append({'original': str(source), 'copy': str(destination.relative_to(output)),
                       'bytes': len(raw), 'sha256': sha(raw)})

    for index, root in enumerate(roots, 1):
        proof = root / 'protected-union.json'
        if proof.exists():
            retain(proof, extra / f'run-{index:02}-protected-union.json')
        cases = root / 'cases'
        for directory in sorted(cases.iterdir()):
            if directory.is_symlink() or not directory.is_dir() or not directory.name.startswith('test_chorus_shared_v1_exact_ba'):
                continue
            for name in ('summary.json', 'baseline.log', 'candidate.log'):
                source = directory / 'parity' / name
                if source.is_file() and source.stat().st_size:
                    retain(source, extra / f'run-{index:02}-{directory.name}-{name}')
    case = canary / 'cases/test_actual_cli_scope_delivery0'
    proof = json.loads(read(case / 'scope-pipeline-proof.json'))
    assert all(proof[key] is True for key in ('completed_replay_no_calls',
               'cli_reuse_refused_without_calls', 'all_originals_preserved'))
    assert proof['provider_calls'] is False and proof['scientific_approval'] is False
    artifacts = [case / 'scope-pipeline-proof.json', case / 'shared-registration.json',
        *(case / 'output' / name for name in ('EXAMPLE_d4d.yaml', 'EXAMPLE_d4d_core.yaml',
          'EXAMPLE_reconciliation.md', 'EXAMPLE_provenance.yaml'))]
    ledgers = list((case / 'output').glob('EXAMPLE_api_usage_*.json'))
    assert len(ledgers) == 1
    assert sha(read(ledgers[0])) == proof['ledger_sha256']
    assert sha(read(case / 'output/EXAMPLE_provenance.yaml')) == proof['provenance_sha256']
    assert sha(read(case / 'shared-registration.json')) == proof['registration_sha256']
    artifacts.extend(ledgers)
    folder = output / 'canary_outputs'
    folder.mkdir()
    for path in artifacts:
        retain(path, folder / path.name)
    retain(profile, extra / profile.name)
    save(extra / 'profile-command.json', {
        'command': ['/usr/bin/sample', '9273', '1', '-file', str(profile)],
        'recorded_local_time': '2026-10-28 23:06:52.662 -0700',
        'scope': 'One-second native read-only diagnostic of the original pytest process.',
        'limits': 'Native frames do not identify the Python mutation iteration. Activity and a finite outer sequence of 21 rechecks do not prove termination. The test later completed; its JUnit result supplies that evidence.',
        'source_unchanged': True})
    save(output / 'summary.json', {'original_head': ORIGINAL, 'merge': MERGE,
         'protected_shared_generation_sha256': PROTECTED_SHA,
         'production_assets_and_data_unchanged_since_merge': True,
         'runs': summaries, 'copied_evidence': copied,
         'scientific_acceptance': 'not_assessed',
         'counting_note': 'Canary and targeted reruns overlap; do not add them as unique cases.'})
    manifest = {'helper_sha256': sha(read(Path(__file__).resolve())), 'files': {
        str(path.relative_to(output)): {'bytes': path.stat().st_size, 'sha256': sha(read(path))}
        for path in sorted(output.rglob('*')) if path.is_file()}}
    save(output / 'manifest.json', manifest)
    print(json.dumps({'runs': [row['counts'] for row in summaries],
                      'manifest_sha256': sha(read(output / 'manifest.json'))}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, action='append', required=True)
    parser.add_argument('--canary', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main([path.resolve() for path in args.evidence], args.canary.resolve(),
         args.profile.resolve(), args.output.resolve())
