"""Diagnose issue 6289 timing history without changing code; 2026-11-18.

Inputs: assigned 7b9497fc1 checkout and its Git history.
Outputs: saved audit and proposed base/override JSON in the assigned scratch.
Serves PR 5968; proposal only until the lead accepts the override design.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = (args.root / 'utils/ci_test_durations.json').read_bytes()
    current = json.loads(raw)
    base_raw = subprocess.check_output([
        'git', 'show', 'a6d773e6a^:utils/ci_test_durations.json'], cwd=args.root)
    base = json.loads(base_raw)
    key = 'successful_ordinary_refresh_43536007079_20261114'
    refresh = current['source'][key]
    reconstructed = {**refresh['previous_file_seconds'], **refresh['file_seconds']}
    differences = {
        path: {'measured': reconstructed.get(path), 'scheduling': value}
        for path, value in current['file_seconds'].items()
        if path not in reconstructed or value != reconstructed[path]
    }
    previous = deepcopy(current)
    del previous['source'][key]
    previous['file_seconds'] = refresh['previous_file_seconds']
    broken_previous_hash = sha((json.dumps(previous, indent=2) + '\n').encode())
    del previous['source']['issue_6289_20261118']
    restored_previous_hash = sha((json.dumps(previous, indent=2) + '\n').encode())
    overrides = {
        'schema_version': 1,
        'base_sha256': sha(base_raw),
        'source': {'issue_6289_20261118': current['source']['issue_6289_20261118']},
        'file_seconds': {path: row['scheduling'] for path, row in differences.items()},
    }
    assert base['file_seconds'] == reconstructed
    assert {**base['file_seconds'], **overrides['file_seconds']} == current['file_seconds']
    assert restored_previous_hash == refresh['previous_snapshot_sha256']
    assert base['source'] == {k: v for k, v in current['source'].items()
                              if k != 'issue_6289_20261118'}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'proposed-measured-base.json').write_bytes(base_raw)
    (args.output / 'proposed-scheduling-overrides.json').write_text(
        json.dumps(overrides, indent=2) + '\n')
    audit = {
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.root,
                                       text=True).strip(),
        'current_timing_sha256': sha(raw),
        'restored_timing_sha256': sha(base_raw),
        'override_count': len(differences),
        'new_keys': sum(row['measured'] is None for row in differences.values()),
        'changed_keys': sum(row['measured'] is not None for row in differences.values()),
        'differences': differences,
        'historical_snapshot_expected_sha256': refresh['previous_snapshot_sha256'],
        'historical_snapshot_actual_sha256': broken_previous_hash,
        'historical_snapshot_restored_sha256': restored_previous_hash,
        'base_matches_reconstructed_measurements': True,
        'overlay_preserves_all_effective_weights': True,
        'script_sha256': sha(Path(__file__).read_bytes()),
    }
    target = args.output / 'timing-history-audit.json'
    target.write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))
    print(str(target) + ' sha256=' + sha(target.read_bytes()))


if __name__ == '__main__':
    main()
