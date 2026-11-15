"""Summarize retained v3 fixture verification for the Claude lead, 2026-11-15.

Inputs: saved JUnit and fixture run records in assigned scratch.
Outputs: JSON summary and stdout; no scans or provider calls.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-scanner-v3-template-20261115'
rows = []
for case in ET.parse(SCRATCH / 'fixtures-v3-required.xml').iter('testcase'):
    outcome = next((kind for kind in ('failure', 'error', 'skipped')
                    if case.find(kind) is not None), 'passed')
    rows.append(dict(name=case.attrib['name'], outcome=outcome))
records = [json.loads(path.read_text()) for path in
           sorted((SCRATCH / 'fixtures-v3-required-temp').rglob('scanner/run.json'))]
summary = dict(
    head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    tests=rows,
    counts={kind: sum(row['outcome'] == kind for row in rows)
            for kind in ('passed', 'failure', 'error', 'skipped')},
    fixtures=[{key: record.get(key) for key in
               ('fixture', 'status', 'commit', 'returncode', 'violation_count',
                'v2_original', 'v3_counterpart', 'anchor_move_reason', 'timed_out')}
              for record in records],
    hashes={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
            ('.claude/skills/d4d-generation-specificity-audit/scan.py',
             'tests/fixtures/native_u3l_review_cases.json')},
)
output = json.dumps(summary, indent=2) + '\n'
(SCRATCH / 'fixtures-v3-summary.json').write_text(output)
print(output, end='')
