"""Bounded role reads and immutable saved-prefix reconstruction, no launch."""
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_native_shared_stages import case, supplied
from tests.test_native_shared_publication import private_case
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_evidence as evidence


def test_actual_selected_journal_capture_then_no_io_saved_read(private_case, monkeypatch):
    selection, execution, _, history = private_case
    reader = capture._Reader(selection)
    result = reader.history(execution)
    assert result.journal == history.journal and result.records == history.records
    assert execution.execution in result.artifacts
    assert execution.init_observation in result.observations
    pool = evidence.CapturePool(tuple(reader.members.values()), ())
    def forbidden(*a, **k): pytest.fail('saved reader performed filesystem I/O')
    monkeypatch.setattr(evidence, 'read_regular', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    assert capture._Reader(selection, pool=pool).history(execution) == result


@pytest.mark.parametrize('role,path', [
    ('response', '/outside/000001.bin'), ('record', '/outside/000000.json'),
    ('unknown', '/outside/unused'), ('selection', '/outside/selection.json')])
def test_role_escape_refuses_before_open(private_case, monkeypatch, role, path):
    selection, *_ = private_case
    monkeypatch.setattr(evidence, 'read_regular', lambda *a, **k: pytest.fail('foreign input read'))
    with pytest.raises(ValueError): capture._Reader(selection).read(role, path)


def test_hash_and_oversized_pin_fail_before_source_can_be_used(private_case, monkeypatch):
    selection, _, phase1, _ = private_case
    bad = replace(phase1.full.pin, sha256='0' * 64)
    with pytest.raises(ValueError, match='exact pin'): capture._Reader(selection).read(bad.role, bad.path, bad)
    too_large = replace(phase1.full.pin, bytes=c.HARD_LIMITS['original_full_bytes']+1)
    monkeypatch.setattr(evidence, 'read_regular', lambda *a, **k: pytest.fail('oversized read'))
    with pytest.raises(ValueError, match='bounded artifact'): capture._Reader(selection).read(too_large.role, too_large.path, too_large)


def test_saved_reader_refuses_missing_or_ambiguous_version(private_case):
    selection, execution, *_ = private_case
    reader = capture._Reader(selection); reader.history(execution)
    members = tuple(reader.members.values())
    journal = reader.members[('journal', selection.role('journal'))]
    missing = evidence.CapturePool(tuple(m for m in members if m != journal), ())
    with pytest.raises(ValueError, match='one exact artifact version'):
        capture._Reader(selection, pool=missing).history(execution)
    # Another raw journal version has a different content/metadata-bound member
    # identity; a current journal read may not silently pick one by path.
    raw = journal.captured.raw + b' '
    other = evidence.PoolMember(c.CapturedArtifact(replace(journal.captured.pin, bytes=len(raw), sha256=c.sha(raw)), raw),
        c.canonical({**c.strict_json(journal.metadata_json), 'size': len(raw)}))
    ambiguous = evidence.CapturePool((*members, other), ())
    with pytest.raises(ValueError, match='one exact artifact version'):
        capture._Reader(selection, pool=ambiguous).history(execution)


def test_journal_pin_cannot_read_arbitrary_host_file(private_case, monkeypatch):
    selection, execution, _, history = private_case
    doc = c.strict_json(history.journal.raw)
    doc['records'][0]['path'] = '/unregistered/host-file.json'
    Path(selection.role('journal')).write_bytes(c.canonical(doc))
    original = evidence.read_regular
    seen = []
    def guarded(path, role, **kwargs):
        seen.append((path, role))
        assert path == selection.role('journal')
        return original(path, role, **kwargs)
    monkeypatch.setattr(evidence, 'read_regular', guarded)
    with pytest.raises(ValueError, match='ordered selected records'):
        capture._Reader(selection).history(execution)
    assert seen == [(selection.role('journal'), 'journal')]


def test_observation_has_flat_prefix_not_future_stream_contents(private_case):
    selection, execution, *_ = private_case
    raw = b'{"synthetic":"explicit prefix only"}\n'
    def prefix(role):
        return c.EvidencePrefix(role, '/synthetic/'+role, raw, len(raw), c.sha(raw), 1)
    payload = {'initialize_sent': {}, 'initialize_ack': {}, 'native_init': {},
               'stream_files': {role: {'device': 0, 'inode': 0} for role in ('transcript', 'control')}}
    result = capture.observation_bytes('initialized', selection, execution.execution.pin.sha256,
        execution.attempt_id, execution.session_id, prefix('transcript'), prefix('control'), payload)
    doc = c.strict_json(result)
    assert doc['transcript_prefix']['through_bytes'] == len(raw)
    assert doc['transcript_prefix']['sha256'] == c.sha(raw)
    assert set(doc['transcript_prefix']) == {'stream_id','stream','path','through_bytes','lines','sha256'}
    assert 'synthetic' not in str(doc['payload'])
