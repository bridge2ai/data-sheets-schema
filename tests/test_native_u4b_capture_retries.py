"""D115 capture reservation regressions, only scripted local Python peers.

The component fixture isolates protected registration reconstruction. Real
bundle/runtime validation, reservation, supervision and saved consumers execute.
No test claims native/account acceptance or consumes a generation reservation.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_subscription_guard_v2 as guard
from tests.test_native_subscription_capture import component, read_arguments


def retained(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


@pytest.mark.parametrize('mode', ['success', 'nonzero'])
def test_three_captures_share_one_word_and_fourth_never_spawns(tmp_path, monkeypatch, mode):
    arguments, value = component(tmp_path, monkeypatch, mode=mode)
    parent = arguments['directory']
    original = capture.subprocess.Popen
    calls = []

    def counted(argv, **kwargs):
        index = len(calls) + 1
        assert (parent / f'claim-{index}.json').is_file()
        assert (parent / f'capture-{index}' / 'claim.json').is_file()
        assert kwargs['env']['CLAUDE_CONFIG_DIR'] == str(parent / f'capture-{index}' / 'config')
        assert kwargs['cwd'] == str(parent / f'capture-{index}' / 'cwd')
        assert argv[0] == value['runtime']['executable']['path']
        assert argv[argv.index('--model') + 1] == value['runtime']['model']
        assert argv[argv.index('--effort') + 1] == value['runtime']['effort']
        assert kwargs['env']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] == '0'
        assert not Path(value['attempt_directory']).exists()
        assert not Path(value['evidence_directory']).exists()
        calls.append(kwargs)
        return original(argv, **kwargs)

    monkeypatch.setattr(capture.subprocess, 'Popen', counted)
    before = {}
    for index in range(1, 4):
        if mode == 'success':
            manifest = capture.capture_subscription(**arguments)
            assert manifest == parent / f'capture-{index}' / 'capture.json'
            result = capture.read_capture(manifest, **read_arguments(arguments))
        else:
            with pytest.raises(ValueError, match='process failed'):
                capture.capture_subscription(**arguments)
            result = json.loads((parent / f'capture-{index}' / 'capture.json').read_bytes())
            assert result['status'] == 'failed'
        assert result['capture_index'] == index
        assert result['lifecycle']['spawn_count'] == 1
        after = retained(parent)
        assert all(after[name] == raw for name, raw in before.items())
        before = after
    with pytest.raises(ValueError, match='allowance exhausted'):
        capture.capture_subscription(**arguments)
    assert len(calls) == 3
    assert retained(parent) == before
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()


def test_expired_capture_is_retained_while_same_word_recaptures(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    first = capture.capture_subscription(**arguments)
    saved = capture.read_capture(first, **read_arguments(arguments))
    event = saved['selected_event']
    terms = review.validate_bundle(**read_arguments(arguments))
    expired = guard._timestamp(event['captured_at'], 'capture') + terms['max_age_seconds'] + 1
    before = retained(first.parent)
    with pytest.raises(ValueError, match='stale or future-dated'):
        guard.prepare_guard(registration_raw=arguments['registration_raw'], runtime=value['runtime'],
            launch_word_raw=arguments['launch_word_raw'], owner_statement=terms,
            event_raw=event['event_json'].encode(), captured_at=event['captured_at'],
            maximum_starting_utilization=terms['max_starting_weekly_utilization'],
            max_age_seconds=terms['max_age_seconds'], clock=lambda: expired)
    second = capture.capture_subscription(**arguments)
    assert second.parent.name == 'capture-2'
    assert retained(first.parent) == before
    # Re-capture never changes which exact historical event the first guard names.
    assert capture.read_capture_for_event(arguments['directory'], **read_arguments(arguments),
        **{key: event[key] for key in ('event_json', 'event_sha256', 'captured_at')}) == saved
    assert not Path(value['attempt_directory']).exists()


def test_interrupted_claim_consumes_slot_without_inventing_completed_capture(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    original = capture._new

    def interruption(path, raw):
        original(path, raw)
        if path.name == 'claim-1.json':
            raise InterruptedError('synthetic interruption after durable reservation')

    monkeypatch.setattr(capture, '_new', interruption)
    with pytest.raises(InterruptedError):
        capture.capture_subscription(**arguments)
    root = arguments['directory']
    claim = (root / 'claim-1.json').read_bytes()
    assert not (root / 'capture-1').exists()
    monkeypatch.setattr(capture, '_new', original)
    second = capture.capture_subscription(**arguments)
    assert second.parent.name == 'capture-2'
    result = capture.read_capture(second, **read_arguments(arguments))
    assert result['previous_claim_sha256'] == capture.sha(claim)
    assert (root / 'claim-1.json').read_bytes() == claim


def test_concurrent_capture_refuses_without_allocating_another_slot(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    original = capture.subprocess.Popen

    def contested(argv, **kwargs):
        with pytest.raises(ValueError, match='another capture holds'):
            capture.capture_subscription(**arguments)
        assert not (arguments['directory'] / 'claim-2.json').exists()
        return original(argv, **kwargs)

    monkeypatch.setattr(capture.subprocess, 'Popen', contested)
    manifest = capture.capture_subscription(**arguments)
    assert capture.read_capture(manifest, **read_arguments(arguments))['capture_index'] == 1


@pytest.mark.parametrize('mutation', ['gap', 'reserve', 'unknown', 'slot_alias', 'claim', 'rebind_word'])
def test_changed_reservation_refuses_before_another_spawn(tmp_path, monkeypatch, mutation):
    arguments, _ = component(tmp_path, monkeypatch)
    first = capture.capture_subscription(**arguments)
    root = arguments['directory']
    if mutation == 'gap':
        (root / 'claim-1.json').rename(root / 'claim-2.json')
    elif mutation == 'reserve':
        body = json.loads((root / 'reserve.json').read_bytes())
        body['max_captures'] = 4
        (root / 'reserve.json').write_bytes(capture.canonical(body))
    elif mutation == 'unknown':
        (root / 'claim-4.json').write_bytes(b'{}')
    elif mutation == 'slot_alias':
        (root / 'capture-2').symlink_to(first.parent, target_is_directory=True)
    elif mutation == 'claim':
        body = json.loads((root / 'claim-1.json').read_bytes())
        body['capture_index'] = True
        (root / 'claim-1.json').write_bytes(capture.canonical(body))
    else:
        token = capture.strict_json(arguments['launch_word_raw'])
        token['ci_sha256'] = '3' * 64
        arguments['launch_word_raw'] = capture.canonical(token)
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('changed journal spawned'))
    with pytest.raises(ValueError):
        capture.capture_subscription(**arguments)


def test_unknown_guard_event_cannot_select_an_arbitrary_retained_capture(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    manifest = capture.capture_subscription(**arguments)
    saved = capture.read_capture(manifest, **read_arguments(arguments))
    event = deepcopy(saved['selected_event'])
    event['event_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='exactly one retained'):
        capture.read_capture_for_event(arguments['directory'], **read_arguments(arguments),
            **{key: event[key] for key in ('event_json', 'event_sha256', 'captured_at')})


def test_legacy_request_cannot_authorize_a_new_capture(tmp_path, monkeypatch):
    arguments, _ = component(tmp_path, monkeypatch)
    body, word = (capture.strict_json(arguments[key])
                  for key in ('review_bundle_raw', 'launch_word_raw'))
    body['owner_statement']['quota_capture'].update(
        kind=capture.LEGACY_REQUEST_KIND, version=1, count=1)
    arguments['review_bundle_raw'] = capture.canonical(body)
    word['review_sha256'] = capture.sha(arguments['review_bundle_raw'])
    arguments['launch_word_raw'] = capture.canonical(word)
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('historical request spawned'))
    with pytest.raises(ValueError, match='readback only'):
        capture.capture_subscription(**arguments)
    assert not arguments['directory'].exists()
