"""Gated PR 5968 serial worker replay and bisect launcher, 2026-11-16.

Inputs: saved exact node JSON, isolated interpreter. Outputs: command, pytest
log, JUnit, cache trace and summary beneath the assigned scratch directory.
Full test collection preserves import effects before replaying exact nodes.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('nodes', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--first', type=int, default=0)
    parser.add_argument('--last', type=int)
    parser.add_argument('--append-targets', action='store_true')
    parser.add_argument('--root', type=Path, help='Detached pre-isolation replay checkout')
    parser.add_argument('--parent-json', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    launcher = root.parent.parent / 'data-sheets-schema/scripts/adhoc/run_lane_20261115.py'
    lock_dir = root.parent / '.d4d-lane-locks'
    root = args.root.resolve() if args.root else root
    nodes = json.loads(args.nodes.read_text())[args.first:args.last]
    if args.append_targets:
        for name in ('test_replaced_copy_alias_disables_shared_values',
                     'test_interpreter_integer_limit_change_refuses_a_warm_value'):
            node = 'tests/test_typed_json_parse_cache.py::' + name
            if node not in nodes:
                nodes.append(node)
    args.output.mkdir(parents=True, exist_ok=True)
    selected = args.output / 'input-nodes.json'
    selected.write_text(json.dumps(nodes, indent=2) + '\n')
    command = [sys.executable, str(launcher), '--lane', 'unit', '--root', str(root),
               '--python', sys.executable, '--gate-wait-seconds', '1800', '--workers', '1',
               '--lock-dir', str(lock_dir),
               '--scratch-dir', str(args.output), '--', 'tests',
               '--ignore=tests/test_fairscape_integration/test_canonical_routes.py',
               '--ignore=tests/test_fairscape_integration/test_forward_typed_projections.py',
               '--ignore=tests/test_fairscape_integration/test_nested_dataset_readback.py',
               '-p', 'scripts.adhoc.trace_cache_order_20261116',
               '--cache-order-input=' + str(selected),
               '--cache-order-output=' + str(args.output / 'executed-nodes.json')]
    if args.parent_json:
        command.append('--cache-order-parent-json')
    (args.output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    with (args.output / 'launcher.log').open('w') as output:
        result = subprocess.run(command, cwd=root, stdout=output, stderr=subprocess.STDOUT)
    print(f'returncode={result.returncode}; output={args.output}', flush=True)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
