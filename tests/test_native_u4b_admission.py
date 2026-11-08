"""U4b capture/bundle/guard joins; registration reconstruction is isolated.

The fixed fake process, review parser, runtime reader, quota parser and saved
readback execute. No full registration or scientific acceptance is claimed.
"""
from copy import deepcopy
from pathlib import Path
import pytest
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_subscription_admission as admission
from data_sheets_schema import native_subscription_guard_v2 as guard
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_execution_orchestration as engine
from tests.test_native_subscription_capture import component, read_arguments


def prepared(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    path = capture.capture_subscription(**arguments)
    saved = capture.read_capture(path, **read_arguments(arguments))
    terms = review.validate_bundle(arguments['registration_raw'], arguments['review_bundle_raw'],
                                   arguments['launch_word_raw'])
    event = saved['selected_event']
    raw = guard.prepare_guard(registration_raw=arguments['registration_raw'], runtime=value['runtime'],
        launch_word_raw=arguments['launch_word_raw'], event_raw=event['event_json'].encode(),
        captured_at=event['captured_at'], owner_statement=terms,
        maximum_starting_utilization=terms['max_starting_weekly_utilization'],
        max_age_seconds=terms['max_age_seconds'])
    paths = {name: tmp_path / (name + '.json') for name in ('guard', 'word', 'review')}
    paths['guard'].write_bytes(raw)
    paths['word'].write_bytes(arguments['launch_word_raw'])
    paths['review'].write_bytes(arguments['review_bundle_raw'])
    return arguments, value, paths, raw


def test_actual_capture_owner_guard_join_and_saved_replay(tmp_path, monkeypatch):
    args, value, paths, raw = prepared(tmp_path, monkeypatch)
    instance = admission.load_current(paths['guard'], guard.sha(raw),
        registration_raw=args['registration_raw'], runtime=value['runtime'],
        launch_word_path=paths['word'], review_path=paths['review'])
    engine._join_subscription_authority(instance, args['registration_raw'], value,
        {'raw': {'launch_word': args['launch_word_raw'], 'review': args['review_bundle_raw']}}, current_launch=True)
    instance.before_dispatch()
    event = guard.strict_json(instance.value['event_json'])
    instance.observe(event)
    module, extra = admission.context(raw, registration_raw=args['registration_raw'],
        runtime=value['runtime'], launch_word_raw=args['launch_word_raw'],
        review_bundle_raw=args['review_bundle_raw'])
    replay = module.validate_saved_observations(raw, instance.snapshot(),
        registration_raw=args['registration_raw'], runtime=value['runtime'],
        launch_word_raw=args['launch_word_raw'], transcript_raw=guard.canonical(event) + b'\n',
        complete=True, **extra)
    assert replay['passed'] is True
    assert instance.snapshot()['observed_windows']['five_hour']['count'] == 1


@pytest.mark.parametrize('mutation', ['maximum', 'age', 'capture_event', 'capture_manifest', 'downgrade'])
def test_rehashed_guard_cannot_substitute_owner_or_capture(tmp_path, monkeypatch, mutation):
    args, value, paths, raw = prepared(tmp_path, monkeypatch)
    doc = guard.strict_json(raw)
    if mutation == 'maximum': doc['max_starting_weekly_utilization'] = 0.99
    elif mutation == 'age': doc['max_age_seconds'] = 300
    elif mutation == 'capture_event':
        event = guard.strict_json(doc['event_json'])
        event['rate_limit_info']['unifiedWindows']['seven_day']['utilization'] = 0.01
        doc['event_json'] = guard.canonical(event).decode(); doc['event_sha256'] = guard.sha(doc['event_json'].encode())
    elif mutation == 'capture_manifest':
        path = args['directory'] / 'capture.json'
        manifest = capture.strict_json(path.read_bytes()); manifest['lifecycle']['spawn_count'] = 0
        path.write_bytes(capture.canonical(manifest))
    else: doc['version'] = 1
    changed = guard.canonical(doc); paths['guard'].write_bytes(changed)
    with pytest.raises(ValueError):
        admission.load_current(paths['guard'], guard.sha(changed), registration_raw=args['registration_raw'],
            runtime=value['runtime'], launch_word_path=paths['word'], review_path=paths['review'])


def test_current_launch_refuses_historical_runtime_before_effects(monkeypatch):
    from data_sheets_schema import native_shared_execution_orchestration as execution
    monkeypatch.setattr(execution.registration, 'verified', lambda _: {'runtime': {'limits_basis': 'historical'}})
    with pytest.raises((ValueError, KeyError)):
        execution.launch(b'fixture', review_path='unused', ci_path='unused', launch_word_path='unused',
                         subscription_guard_path='unused', subscription_guard_sha256='0' * 64)


def test_frontdoor_registers_explicit_capture_and_offline_guard_commands():
    from data_sheets_schema.native_generation import parser
    capture_args = parser().parse_args(['capture-subscription-event', '--registration', 'e',
        '--review', 'r', '--launch-word', 'w', '--output-directory', 'c', '--account-choice', 'a'])
    assert capture_args.command == 'capture-subscription-event'
    guard_args = parser().parse_args(['prepare-subscription-guard-v2', '--registration', 'e',
        '--review', 'r', '--launch-word', 'w', '--capture', 'c', '--output', 'g', '--account-choice', 'a'])
    assert guard_args.command == 'prepare-subscription-guard-v2'


def test_historical_guard_readback_keeps_v1_dispatch():
    module, extra = admission.context(b'{"version":1}', registration_raw=b'old',
        runtime={'limits_basis': 'historical'}, launch_word_raw=b'old', review_bundle_raw=b'old')
    assert module.VERSION == 1 and extra == {}


def test_lower_engine_join_cannot_downgrade_to_legacy_admission():
    from types import SimpleNamespace
    with pytest.raises(ValueError):
        engine._join_subscription_authority(SimpleNamespace(raw=b'{"version":1}'), b'old',
            {'runtime': {'limits_basis': 'historical'}},
            {'raw': {'launch_word': b'old', 'review': b'old'}}, current_launch=True)
