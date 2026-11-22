"""Compare complete retained specificity findings for PR6302, 2026-11-21.

Inputs: baseline JSON, candidate JSON, fresh output JSON path.
Output: input hashes, exact violation equality and candidate self-test outcome.
This reads reports only and never changes scanner findings or exemptions.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    baseline_path, candidate_path, output = map(Path, sys.argv[1:])
    baseline_raw, candidate_raw = baseline_path.read_bytes(), candidate_path.read_bytes()
    baseline, candidate = json.loads(baseline_raw), json.loads(candidate_raw)
    equal = baseline['violations'] == candidate['violations']
    record = {'baseline': str(baseline_path), 'candidate': str(candidate_path),
        'baseline_sha256': hashlib.sha256(baseline_raw).hexdigest(),
        'candidate_sha256': hashlib.sha256(candidate_raw).hexdigest(),
        'violations_equal': equal, 'violation_count': len(candidate['violations']),
        'self_test': candidate['self_test']}
    with output.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record, indent=2))
    return 0 if equal and candidate['self_test']['passed'] is True else 1


if __name__ == '__main__':
    raise SystemExit(main())
