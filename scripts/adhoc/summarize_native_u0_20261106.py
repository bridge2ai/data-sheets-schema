#!/usr/bin/env python3
"""Verify and summarize saved U0 evidence, #4354/D92, 2026-11-06.

Inputs: one external trial directory and its wrapper sibling. Output: new JSON
summary; no tests, source imports, native executable or provider operations.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes()) if path.is_file() else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trial', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    trial = args.trial.absolute()
    wrapper = trial.with_name(trial.name + '.wrapper')
    outcome = read(trial / 'outcome.json')
    gate = read(trial / 'idle-decision.json')
    wrap = read(wrapper / 'outcome.json')
    network = read(wrapper / 'network-self-check.json')
    inputs = {}
    for directory in (trial, wrapper):
        if directory.is_dir():
            for file in sorted(directory.iterdir()):
                if file.is_file():
                    inputs[str(file)] = {'bytes': file.stat().st_size, 'sha256': digest(file)}
    competitors = defaultdict(lambda: {'samples': 0, 'peak_cpu_percent': 0.0})
    if gate:
        for sample in gate.get('competing_process_observations', []):
            for row in sample['processes']:
                key = str(row['pid']) + ' ' + row['name']
                competitors[key]['samples'] += 1
                competitors[key]['peak_cpu_percent'] = max(competitors[key]['peak_cpu_percent'], row['cpu_percent'])
    before, after = read(trial / 'source-before.json'), read(trial / 'source-after.json')
    result = {'format': 'native_u0_evidence_summary_v1', 'trial': str(trial),
        'wrapper': wrap, 'network_self_check': network, 'outcome': outcome,
        'gate': {key: value for key, value in (gate or {}).items() if key != 'competing_process_observations'},
        'competitors': dict(sorted(competitors.items())),
        'source_inventories_equal': before is not None and before == after,
        'source_head': (before or {}).get('head'), 'source_pristine': (before or {}).get('pristine'),
        'source_file_count': len((before or {}).get('files', {})),
        'trial_launched': bool(outcome and outcome.get('child_pid')),
        'inputs': inputs, 'canary_artifacts_verified': False,
        'scope': 'saved evidence identity/flags; no fresh native/runtime/scientific acceptance'}
    if outcome and outcome.get('status') == 'software_test_passed':
        candidates = list((trial / 'cases').glob('**/native26/actual-result.json'))
        if len(candidates) != 1:
            raise ValueError('expected exactly one persisted neutral actual result')
        actual_path = candidates[0]
        root = actual_path.parent
        actual = read(actual_path)
        final = root / 'native-evidence/final.json'
        published = read(root / 'native-evidence/published.json')
        reg = root / 'native-attempt/registration.json'
        started = root / 'native-attempt/started.json'
        runtime = read(root / 'authority/runtime-execution.json')
        peer = root / 'ordinary-python-test-peer'
        if (read(final) != actual or actual.get('state') != 'completed_pending_independent_review'
                or actual.get('runtime_gates_passed') is not True
                or actual.get('scientific_acceptance') != 'not_assessed'):
            raise ValueError('persisted final result does not establish synthetic completion')
        for field, path in [('final_sha256', final), ('registration_sha256', reg), ('started_sha256', started)]:
            if published.get(field) != digest(path):
                raise ValueError('publication binding differs: ' + field)
        if (runtime['deadline_seconds'] != 900 or runtime['executable']['path'] != str(peer)
                or runtime['executable']['sha256'] != digest(peer)
                or b'SYNTHETIC' not in peer.read_bytes()):
            raise ValueError('runtime is not the exact bounded synthetic peer')
        result['canary_artifacts_verified'] = True
        result['persisted_completion'] = {'root': str(root), 'result_sha256': digest(actual_path),
            'registration_sha256': digest(reg), 'peer_sha256': digest(peer),
            'deadline_seconds': 900, 'scientific_acceptance': 'not_assessed',
            'readback_and_spent_assertions': 'covered by the one exact passing JUnit node; not re-executed here'}
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('trial_launched', 'source_inventories_equal',
        'source_head', 'source_pristine', 'source_file_count', 'canary_artifacts_verified', 'gate', 'competitors')}, sort_keys=True))


if __name__ == '__main__':
    main()
