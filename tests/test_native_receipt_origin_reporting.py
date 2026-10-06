"""Captured reporting and real saved readers, without native execution.

Saved-publication fixtures disclose a private registration-parser seam. Their
file capture, publication hashes, metadata checks and reporting recheck are
real; the failed publications make no runtime-completion claim.
"""
from copy import deepcopy
import os
from pathlib import Path
import socket
import subprocess

import pytest

from data_sheets_schema import native_attribution_registration as encoding
from data_sheets_schema.native_attribution_results import Capture
from data_sheets_schema import native_receipt_origin as origin
from data_sheets_schema import native_execution as direct
from data_sheets_schema import native_shared_execution as shared
from data_sheets_schema import native_attempt_supervisor as supervisor
from tests.test_receipt_origin_record import _three_origins
from tests.test_native_shared_gates import receipt_prepared, captured_run, declaration, inputs

FAMILIES = ('native_attribution', 'neutral_supervisor', 'native_shared')
KINDS = {v: k for k, v in origin.FAMILIES.items()}


@pytest.fixture
def captured(tmp_path):
    run, transcript = _three_origins(tmp_path / 'attempt')
    run.full.write_bytes(b'id: x\n')
    effective = tmp_path / 'effective.yaml'
    effective.write_bytes(run.receipt.read_bytes())  # Equal bytes, distinct identity.
    core = run.receipt.with_name('CHORUS_d4d_core.yaml')
    core.write_bytes(b'id: x\n')  # Known distinct output of the actual derive spelling.
    capture = Capture(tmp_path)
    for path, role in ((transcript, 'transcript'), (run.receipt, 'receipt'),
                       (run.full, 'full'), (effective, 'effective_receipt'), (core, 'core')):
        capture.read(path, role)
    capture.sealed = True
    return run, capture, effective


def value_for(family, run):
    return {'kind': KINDS[family], origin.KEY: origin.declaration(str(run.root),
        {'receipt': str(run.receipt), 'full': str(run.full)})}


def gate_for(capture, effective, family):
    gate = {'checked': True, 'passed': True, 'floors': {'synthetic floor': 0}}
    if family == 'native_shared':
        gate['effective_receipt'] = {'role': 'effective_receipt', 'path': str(effective),
            'bytes': len(capture.raw[str(effective)]), 'sha256': encoding._sha(capture.raw[str(effective)])}
    return gate


@pytest.mark.parametrize('family', FAMILIES)
def test_actual_captured_history_is_reported_without_ambient_operations(captured, family, monkeypatch):
    run, capture, effective = captured
    value = value_for(family, run)
    gate = gate_for(capture, effective, family)
    before = deepcopy(gate)
    def forbidden(*args, **kwargs):
        pytest.fail('captured reporting consulted the ambient host')
    with monkeypatch.context() as guard:
        for name in ('read_bytes', 'read_text', 'open', 'resolve'):
            guard.setattr(Path, name, forbidden)
        guard.setattr(os, 'getcwd', forbidden)
        guard.setattr(subprocess, 'Popen', forbidden)
        guard.setattr(socket, 'socket', forbidden)
        reported = origin.attach(value, gate, raw=capture.raw,
                                 aliases=capture.aliases, metadata=capture.metadata)
        origin.check_saved(value, reported, raw=capture.raw,
                           aliases=capture.aliases, metadata=capture.metadata)
    assert gate == before and set(reported) == set(gate) | {origin.REPORT_KEY}
    for key in gate:
        assert reported[key] == gate[key]
    block = reported[origin.REPORT_KEY]
    assert block['original_receipt']['status'] == 'checked', block['original_receipt']
    assert block['original_receipt']['origin'] == {
        'contemporaneous': 3, 'phase1_correction': 1, 'phase3_backport': 1}
    if family == 'native_shared':
        assert block['effective_receipt']['status'] == 'unknown'
        assert 'origin' not in block['effective_receipt']
        assert block['inputs']['effective_receipt']['sha256'] == block['inputs']['original_receipt']['sha256']
        assert block['inputs']['effective_receipt']['path'] != block['inputs']['original_receipt']['path']


@pytest.mark.parametrize('family', FAMILIES)
def test_default_output_unchanged_and_declared_missing_capture_is_unknown(family, captured):
    run, capture, effective = captured
    gate = gate_for(capture, effective, family)
    legacy = {'kind': KINDS[family]}
    assert origin.attach(legacy, gate, raw={}, aliases={}, metadata={}) is gate
    origin.check_saved(legacy, gate, raw={}, aliases={}, metadata={})
    value = value_for(family, run)
    unavailable = origin.attach(value, gate, raw={}, aliases={}, metadata={})
    assert unavailable[origin.REPORT_KEY]['original_receipt']['status'] == 'unknown'
    assert all(pin is None for pin in unavailable[origin.REPORT_KEY]['inputs'].values())
    with pytest.raises(ValueError, match='undeclared'):
        origin.check_saved(legacy, unavailable, raw={}, aliases={}, metadata={})


def publish(value, raw, result):
    evidence = Path(value['evidence_directory'])
    final = encoding._encoded(result)
    (evidence / 'final.json').write_bytes(final)
    (evidence / 'published.json').write_bytes(encoding._encoded({
        'final_sha256': encoding._sha(final), 'registration_sha256': encoding._sha(raw),
        'started_sha256': result['started_sha256']}))


@pytest.fixture(params=FAMILIES)
def saved(captured, tmp_path, monkeypatch, request):
    family, reporting_version = request.param if isinstance(request.param, tuple) else (request.param, 1)
    run, capture, effective = captured
    module = {'native_attribution': direct, 'native_shared': shared,
              'neutral_supervisor': supervisor}[family]
    value = value_for(family, run)
    if reporting_version == 0:
        value.pop(origin.KEY)
    evidence = tmp_path / 'evidence'; evidence.mkdir()
    value.update(attempt_directory=str(run.root), evidence_directory=str(evidence),
                 attempt_id='synthetic-readback', composition_sha256='a' * 64,
                 runtime={'keep_awake': {'policy': 'not_applicable'}})
    raw = encoding._encoded(value)
    # The only authority seam: test the real reader, not a native launch.
    registration = module if family == 'neutral_supervisor' else module.registration
    def verified(supplied):
        assert supplied == raw
        return deepcopy(value)
    monkeypatch.setattr(registration, 'verified', verified)
    (run.root / 'registration.json').write_bytes(raw)
    started = b'{}\n'; (run.root / 'started.json').write_bytes(started)
    names = supervisor.GATES if family == 'neutral_supervisor' else direct.gates.GATES
    gates = {name: {'checked': False, 'passed': False, 'reason': 'synthetic stopped capture'} for name in names}
    # The captured origin may be classified, independently of failed gates.
    gates['receipts'] = {**gate_for(capture, effective, family), 'checked': False, 'passed': False}
    gates = origin.attach_prepared(value, gates, {'snapshot': capture})
    result = {'kind': module.KIND, 'version': 1, 'attempt_id': value['attempt_id'],
        'composition_sha256': value['composition_sha256'], 'registration_sha256': encoding._sha(raw),
        'started_sha256': encoding._sha(started), **module.UNASSESSED,
        'first_stop': 'synthetic stopped capture', 'gates': gates,
        'captured_files': capture.identity(), 'captured_aliases': dict(capture.aliases),
        'captured_metadata': deepcopy(capture.metadata),
        'captured_alias_metadata': deepcopy(capture.alias_metadata), 'additional_report': None}
    if family == 'neutral_supervisor':
        result.update(engineering_completion=False, execution=supervisor.EXECUTION)
    else:
        result.update(runtime_gates_passed=False, state='failed', runtime_observation=None,
                      keep_awake=None, lifecycle_artifacts={})
    publish(value, raw, result)
    return module, value, raw, result, capture


def test_real_saved_reader_accepts_captured_report_and_refuses_rehashed_changes(saved):
    module, value, raw, result, capture = saved
    before = {path: Path(path).read_bytes() for path in capture.raw}
    assert module.read_final(raw) == result
    for mutation in ('count', 'pin', 'missing', 'foreign'):
        changed = deepcopy(result)
        report = changed['gates']['receipts'][origin.REPORT_KEY]
        if mutation == 'count':
            report['original_receipt']['origin']['contemporaneous'] += 1
        elif mutation == 'pin':
            report['inputs']['original_receipt']['sha256'] = '0' * 64
        elif mutation == 'missing':
            del changed['gates']['receipts'][origin.REPORT_KEY]
        else:
            report['declaration']['receipt_path'] = '/foreign/receipt.yaml'
        publish(value, raw, changed)  # Honest new outer checksums cannot grant semantic credit.
        with pytest.raises(ValueError, match='receipt-origin'):
            module.read_final(raw)
    assert {path: Path(path).read_bytes() for path in capture.raw} == before


def test_real_saved_reader_checks_unavailable_report_before_failed_early_return(saved):
    module, value, raw, result, _ = saved
    result.update(captured_files={}, captured_aliases={}, captured_metadata={}, captured_alias_metadata={})
    gate = result['gates']['receipts']
    gate.pop(origin.REPORT_KEY)
    result['gates']['receipts'] = origin.attach(value, gate, raw={}, aliases={}, metadata={})
    publish(value, raw, result)
    assert module.read_final(raw) == result
    result['gates']['receipts'][origin.REPORT_KEY]['original_receipt']['status'] = 'checked'
    publish(value, raw, result)
    with pytest.raises(ValueError, match='receipt-origin'):
        module.read_final(raw)


@pytest.mark.parametrize('saved', [(family, 0) for family in FAMILIES], indirect=True)
def test_default_public_reader_keeps_exact_result_and_refuses_undeclared_extension(saved):
    module, value, raw, result, _ = saved
    assert origin.KEY not in value and origin.REPORT_KEY not in result['gates']['receipts']
    assert encoding._encoded(module.read_final(raw)) == encoding._encoded(result)
    result['gates']['receipts'][origin.REPORT_KEY] = {'version': 1, 'status': 'unknown'}
    publish(value, raw, result)
    with pytest.raises(ValueError, match='undeclared receipt-origin'):
        module.read_final(raw)


def test_actual_native_receipt_gate_pins_and_floors_are_preserved(receipt_prepared, monkeypatch):
    """Real receipt/floor/pin checks; existing fixture spies typed assembly only."""
    from data_sheets_schema import native_shared_gates
    from tests.test_native_shared_gates import no_reads
    prepared, calls = receipt_prepared
    run = prepared['run']
    raw = {m.captured.pin.path: m.captured.raw for m in run.pool.members}
    aliases = {path: path for path in raw}
    metadata = {path: {'exists': True, 'regular': True} for path in raw}
    value = {'kind': KINDS['native_shared'], origin.KEY: origin.declaration(
        '/synthetic/attempt', run.spec._agentic_artifact_paths)}
    no_reads(monkeypatch)
    gate = {'checked': True, **native_shared_gates.receipt_gate(prepared)}
    before = deepcopy(gate)
    reported = origin.attach(value, gate, raw=raw, aliases=aliases, metadata=metadata)
    assert calls == ['fresh reconstruction'] and gate == before
    assert gate['passed'] is True and not any(gate['floors'].values())
    block = reported[origin.REPORT_KEY]
    assert block['inputs']['original_receipt']['sha256'] == gate['original_receipt']['sha256']
    assert block['inputs']['effective_receipt']['sha256'] == gate['effective_receipt']['sha256']
    assert block['inputs']['original_receipt']['sha256'] != block['inputs']['effective_receipt']['sha256']
    assert block['original_receipt']['status'] == 'unknown'  # No transcript invented by this fixture.
    assert block['effective_receipt']['status'] == 'unknown'
    assert {k: reported[k] for k in gate} == before


@pytest.mark.parametrize('bad', [True, False, None, -1, 2, 1.0, '1'])
@pytest.mark.parametrize('module', [direct.registration, shared.registration, supervisor])
def test_invalid_registration_optin_refuses_before_reading_inputs(module, bad):
    kwargs = {'receipt_origin_version': bad, 'attempt_id': 'a', 'attempt_directory': '/a',
              'evidence_directory': '/e'}
    if module is supervisor:
        kwargs.update(deadline_seconds=1, synthetic_runtime={})
    elif module is direct.registration:
        kwargs.update(permission_probe_path='/probe', runtime={})
    else:
        kwargs.update(permission_probe_path='/probe', max_draft_checks=1)
    with pytest.raises(ValueError, match='receipt_origin_version'):
        module.registration('/does-not-exist', '/does-not-exist', **kwargs)
