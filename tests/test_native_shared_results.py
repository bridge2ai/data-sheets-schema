"""Real bounded initial capture and saved-only reconstruction; invented frames."""
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_native_shared_live_capture import started, native_init, stream_capture
from tests.test_native_shared_registration import execution, bound, native_spec, declaration
from data_sheets_schema import native_shared_capture as cap
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_contract as c


def initial(started):
    selection, value, composition, raw, start = started
    transcript, control = native_init(selection, value, composition)
    cap.initialize(selection.registration.pin.path, transcript_bytes=len(transcript), control_bytes=len(control), **stream_capture(value))
    live = cap._load(selection.registration.pin.path)
    members = {member.member_id: member for member in live.pool.members}
    for artifact in (selection.registration, selection.receipt_policy, *selection.authority,
                     *(a for s in selection.schemas for a in s.sources)):
        member = evidence.read_regular(artifact.pin.path, artifact.pin.role, max_bytes=artifact.pin.bytes)
        members[member.member_id] = member
    return live, evidence.CapturePool(tuple(members.values()), live.pool.stream_bindings)


def test_saved_initial_capture_rebuild_has_no_filesystem_fallback(started, monkeypatch):
    live, pool = initial(started)
    def forbidden(*a, **k):
        pytest.fail('saved reconstruction read filesystem')
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    rebuilt = results.rebuild(pool, live.value)
    assert rebuilt.selection == live.selection
    assert rebuilt.binding == live.binding
    assert rebuilt.history == live.history
    assert rebuilt.phase1 is None
    assert cap.phase_replay(rebuilt)[0]['passed']


def test_saved_observation_gap_and_foreign_execution_refuse(started):
    live, pool = initial(started)
    missing = evidence.CapturePool(tuple(m for m in pool.members
        if m.captured.pin.role != 'observation'), pool.stream_bindings)
    with pytest.raises(ValueError):
        results.rebuild(missing, live.value)
    wrong = {**live.value, 'attempt_id': 'foreign'}
    with pytest.raises(ValueError):
        results.rebuild(pool, wrong)


def test_actual_selected_receipt_paths_need_no_future_seal(started):
    selection, value, composition, raw, start = started
    actual = cap.selected_receipt_paths(selection.registration.pin.path)
    paths = composition['render_spec']['agentic_artifact_paths']
    assert actual['full'] == Path(paths['full'])
    assert actual['receipt'] == Path(paths['receipt'])
    assert actual['provenance'] == Path(composition['policy']['post_final_recorder']['destination'])
    assert actual['core_dir'] == Path(paths['core']).parent
    assert not Path(selection.role('phase1_seal')).exists()


def test_saved_snapshot_never_reads_uncaptured_target(tmp_path, monkeypatch):
    path = tmp_path / 'member.json'; path.write_bytes(b'{}')
    member = evidence.read_regular(str(path), 'one', max_bytes=10)
    snapshot = results.Snapshot(str(tmp_path), (member,)); snapshot.sealed = True
    monkeypatch.setattr(Path, 'read_bytes', lambda *a: pytest.fail('saved snapshot read live file'))
    assert snapshot.read(path, 'one') == b'{}'
    with pytest.raises(ValueError, match='uncaptured'):
        snapshot.read(tmp_path / 'missing.json', 'missing')
    with pytest.raises(ValueError, match='sealed'):
        snapshot.add(member)


@pytest.mark.parametrize('change', ['bytes', 'metadata'])
def test_actual_snapshot_publication_guard_catches_drift(tmp_path, change):
    path = tmp_path / 'member.json'; path.write_bytes(b'{}')
    member = evidence.read_regular(str(path), 'one', max_bytes=10)
    snapshot = results.Snapshot(str(tmp_path), (member,)); snapshot.sealed = True
    if change == 'bytes': path.write_bytes(b'[]')
    else: path.touch()
    with pytest.raises(ValueError, match='changed'):
        snapshot.verify_unchanged()


def test_publication_cannot_collapse_contradictory_versions(tmp_path):
    path = tmp_path / 'member.json'; path.write_bytes(b'{}')
    first = evidence.read_regular(str(path), 'one', max_bytes=10)
    path.write_bytes(b'[]')
    second = evidence.read_regular(str(path), 'two', max_bytes=10)
    with pytest.raises(ValueError, match='contradictory'):
        results.Snapshot(str(tmp_path), (first, second))


def test_new_file_basis_rejects_oversized_declaration_without_open(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'read_regular', lambda *a, **k: pytest.fail('oversized file opened'))
    result = {'captured_files': {str(tmp_path / 'large'): {'bytes': c.HARD_LIMITS['stream_bytes'] + 1,
        'sha256': 'a' * 64, 'roles': ['transcript']}}}
    with pytest.raises(ValueError, match='oversized'):
        results.validate_file_basis({}, result)


def test_large_pool_open_is_bounded_and_preserves_bytes(tmp_path):
    path = tmp_path / 'pool'; path.write_bytes(b'123456789')
    assert results._read_pool(str(path), 9) == b'123456789'
    with pytest.raises(ValueError, match='bounded'):
        results._read_pool(str(path), 8)
    assert path.read_bytes() == b'123456789'


@pytest.mark.parametrize('order', ['settled', 'write_call_before_result', 'callback_before_result'])
def test_response_intent_requires_completed_read_before_both_native_announcements(order):
    from copy import deepcopy
    from tests.test_native_shared_observations import events, trace
    native, parent, request = events()
    writes, decisions, _ = events('Write', b'{"answer":true}')
    # Distinct actual native identities; each callback/result joins its own call.
    for row in writes + decisions:
        def rename(value):
            if isinstance(value, dict): return {k: rename(v) for k, v in value.items()}
            if isinstance(value, list): return [rename(v) for v in value]
            return {'tool-1': 'tool-2', 'callback-1': 'callback-2'}.get(value, value) if isinstance(value, str) else value
        row.update(rename(deepcopy(row)))
    if order == 'settled': frames = native + writes[:2]
    elif order == 'write_call_before_result': frames = native[:2] + [writes[0], native[2], writes[1]]
    else: frames = native[:2] + writes[:2] + [native[2]]
    actual = trace(frames, parent + decisions)
    read = actual.settled('tool-1')
    from data_sheets_schema.native_shared_observations import complete_request_read
    assert complete_request_read(actual, read, request)
    write = actual.request('tool-2')
    if order == 'settled': cap._require_completed_read_before_write(write, read)
    else:
        with pytest.raises(ValueError, match='complete current request Read'):
            cap._require_completed_read_before_write(write, read)
