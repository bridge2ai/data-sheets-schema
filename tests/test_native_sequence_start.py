"""#5989 offline direction-replay regressions, 2026-11-12.
Only synthetic start records and fabricated command output; no actual capture.
"""
from pathlib import Path
import pytest
from data_sheets_schema import native_launch_sequence as seq
from data_sheets_schema import native_sequence_start as start
from data_sheets_schema import native_capture_words as words
from tests import test_native_launch_sequence as fixtures
from tests.test_native_launch_sequence import deny_real_commands


def test_different_packet_retry_needs_new_direction(tmp_path, monkeypatch):
    p=fixtures.paths(tmp_path)
    monkeypatch.setattr(seq,'_utc_now',lambda:'2026-11-12T12:00:00Z')
    flags=['--direction-recorded-at','2026-11-12T11:59:00Z',
           '--host-confirmed-at','2026-11-12T11:59:00Z']
    calls=fixtures.fake_commands(monkeypatch,p,fail=seq.COMMANDS[0])
    assert fixtures.run_sequence([*fixtures.argv(p),*flags])==1
    assert len(calls)==1
    old=Path(fixtures.record(p)['start_claim']); raw=old.read_bytes()
    first_manifest=fixtures.manifest(p)
    p['packet-directory']=tmp_path/'second-packet'
    p['subscription-guard']=tmp_path/'second-guard.json'
    calls=fixtures.fake_commands(monkeypatch,p)
    # Equivalent UTC spelling and a refreshed host confirmation do not renew it.
    flags[1]='2026-11-12T11:59:00.000000Z'; flags[3]='2026-11-12T12:00:00Z'
    assert fixtures.run_sequence([*fixtures.argv(p),*flags])==1
    assert calls==[] and old.read_bytes()==raw
    p['packet-directory']=tmp_path/'third-packet'
    flags[1]='2026-11-12T11:59:01Z'
    monkeypatch.setattr(fixtures,'manifest',lambda paths:first_manifest.parent.parent/'capture-2/capture.json')
    calls=fixtures.fake_commands(monkeypatch,p)
    assert fixtures.run_sequence([*fixtures.argv(p),*flags])==0
    assert len(calls)==3 and old.read_bytes()==raw
    assert Path(fixtures.record(p)['start_claim']) != old
    assert not (tmp_path/'NEVER-RESERVED-ATTEMPT').exists()


def test_owner_start_records_are_repeatable(tmp_path):
    p=fixtures.paths(tmp_path)
    args=dict(launch_word_raw=p['launch-word'].read_bytes(), direction=None,confirmation=None,
              packet=p['packet-directory'],started_at='2026-11-12T12:00:00Z')
    a=Path(start.claim(p['registration'].read_bytes(),**args))
    b=Path(start.claim(p['registration'].read_bytes(),**args))
    assert a!=b
    first, second = (words.strict_json(path.read_bytes()) for path in (a, b))
    assert first['direction_identity'] is second['direction_identity'] is None
    assert second['previous_sha256'] == words.sha(a.read_bytes())
    assert not p['output-directory'].exists()


def test_sequence_start_accepts_registration_above_quota_event_limit(tmp_path):
    p = fixtures.paths(tmp_path, registration_padding=65536)
    registration_raw = p['registration'].read_bytes()
    assert 65536 < len(registration_raw) <= 32 * 1024 * 1024
    # The shared parser must retain its smaller default for quota evidence.
    with pytest.raises(ValueError, match='not bounded JSON bytes'):
        words.strict_json(registration_raw)
    word = words.strict_json(p['launch-word'].read_bytes())
    review = words.strict_json(p['review'].read_bytes())
    assert word['registration_sha256'] == review['registration_sha256'] == words.sha(registration_raw)
    root = tmp_path / 'word-state'
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}

    event_path = Path(start.claim(registration_raw,
        launch_word_raw=p['launch-word'].read_bytes(), direction=None, confirmation=None,
        packet=p['packet-directory'], started_at='2026-11-12T12:00:00Z'))

    event = words.strict_json(event_path.read_bytes())
    assert event['type'] == 'sequence_start'
    assert event['registration_sha256'] == words.sha(registration_raw)
    assert event['previous_sha256'] == words.sha(before[Path('events/000001.json')])
    after = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}
    assert after.keys() - before.keys() == {event_path.relative_to(root)}
    assert all(after[name] == raw for name, raw in before.items())
    assert not p['output-directory'].exists()
    assert not (tmp_path / 'NEVER-RESERVED-ATTEMPT').exists()


def test_sequence_start_rejects_registration_above_input_limit_before_lock(tmp_path, monkeypatch):
    p = fixtures.paths(tmp_path)
    registration_raw = p['registration'].read_bytes()
    registration_raw += b' ' * (32 * 1024 * 1024 + 1 - len(registration_raw))
    root = tmp_path / 'word-state'
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}
    def forbidden_lock(*args, **kwargs):
        pytest.fail('oversized registration reached the journal lock')
    monkeypatch.setattr(words, 'locked', forbidden_lock)

    with pytest.raises(ValueError, match='not bounded JSON bytes'):
        start.claim(registration_raw,
            launch_word_raw=p['launch-word'].read_bytes(), direction=None, confirmation=None,
            packet=p['packet-directory'], started_at='2026-11-12T12:00:00Z')

    assert {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()} == before
    assert not p['output-directory'].exists()
    assert not (tmp_path / 'NEVER-RESERVED-ATTEMPT').exists()


def test_direction_claim_refuses_symlink_state(tmp_path):
    p=fixtures.paths(tmp_path); elsewhere=tmp_path/'elsewhere'; elsewhere.mkdir()
    (tmp_path/'word-state').rename(tmp_path/'retained-word-state')
    (tmp_path/'word-state').symlink_to(elsewhere,target_is_directory=True)
    with pytest.raises(ValueError,match='physical'):
        start.claim(p['registration'].read_bytes(), launch_word_raw=p['launch-word'].read_bytes(),
                    direction=None,confirmation=None,
                    packet=p['packet-directory'],started_at='2026-11-12T12:00:00Z')
    assert not list(elsewhere.iterdir())


def test_claim_latency_cannot_cross_delegated_start_limit(tmp_path,monkeypatch):
    p=fixtures.paths(tmp_path)
    moments=iter(['2026-11-12T12:00:00Z','2026-11-12T12:00:00Z',
                  '2026-11-12T12:00:01Z','2026-11-12T12:00:01Z'])
    monkeypatch.setattr(seq,'_utc_now',lambda:next(moments))
    assert fixtures.run_sequence([*fixtures.argv(p),
        '--direction-recorded-at','2026-11-12T11:30:00Z',
        '--host-confirmed-at','2026-11-12T11:30:00Z'])==1
    saved=fixtures.record(p)
    assert Path(saved['start_claim']).is_file() and saved['steps']==[]
    assert not p['output-directory'].exists()


@pytest.mark.parametrize('missing', ['journal', 'empty_journal', 'authority', 'word', 'unreadable'])
def test_missing_or_replaced_word_state_refuses_before_capture(tmp_path, monkeypatch, missing):
    p = fixtures.paths(tmp_path)
    root = tmp_path / 'word-state'
    if missing in ('journal', 'empty_journal'):
        root.rename(tmp_path / 'retained-state')
        if missing == 'empty_journal':
            root.mkdir()
    elif missing == 'authority':
        (root / 'authority.json').rename(root / 'retained-authority.json')
    elif missing == 'word':
        (root / 'events').rename(tmp_path / 'retained-events')
        (root / 'events').mkdir()
    else:
        monkeypatch.setattr(words, '_read', lambda path: (_ for _ in ()).throw(PermissionError('fixture unreadable journal')))
    calls = fixtures.fake_commands(monkeypatch, p)
    monkeypatch.setattr(seq, '_utc_now', lambda: '2026-11-12T12:00:00Z')
    assert fixtures.run_sequence([*fixtures.argv(p), '--direction-recorded-at', '2026-11-12T11:59:00Z',
                                  '--host-confirmed-at', '2026-11-12T11:59:00Z']) == 1
    assert calls == [] and not p['output-directory'].exists()
    assert not (tmp_path / '.native-sequence-starts').exists()


def test_start_event_is_synced_before_first_child(tmp_path, monkeypatch):
    import os
    import stat
    p = fixtures.paths(tmp_path)
    completed = []
    synced = []
    original_sync, original_new = os.fsync, words._new
    def sync(fd):
        synced.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file')
        return original_sync(fd)
    def new(path, raw):
        before = len(synced)
        original_new(path, raw)
        assert synced[before:] == ['file', 'directory']
        completed.append(path)
    monkeypatch.setattr(os, 'fsync', sync)
    monkeypatch.setattr(words, '_new', new)
    calls = fixtures.fake_commands(monkeypatch, p)
    fake = seq.subprocess.run
    def child(*args, **kwargs):
        assert len(completed) == 1
        assert words.strict_json(completed[0].read_bytes())['type'] == 'sequence_start'
        return fake(*args, **kwargs)
    monkeypatch.setattr(seq.subprocess, 'run', child)
    assert fixtures.run_sequence(fixtures.argv(p)) == 0
    assert len(calls) == 3


def test_historical_v1_journal_is_read_only(tmp_path):
    p = fixtures.paths(tmp_path)
    root = tmp_path / 'word-state'
    authority = words.strict_json((root / 'authority.json').read_bytes())
    authority.update(kind=words.PREVIOUS_KIND, version=1)
    (root / 'authority.json').write_bytes(words.canonical(authority))
    path = root / 'events/000001.json'
    row = words.strict_json(path.read_bytes())
    row.update(kind=words.PREVIOUS_KIND, version=1, header_sha256=words.sha(words.canonical(authority)))
    path.write_bytes(words.canonical(row))
    reg_raw = p['registration'].read_bytes()
    value = words.strict_json(reg_raw)['registration']
    with words.locked(value, reg_raw, historical=True) as journal:
        assert journal.require(p['launch-word'].read_bytes(), current=False) == row
        with pytest.raises(ValueError, match='historical journal'):
            journal.start(p['launch-word'].read_bytes(), direction=None, confirmation=None,
                          packet=p['packet-directory'], now=words._timestamp('2026-11-12T12:00:00Z', 'fixture'))
        with pytest.raises(ValueError, match='historical journal'):
            journal.activate(p['launch-word'].read_bytes(), p['review'].read_bytes(), value)
    with pytest.raises(ValueError, match='historical journal'):
        with words.locked(value, reg_raw):
            pytest.fail('current lock admitted historical journal')


@pytest.mark.parametrize('event_type', ['sequence_start', 'limits_refusal'])
def test_known_unanchored_tail_limit_is_shared_with_latch(tmp_path, event_type):
    """Document the approved strength: a retained chain does not anchor its tail."""
    p = fixtures.paths(tmp_path)
    reg_raw, word_raw = p['registration'].read_bytes(), p['launch-word'].read_bytes()
    value = words.strict_json(reg_raw)['registration']
    now = words._timestamp('2026-11-12T12:00:00Z', 'fixture')
    with words.locked(value, reg_raw) as journal:
        if event_type == 'sequence_start':
            row = journal.start(word_raw, direction='2026-11-12T11:59:00Z',
                confirmation='2026-11-12T11:59:00Z', packet=p['packet-directory'], now=now)
        else:
            terminal = words.canonical({'type': 'result', 'modelUsage': {'fixture-model':
                {'contextWindow': 101, 'maxOutputTokens': 10}}})
            row = journal.refuse_limits(word_raw, terminal,
                journal.root / 'captures' / words.sha(word_raw) / 'capture-1/capture.json', now)
        with pytest.raises(ValueError, match='already consumed|permanently refused'):
            journal.start(word_raw, direction='2026-11-12T11:59:00Z',
                confirmation='2026-11-12T11:59:00Z', packet=p['packet-directory'], now=now)
        # Only scratch evidence is removed, to expose rather than hide the limit.
        (journal.root / 'events' / f"{row['index']:06d}.json").unlink()
        assert journal.start(word_raw, direction='2026-11-12T11:59:00Z',
            confirmation='2026-11-12T11:59:00Z', packet=p['packet-directory'], now=now)


def test_word_renewal_after_start_preserves_registration_wide_direction_claim(tmp_path):
    p = fixtures.paths(tmp_path)
    reg_raw, word_raw = p['registration'].read_bytes(), p['launch-word'].read_bytes()
    value = words.strict_json(reg_raw)['registration']
    now = words._timestamp('2026-11-12T12:00:00Z', 'fixture')
    with words.locked(value, reg_raw) as journal:
        args = dict(direction='2026-11-12T11:59:00Z', confirmation='2026-11-12T11:59:00Z',
                    packet=p['packet-directory'], now=now)
        journal.start(word_raw, **args)
        newer = words.strict_json(word_raw)
        newer['authorized_at'] = '2026-11-12T11:59:30Z'
        new_raw = words.canonical(newer)
        journal.activate(new_raw, p['review'].read_bytes(), value, now)
        with pytest.raises(ValueError, match='already consumed'):
            journal.start(new_raw, **args)
