#!/usr/bin/env python3
"""Refresh the unapplied issue-6207 dispatch proposal after 6217, 2026-11-14.

Inputs: committed current sources and hash-pinned historical proposal generator.
Outputs: exclusive scratch-g2-20261114/proposal-6207-after-6217 snapshots, patch,
AST/apply checks, plan and metadata. No project imports, source edits or tests.
The original generator, proposal and static review remain historical evidence.
"""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = ROOT / 'scripts/adhoc/propose_g2_dispatch_boundary_6207_20261114.py'
BASE_SHA256 = '5403fd013483ed9997ea47680f70da0d0c293807ff0df37a793e83acdaa30e01'
EXPECTED_HEAD = '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'

def engine_candidate(source):
    launch = '                    def launch_check():\n'
    source = base.once(source, launch,
        '                    dispatch_authority = None\n' + launch +
        '                        nonlocal dispatch_authority\n')
    source = base.once(source, 'def _admit_subscription_guard(guard, attempt, file, write):\n',
        base.ENGINE_MEMORY + 'def _admit_subscription_guard(guard, attempt, file, write):\n')
    identity_checked = "                            raise ValueError('native admission is closed or consumed identity changed')\n"
    source = base.once(source, identity_checked, identity_checked +
        '                        dispatch_authority = _dispatch_memory_authority(\n'
        '                            value, authorization, selected, observation, adapter.policy,\n'
        '                            registration_raw, started_raw)\n')
    source = base.once(source,
        '                        # A final check at actual Popen remains the separate 6207 gap.\n',
        '                        # Final temporal revalidation follows activation and alarm teardown.\n')
    anchor = '                        contract.activate_before_dispatch(adapter, started_raw)\n'
    source = base.once(source, anchor, anchor + textwrap.indent(base.ENGINE_FINAL, '    '))
    launch_argument = "                        deadline_seconds=value['runtime']['deadline_seconds'], verify_launch=launch_check,\n"
    source = base.once(source, launch_argument,
        launch_argument + '                        verify_dispatch=dispatch_check,\n')
    node, = [node for node in ast.walk(ast.parse(source))
             if isinstance(node, ast.FunctionDef) and node.name == 'launch_check']
    segment = ast.get_source_segment(source, node)
    assert segment.index('host_power.dispatch_power()') < segment.index('_admit_subscription_guard')
    assert segment.index('_admit_subscription_guard') < segment.index('contract.activate_before_dispatch')
    assert segment.index('_dispatch_memory_authority') < segment.index('_require_launch_profile')
    return source

def publication_parts(source):
    tree = ast.parse(source)
    names = ('_publication_signal_cutoff', '_publication_subscription', 'read_final')
    parts = {node.name: ast.dump(node, include_attributes=False) for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in names}
    assert set(parts) == set(names)
    # Every byte from the record-only transition through final publication stays.
    tail = source[source.index('                finally:\n                    # Transport/preparation has ended.'):]
    return parts, tail

def verify_shape(candidates):
    base_verify(candidates)
    before = (ROOT / base.ENGINE).read_text()
    after = candidates[base.ENGINE].decode()
    assert publication_parts(before) == publication_parts(after)
    assert b'record_only_signals()' in candidates[base.ENGINE]

def main():
    assert base.pin(BASE_PATH)['sha256'] == BASE_SHA256
    assert base.git('rev-parse', 'HEAD').decode().strip() == EXPECTED_HEAD
    historical = {name: base.pin(base.SCRATCH / name) for name in (
        'proposal-6207/proposal.json', 'review-6207-final.json')}
    with contextlib.redirect_stdout(io.StringIO()):
        base.main()
    path = base.OUTPUT / 'proposal.json'
    metadata = json.loads(path.read_bytes())
    metadata['base_generator'] = base.pin(BASE_PATH)
    metadata['historical_artifacts'] = historical
    metadata['source_refresh'] = {
        'reason': 'Regenerated against committed 6217 record-only signal cleanup and publication cutoff.',
        'head': EXPECTED_HEAD,
        'preserved': 'The complete engine tail beginning at the record-only transition, publication cutoff, subscription publication validator and independent reader are byte/AST identical.',
    }
    raw = json.dumps(metadata, indent=2) + '\n'
    assert chr(64) not in raw
    path.write_text(raw)
    assert path.read_text() == raw
    assert all(base.pin(base.SCRATCH / name) == pin for name, pin in historical.items())
    assert base.pin(BASE_PATH)['sha256'] == BASE_SHA256
    print(json.dumps({'proposal': base.pin(path), 'patch': base.pin(base.OUTPUT / 'dispatch-boundary.patch'),
                      'applied': False, 'tests_run': False}))

spec = importlib.util.spec_from_file_location('historical_6207_generator', BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
assert base.pin(BASE_PATH)['sha256'] == BASE_SHA256
base.__file__ = __file__
base.OUTPUT = base.SCRATCH / 'proposal-6207-after-6217'
base.engine_candidate = engine_candidate
base_verify = base.verify_proposal_shape
base.verify_proposal_shape = verify_shape
base.TEST_PLAN['complete_files_after_approval'].append('tests/test_native_publication_signals.py')
if __name__ == '__main__':
    main()
