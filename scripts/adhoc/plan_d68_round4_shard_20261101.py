#!/usr/bin/env python3
"""#5212 round 4, 2026-11-01: choose the ordinary CI shard containing D68.

Inputs: pinned archive and full collection JSON from the offline runner.
Output: exact four-way timing-based assignment and chosen shard JSON.
"""
import argparse
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('tree', type=Path)
p.add_argument('collection', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
sys.path.insert(0, str(a.tree.resolve()))
from utils import pytest_shard
assert Path(pytest_shard.__file__).resolve().is_relative_to(a.tree.resolve())
collection = json.loads(a.collection.read_text())
assert collection['exit_code'] == 0 and not collection['collection_errors']
nodes = pytest_shard.partition_lanes(collection['selected'])['ordinary']
weights = pytest_shard.read_weights(a.tree / 'utils/ci_test_durations.json')
assignment = pytest_shard.balanced_files((node.split('::', 1)[0] for node in nodes), 4, weights)
index = assignment['tests/test_d68_legacy_readonly.py']
selected = [node for node in nodes if assignment[node.split('::', 1)[0]] == index]
a.output.write_text(json.dumps({'shard': f'{index}/4', 'collection_count': len(collection['selected']),
    'ordinary_count': len(nodes), 'selected_count': len(selected), 'file_assignments': assignment}, indent=2))
print(f'{index}/4: {len(selected)} ordinary nodes; D68 included')
