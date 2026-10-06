"""Capture real stage publications from explicitly synthetic declared histories."""
from dataclasses import replace
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_publication as publication
from data_sheets_schema import native_shared_stage as stage
from tests.test_native_shared_stages import (case, supplied, respond, receipt_answer,
    artifact, append, publish, replies)
from tests.test_native_shared_publication import private_case, invocation


def _materialize(case):
    selection, execution, phase1, history = case
    items = (execution.execution, execution.started, execution.binding_artifact,
        execution.init_observation, phase1.full, phase1.original_receipt,
        phase1.seal, phase1.full_seal_observation, phase1.core,
        phase1.core_seal, phase1.core_seal_observation,
        *history.records, *history.artifacts, *history.observations, history.journal)
    for item in items:
        if item is not None:
            path = Path(item.pin.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(item.raw)


def _admit(case, target, *, publish_request=True):
    case, _ = respond(case, receipt_answer(case))
    selection, execution, phase1, history = case
    # Pure-stage fixtures may reuse invented observation paths. A physical
    # capture requires one distinct immutable path for every observation.
    observation = artifact('observation', selection.role('observations_root') +
        f'/{len(history.observations) + 2:06d}.json', b'{"fixture":"core helper"}')
    phase1 = replace(phase1,
        core=artifact('phase1_core', selection.role('phase1_core'), b'name: Example\n'),
        core_seal=artifact('core_seal', selection.role('core_seal'), b'{"fixture":"core sealed"}'),
        core_seal_observation=observation)
    history = replace(history, observations=(*history.observations, observation))
    records, journal = stage.append_records(selection, execution, history, (
        ('core_sealed', c.canonical({'seal': c.pin_dict(phase1.core_seal.pin),
            'core': c.pin_dict(phase1.core.pin), 'observation': c.pin_dict(observation.pin)})),))
    case = selection, execution, phase1, append(history, records, journal)
    while True:
        decision = stage.prepare_next(*case)
        assert decision.state == 'request_ready'
        if decision.cursor.kind == target:
            _materialize(case)
            if not publish_request:
                return case, decision, ()
            result, observed = publication.publish_derived(invocation(case), decision)
            assert result['state'] == 'awaiting_response'
            expected = publish(case[3], decision)
            return (*case[:3], expected), decision, observed
        packet = stage._Replay(*case).run().packet
        workers, omission, delta, _ = replies(packet, 2)
        raw = workers[decision.cursor.target_id] if decision.cursor.kind == 'worker' else c.canonical(
            omission if decision.cursor.kind == 'omission' else delta)
        case, checked = respond(case, raw)
        assert checked.disposition == 'checked'


@pytest.mark.parametrize('target,role', [('worker', 'packet'), ('integration', 'typed_index')])
def test_actual_auxiliary_publication_survives_live_and_saved_history_capture(private_case, monkeypatch, target, role):
    case, decision, published = _admit(private_case, target)
    selection, execution, phase1, expected = case
    auxiliary = next(item.captured for item in published if item.captured.pin.role == role)
    assert auxiliary.pin.path == selection.role(role)
    reader = capture._Reader(selection)
    history = reader.history(execution)
    assert auxiliary in history.artifacts
    live = stage.prepare_next(selection, execution, phase1, history)
    assert live.state == 'awaiting_response'
    assert live.request == stage.prepare_next(*case).request
    pool = evidence.CapturePool(tuple(reader.members.values()), ())
    def forbidden(*args, **kwargs):
        pytest.fail('saved history attempted filesystem I/O')
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    saved = capture._Reader(selection, pool=pool).history(execution)
    assert saved == history
    assert stage.prepare_next(selection, execution, phase1, saved) == live


@pytest.mark.parametrize('target,role', [('worker', 'packet'), ('integration', 'typed_index')])
@pytest.mark.parametrize('change', ['missing', 'tampered'])
def test_live_auxiliary_is_required_and_reconstructed(private_case, target, role, change):
    case, _, _ = _admit(private_case, target)
    selection, execution, phase1, _ = case
    path = Path(selection.role(role))
    if change == 'missing':
        path.unlink()
        with pytest.raises((OSError, ValueError)):
            capture._Reader(selection).history(execution)
    else:
        path.write_bytes(path.read_bytes() + b' ')
        history = capture._Reader(selection).history(execution)
        with pytest.raises(ValueError, match='exact captured artifact'):
            stage.prepare_next(selection, execution, phase1, history)


@pytest.mark.parametrize('target,role', [('worker', 'packet'), ('integration', 'typed_index')])
@pytest.mark.parametrize('change', ['missing', 'ambiguous', 'tampered'])
def test_saved_auxiliary_has_no_live_fallback(private_case, monkeypatch, target, role, change):
    case, _, _ = _admit(private_case, target)
    selection, execution, phase1, _ = case
    reader = capture._Reader(selection)
    reader.history(execution)
    members = tuple(reader.members.values())
    original = next(m for m in members if m.captured.pin.role == role)
    raw = original.captured.raw + b' '
    changed = evidence.PoolMember(
        c.CapturedArtifact(replace(original.captured.pin, bytes=len(raw), sha256=c.sha(raw)), raw),
        c.canonical({**c.strict_json(original.metadata_json), 'size': len(raw)}))
    others = tuple(m for m in members if m != original)
    selected = others if change == 'missing' else (
        (*members, changed) if change == 'ambiguous' else (*others, changed))
    pool = evidence.CapturePool(selected, ())
    def forbidden(*args, **kwargs):
        pytest.fail('missing or altered saved evidence reached live filesystem')
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    if change in ('missing', 'ambiguous'):
        with pytest.raises(ValueError, match='one exact artifact version'):
            capture._Reader(selection, pool=pool).history(execution)
    else:
        history = capture._Reader(selection, pool=pool).history(execution)
        with pytest.raises(ValueError, match='exact captured artifact'):
            stage.prepare_next(selection, execution, phase1, history)


@pytest.mark.parametrize('target,role,limit', [('worker', 'packet', 'packet_bytes'),
    ('integration', 'typed_index', 'assembly_bytes')])
def test_auxiliary_capture_enforces_its_role_byte_bound(private_case, monkeypatch, target, role, limit):
    case, _, published = _admit(private_case, target)
    selection, execution, _, _ = case
    artifact = next(m.captured for m in published if m.captured.pin.role == role)
    monkeypatch.setattr(c, 'HARD_LIMITS', {**c.HARD_LIMITS, limit: len(artifact.raw) - 1})
    with pytest.raises(ValueError):
        capture._Reader(selection).history(execution)


@pytest.mark.parametrize('target,role', [('worker', 'packet'), ('integration', 'typed_index')])
def test_unadmitted_auxiliary_path_is_not_read(private_case, monkeypatch, target, role):
    case, _, _ = _admit(private_case, target, publish_request=False)
    selection, execution, phase1, _ = case
    path = Path(selection.role(role))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'unadmitted bytes must not become authority')
    real = evidence.read_regular
    def guarded(pathname, actual_role, **kwargs):
        assert actual_role != role
        return real(pathname, actual_role, **kwargs)
    monkeypatch.setattr(evidence, 'read_regular', guarded)
    history = capture._Reader(selection).history(execution)
    assert not any(item.pin.role == role for item in history.artifacts)
    assert stage.prepare_next(selection, execution, phase1, history).state == 'request_ready'


@pytest.mark.parametrize('target', ['worker', 'integration'])
def test_auxiliary_bytes_count_toward_complete_capture_budget(private_case, monkeypatch, target):
    case, _, _ = _admit(private_case, target)
    selection, execution, _, _ = case
    reader = capture._Reader(selection)
    reader.history(execution)
    total = reader.total
    bounds = selection.bounds()
    monkeypatch.setattr(c.NativeSelectionCapture, 'bounds', lambda self: {
        **bounds, 'max_evidence_bytes': total - 1})
    with pytest.raises(ValueError, match='complete stage capture exceeds its total bound'):
        capture._Reader(selection).history(execution)
