#!/usr/bin/env python3
"""Save C4's explicit offline validation roster; never launch tests, 2026-11-07.

Input: current checkout and physical dependency Python --python.
Output: one new JSON file below scratch-native-u3c-r4, with exact node lists,
file counts and commands. This is a plan, not collection or passing evidence.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'


def files(*patterns):
    return sorted({p.relative_to(ROOT).as_posix() for pattern in patterns
                   for p in (ROOT / 'tests').glob(pattern) if p.is_file()})


def plan(python):
    api = files('test_api_*.py', 'test_source_heading*.py', 'test_renderer_contract_captures.py')
    api.append('tests/test_download/test_api_runner.py')
    groups = {
        'canary': ['tests/test_native_shared_capture_integration.py::test_complete_observed_typed_sequence_accounts_for_every_stage_and_source'],
        'helpers': ['tests/test_native_u3c_round4_helpers.py::test_parent_worker_and_subprocess_reenter_c4_wrapper'],
        'census': ['tests/test_native_u3c_round4_helpers.py::test_actual_c_and_overlay_d_graphs_are_accepted'],
        'c': files('test_native_shared*.py') + ['tests/test_native_u3c_test_driver.py'],
        'a-core': files('test_native_execution_*v2.py', 'test_native_u3a_test_driver.py'),
        'a-legacy-runtime': ['tests/' + name + '.py' for name in (
            'test_native_execution', 'test_native_attempt_supervisor', 'test_native_execution_gates',
            'test_native_execution_observation', 'test_native_execution_permissions')],
        'a-legacy-authority': ['tests/' + name + '.py' for name in (
            'test_native_authority_v2', 'test_native_authority_replay_v1',
            'test_native_preparer_v2_boundaries', 'test_native_preparer_v2_equivalence',
            'test_native_source_roster', 'test_native_attribution_controller')],
        'b-focused': files('test_native_u3b_reuse.py', 'test_native_schema_metadata_reuse.py',
            'test_schema_event_replay.py', 'test_schema_snapshot*.py', 'test_schema_cache*.py',
            'test_cache_dependencies*.py', 'test_native_shared_selection.py'),
        'b-shared': files('test_shared_generation*.py', 'test_typed_audit*.py', 'test_audit_omission*.py'),
        'b-bc1': files('test_bc1*.py', 'test_wave7*bc1*.py'),
        **{f'b-api-{i+1}': api[i::4] for i in range(4)},
        'collect': ['tests'],
    }
    rows = {}
    for name, nodes in groups.items():
        if not nodes or any(not (ROOT / n.split('::', 1)[0]).exists() for n in nodes):
            raise ValueError('missing or empty suite: ' + name)
        command = [str(python), '-S', '-P', '-B',
                   str(ROOT / 'scripts/adhoc/run_native_u3c_round4_20261107.py'),
                   '--out', str(SCRATCH / name), '--workers', '0' if name in ('collect', 'census') else '2']
        if name == 'collect':
            command.append('--collect-only')
        rows[name] = {'nodes': nodes, 'selected_files': len({n.split('::', 1)[0] for n in nodes}),
                      'command': command + nodes, 'deadline_seconds': 3600}
    return {'groups': rows, 'required_order': 'verify one canary before any suite',
            'limits': ['Node counts are established by collection, never inferred from file counts.',
                       'API partitions are broad coverage, not B full-order timing/parity acceptance.',
                       'No artifact-mode parity is claimed with U1_PARITY_OUTPUT absent.',
                       'The C group includes shared selection also covered by B-focused.',
                       'Keep pending projection-lifetime requirements unmarked; retain and classify their failures.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.absolute()
    if out != out.resolve() or out == SCRATCH or not out.is_relative_to(SCRATCH):
        parser.error('plan must be a new literal file below C4 scratch')
    with out.open('x', encoding='utf-8') as stream:
        json.dump(plan(args.python), stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(str(out))
