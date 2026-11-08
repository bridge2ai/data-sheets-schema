"""A3 word renewal and every-capture limits, scripted Python peers only.

The shared component fixture isolates protected registration reconstruction;
real bundle, runtime, journal, subprocess, terminal and saved readers execute.
No native binary, account, provider or generation attempt is exercised.
"""
from datetime import datetime, timedelta
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema.native_u4b_policy import registered_policy, timestamp
from tests.test_native_subscription_capture import component, read_arguments, word_directory


def newer(arguments, seconds=1):
    result = dict(arguments)
    word = capture.strict_json(result['launch_word_raw'])
    moment = datetime.fromisoformat(word['authorized_at'].replace('Z', '+00:00')) + timedelta(seconds=seconds)
    word['authorized_at'] = moment.isoformat().replace('+00:00', 'Z')
    result['launch_word_raw'] = capture.canonical(word)
    return result


def journal_rows(arguments):
    return [json.loads(path.read_bytes()) for path in sorted((arguments['directory'] / 'events').glob('*.json'))]


def test_capture_saves_terminal_model_usage_and_rechecks_saved_bytes(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    path = capture.capture_subscription(**arguments)
    saved = capture.read_capture(path, **read_arguments(arguments), require_current=True)
    terminal = saved['terminal']
    assert terminal['modelUsage'] == {value['runtime']['model']: value['runtime']['limits']}
    assert terminal['limits_match'] is True
    assert terminal['observed_limits'] == terminal['registered_limits'] == value['runtime']['limits']
    line = (path.parent / 'stdout.jsonl').read_bytes().splitlines()[terminal['line'] - 1]
    assert terminal['terminal_json'].encode() == line
    assert terminal['terminal_sha256'] == capture.sha(line)
    assert terminal['result'] == json.loads(line)
    saved['terminal']['observed_limits']['contextWindow'] = 200000
    path.write_bytes(capture.canonical(saved))
    with pytest.raises(ValueError, match='terminal limits'):
        capture.read_capture(path, **read_arguments(arguments))


@pytest.mark.parametrize('mode,index', [('mismatch', 1), ('second_mismatch', 2)])
def test_any_limits_mismatch_permanently_refuses_registration_across_words(tmp_path, monkeypatch, mode, index):
    arguments, value = component(tmp_path, monkeypatch, mode=mode)
    first = capture.capture_subscription(**arguments) if index == 2 else None
    with pytest.raises(ValueError, match='registration permanently refused'):
        capture.capture_subscription(**arguments)
    failed = word_directory(arguments) / f'capture-{index}' / 'capture.json'
    saved = json.loads(failed.read_bytes())
    assert saved['status'] == 'failed' and saved['terminal']['limits_match'] is False
    assert saved['terminal']['observed_limits']['contextWindow'] == 200000
    rows = journal_rows(arguments)
    refusal = rows[-1]
    assert refusal['type'] == 'limits_refusal'
    assert refusal['capture_path'] == str(failed)
    assert refusal['word_sha256'] == capture.sha(arguments['launch_word_raw'])
    assert refusal['terminal_sha256'] == saved['terminal']['terminal_sha256']
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('poisoned registration spawned'))
    for selected in (arguments, newer(arguments)):
        with pytest.raises(ValueError, match='permanently refused'):
            capture.activate_capture_word(**read_arguments(selected))
        with pytest.raises(ValueError, match='permanently refused'):
            capture.capture_subscription(**selected)
    assert journal_rows(arguments) == rows
    if first is not None:
        assert capture.read_capture(first, **read_arguments(arguments))['status'] == 'captured'
        with pytest.raises(ValueError, match='permanently refused'):
            capture.read_capture(first, **read_arguments(arguments), require_current=True)


def test_failed_process_still_records_observed_limits_mismatch(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch, mode='mismatch_nonzero')
    with pytest.raises(ValueError, match='process failed'):
        capture.capture_subscription(**arguments)
    result = json.loads((word_directory(arguments) / 'capture-1' / 'capture.json').read_bytes())
    assert result['lifecycle']['returncode'] == 7
    assert result['terminal']['limits_match'] is False
    assert journal_rows(arguments)[-1]['type'] == 'limits_refusal'
    with pytest.raises(ValueError, match='permanently refused'):
        capture.activate_capture_word(**read_arguments(newer(arguments)))


@pytest.mark.parametrize('prefix', [b'{broken\n', b'{"type":"result"}\n'])
def test_failed_stream_cannot_hide_retained_terminal_limits_mismatch(tmp_path, monkeypatch, prefix):
    """Isolate deterministic supervisor delivery; authority and journal are real.

    The real supervisor retains an entire bounded read before parsing its first
    line, so later result bytes can survive a failure on an earlier line.
    """
    arguments, value = component(tmp_path, monkeypatch)
    terminal = capture.canonical({'type': 'result', 'subtype': 'success', 'is_error': False,
        'modelUsage': {value['runtime']['model']: {'contextWindow': 200000, 'maxOutputTokens': 64000}}})
    retained = prefix + terminal + b'\n'

    def failed_delivery(invocation, deadline, outputs, observations, lifecycle):
        outputs['stdout'].extend(retained)
        raise ValueError('isolated malformed or ambiguous stream delivery')

    monkeypatch.setattr(capture, '_supervise', failed_delivery)
    with pytest.raises(ValueError, match='isolated malformed or ambiguous'):
        capture.capture_subscription(**arguments)
    path = word_directory(arguments) / 'capture-1' / 'capture.json'
    saved = json.loads(path.read_bytes())
    assert saved['status'] == 'failed'
    assert saved['error']['message'] == 'isolated malformed or ambiguous stream delivery'
    assert saved['terminal']['terminal_json'].encode() == terminal
    assert saved['terminal']['line'] == 2 and saved['terminal']['limits_match'] is False
    assert (path.parent / 'stdout.jsonl').read_bytes() == retained
    refusal = journal_rows(arguments)[-1]
    assert refusal['type'] == 'limits_refusal'
    assert refusal['terminal_sha256'] == capture.sha(terminal)
    assert refusal['capture_path'] == str(path)
    with pytest.raises(ValueError):
        capture.read_capture(path, **read_arguments(arguments))
    for selected in (arguments, newer(arguments)):
        with pytest.raises(ValueError, match='permanently refused'):
            capture.activate_capture_word(**read_arguments(selected))
    assert not Path(value['attempt_directory']).exists()


def test_refusal_scan_does_not_admit_malformed_stream_with_matching_limits(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    terminal = capture.canonical({'type': 'result', 'subtype': 'success', 'is_error': False,
        'modelUsage': {value['runtime']['model']: value['runtime']['limits']}})

    def failed_delivery(invocation, deadline, outputs, observations, lifecycle):
        outputs['stdout'].extend(b'{broken\n' + terminal + b'\n')
        raise ValueError('isolated malformed stream delivery')

    monkeypatch.setattr(capture, '_supervise', failed_delivery)
    with pytest.raises(ValueError, match='isolated malformed stream'):
        capture.capture_subscription(**arguments)
    path = word_directory(arguments) / 'capture-1' / 'capture.json'
    saved = json.loads(path.read_bytes())
    assert saved['status'] == 'failed' and saved['terminal'] is None
    assert saved['terminal_error'] and len(journal_rows(arguments)) == 1
    with pytest.raises(ValueError):
        capture.read_capture(path, **read_arguments(arguments))


def test_new_word_restores_three_capture_slots_without_consuming_attempt(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch, mode='nonzero')
    for _ in range(3):
        with pytest.raises(ValueError, match='process failed'):
            capture.capture_subscription(**arguments)
    old = {path.name: path.read_bytes() for path in word_directory(arguments).glob('claim-*.json')}
    with pytest.raises(ValueError, match='allowance exhausted'):
        capture.capture_subscription(**arguments)
    renewed = newer(arguments)
    activated = capture.activate_capture_word(**read_arguments(renewed))
    assert activated['word_sha256'] == capture.sha(renewed['launch_word_raw'])
    for index in range(1, 4):
        with pytest.raises(ValueError, match='process failed'):
            capture.capture_subscription(**renewed)
        assert (word_directory(renewed) / f'claim-{index}.json').is_file()
    with pytest.raises(ValueError, match='allowance exhausted'):
        capture.capture_subscription(**renewed)
    assert {path.name: path.read_bytes() for path in word_directory(arguments).glob('claim-*.json')} == old
    assert len(journal_rows(arguments)) == 2
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()


def test_word_supersession_blocks_old_current_admission_but_preserves_history(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    first = capture.capture_subscription(**arguments)
    before = first.read_bytes()
    renewed = newer(arguments)
    capture.activate_capture_word(**read_arguments(renewed))
    with pytest.raises(ValueError, match='superseded'):
        capture.require_current_capture_authority(**read_arguments(arguments))
    with pytest.raises(ValueError, match='superseded'):
        capture.read_capture(first, **read_arguments(arguments), require_current=True)
    with pytest.raises(ValueError, match='superseded'):
        capture.capture_subscription(**arguments)
    assert capture.read_capture(first, **read_arguments(arguments))['status'] == 'captured'
    assert first.read_bytes() == before
    second = capture.capture_subscription(**renewed)
    assert second.parent.name == 'capture-1'
    saved = capture.read_capture(second, **read_arguments(renewed), require_current=True)
    assert saved['launch_word_sha256'] != json.loads(before)['launch_word_sha256']
    with pytest.raises(ValueError):
        capture.read_capture(first, **read_arguments(renewed))


@pytest.mark.parametrize('location', ['before', 'at_expiry', 'after_expiry'])
def test_activation_requires_explicit_registration_validity_before_state_creation(tmp_path, monkeypatch, location):
    arguments, value = component(tmp_path, monkeypatch)
    policy = registered_policy(value['runtime'])
    now = (timestamp(policy['valid_from'], 'from') - 1 if location == 'before'
           else timestamp(policy['valid_until'], 'until') + (location == 'after_expiry'))
    with pytest.raises(ValueError, match='outside registration validity'):
        capture.activate_capture_word(**read_arguments(arguments), now=now)
    assert not arguments['directory'].exists()
    assert not Path(value['attempt_directory']).exists()


def test_generation_reservation_prevents_renewal_and_capture(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    capture.activate_capture_word(**read_arguments(arguments))
    Path(value['attempt_directory']).mkdir()
    # Reading the already active word remains valid after reservation.
    capture.require_current_capture_authority(**read_arguments(arguments))
    with pytest.raises(ValueError, match='spent generation reservation'):
        capture.activate_capture_word(**read_arguments(newer(arguments)))
    with pytest.raises(ValueError, match='spent generation reservation'):
        capture.capture_subscription(**arguments)


def test_admission_lease_excludes_word_renewal_during_reservation(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    capture.activate_capture_word(**read_arguments(arguments))
    with capture.capture_admission_lease(**read_arguments(arguments)):
        with pytest.raises(ValueError, match='already in use'):
            capture.activate_capture_word(**read_arguments(newer(arguments)))
    assert len(journal_rows(arguments)) == 1


def test_missing_terminal_is_retained_failure_not_fabricated_limits_mismatch(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch, mode='missing_terminal')
    with pytest.raises(ValueError, match='final terminal'):
        capture.capture_subscription(**arguments)
    saved = json.loads((word_directory(arguments) / 'capture-1' / 'capture.json').read_bytes())
    assert saved['status'] == 'failed' and saved['terminal'] is None
    assert saved['terminal_error'] and len(journal_rows(arguments)) == 1
    capture.activate_capture_word(**read_arguments(newer(arguments)))
    assert len(journal_rows(arguments)) == 2
