#!/usr/bin/env python3
# Observe existing G2 component final artifacts while pytest runs, 2026-11-14.
# Inputs: saved final-components case JSON only. Outputs: timestamped immutable
# scratch snapshots and selected failure fields; never inference of pytest E/F.
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
CASES = SCRATCH / 'final-components/cases'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)


def main():
    output = SCRATCH / ('component-artifact-observation-' + str(time.time_ns()))
    output.mkdir()
    rows = []
    for path in sorted(CASES.rglob('final.json')):
        if path.parent.name not in ('evidence', 'native-evidence'):
            continue
        original_stat = path.stat()
        raw = path.read_bytes()
        end_stat = path.stat()
        if ((original_stat.st_mtime_ns, original_stat.st_size)
                != (end_stat.st_mtime_ns, end_stat.st_size)) or path.read_bytes() != raw:
            rows.append({'observed_path': str(path), 'observation': 'changed during read; omitted'})
            continue
        value = json.loads(raw)
        snapshot = output / 'snapshots' / path.relative_to(CASES)
        save(snapshot, raw)
        row = {'observed_path': str(path), 'observed_mtime_ns': end_stat.st_mtime_ns,
               'snapshot': pin(snapshot),
               'selected_fields': {name: value[name] for name in (
                   'state', 'runtime_gates_passed', 'engineering_completion', 'first_stop',
                   'child_exit_code', 'publication_validation_failure', 'capture_problems') if name in value},
               'gates_not_passed': {name: {key: gate.get(key) for key in ('checked', 'passed', 'reason')}
                   for name, gate in value.get('gates', {}).items()
                   if isinstance(gate, dict) and gate.get('passed') is not True}}
        marker = path.with_name('published.json')
        if marker.is_file():
            marker_raw = marker.read_bytes()
            marker_snapshot = snapshot.with_name('published.json')
            save(marker_snapshot, marker_raw)
            row['publication_snapshot'] = pin(marker_snapshot)
            row['marker_matches_observed_final'] = json.loads(marker_raw).get('final_sha256') == pin(snapshot)['sha256']
        rows.append(row)
    record = {'producer': pin(Path(__file__).resolve()), 'observations': rows,
              'scope': 'Read-only snapshots of existing final JSON while tests are active. Tests may intentionally forge artifacts. These observations neither identify pytest E/F cases nor establish final test outcomes or regression causality.'}
    destination = output / 'observations.json'
    save(destination, (json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps({'observation': pin(destination), 'records': [
        {'path': row['observed_path'], **row.get('selected_fields', {}),
         'gates_not_passed': row.get('gates_not_passed')} for row in rows]}, indent=2))


if __name__ == '__main__':
    main()
