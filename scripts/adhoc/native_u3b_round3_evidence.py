"""Verify the single ordered API run for P2-3, 2026-11-07.

Inputs: round-3 logs and saved round-2 collection; outputs: evidence JSON.
No tests, network, production mutations or inferred passing outcomes.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3b'
OUT = SCRATCH / 'round3-20261107-ordered'
BASE = SCRATCH / 'round2-20261107T064201Z'
NAME = 'api-round3-ordered'
log = (OUT / (NAME + '.log')).read_text()
header = json.loads(log.splitlines()[0])
events = [json.loads(line) for line in (OUT / (NAME + '.events.jsonl')).read_text().splitlines()]
roster = (OUT / (NAME + '-roster.txt')).read_text()
assert roster == (BASE / 'api-wall-final-roster.txt').read_text()
nodes = re.findall(r'^(tests/[^\n]+::[^\n]+)$', (BASE / 'collect-final.log').read_text(), re.M)
expected = [node for filename in roster.splitlines() for node in nodes if node.split('::', 1)[0] == filename]
observed = [row['nodeid'] for row in events if row['phase'] == 'call']
source_equal = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                   for name, digest in header['source_sha256'].items())
assert source_equal
assert not subprocess.check_output(['git', 'diff', '35d1aae4a', '--', 'src', 'tests'], cwd=ROOT)
ending = re.search(r'U3B_EXIT=(-?\d+); elapsed_seconds=([\d.]+); wall_seconds=([\d.]+)', log)
assert ending, 'Run has not finished'
result = {
    'start_utc': header['start_utc'], 'deadline_seconds': header['deadline_seconds'],
    'exit': int(ending[1]), 'elapsed_seconds': float(ending[2]), 'wall_seconds': float(ending[3]),
    'expected_nodes': len(expected), 'observed_nodes': len(observed),
    'complete_collection_order': observed == expected,
    'matches_collection_prefix': observed == expected[:len(observed)],
    'next_unfinished_node': expected[len(observed)] if len(observed) < len(expected) else None,
    'same_original_file_roster': True, 'production_and_tests_unchanged': True,
    'source_hashes_match': source_equal,
    'outcomes': dict(Counter(row['phase'] + ':' + row['outcome'] for row in events)),
    'failures': [row for row in events if row['outcome'] == 'failed'],
    'artifacts': {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in sorted(OUT.glob(NAME + '.*')) if p.is_file()},
    'collection_sha256': hashlib.sha256((BASE / 'collect-final.log').read_bytes()).hexdigest(),
}
result['p2_3_closed'] = (result['exit'] == 0 and observed == expected and len(expected) == 522
    and result['outcomes'] == {'call:passed': 522} and result['wall_seconds'] < 7200)
if result['exit'] == 0:
    suites = ET.parse(OUT / (NAME + '.xml')).getroot().findall('testsuite')
    result['junit'] = {key: sum(int(suite.attrib[key]) for suite in suites)
                       for key in ('tests', 'failures', 'errors', 'skipped')}
    assert result['junit'] == {'tests': 522, 'failures': 0, 'errors': 0, 'skipped': 0}
destination = OUT / 'evidence.json'
destination.write_text(json.dumps(result, indent=2) + '\n')
assert destination.stat().st_size
print(json.dumps(result, indent=2))
