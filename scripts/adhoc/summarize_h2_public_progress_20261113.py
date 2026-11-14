#!/usr/bin/env python3
"""Summarize saved public-case outcomes and diagnostic spans, 2026-11-13.
Inputs: named completed cohort under sibling scratch-h2-resume-20261113.
Outputs: public-summary.json beside its JUnit; helper-2 issue 6200 evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
from report_h2_resume_20261113 import timing_evidence
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('cohort')
a = p.parse_args()
out = ROOT.parent / 'scratch-h2-resume-20261113' / a.cohort
record = {'cohort': a.cohort, 'outcome': json.loads((out / 'outcome.json').read_bytes()),
    'results': [{'path': str(path), **{key: value for key, value in json.loads(path.read_bytes()).items()
        if key in ('state', 'first_stop', 'runtime_gates_passed')}}
        for path in (out / 'cases').rglob('actual-result.json')],
    'timing': timing_evidence(out / 'cases')}
path = out / 'public-summary.json'
with path.open('x') as stream:
    stream.write(json.dumps(record, indent=2) + '\n')
print(json.dumps({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'results': record['results'], 'spans_seconds': [span['seconds'] for item in record['timing']
    for span in item['capture_to_reservation']]}))
