"""PR #5162 x #5211, F1, 2026-10-29: compare offline specificity scans.

Inputs: scanner JSON for the merge's production files and final production files.
Output: compact JSON proving whether violations and API meaning changed.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raw = {key: getattr(args, key).read_bytes() for key in ('before', 'after')}
    docs = {key: json.loads(value) for key, value in raw.items()}
    rows = {key: Counter(json.dumps(row, sort_keys=True) for row in doc['violations'])
            for key, doc in docs.items()}
    added = rows['after'] - rows['before']
    removed = rows['before'] - rows['after']
    derived = {key: set(doc['facts']['model_facing_modules']['derived']) for key, doc in docs.items()}
    result = {
        'before_commit': docs['before']['commit'],
        'source_sha256': {key: hashlib.sha256(value).hexdigest() for key, value in raw.items()},
        'exit_codes': {key: doc['exit'] for key, doc in docs.items()},
        'violation_counts': {key: sum(counter.values()) for key, counter in rows.items()},
        'added_violations': [json.loads(row) for row in added.elements()],
        'removed_violations': [json.loads(row) for row in removed.elements()],
        'self_tests': {key: doc['self_test'] for key, doc in docs.items()},
        'api_meaning_unchanged': docs['before']['api_meaning'] == docs['after']['api_meaning'],
        'newly_derived_modules': sorted(derived['after'] - derived['before']),
        'no_longer_derived_modules': sorted(derived['before'] - derived['after']),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    assert not added and not removed and result['api_meaning_unchanged']
    assert result['newly_derived_modules'] == ['typed_audit'] and not result['no_longer_derived_modules']
    assert all(doc['self_test']['passed'] for doc in docs.values())


if __name__ == '__main__':
    main()
