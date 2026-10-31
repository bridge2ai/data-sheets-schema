"""P4a validation provenance, 2026-10-30.

Inputs: completed CI-scope collection log and the repository's shard plugin.
Output: exact selected node count and leading nodes for the serial 1/6 shard.
No test execution or change to the CI selection.
"""
from collections import Counter
from pathlib import Path
from utils import pytest_shard as shard

ROOT = Path(__file__).resolve().parents[3]
nodes = [line for line in (ROOT / '.g1-round2-evidence/collect-final.log').read_text().splitlines()
         if line.startswith('tests/') and '::' in line]
eligible = set(shard.partition_lanes(nodes)['ordinary'])
nodes = [node for node in nodes if node in eligible]
counts = Counter(node.split('::', 1)[0] for node in nodes)
weights = shard.read_weights(ROOT / 'utils/ci_test_durations.json')
owners = shard.balanced_files(counts, 6, weights)
estimates = shard._estimates(counts, weights)
selected = [node for node in nodes if owners[node.split('::', 1)[0]] == 1]
selected.sort(key=lambda node: -estimates[node.split('::', 1)[0]] / counts[node.split('::', 1)[0]])
print('selected', len(selected))
print('\n'.join(selected[:20]))
