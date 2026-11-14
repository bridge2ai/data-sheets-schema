#!/usr/bin/env python3
"""U3-E continuation, 2026-11-08: bounded file cohorts after retained timeout.
Inputs: initial frozen plan and checkout; outputs: exclusive assigned scratch
directories. Includes omitted receipt-v5/D68/D69/schema gates and SG2 final batch.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u1u3'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
RUNNER = ROOT / 'scripts/adhoc/run_native_u1u3_20261108.py'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'

def run(label, nodes, collect=False, root=ROOT, runner=RUNNER):
    while os.path.lexists(LOCK):
        print('quiet window: wait 60 seconds', flush=True)
        time.sleep(60)
    command = [str(PYTHON), '-S', '-P', '-B', str(runner), '--out', str(OUT / label),
               '--workers', '0' if collect else '2']
    if collect:
        command.append('--collect-only')
    print('START ' + label, flush=True)
    result = subprocess.run(command + nodes, cwd=root)
    print('END ' + label + ' returncode=' + str(result.returncode), flush=True)
    return result.returncode

def main():
    action = sys.argv[1]
    if action == 'canary':
        return run('cutoff-canary', ['tests/test_native_shared_capture_integration.py::test_complete_observed_typed_sequence_accounts_for_every_stage_and_source'])
    if action == 'finish':
        assert json.loads((OUT / 'cutoff-canary/outcome.json').read_text())['returncode'] == 0
        plan = json.loads((OUT / 'suite-plan.json').read_text())
        groups = [(f'finish-{name}-{i:02}', [node]) for name in ('remaining-3', 'remaining-4')
                  for i, node in enumerate(plan[name], 1)]
        for label, patterns in [('receipt-v5', ('test_receipts_v5*.py', 'test_review_receipts_v5*.py')),
                                ('d68-d69', ('test_d68*.py', 'test_d69*.py'))]:
            nodes = sorted({str(p.relative_to(ROOT)) for pattern in patterns for p in (ROOT / 'tests').glob(pattern)})
            groups.append(('finish-' + label, nodes))
        groups.append(('finish-schema', ['tests/test_schema']))
        (OUT / 'continuation-plan.json').write_text(json.dumps(groups, indent=2) + '\n')
        for label, nodes in groups:
            code = run(label, nodes)
            if code not in (0, 1):
                outcome = OUT / label / 'outcome.json'
                cutoff = OUT / label / 'early-cutoff.json'
                value = json.loads(outcome.read_text()) if outcome.exists() else {}
                events = json.loads(cutoff.read_text()).get('events', []) if cutoff.exists() else []
                if (value.get('interrupted') == 'deadline' or events) and value.get('observed_surviving_pids') == []:
                    print('Retained incomplete bounded run; continuing unaffected files', flush=True)
                else:
                    return 125
        # Full collection already completed; helpers do not alter test nodes.
        assert json.loads((OUT / 'full-collection/outcome.json').read_text())['returncode'] == 0
        return 0
    if action == 'sg2':
        for variant in ('none', 'explicit', 'conventional'):
            if run('final-sg2-' + variant, ['tests/test_wave7_5213_d76_registration.py::test_sg2_root_launch_completes_and_records_registered_paths[' + variant + ']']) not in (0, 1):
                return 125
        return 0
    if action in ('packet-canary', 'packet-suite'):
        root = OUT / 'final-packet-composition/tree'
        nodes = ['tests/test_native_shared_render.py::test_native_construction_and_replay_use_validated_shared_admission'] if action == 'packet-canary' else [
            'tests/test_native_shared_render.py', 'tests/test_prompt_registry.py', 'tests/test_bc1_g2_round2.py',
            'tests/test_native_u1_scanner_contracts.py', 'tests/test_wave7_5213_d76_round4_inventory.py']
        return run(action, nodes, root=root, runner=root / 'scripts/adhoc/run_native_u1u3_20261108.py')
    raise SystemExit('choose canary, finish, sg2, packet-canary, packet-suite')

if __name__ == '__main__':
    raise SystemExit(main())
