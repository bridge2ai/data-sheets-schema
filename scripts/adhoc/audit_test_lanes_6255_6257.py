"""Audit saved collection and capture records for issues 6255/6257, 2026-11-15.

Inputs: scratch collection log and fake-capture records. Output: audit.json.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import partition_lanes

scratch = ROOT.parent / 'scratch-test-lanes-6255-20261115'
nodes = [line for line in (scratch / 'collection.log').read_text().splitlines()
         if line.startswith('tests/') and '::' in line]
lanes = partition_lanes(nodes)
denials = {node: lane for lane, members in lanes.items() for node in members
           if node.startswith('tests/test_native_shared_denials.py::')}
captures = {}
for path in sorted((scratch / 'capture-tmp').rglob('capture.json')):
    value = json.loads(path.read_bytes())
    captures[str(path)] = {key: value.get(key) for key in ('status', 'error', 'lifecycle')}
readbacks = {}
for path in sorted(scratch.glob('readback-*-tmp/**/native-evidence/final.json')):
    value = json.loads(path.read_bytes())
    readbacks[str(path)] = dict(
        bytes=path.stat().st_size,
        state=value['state'], first_stop=value['first_stop'],
        runtime_gates_passed=value['runtime_gates_passed'])
result = dict(collected_nodes=len(nodes), denial_lanes=denials,
              captures=captures, readbacks=readbacks)
target = scratch / 'audit.json'
target.write_text(json.dumps(result, indent=2) + '\n')
print(target.read_text())
