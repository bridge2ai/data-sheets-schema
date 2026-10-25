"""Actual initial capture and portable saved anchors; no runtime launch."""
from dataclasses import replace
from pathlib import Path
import os

import pytest

from tests.test_native_shared_results import initial
from tests.test_native_shared_live_capture import started, native_init
from tests.test_native_shared_registration import execution, bound, native_spec, declaration
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_streams as streams
from data_sheets_schema import native_shared_results as results


def test_real_init_anchor_live_recapture_and_saved_replay_are_separate(started, monkeypatch, tmp_path):
    live, pool = initial(started)
    init = c.strict_json(live.binding.init_observation.raw)
    stream_members = tuple(pool.member(member) for _, member in pool.stream_bindings)
    assert init['payload']['stream_files'] == streams.stream_files(stream_members)
    fresh = capture._load_live(live.selection.registration.pin.path)
    assert fresh.binding == live.binding and fresh.history == live.history
    assert fresh._catalogs is not live._catalogs
    rebuilt = results.rebuild(pool, live.value)
    assert rebuilt.binding == live.binding

    def forbidden(*a, **k): pytest.fail('portable saved replay accessed host files or live streams')
    with monkeypatch.context() as m:
        for name in ('read_bytes', 'resolve', 'stat', 'lstat'): m.setattr(Path, name, forbidden)
        m.setattr(evidence, 'read_regular', forbidden)
        m.setattr(streams, 'read_live_stream', forbidden)
        m.setattr(os, 'fstat', forbidden)
        assert results.rebuild(pool, live.value).binding == live.binding

        # This deliberately changes captured metadata, not host metadata. The
        # container is readdressed so the failure reaches the initialized join.
        selected = stream_members[0]
        meta = c.strict_json(selected.metadata_json); meta['inode'] += 1
        changed = replace(selected, metadata_json=c.canonical(meta))
        other = evidence.CapturePool(tuple(changed if item == selected else item for item in pool.members),
            tuple((stream, changed.member_id if member == selected.member_id else member)
                  for stream, member in pool.stream_bindings))
        with pytest.raises(ValueError, match='physical identities'): results.rebuild(other, live.value)

    # A helper process would reopen this path: identical bytes on another inode
    # must fail against the durable initialization anchor, not only RAM state.
    path = Path(live.value['attempt_directory']) / 'transcript.jsonl'
    raw = path.read_bytes(); retained = tmp_path / 'retained-original-transcript'
    path.rename(retained); path.write_bytes(raw)
    with pytest.raises(ValueError, match='file identity'): capture._load_live(live.selection.registration.pin.path)
    with pytest.raises(ValueError, match='physical identities'): capture._load(live.selection.registration.pin.path)
    assert retained.read_bytes() == path.read_bytes() == raw


def test_parent_prefix_drift_refuses_initialization_before_observation_publication(started):
    selection, value, composition, *_ = started
    transcript, control = native_init(selection, value, composition)
    members, prefixes = capture._streams(value)
    anchors = streams.stream_files(members)
    expected = dict(zip(streams.ROLES, prefixes))
    path = Path(value['attempt_directory']) / 'transcript.jsonl'
    # Same-length, still-valid JSON differs from the parent's exact observation.
    path.write_bytes(transcript.replace(b'"subtype":"init"', b'"subtype":"nope"'))
    with pytest.raises(ValueError, match='parent-observed'):
        capture.initialize(selection.registration.pin.path, transcript_bytes=len(transcript),
            control_bytes=len(control), stream_files=anchors, observed_prefixes=expected)
    assert not Path(selection.role('session_binding')).exists()
    assert not tuple(Path(selection.role('observations_root')).glob('*.json'))


@pytest.mark.parametrize('bad', [{}, {'transcript': {'device': 1, 'inode': 2}},
    {'transcript': {'device': True, 'inode': 2}, 'control': {'device': 1, 'inode': 2}},
    {'transcript': {'device': 1, 'inode': 2, 'size': 0}, 'control': {'device': 1, 'inode': 2}}])
def test_anchor_shape_has_no_legacy_or_boolean_fallback(bad):
    with pytest.raises(ValueError): streams.identities(bad)


def test_final_results_capture_calls_strict_load_first(started, monkeypatch):
    selection, value, composition, raw, _ = started
    class StrictWitness(Exception): pass
    def strict(path):
        assert path == selection.registration.pin.path
        raise StrictWitness
    monkeypatch.setattr(capture, '_load', strict)
    monkeypatch.setattr(capture, '_load_live', lambda *a, **k: pytest.fail('final capture used live route'))
    with pytest.raises(StrictWitness):
        results.capture(value, {}, authority_inputs={}, registration_raw=raw)
