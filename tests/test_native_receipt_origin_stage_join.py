"""Real pure stage/assembly/receipt/report join over fictional captured history.

The reused fixture invents authority, seals and observations. This test does not
claim a native controller capture, permission observation or COMPLETE pool.
No production checker is replaced, and no native transcript is fabricated.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import socket
import subprocess

import pytest

from data_sheets_schema import audit_omissions as omissions, resources
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_gates as gates
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_shared_selection as selection_api
from data_sheets_schema import native_receipt_origin as origin
from data_sheets_schema.native_shared_capture import _CapturedRun, _Reader
from data_sheets_schema.native_shared_results import Snapshot
from tests.test_native_shared_stages import case, artifact, respond, publish, add_core, append
from tests.test_typed_audit import supplied, replies


def _with_actual_policy(case):
    """Keep the fictional stage fixture, but capture the real gate policy asset."""
    selected, binding, phase1, _ = case
    raw = (Path(__file__).resolve().parents[1] / selection_api.RECEIPT_POLICY).read_bytes()
    assert c.sha(raw) == selection_api.RECEIPT_POLICY_SHA256
    old_asset = next(item for item in selected.authority if item.pin.role == 'native_policy')
    asset = artifact(old_asset.pin.role, old_asset.pin.path, raw)
    policy = c.strict_json(selected.receipt_policy.raw)
    policy['runtime_policy_sha256'] = asset.pin.sha256
    policy_artifact = artifact(selected.receipt_policy.pin.role,
                               selected.receipt_policy.pin.path, c.canonical(policy))
    descriptor = c.strict_json(selected.descriptor.raw)
    name = descriptor['receipt_policy']['path']
    descriptor['receipt_policy']['sha256'] = asset.pin.sha256
    descriptor['assets'][name] = asset.pin.sha256
    descriptor_raw = c.canonical(descriptor)
    descriptor_capture = c.DescriptorCapture(descriptor_raw, c.sha(descriptor_raw))
    doc = selected.document()
    doc['selection']['descriptor_sha256'] = descriptor_capture.sha256
    doc['selection']['assets'][name] = {key: getattr(asset.pin, key)
                                      for key in ('path', 'bytes', 'sha256')}
    doc['receipt_policy'] = {key: getattr(policy_artifact.pin, key)
                             for key in ('path', 'bytes', 'sha256')}
    changed = {asset.pin.role: asset, policy_artifact.pin.role: policy_artifact}
    selected = replace(selected, descriptor=descriptor_capture, receipt_policy=policy_artifact,
        authority=tuple(changed.get(item.pin.role, item) for item in selected.authority),
        registration=artifact('selection', selected.registration.pin.path, c.canonical(doc)))
    binding = replace(binding, selection_sha256=selected.registration.pin.sha256)
    journal = artifact('journal', selected.role('journal'), stage.journal_bytes(
        selection_sha256=selected.registration.pin.sha256,
        execution_sha256=binding.execution.pin.sha256, attempt_id=binding.attempt_id, records=()))
    history = c.RawHistory(journal=journal, records=(), artifacts=(), observations=())
    entries = (
        ('genesis', c.canonical({'execution': c.pin_dict(binding.execution.pin),
                                'started': c.pin_dict(binding.started.pin)})),
        ('session_bound', c.canonical({'binding': c.pin_dict(binding.binding_artifact.pin),
                                      'init_observation': c.pin_dict(binding.init_observation.pin)})),
        ('phase1_sealed', c.canonical({'seal': c.pin_dict(phase1.seal.pin),
            'full': c.pin_dict(phase1.full.pin), 'original_receipt': c.pin_dict(phase1.original_receipt.pin),
            'observation': c.pin_dict(phase1.full_seal_observation.pin)})))
    records, journal = stage.append_records(selected, binding, history, entries)
    return selected, binding, phase1, append(history, records, journal)


def _complete_with_added_receipt(case):
    manifest = c.strict_json(case[0].raw('chunk_manifest'))
    chunk = next(row for row in manifest['chunks'] if row.get('source') == 'manual.txt')
    answer = c.canonical({'rereceipt': [{'path': 'name', 'receipt': {
        'chunk': chunk['id'], 'snippet': 'Example release provides a complete description.'}}]})
    case, transition = respond(case, answer)
    assert transition.disposition == 'checked'
    waiting = stage.prepare_next(*case)
    assert waiting.state == 'await_core'
    case = add_core((*case[:3], publish(case[3], waiting)))
    for _ in range(case[0].bounds()['max_submissions']):
        decision = stage.prepare_next(*case)
        if decision.state == 'assembly_complete':
            return case, decision.completion
        assert decision.state == 'request_ready'
        packet = stage._Replay(*case).run().packet
        workers, omission, integration, _ = replies(packet, 2)
        raw = (workers[decision.cursor.target_id] if decision.cursor.kind == 'worker'
               else c.canonical(omission if decision.cursor.kind == 'omission' else integration))
        case, transition = respond(case, raw)
        assert transition.disposition == 'checked'
    raise AssertionError('fictional stage fixture did not reach assembly completion')


def _prepared(case, completion, *, effective_raw=None, assembly_raw=None):
    selected, binding, phase1, history = case
    paths = {name: '/neutral/output/' + name + '.yaml'
             for name in ('full', 'core', 'receipt', 'report')}
    items = [completion.effective_receipt, completion.receipt_result,
             completion.receipt_carry, completion.packet, completion.typed_index,
             completion.assembly, completion.audit,
             artifact('original_receipt_output', paths['receipt'], phase1.original_receipt.raw),
             artifact('final_full', paths['full'], phase1.full.raw)]
    replacements = {'effective_receipt': effective_raw, 'typed_assembly': assembly_raw}
    items = [artifact(item.pin.role, item.pin.path, replacements[item.pin.role])
             if replacements.get(item.pin.role) is not None else item for item in items]
    members = tuple(evidence.PoolMember(item, c.canonical({
        'exists': True, 'regular': True, 'symlink': False, 'links': 1,
        'device': 0, 'inode': index, 'size': len(item.raw), 'mtime_ns': 0}))
        for index, item in enumerate(items, 1))
    pool = evidence.CapturePool(members, ())
    snapshot = Snapshot('/neutral', members)
    snapshot.sealed = True
    value = {'kind': 'd4d_native_shared_execution_registration',
             origin.KEY: origin.declaration('/neutral/attempt', paths)}
    run = _CapturedRun(selection=selected, value=value,
        composition={'policy': {'post_final_recorder': {'destination': '/neutral/provenance.yaml'}}},
        spec=SimpleNamespace(_agentic_artifact_paths=paths), reader=_Reader(selected, pool=pool),
        pool=pool, transcript=None, control=None, binding=binding, history=history,
        observations=(), phase1=phase1)
    return {'run': run, 'snapshot': snapshot}, value


def test_real_stage_assembly_receipt_and_saved_origin_join(case, tmp_path, monkeypatch):
    # Ordinary fixture setup above captures all schema/asset bytes. From here,
    # every actual production derivation must use those immutable carriers.
    import data_sheets_schema.schema_view
    case = _with_actual_policy(case)
    before = case[2].original_receipt.raw
    def forbidden(*args, **kwargs):
        pytest.fail('pure reporting join consulted ambient files or launched a process/transport')
    with monkeypatch.context() as guard:
        for name in ('read_bytes', 'read_text', 'open', 'resolve'):
            guard.setattr(Path, name, forbidden)
        guard.setattr(resources, 'resource_path', forbidden)
        guard.setattr(omissions, '_asset', forbidden)
        guard.setattr(evidence, 'read_regular', forbidden)
        guard.setattr(subprocess, 'Popen', forbidden)
        guard.setattr(socket, 'socket', forbidden)
        completed, completion = _complete_with_added_receipt(case)
        assert stage.check_assembly(*completed, completion.assembly.raw) == completion
        assert completion.effective_receipt.raw != before
        prepared, value = _prepared(completed, completion)
        gate = gates.receipt_gate(prepared)
        assert gate['passed'] is True and not any(gate['floors'].values()), gate
        assert gate['receipts']['final_stage_complete'] is True
        assert gate['receipts']['snippets']['by_origin']['rereceipt']['total'] == 1
        assert gate['original_receipt']['sha256'] == c.sha(before)
        assert gate['effective_receipt'] == c.pin_dict(completion.effective_receipt.pin)
        assert prepared['run'].phase1.original_receipt.raw == before
        reported = origin.attach_prepared(value, {'receipts': gate}, prepared)['receipts']
        assert {key: reported[key] for key in gate} == gate
        snapshot = prepared['snapshot']
        origin.check_saved(value, reported, raw=snapshot.raw,
                           aliases=snapshot.aliases, metadata=snapshot.metadata)
        report = reported[origin.REPORT_KEY]
        assert report['inputs']['original_receipt']['sha256'] == c.sha(before)
        assert report['inputs']['effective_receipt']['sha256'] == completion.effective_receipt.pin.sha256
        assert report['inputs']['original_receipt']['path'] != report['inputs']['effective_receipt']['path']
        assert report['inputs']['transcript'] is None
        assert report['original_receipt']['status'] == report['effective_receipt']['status'] == 'unknown'
        assert 'origin' not in report['effective_receipt']

        changed_report = deepcopy(reported)
        changed_report[origin.REPORT_KEY]['inputs']['effective_receipt']['sha256'] = '0' * 64
        with pytest.raises(ValueError, match='saved receipt-origin report differs'):
            origin.check_saved(value, changed_report, raw=snapshot.raw,
                               aliases=snapshot.aliases, metadata=snapshot.metadata)
        changed, _ = _prepared(completed, completion,
                               effective_raw=completion.effective_receipt.raw + b'\n')
        with pytest.raises(ValueError, match='effective native receipt differs from reconstructed'):
            gates.receipt_gate(changed)
        assembly = c.strict_json(completion.assembly.raw, max_bytes=c.HARD_LIMITS['assembly_bytes'])
        assembly['foreign_extension'] = True
        changed, _ = _prepared(completed, completion, assembly_raw=c.canonical(assembly))
        with pytest.raises(ValueError, match='assembly differs from exact current captured history'):
            gates.receipt_gate(changed)
        assert prepared['run'].phase1.original_receipt.raw == before

    # Retained engineering evidence, written only after the pure-operation barrier.
    out = tmp_path / 'join-evidence'
    out.mkdir()
    for name, raw in {'original-receipt.yaml': before,
                      'effective-receipt.yaml': completion.effective_receipt.raw,
                      'assembly.json': completion.assembly.raw,
                      'gate.json': c.canonical(gate), 'reported-gate.json': c.canonical(reported)}.items():
        (out / name).write_bytes(raw)
    (out / 'summary.json').write_bytes(c.canonical({
        'scope': 'Fictional pure stage history; no observed native controller or COMPLETE pool.',
        'assembly_sha256': completion.assembly.pin.sha256,
        'original_receipt_sha256': c.sha(before),
        'effective_receipt_sha256': completion.effective_receipt.pin.sha256,
        'real_receipt_gate_passed': gate['passed'], 'negative_controls': 3,
        'stage_counts': c.strict_json(completion.counts_json)}))
