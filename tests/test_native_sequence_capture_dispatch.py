"""Issues 6048/5992: synthetic journal and capture-boundary checks, no binary."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest

from data_sheets_schema import native_capture_words as words
from data_sheets_schema import native_sequence_start as start
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema.native_u4b_policy import registered_policy
from tests.test_native_subscription_capture import component


def claimed(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    capture.activate_capture_word(**{k: v for k, v in arguments.items() if k != 'directory'})
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    path = Path(start.claim(arguments['registration_raw'], launch_word_raw=arguments['launch_word_raw'],
        direction=now, confirmation=now, packet=tmp_path / 'packet', started_at=now))
    return arguments, value, {'path': str(path), 'sha256': words.sha(path.read_bytes())}


def no_capture(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('refused sequence reached a capture reservation or execution')
    monkeypatch.setattr(capture, '_reserve', forbidden)
    monkeypatch.setattr(capture, '_perform_capture', forbidden)


@pytest.mark.parametrize('replacement', ['missing', 'empty'])
def test_state_moved_after_durable_claim_before_child_lock_refuses(tmp_path, monkeypatch, replacement):
    arguments, value, pin = claimed(tmp_path, monkeypatch)
    root = Path(registered_policy(value['runtime'])['capture_state_directory'])
    retained = tmp_path / 'retained-state'
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    locked = words.locked
    entered = []
    @contextmanager
    def move_before_lock(*args, **kwargs):
        entered.append(kwargs)
        assert kwargs.get('create') is False
        root.rename(retained)
        if replacement == 'empty':
            root.mkdir()
        with locked(*args, **kwargs) as journal:
            yield journal
    monkeypatch.setattr(words, 'locked', move_before_lock)
    no_capture(monkeypatch)
    with pytest.raises(ValueError, match='no recorded word state|incomplete'):
        capture.capture_subscription(**arguments, sequence_start=pin)
    assert entered == [{'create': False}]
    assert (not root.exists()) if replacement == 'missing' else not list(root.iterdir())
    assert before == {p.relative_to(retained): p.read_bytes() for p in retained.rglob('*') if p.is_file()}
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()


@pytest.mark.parametrize('change', ['digest', 'path', 'tail_removed', 'later_start'])
def test_sequence_requires_exact_current_start(tmp_path, monkeypatch, change):
    arguments, value, pin = claimed(tmp_path, monkeypatch)
    if change == 'digest':
        pin['sha256'] = '0' * 64
    elif change == 'path':
        pin['path'] = str(tmp_path / 'unrelated-start.json')
    elif change == 'tail_removed':
        Path(pin['path']).rename(tmp_path / 'retained-start.json')
    else:
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        start.claim(arguments['registration_raw'], launch_word_raw=arguments['launch_word_raw'],
            direction=None, confirmation=None, packet=tmp_path / 'other-packet', started_at=now)
    no_capture(monkeypatch)
    with pytest.raises(ValueError, match='matching current start'):
        capture.capture_subscription(**arguments, sequence_start=pin)


def test_valid_dispatch_checks_start_under_lock_before_synthetic_capture(tmp_path, monkeypatch):
    arguments, value, pin = claimed(tmp_path, monkeypatch)
    before = Path(pin['path']).read_bytes()
    seen = []
    def perform(slot, claim, bound, authority, directory, reg, review, word, journal):
        assert journal.require_start(word, pin)['type'] == 'sequence_start'
        with pytest.raises(ValueError, match='already in use'):
            with words.locked(value, reg):
                pytest.fail('capture did not retain the journal lock')
        seen.append(slot)
        return slot / 'synthetic-only.json'
    monkeypatch.setattr(capture, '_perform_capture', perform)
    result = capture.capture_subscription(**arguments, sequence_start=pin)
    assert len(seen) == 1 and result.parent == seen[0]
    assert Path(pin['path']).read_bytes() == before


def test_standalone_capture_still_records_word_and_reserves_slot(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    root = Path(registered_policy(value['runtime'])['capture_state_directory'])
    assert not root.exists()
    seen = []
    def perform(slot, claim, bound, authority, directory, reg, review, word, journal):
        assert [event['type'] for event in journal.events()] == ['word']
        seen.append(slot)
        return slot / 'synthetic-only.json'
    monkeypatch.setattr(capture, '_perform_capture', perform)
    result = capture.capture_subscription(**arguments)
    assert len(seen) == 1 and result.parent == seen[0]
    assert (root / 'authority.json').is_file()
