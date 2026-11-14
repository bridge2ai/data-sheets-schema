#!/usr/bin/env python3
# Trace saved legacy deadline stops against issue 6217 source scope, 2026-11-14.
# Inputs: immutable component observation, commits before/after 6217.
# Outputs: source snapshots and bounded static comparison; no tests/probes.
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
OBSERVATION = SCRATCH / 'component-artifact-observation-1794631660767531000/observations.json'
OUTPUT = SCRATCH / 'legacy-deadline-static-trace-6217'
BEFORE = '748ea6be5be5fdfa1174b1e0b58071bd129e1b5a'
AFTER = '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)


def function(source, name):
    node, = [node for node in ast.parse(source).body
             if isinstance(node, ast.FunctionDef) and node.name == name]
    return ast.dump(node, include_attributes=False)


def main():
    OUTPUT.mkdir()
    source_proof = []
    for relative, names in (
            ('src/data_sheets_schema/native_execution.py', ['launch', 'read_final', '_signals']),
            ('tests/test_native_execution.py', ['make_native_case', 'case',
                 'test_reservation_failures_never_dispatch_and_never_resume',
                 'test_observation_persistence_failure_always_releases_acquired_assertions']),
            ('tests/test_native_receipt_origin_reporting.py', ['completed_origin_case'])):
        raw = {}
        snapshots = {}
        for commit in (BEFORE, AFTER):
            raw[commit] = subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=ROOT)
            path = OUTPUT / commit[:12] / relative
            save(path, raw[commit])
            snapshots[commit] = pin(path)
        source_proof.append({'source_path': relative, 'snapshots': snapshots,
            'functions': [{'name': name, 'same_ast_before_after_6217':
                           function(raw[BEFORE], name) == function(raw[AFTER], name)} for name in names]})
    observations = json.loads(OBSERVATION.read_bytes())
    observed_stops = []
    for row in observations['observations']:
        if row.get('selected_fields', {}).get('first_stop') != 'native attempt deadline elapsed; retain all incomplete charge reservations':
            continue
        snapshot = Path(row['snapshot']['path'])
        assert pin(snapshot) == row['snapshot']
        value = json.loads(snapshot.read_bytes())
        observed_stops.append({'observed_path': row['observed_path'], 'snapshot': row['snapshot'],
            'first_stop': value['first_stop'], 'signals_received': value['keep_awake'].get('signals_received'),
            'state': value['state'], 'child_exit_code': value['child_exit_code'],
            'shutdown': value.get('shutdown')})
    record = {'producer': pin(Path(__file__).resolve()), 'observation': pin(OBSERVATION),
        'before_commit': BEFORE, 'after_commit': AFTER, 'source_proof': source_proof,
        'saved_deadline_stops': observed_stops,
        'interpretation': 'The legacy launch and reader, fixture construction, reservation-failure and observation-persistence test functions are unchanged across 6217. Only the shared signal context helper differs; legacy launch ignores its new yielded callback. Saved signal arrays are retained exactly below.',
        'limits': 'Static scope comparison and saved-artifact observations do not reproduce a baseline failure, identify pytest E/F outcomes, or establish the internal cause of a deadline stop. No timeout or validation change is recommended from these facts.'}
    destination = OUTPUT / 'analysis.json'
    save(destination, (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'analysis': pin(destination), 'saved_deadline_stops': observed_stops}, indent=2))


if __name__ == '__main__':
    main()
