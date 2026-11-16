"""Issue 6273 offline validation through the shared lane gate, 2026-11-16.

Inputs: checkout tests, explicit interpreter and scratch root. Outputs: collected
node IDs and lane logs in scratch. No provider or native executable is invoked.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('--group', choices=['audit', 'scanner', 'new'], required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    launcher = root.parent.parent / 'data-sheets-schema/scripts/adhoc/run_lane_20261115.py'
    groups = {
        'audit': ['tests/test_typed_audit.py', 'tests/test_typed_audit_derivations.py',
                  'tests/test_typed_audit_captured_assets.py', 'tests/test_typed_json_parse_cache.py',
                  'tests/test_native_catalog_fast_guards.py',
                  'tests/test_native_pending_receipt_gate_rules.py'],
        'scanner': ['tests/test_native_u1_scanner_contracts.py', 'tests/test_native_u1_selector_refusals.py'],
        'new': ['tests/test_native_execution_round3_v2.py::test_wire_commit_proof_precedes_any_helper_loading',
                'tests/test_native_execution_bridge_v2.py::test_wire_still_invokes_pinned_envelope_check_after_structural_precheck',
                'tests/test_native_generation_frontdoor.py::test_prepared_directory_route_passes_argument_gate_before_reading',
                'tests/test_native_generation_frontdoor.py::test_launch_requires_all_authority_arguments_before_any_dispatch'],
    }

    def run(name, targets):
        scratch = args.scratch / name
        command = [sys.executable, str(launcher), '--lane', 'unit', '--root', str(root),
            '--python', sys.executable, '--gate-wait-seconds', '1800', '--workers', '1',
            '--scratch-dir', str(scratch), '--json-summary', str(scratch / 'summary.json'),
            '--', *targets]
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        with (scratch / 'launcher.log').open('w') as log:
            result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        print(f'{name}: returncode={result.returncode}', flush=True)
        return scratch, result.returncode

    collection, code = run(args.group + '-collection', ['--collect-only', '-q', '-q', *groups[args.group]])
    if code:
        return code
    summary = json.loads((collection / 'summary.json').read_text())
    output = Path(summary['steps'][0]['log_path']).read_text()
    nodes = [line.strip() for line in output.splitlines() if line.startswith('tests/') and '::' in line]
    if not nodes:
        raise RuntimeError('Collection did not produce exact test node IDs')
    (collection / 'nodes.json').write_text(json.dumps(nodes, indent=2) + '\n')
    _, code = run(args.group + '-tests', nodes)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
