"""Summarize saved native-lane verification for PR 5968, 2026-11-13.

Input: task scratch logs/JUnit/JSON. Output: evidence-summary.json and stdout.
Run only after the acceptance suite and all collection checks have finished.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import NATIVE_CASE_LANES

parser = argparse.ArgumentParser()
parser.add_argument('scratch', type=Path)
args = parser.parse_args()
outcomes = defaultdict(lambda: dict(tests=0, failures=0, errors=0, skipped=0))
for case in ET.parse(args.scratch / 'acceptance.xml').iter('testcase'):
    row = outcomes[case.attrib['classname']]
    row['tests'] += 1
    for tag, key in [('failure', 'failures'), ('error', 'errors'), ('skipped', 'skipped')]:
        row[key] += case.find(tag) is not None
collections = []
for lane, node in NATIVE_CASE_LANES.items():
    result = json.loads((args.scratch / (lane + '.json')).read_text())
    assert result['selection_verified'] and result['selected_nodes'] == [node]
    assert result['returncode'] == 1 and len(result['collection_errors']) == 3
    assert Path(result['log']).is_file()
    collections.append(result)
evidence = dict(
    acceptance=dict(outcomes),
    native_lanes_verified=len(collections),
    collection_only=True,
    known_collection_errors=collections[0]['collection_errors'],
    interpreter=(args.scratch / 'interpreter.txt').read_text().strip(),
    files_sha256={name: hashlib.sha256((args.scratch / name).read_bytes()).hexdigest()
                  for name in ['acceptance.log', 'acceptance.xml', 'canary.log',
                               'collection-canary.log', 'collection-remaining.log']},
)
raw = json.dumps(evidence, indent=2) + '\n'
(args.scratch / 'evidence-summary.json').write_text(raw)
print(raw, end='')
