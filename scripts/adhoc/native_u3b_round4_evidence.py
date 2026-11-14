"""Verify and summarize Round 4 timing evidence, 2026-11-07.

Inputs: two launcher logs, events, XML and exact local Git revisions.
Outputs: identical scratch/committed JSON manifests for the Round 4 ruling.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u3b/round4-20261107-timing'
identity = json.loads((OUT / 'identity.json').read_text())
results = {}
for label in ('base', 'head'):
    name = 'round4-' + label
    log = (OUT / (name + '.log')).read_text()
    metadata = json.loads(log.splitlines()[0])
    assert metadata['deadline_seconds'] == 3600
    command = metadata['command']
    assert command[command.index('-n') + 1] == '0'
    ending = re.search(r'U3B_EXIT=(\d+); elapsed_seconds=([\d.]+); wall_seconds=([\d.]+)', log)
    assert ending and ending[1] == '0'
    assert float(ending[3]) < 3600
    events = [json.loads(line) for line in (OUT / (name + '.events.jsonl')).read_text().splitlines()]
    assert len(events) == 1 and events[0]['nodeid'] == identity['node']
    assert events[0]['phase'] == 'call' and events[0]['outcome'] == 'passed'
    xml = ET.parse(OUT / (name + '.xml')).getroot()
    cases = list(xml.iter('testcase'))
    assert len(cases) == 1 and not list(xml.iter('failure')) and not list(xml.iter('error'))
    for path, digest in metadata['source_sha256'].items():
        exact = subprocess.check_output(['git', 'show', identity[label] + ':' + path], cwd=ROOT)
        assert hashlib.sha256(exact).hexdigest() == digest, (label, path)
        tree = OUT / 'base' if label == 'base' else ROOT
        assert hashlib.sha256((tree / path).read_bytes()).hexdigest() == digest
    results[label] = {'revision': identity[label], 'call_seconds': events[0]['duration'],
                      'junit_seconds': float(cases[0].attrib['time']),
                      'supervisor_wall_seconds': float(ending[3]),
                      'start_utc': metadata['start_utc'], 'outcome': 'passed',
                      'source_hashes_verified': len(metadata['source_sha256']),
                      'artifacts': {suffix: hashlib.sha256((OUT / (name + suffix)).read_bytes()).hexdigest()
                                    for suffix in ('.log', '.events.jsonl', '.xml')}}
ratio = results['head']['call_seconds'] / results['base']['call_seconds']
manifest = {'identity': identity, 'runs': results, 'head_over_base_call_ratio': ratio,
            'materially_slower': ratio > 1.25,
            'limits': 'One base-first/head-second observation, not replicated or host-normalized; serial distribution only.'}
rendered = json.dumps(manifest, indent=2) + '\n'
(OUT / 'evidence.json').write_text(rendered)
(ROOT / 'scripts/adhoc/native_u3b_round4_evidence.json').write_text(rendered)
print(rendered)
