"""PR 5968 saved shard-12 worker order reconstruction, 2026-11-16.

Input: downloaded CI log. Outputs: scratch JSON node orders and file inventory.
Optional local collection is compared with CI's observed shard membership.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import balanced_files, partition_lanes, read_weights, _estimates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scratch', type=Path)
    args = parser.parse_args()
    source = args.scratch / 'pr_job_133067816331.log'
    rows = []
    for line in source.read_text().splitlines():
        match = re.search(r'\[(gw\d+)\]\s+\[\s*\d+%\]\s+(PASSED|FAILED|ERROR|SKIPPED) (tests/.+)', line)
        if match:
            rows.append({'worker': match[1], 'outcome': match[2], 'node': match[3].rstrip()})
    worker = [row['node'] for row in rows if row['worker'] == 'gw2']
    target = 'tests/test_typed_json_parse_cache.py::test_interpreter_integer_limit_change_refuses_a_warm_value'
    prefix = worker[:worker.index(target) + 1]
    (args.scratch / 'ci-worker-prefix.json').write_text(json.dumps(prefix, indent=2) + '\n')
    (args.scratch / 'ci-shard-observed.json').write_text(json.dumps(rows, indent=2) + '\n')
    summary = {'ci_observed_nodes': len(rows), 'worker_prefix_nodes': len(prefix),
               'worker_prefix_files': dict(Counter(node.split('::')[0] for node in prefix))}
    full = args.scratch / 'full-order.json'
    rebuilt = args.scratch / 'shard-rebuilt.json'
    if full.exists():
        ordinary = partition_lanes(json.loads(full.read_text()))['ordinary']
        paths = {node.split('::')[0] for node in ordinary}
        # The three unavailable local FAIRSCAPE modules still own CI slots.
        # Preserve their file weights without pretending their tests ran.
        unavailable = {
            'tests/test_fairscape_integration/test_canonical_routes.py',
            'tests/test_fairscape_integration/test_forward_typed_projections.py',
            'tests/test_fairscape_integration/test_nested_dataset_readback.py',
        } - paths
        weights = read_weights(ROOT / 'utils/ci_test_durations.json')
        assignments = balanced_files(paths | unavailable, 12, weights)
        local = [node for node in ordinary if assignments[node.split('::')[0]] == 12]
        counts = Counter(node.split('::')[0] for node in local)
        estimates = _estimates(counts, weights)
        local.sort(key=lambda node: -estimates[node.split('::')[0]] / counts[node.split('::')[0]])
        rebuilt.write_text(json.dumps(local, indent=2) + '\n')
        summary['unavailable_collection_modules'] = sorted(unavailable)
        summary['unavailable_modules_in_shard'] = sorted(path for path in unavailable if assignments[path] == 12)
    if rebuilt.exists():
        local = json.loads(rebuilt.read_text())
        ci = {row['node'] for row in rows}
        summary.update(local_nodes=len(local), ci_only=sorted(ci - set(local)),
                       local_only=sorted(set(local) - ci))
        end = local.index(target) + 1
        (args.scratch / 'shard-prefix.json').write_text(json.dumps(local[:end], indent=2) + '\n')
        summary['serial_shard_prefix_nodes'] = end
    (args.scratch / 'worker-reconstruction.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
