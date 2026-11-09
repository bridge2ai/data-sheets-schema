"""Addendum 1 R1/R2(b)/R4 regressions, 2026-11-08; offline evidence only.

Approval records and quota observations are invented. The actual v2 review
reader, local Git/workflow checks, bundle validator and saved guard replay run.
Capture tests isolate only full registration reconstruction and execute the
existing scripted Python peer; no native generation executable is launched.
This does not establish real CI, reviewers, account state or full registration.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from data_sheets_schema import native_execution_orchestration as engine
from data_sheets_schema import native_execution_registration_v2 as reader
from data_sheets_schema import native_launch_review as review
from data_sheets_schema import native_shared_execution_orchestration as execution
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_subscription_guard_v2 as guard
from data_sheets_schema import native_u4b_runtime as runtime_evidence
from tests.test_native_execution_registration_v2 import fabricated_authorizations
from tests.test_native_subscription_capture import component, read_arguments
from tests.test_native_subscription_guard_v2 import case as guard_case, build
from tests.test_native_u4b_runtime import runtime_inputs
from tests.utils.native_u4b_fixtures import bundle_for


@pytest.fixture
def bundle_reader_case(tmp_path, fabricated_authorizations):
    """Use the genuine v2 parser, with fabricated CI tied to real local bytes."""
    _, value, original, paths = fabricated_authorizations
    runtime, arguments = runtime_inputs(tmp_path)
    arguments['admission_policy']['capture_state_directory'] = str(tmp_path / 'not-yet-captured')
    value['runtime'] = runtime_evidence.prepare_runtime(runtime, **arguments)
    raw = guard.canonical({'authority_version': 2, 'controller_sources_sha256': 'f' * 64,
                           'registration': value})
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    bundle_raw, word_raw = bundle_for(raw, tmp_path / 'not-yet-captured', now=now)
    bundle, word = guard.strict_json(bundle_raw), guard.strict_json(word_raw)
    ci = deepcopy(original['ci'])
    ci['registration_sha256'] = guard.sha(raw)
    word['ci_sha256'] = guard.sha(guard.canonical(ci))
    records = {'review': bundle, 'ci': ci, 'launch_word': word}

    def persist():
        for name, record in records.items():
            paths[name].write_bytes(guard.canonical(record))

    persist()
    return raw, value, records, paths, persist


def read_bundle(case):
    raw, value, _, paths, _ = case
    return reader._authorizations(raw, value,
        **{name + '_path': path for name, path in paths.items()})


def test_real_v2_reader_consumes_two_review_bundle_and_replays_exact_bytes(bundle_reader_case):
    _, _, records, paths, _ = bundle_reader_case
    before = {name: path.read_bytes() for name, path in paths.items()}
    assert len(records['review']['reviews']) == 2
    first, repeated = read_bundle(bundle_reader_case), read_bundle(bundle_reader_case)
    assert {name: member.raw for name, member in first.items()} == before
    assert {name: member.raw for name, member in repeated.items()} == before
    assert {name: path.read_bytes() for name, path in paths.items()} == before


@pytest.mark.parametrize('mutation,diagnostic', [
    ('late_bundle', 'coded word differs'),
    ('late_review', 'precedes an independent review'),
    ('operator_review', 'reviewers must differ'),
    ('one_review', 'exactly two independent reviews'),
    ('source', 'review must bind this exact'),
    ('attempt', 'review must bind this exact'),
    ('context', 'context mode differs'),
])
def test_real_v2_reader_refuses_rehashed_bad_review_or_post_word_edit(
        bundle_reader_case, mutation, diagnostic):
    _, _, records, paths, persist = bundle_reader_case
    bundle, word = records['review'], records['launch_word']
    if mutation == 'late_bundle':
        bundle['reviews'][0]['document']['sha256'] = '0' * 64
    elif mutation == 'late_review':
        later = datetime.fromisoformat(word['authorized_at'].replace('Z', '+00:00')) + timedelta(seconds=1)
        bundle['reviews'][0]['reviewed_at'] = later.isoformat().replace('+00:00', 'Z')
    elif mutation == 'operator_review':
        bundle['reviews'][0]['reviewer'] = bundle['operator']
    elif mutation == 'one_review':
        bundle['reviews'].pop()
    elif mutation == 'source':
        bundle['source_commit'] = '0' * 40
    elif mutation == 'attempt':
        bundle['attempt_id'] += '-different'
    else:
        bundle['owner_statement']['context_mode'] = '200k'
    if mutation != 'late_bundle':
        word['review_sha256'] = guard.sha(guard.canonical(bundle))
    persist()
    before = {name: path.read_bytes() for name, path in paths.items()}
    with pytest.raises(ValueError, match=diagnostic):
        read_bundle(bundle_reader_case)
    assert {name: path.read_bytes() for name, path in paths.items()} == before


def test_expired_capture_stays_spent_and_refuses_before_generation_reservation(tmp_path, monkeypatch):
    arguments, value = component(tmp_path, monkeypatch)
    manifest = capture.capture_subscription(**arguments)
    saved = capture.read_capture(manifest, **read_arguments(arguments))
    terms = review.validate_bundle(arguments['registration_raw'], arguments['review_bundle_raw'],
                                   arguments['launch_word_raw'])
    event = saved['selected_event']
    raw = guard.prepare_guard(registration_raw=arguments['registration_raw'], runtime=value['runtime'],
        launch_word_raw=arguments['launch_word_raw'], owner_statement=terms,
        event_raw=event['event_json'].encode(), captured_at=event['captured_at'],
        maximum_starting_utilization=terms['max_starting_weekly_utilization'],
        max_age_seconds=terms['max_age_seconds'])
    paths = {name: tmp_path / (name + '-input.json') for name in ('guard', 'review', 'word')}
    paths['guard'].write_bytes(raw)
    paths['review'].write_bytes(arguments['review_bundle_raw'])
    paths['word'].write_bytes(arguments['launch_word_raw'])
    before = {path.name: path.read_bytes() for path in manifest.parent.iterdir() if path.is_file()}
    expired = guard._timestamp(event['captured_at'], 'capture') + terms['max_age_seconds'] + 1
    monkeypatch.setattr(guard, '_now', lambda: expired)

    def forbidden(*args, **kwargs):
        pytest.fail('expired capture reached generation engine or a second process')

    monkeypatch.setattr(engine, 'launch', forbidden)
    monkeypatch.setattr(capture.subprocess, 'Popen', forbidden)
    with pytest.raises(ValueError, match='stale or future-dated'):
        execution.launch(arguments['registration_raw'], review_path=paths['review'],
            ci_path=tmp_path / 'must-not-be-opened-ci.json', launch_word_path=paths['word'],
            subscription_guard_path=paths['guard'], subscription_guard_sha256=guard.sha(raw))
    assert not Path(value['attempt_directory']).exists()
    assert not Path(value['evidence_directory']).exists()
    assert capture.read_capture(manifest, **read_arguments(arguments)) == saved
    # D115 now permits two further separately reserved captures. This check
    # proves the old expired slot remains unchanged, not that the root is spent.
    after = {path.name: path.read_bytes() for path in manifest.parent.iterdir() if path.is_file()}
    assert after == before


@pytest.mark.parametrize('mutation', ['statement', 'runtime', 'both'])
def test_saved_guard_readback_rechecks_context_even_after_hashes_are_rebound(guard_case, mutation):
    case = guard_case
    instance = build(case)
    instance.before_dispatch()
    runtime, bundle = deepcopy(case['runtime']), guard.strict_json(case['bundle'])
    if mutation in ('runtime', 'both'):
        runtime['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] = '1'
    if mutation in ('statement', 'both'):
        bundle['owner_statement']['context_mode'] = '200k'
    word = guard.strict_json(case['word'])
    word['review_sha256'] = guard.sha(guard.canonical(bundle))
    word_raw = guard.canonical(word)
    document = {**case['document'], 'runtime_sha256': guard.sha(guard.canonical(runtime)),
        'launch_word_sha256': guard.sha(word_raw),
        'owner_statement_sha256': guard.sha(guard.canonical(bundle['owner_statement']))}
    # Changing the runtime now fails its exact registration-byte join before
    # the owner/context check; changing only the statement still reaches it.
    reason = 'context mode differs' if mutation == 'statement' else 'registered runtime bytes'
    with pytest.raises(ValueError, match=reason):
        guard.validate_saved_observations(guard.canonical(document), instance.snapshot(),
            registration_raw=case['registration'], runtime=runtime, launch_word_raw=word_raw,
            owner_statement=bundle['owner_statement'], transcript_raw=b'{"type":"system"}\n', complete=True)


@pytest.mark.parametrize('mutation,diagnostic', [
    ('missing', 'no five_hour window'),
    ('nested_unsafe', 'five_hour subscription window is rejected'),
    ('unknown', 'unrecognized.*exhausted'),
])
def test_admission_requires_five_hour_and_checks_every_present_window(guard_case, mutation, diagnostic):
    case = guard_case
    event = deepcopy(case['event'])
    windows = event['rate_limit_info']['unifiedWindows']
    if mutation == 'missing':
        del windows['five_hour']
    elif mutation == 'nested_unsafe':
        windows['five_hour']['status'] = 'rejected'
    else:
        windows['unrecognized'] = deepcopy(windows['five_hour'])
        windows['unrecognized']['utilization'] = 1
    event_raw = guard.canonical(event)
    document = {**case['document'], 'event_json': event_raw.decode(), 'event_sha256': guard.sha(event_raw)}
    with pytest.raises(ValueError, match=diagnostic):
        build(case, document=document)
    if mutation != 'missing':
        # Successful saved replay cannot suppress an unsafe buffered event
        # simply by supplying an unchanged, otherwise valid success snapshot.
        watched = build(case)
        watched.before_dispatch()
        with pytest.raises(ValueError, match=diagnostic):
            guard.validate_saved_observations(watched.raw, watched.snapshot(),
                registration_raw=case['registration'], runtime=case['runtime'],
                launch_word_raw=case['word'], owner_statement=case['owner'],
                transcript_raw=event_raw + b'\n', complete=True)
