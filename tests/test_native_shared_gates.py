"""Captured-reader adapters and real evidence checks, not native execution.

The stage-completion adapter tests explicitly replace only the already-tested
typed reconstruction with a spy. Receipt checking, policy floors, file-role
selection, schema/pair checking and evidence algorithms remain real.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import json
import socket
import subprocess
import yaml

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as pool
from data_sheets_schema import native_shared_gates as gates
from data_sheets_schema import native_shared_selection as selected
from data_sheets_schema import native_shared_receipts as receipts
from data_sheets_schema import native_shared_stage as stages
from data_sheets_schema import evidence_assertions as evidence
from data_sheets_schema.native_shared_capture import _CapturedRun, _Reader
from tests.test_native_shared_selection import declaration, pin, save
from tests.test_source_attribution_preflight import inputs
from tests.test_native_shared_phase import Trace


def artifact(role, path, raw):
    return c.CapturedArtifact(c.ArtifactPin(role, str(path), len(raw), c.sha(raw)), raw)


def member(item):
    # Invented stable file metadata: no actual controller admission is claimed.
    return pool.PoolMember(item, c.canonical({'exists': True, 'regular': True, 'symlink': False,
        'links': 1, 'device': 0, 'inode': 1, 'size': len(item.raw), 'mtime_ns': 0}))


class Snapshot:
    def __init__(self, members):
        self.raws = {(m.captured.pin.path, m.captured.pin.role): m.captured.raw for m in members}

    def read(self, path, role):
        return self.raws[str(path), role]


def replace_pool(run, items):
    captured = pool.CapturePool(tuple(member(item) for item in items), ())
    return replace(run, pool=captured, reader=_Reader(run.selection, pool=captured))


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail('native gate adapter executed a process or transport')
    for name in ('run', 'Popen', 'check_output'):
        monkeypatch.setattr(subprocess, name, refused)
    monkeypatch.setattr(socket.socket, 'connect', refused)


@pytest.fixture
def captured_run(declaration, inputs, tmp_path):
    # Exact real selection capture, with the existing independent source-review
    # fixture. Synthetic seals below test consumers, not seal observation.
    declaration['run']['project'] = declaration['inputs']['project'] = inputs['project']
    for key, source in (('bundle', 'bundle_raw'), ('chunk_manifest', 'chunk_manifest_raw'),
                        ('source_manifest', 'source_manifest_raw')):
        path = tmp_path.resolve() / (key + '.yaml')
        path.write_bytes(inputs[source])
        declaration['inputs'][key] = pin(path, inputs[source])
    policy_path = Path(declaration['receipt_policy']['path'])
    policy = c.strict_json(policy_path.read_bytes())
    policy['coverage_floor'] = {'state': 'registered', 'numerator': 1, 'denominator': 1}
    policy_path.write_bytes(c.canonical(policy))
    declaration['receipt_policy'] = pin(policy_path, policy_path.read_bytes())
    for kind, cls in (('full', 'Dataset'), ('core', 'CoreDataset')):
        schema = declaration['inputs'][kind + '_schema']
        path = Path(schema['root'])
        raw = path.read_bytes().replace(('  ' + cls + ': {}').encode(),
            ('  ' + cls + ':\n    attributes:\n      description: {}\n      purpose: {}').encode())
        path.write_bytes(raw)
        schema['sources'][0].update(pin(path, raw))
    save(declaration)
    selection = selected.capture(declaration['registration_path'])
    paths = {role: str(tmp_path.resolve() / (role + '.out')) for role in ('full', 'core', 'report', 'receipt')}
    review = evidence.report_payload(inputs['report_raw'].decode(), protocol_version=7)['source_review']
    original_review = {**deepcopy(review), 'artifact': 'original_full'}
    audit = c.canonical({'findings': [], 'summary': 'No finding declared.', 'source_review': original_review})
    manifest = yaml.safe_load(inputs['chunk_manifest_raw'])
    original_receipt = c.canonical({'bundle_md5': manifest['bundle_md5'], 'chunks': [
        {'id': row['id'], 'status': 'nothing_relevant', 'reason': 'Await selected receipt completion.'}
        for row in manifest['chunks']]})
    phase1 = c.Phase1Capture(
        full=artifact('phase1_full', selection.role('phase1_full'), inputs['record_raw']),
        core=artifact('phase1_core', selection.role('phase1_core'), inputs['record_raw']),
        original_receipt=artifact('phase1_receipt', selection.role('phase1_receipt'), original_receipt),
        seal=artifact('phase1_seal', selection.role('phase1_seal'), b'{}'),
        core_seal=artifact('core_seal', selection.role('core_seal'), b'{}'),
        full_seal_observation=artifact('observation', selection.role('observations_root') + '/000000.json', b'{}'),
        core_seal_observation=artifact('observation', selection.role('observations_root') + '/000001.json', b'{}'))
    items = [artifact('audit', selection.role('audit'), audit),
        artifact('final_full', paths['full'], inputs['record_raw']),
        artifact('final_core', paths['core'], inputs['record_raw']),
        artifact('final_report', paths['report'], inputs['report_raw']),
        artifact('original_receipt_output', paths['receipt'], original_receipt)]
    run = _CapturedRun(selection=selection, value={},
        composition={'policy': {'post_final_recorder': {'destination': str(tmp_path / 'provenance.out')}}},
        spec=SimpleNamespace(_agentic_artifact_paths=paths), reader=None, pool=None,
        transcript=None, control=None, binding=None, history=None, observations=(), phase1=phase1)
    return replace_pool(run, items)


def no_reads(monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail('captured adapter reread the live filesystem')
    for name in ('read_bytes', 'read_text', 'resolve'):
        monkeypatch.setattr(Path, name, refused)
    monkeypatch.setattr(pool, 'read_regular', refused)


def test_current_evidence_matches_real_final_helper_exactly(captured_run, tmp_path, monkeypatch):
    run = captured_run
    selected_paths = {}
    for name, item in (('original_full', run.phase1.full), ('original_core', run.phase1.core)):
        path = tmp_path / (name + '.yaml'); path.write_bytes(item.raw); selected_paths[name] = path
    raw_roles = {m.captured.pin.role: m.captured for m in run.pool.members}
    for role in ('final_full', 'final_core', 'final_report', 'audit'):
        path = tmp_path / (role + '.data'); path.write_bytes(raw_roles[role].raw); selected_paths[role] = path
    actual = evidence.check_files(audit=selected_paths['audit'],
        bundle=Path(run.selection.document()['inputs']['bundle']['path']),
        manifest=Path(run.selection.document()['inputs']['chunk_manifest']['path']),
        artifacts={key: selected_paths[key] for key in ('original_full', 'original_core', 'final_full', 'final_core')},
        report=selected_paths['final_report'], protocol_version=7,
        source_manifest=Path(run.selection.document()['inputs']['source_manifest']['path']),
        project=run.selection.document()['run']['project'])
    assert actual['checked'] is True and actual['findings'] == []
    no_reads(monkeypatch)
    checked = gates.current_evidence(run)
    assert c.canonical(checked) == c.canonical(actual)
    assert checked['artifact_sha256']['original_full'] == c.sha(run.phase1.full.raw)


@pytest.mark.parametrize('mutation', ['report_claim', 'audit_original', 'missing_final', 'missing_original'])
def test_actual_evidence_does_not_accept_stale_or_missing_bytes(captured_run, mutation, monkeypatch):
    run = captured_run
    items = [m.captured for m in run.pool.members]
    if mutation == 'missing_original':
        run = replace(run, phase1=None)
    elif mutation == 'missing_final':
        items = [item for item in items if item.pin.role != 'final_full']
    else:
        role = 'final_report' if mutation == 'report_claim' else 'audit'
        items = [artifact(item.pin.role, item.pin.path,
                         item.raw.replace(b'protocol.txt', b'outside.txt') if role == 'final_report'
                         else item.raw.replace(c.sha(run.phase1.full.raw).encode(), b'a' * 64))
                 if item.pin.role == role else item for item in items]
    run = replace_pool(run, items)
    no_reads(monkeypatch)
    if mutation.startswith('missing'):
        with pytest.raises(ValueError): gates.current_evidence(run)
    else:
        out = gates.current_evidence(run)
        assert out['checked'] is True and out['findings']


def full_phase():
    trace = Trace(); trace.assembly(); trace.final_checks(); trace.finish()
    return trace


def test_actual_phase_and_typed_settlement_keep_exit_one_draft_corrections():
    trace = Trace(); trace.assembly(); trace.final_checks()
    trace.helper('final_source_inventory'); trace.write('report')
    trace.helper('draft', code=1)
    trace.finish()
    report = trace.state.report(complete=True)
    events = [{'type': 'system', 'subtype': 'init', 'session_id': 'session'}] + [item[0] for item in trace.events]
    import shlex
    kinds = {'draft': 'draft', 'audit_evidence': 'evidence', 'final_evidence': 'final_evidence',
             'original_source_inventory': 'source_inventory', 'final_source_inventory': 'source_inventory'}
    prepared = {'phase_report': report, 'events': events,
        'state': SimpleNamespace(spec=SimpleNamespace(), commands={shlex.join(trace.commands[k]): v for k, v in kinds.items()})}
    out = gates.tool_history(prepared)
    assert out['passed'] is True
    assert any(row['helper_kind'] == 'draft' and row['exit_code'] == 1 for row in out['bash_results'])
    broken = deepcopy(prepared)
    result = next(e for e in broken['events'] if 'tool_use_result' in e)
    result['tool_use_result']['exit_code'] = 7
    with pytest.raises(ValueError, match='contradictory'): gates.tool_history(broken)


@pytest.mark.parametrize('field', ['checked', 'passed', 'complete', 'phase1_sealed', 'core_sealed',
                                  'assembly_complete', 'native_terminal', 'problems', 'pending_tool_ids'])
def test_partial_or_contradictory_phase_cannot_certify_completion(field):
    report = full_phase().state.report(complete=True)
    assert gates.phase_gate({'phase_report': report})['passed'] is True
    report[field] = ['unfinished'] if field in ('problems', 'pending_tool_ids') else 1
    assert gates.phase_gate({'phase_report': report})['passed'] is False


@pytest.mark.parametrize('field', ['checked', 'passed', 'additional_gate_passed', 'recorder_completed_in_trace', 'problems'])
def test_saved_gate_requires_every_fresh_replay_obligation(field):
    out = {'checked': True, 'passed': True, 'additional_gate_passed': True,
           'recorder_completed_in_trace': True, 'problems': []}
    prepared = {'replay_complete': True, 'saved_result': out}
    assert gates.saved_gate(prepared)['passed'] is True
    out[field] = ['failure'] if field == 'problems' else 1
    assert gates.saved_gate(prepared)['passed'] is False
    prepared['replay_complete'] = 1
    with pytest.raises(ValueError, match='complete native'): gates.saved_gate(prepared)


def test_all_fifteen_gates_remain_present_on_incomplete_capture():
    from tests.test_native_execution_gates import selected as stream_fixture
    prepared, runtime = stream_fixture()
    # Deliberately incomplete controls: all gates must be retained, and missing
    # authority must fail within its own gate rather than disappear.
    result = gates.check(prepared, {}, runtime, {'run_direct_canary': None}, exit_code=0, shutdown=None,
        live={}, first_stop=None, runtime_authority={'passed': False}, keep_awake={'passed': False})
    assert tuple(result) == gates.GATES and len(result) == 15
    assert result['terminal']['passed'] is True
    assert result['schema']['passed'] is False and result['receipts']['passed'] is False
    assert not all(row['passed'] for row in result.values())


def test_schema_pair_adapters_ignore_foreign_projection_and_bind_same_bytes(captured_run, monkeypatch):
    from data_sheets_schema import native_shared_schema_gates as schema
    run = captured_run
    prepared = {'run': run, 'snapshot': Snapshot(run.pool.members)}
    calls = []
    def checked(selection, full, core):
        assert selection is run.selection
        assert full == core == run.phase1.full.raw
        calls.append((selection, full, core))
        return {'passed': True}
    monkeypatch.setattr(schema, 'check_schemas', checked)
    monkeypatch.setattr(schema, 'check_pair', checked)
    no_reads(monkeypatch)
    assert gates.schema_gate(prepared, {'foreign': '/unused'})['passed'] is True
    assert gates.pair_gate(prepared, {'foreign': '/unused'})['passed'] is True
    assert len(calls) == 2  # Routing only; real schema semantics have their own tests.
    prepared['snapshot'].raws[run.spec._agentic_artifact_paths['full'], 'final_full'] += b'\n'
    with pytest.raises(ValueError, match='snapshot differs'): gates.schema_gate(prepared, {})


@pytest.fixture
def receipt_prepared(captured_run, monkeypatch):
    run = captured_run
    runtime = artifact('runtime', '/neutral/runtime', c.canonical({'limits': {'maxOutputTokens': 4000}}))
    binding = SimpleNamespace(execution=artifact('execution_capture', run.selection.role('execution_capture'), b'{}'),
        runtime_declaration=runtime, runtime_declaration_sha256=runtime.pin.sha256,
        attempt_id='neutral', session_id='neutral-session')
    request = receipts.prepare(run.selection, binding, run.phase1)
    chunks = yaml.safe_load(run.selection.raw('chunk_manifest'))['chunks']
    chunk = next(row['id'] for row in chunks if row['source'] == 'protocol.txt')
    answer = {'rereceipt': [{'path': path, 'receipt': {'chunk': chunk,
        'snippet': 'The deployment is planned.'}} for path in request['requested_paths']]}
    finished = receipts.complete(run.selection, binding, run.phase1, c.canonical(answer))
    assert finished.effective_receipt != run.phase1.original_receipt.raw
    outputs = {role: artifact(role, run.selection.role(role), raw) for role, raw in {
        'effective_receipt': finished.effective_receipt, 'receipt_result': finished.result_json,
        'receipt_carry': finished.carry_json, 'packet': b'{}', 'typed_index': b'{}',
        'typed_assembly': b'{}', 'audit': run.reader.read('audit', run.selection.role('audit')).raw}.items()}
    completion = c.StageCompletion(selection_sha256=run.selection.registration.pin.sha256,
        execution_sha256=binding.execution.pin.sha256, attempt_id=binding.attempt_id,
        session_id=binding.session_id, history_sha256='a' * 64,
        phase1_seal_sha256=run.phase1.seal.pin.sha256, core_seal_sha256=run.phase1.core_seal.pin.sha256,
        effective_receipt=outputs['effective_receipt'], receipt_result=outputs['receipt_result'],
        receipt_carry=outputs['receipt_carry'], packet=outputs['packet'], typed_index=outputs['typed_index'],
        assembly=outputs['typed_assembly'], audit=outputs['audit'], counts_json=b'{}', stage_origins_json=b'{}')
    items = [m.captured for m in run.pool.members if m.captured.pin.role not in outputs] + list(outputs.values())
    run = replace_pool(replace(run, binding=binding, history=object()), items)
    calls = []
    def reconstruct(selection, execution, phase1, history, assembly_raw):
        assert selection is run.selection and execution is binding and phase1 is run.phase1 and history is run.history
        assert assembly_raw == outputs['typed_assembly'].raw
        calls.append('fresh reconstruction')
        return completion
    monkeypatch.setattr(stages, 'check_assembly', reconstruct)
    return {'run': run, 'snapshot': Snapshot(run.pool.members)}, calls


def test_receipt_gate_checks_effective_bytes_and_preserves_original(receipt_prepared, monkeypatch):
    prepared, calls = receipt_prepared
    before = prepared['run'].phase1.original_receipt.raw
    no_reads(monkeypatch)
    result = gates.receipt_gate(prepared)
    assert calls == ['fresh reconstruction'] and result['passed'] is True
    assert not any(result['floors'].values())
    assert result['original_receipt']['sha256'] == c.sha(before)
    assert result['effective_receipt']['sha256'] != c.sha(before)
    assert result['receipts']['snippets']['by_origin']['phase1']['total'] == 0
    assert result['receipts']['snippets']['by_origin']['rereceipt']['total'] == 1
    assert prepared['run'].phase1.original_receipt.raw == before


@pytest.mark.parametrize('mutation', ['original_changed', 'effective_changed', 'unreconstructed', 'final_changed'])
def test_receipt_gate_refuses_split_original_effective_or_incomplete_basis(receipt_prepared, mutation, monkeypatch):
    prepared, calls = receipt_prepared
    run = prepared['run']
    if mutation == 'unreconstructed':
        def refuse(*args): raise ValueError('typed assembly remains incomplete')
        monkeypatch.setattr(stages, 'check_assembly', refuse)
    else:
        role = {'original_changed': 'original_receipt_output', 'effective_changed': 'effective_receipt',
                'final_changed': 'final_full'}[mutation]
        items = [artifact(item.pin.role, item.pin.path,
                    b'description: The deployment is planned.\npurpose: An additional declared value.\n' if role == 'final_full' else item.raw + b'\n')
                 if item.pin.role == role else item for item in (m.captured for m in run.pool.members)]
        changed = replace_pool(run, items)
        # Keep captured reconstruction inputs/identity stable; only captured
        # ordinary/output bytes have changed in this adapter mutation.
        run.reader.pool = changed.pool
        run.reader.members.clear()
        prepared['snapshot'] = Snapshot(changed.pool.members)
    no_reads(monkeypatch)
    if mutation == 'final_changed':
        result = gates.receipt_gate(prepared)
        assert result['receipts']['slots']['receiptable'] == 2
        assert result['receipts']['slots']['with_receipt'] == 1
        assert result['passed'] is False and result['floors']['registered receipt coverage'] == 1
    else:
        with pytest.raises(ValueError): gates.receipt_gate(prepared)
    if mutation == 'original_changed': assert calls == []
