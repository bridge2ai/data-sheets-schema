#!/usr/bin/env python3
# Purpose: freeze D76 validation selections and the actual CI shard containing runtime API tests.
# Inputs: clean checkout, retained reviewer file list/#5408 cohort, optional full collection.
# Outputs: JSON target lists and selection ledger under a fresh external directory.
# Serves #5213/D76, 2026-10-31. Read-only source; no provider/network.
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--review-files', type=Path, required=True)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--probes', type=Path, required=True, help='scratch-5213review/scripts/adhoc')
    parser.add_argument('--collection', type=Path, help='full collection nodes.json from D76 driver')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.tree.resolve(strict=True)
    args.output.mkdir(parents=True, exist_ok=False)
    heavy = ['tests/test_shared_generation_runtime.py', 'tests/test_report_admission.py',
             'tests/test_download/test_api_runner.py', 'tests/test_source_heading_runtime_api.py']
    extra = ['tests/test_source_heading_output_layout.py', 'tests/test_native_attempt_supervisor.py']
    closure = ['tests/test_native_attribution_controller.py', 'tests/test_native_execution.py',
               'tests/test_native_registered_provenance.py', 'tests/test_claudecode_direct_arm.py',
               'notes/claudecode_direct/test_direct_arm.py']
    light = set(json.loads(args.review_files.read_text()))
    for pattern in ('test_shared_generation*.py', 'test_provenance*.py', 'test_wave7_5213_*.py'):
        light.update(str(path.relative_to(root)) for path in (root / 'tests').glob(pattern))
    light.update(['tests/test_arm_comparison.py', 'tests/test_resume_inputs.py'])
    # Range-changed modules supplement the reviewer's exact list, including newly added regressions.
    changed = subprocess.check_output(['git', '-C', str(root), 'diff', '--name-only',
        'ada666af6c7bbeae27bf937f7c061327e28f663f', 'HEAD', '--', 'tests'], text=True).splitlines()
    light.update(path for path in changed if path.endswith('.py') and Path(path).name.startswith('test_'))
    light.difference_update(heavy)
    new = sorted(str(path.relative_to(root)) for path in (root / 'tests').glob('test_wave7_5213_d76_*.py'))
    cohort = json.loads(args.cohort.read_text())
    nodes = [row['nodeid'] for row in cohort['rows']]
    if len(nodes) != 107 or len(set(nodes)) != 107:
        raise ValueError('expected exactly 107 unique historical node IDs')
    probes = sorted(str(path) for path in (args.probes / 'claude-probes-20261031').glob('test_probe_*.py'))
    probes.append(str(args.probes / 'test_5213_adversarial.py'))
    lists = {'light': sorted(light), 'heavy': heavy, 'extra': extra, 'closure': closure, 'historical107': nodes,
             'new': new, 'reviewer-probes': probes}
    for name, targets in lists.items():
        for value in targets:
            path = Path(value.split('::', 1)[0])
            if not path.is_absolute():
                path = root / path
            if not path.is_file():
                raise ValueError('missing target ' + value)
        save(args.output / (name + '.json'), targets)
    data = {'head': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
            'inputs': {str(path): sha(path) for path in (args.review_files, args.cohort)},
            'target_counts': {name: len(targets) for name, targets in lists.items()},
            'light_scope': 'reviewer list plus range-changed modules and requested globs, minus heavy modules'}
    if args.collection:
        spec = importlib.util.spec_from_file_location('d76_selected_ci', root / 'utils/pytest_shard.py')
        selector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(selector)
        collection = json.loads(args.collection.read_text())['collected']
        ordinary = selector.partition_lanes(collection)['ordinary']
        weights = selector.read_weights(root / 'utils/ci_test_durations.json')
        assignment = selector.balanced_files((node.split('::', 1)[0] for node in ordinary), 4, weights)
        module = 'tests/test_source_heading_runtime_api.py'
        shard = assignment[module]
        selected = [node for node in ordinary if assignment[node.split('::', 1)[0]] == shard]
        save(args.output / 'ci-ordinary-expected-nodes.json', selected)
        data['ci'] = {'collection_sha256': sha(args.collection), 'shard': shard, 'total': 4,
            'selector_sha256': sha(root / 'utils/pytest_shard.py'),
            'timings_sha256': sha(root / 'utils/ci_test_durations.json'),
            'expected_occurrences': len(selected), 'holds_module': module,
            'held_module_nodes': [node for node in selected if node.split('::', 1)[0] == module],
            'dedicated_nodes_excluded_by_unchanged_ci_lane': list(selector.API_CASE_LANES.values())}
    save(args.output / 'plan.json', data)
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
