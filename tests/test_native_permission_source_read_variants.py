"""PR 6302 source prerequisite selection; no native process or provider runs.

Invented case rows exercise the diagnostic selector and saved Read replay only.
These are software tests, not native permission observations. 2026-11-21.
"""
from copy import deepcopy

import pytest

from data_sheets_schema import native_shared_permissions as consumer
from data_sheets_schema import native_shared_permission_orchestration as permission_orchestration
from tests.test_native_shared_permissions import (
    encoded,
    fabricated_native_refusal,
    fixture,
    prohibit_real_transports,
    put_rows,
    rows,
)
from tests.utils.native_shared_consumer_scope import loaded_consumer


SOURCE = '/synthetic/source.txt'


def cases_with_source_read(**read_fields):
    return [
        {'id': 'source_read', 'tool': 'Read',
         'input': {'file_path': SOURCE, **read_fields},
         'context': 'baseline', 'mode': 'allowed'},
        {'id': 'response_worker_write', 'tool': 'Write',
         'input': {'file_path': '/synthetic/response.bin', 'content': 'response'},
         'context': 'worker', 'mode': 'allowed'},
        {'id': 'arbitrary_python', 'tool': 'Bash',
         'input': {'command': 'unregistered'},
         'context': 'baseline', 'mode': 'native_denied'},
        {'id': 'source_write', 'tool': 'Write',
         'input': {'file_path': SOURCE, 'content': 'D4D_SOURCE_MUST_NOT_CHANGE\n'},
         'context': 'baseline', 'mode': 'observer_stopped'},
        {'id': 'future_response_write', 'tool': 'Write',
         'input': {'file_path': '/synthetic/future.bin', 'content': 'D4D_FORBIDDEN\n'},
         'context': 'worker', 'mode': 'observer_stopped'},
    ]


def test_source_read_ships_whole_and_has_exact_variant_shapes():
    assert consumer.SOURCE_WRITE_READ_VARIANT == 'whole'
    original = cases_with_source_read()
    variants = {
        'whole': {'file_path': SOURCE},
        'bounded': {'file_path': SOURCE, 'offset': 1, 'limit': 12},
        'allow_large': {'file_path': SOURCE, 'allow_large': True},
    }
    for variant, wanted in variants.items():
        selected = consumer.trace_cases(
            original, 'stop-source_write', source_write_read_variant=variant)
        assert [case['id'] for case in selected] == ['source_read', 'source_write']
        assert selected[0]['input'] == wanted
        assert selected[1] == original[3]
    assert consumer.trace_cases(original, 'stop-source_write')[0]['input'] == variants['whole']


def test_source_read_variant_never_mutates_original_cases():
    for variant in ('whole', 'bounded', 'allow_large'):
        original = cases_with_source_read()
        before = deepcopy(original)
        selected = consumer.trace_cases(
            original, 'stop-source_write', source_write_read_variant=variant)
        assert original == before
        assert selected[0] is not original[0]
        assert selected[0]['input'] is not original[0]['input']
        selected[0]['input']['file_path'] = '/synthetic/changed.txt'
        assert original == before


def test_source_read_variant_preserves_settled_and_other_stop_cases():
    original = cases_with_source_read(offset=1, limit=7)
    before = deepcopy(original)
    for variant in ('whole', 'bounded', 'allow_large'):
        settled = consumer.trace_cases(original, 'settled', source_write_read_variant=variant)
        assert settled == original[:3]
        future = consumer.trace_cases(
            original, 'stop-future_response_write', source_write_read_variant=variant)
        assert future == [original[4]]
        assert original == before


def test_source_read_bounded_variant_preserves_registered_first_range():
    for count in (1, 7, 12):
        original = cases_with_source_read(offset=1, limit=count)
        before = deepcopy(original)
        selected = consumer.trace_cases(
            original, 'stop-source_write', source_write_read_variant='bounded')
        assert selected[0]['input'] == {'file_path': SOURCE, 'offset': 1, 'limit': count}
        assert original == before


def test_whole_variants_cannot_discard_an_existing_read_bound():
    for fields in ({'offset': 1, 'limit': 7}, {'offset': 1}, {'limit': 7}):
        for variant in ('whole', 'allow_large'):
            original = cases_with_source_read(**fields)
            before = deepcopy(original)
            with pytest.raises(ValueError):
                consumer.trace_cases(original, 'stop-source_write', source_write_read_variant=variant)
            assert original == before


def test_source_read_variant_rejects_unknown_enum_values():
    original = cases_with_source_read()
    for variant in ('', 'all', 'whole_allow_large', 'BOUNDED', True, 1):
        with pytest.raises(ValueError):
            consumer.trace_cases(original, 'stop-source_write', source_write_read_variant=variant)


def test_diagnostic_constant_override_has_explicit_argument_precedence(monkeypatch):
    original = cases_with_source_read()
    before = deepcopy(original)
    monkeypatch.setattr(consumer, 'SOURCE_WRITE_READ_VARIANT', 'bounded')
    selected = consumer.trace_cases(original, 'stop-source_write')
    assert selected[0]['input'] == {'file_path': SOURCE, 'offset': 1, 'limit': 12}
    selected = consumer.trace_cases(original, 'stop-source_write', source_write_read_variant='whole')
    assert selected[0]['input'] == {'file_path': SOURCE}
    assert consumer.trace_cases(original, 'settled') == original[:3]
    assert original == before


def test_source_read_variants_obey_replay_classifier_input_bounds():
    policy = {'readonly_lookups': {'inputs': [SOURCE], 'output_directories': [], 'bounded_reads': {}}}
    original = cases_with_source_read()
    for variant in ('whole', 'bounded', 'allow_large'):
        case = consumer.trace_cases(
            original, 'stop-source_write', source_write_read_variant=variant)[0]
        assert consumer._file_classification(policy, case)[0] == 'prescribed'
    policy['readonly_lookups']['bounded_reads'][SOURCE] = 7
    bounded = consumer.trace_cases(
        cases_with_source_read(offset=1, limit=7), 'stop-source_write',
        source_write_read_variant='bounded')[0]
    assert consumer._file_classification(policy, bounded)[0] == 'prescribed'
    for variant in ('whole', 'allow_large'):
        case = consumer.trace_cases(
            original, 'stop-source_write', source_write_read_variant=variant)[0]
        assert consumer._file_classification(policy, case)[0] == 'not_prescribed'


def test_bounded_source_content_uses_captured_source_without_registered_bound():
    lines = ['source line ' + str(number) for number in range(1, 24)]
    source_raw = '\n'.join(lines).encode()
    policy = {'readonly_lookups': {'bounded_reads': {}}}
    case = consumer.trace_cases(
        cases_with_source_read(), 'stop-source_write', source_write_read_variant='bounded')[0]
    content, rendered, count, total = consumer._read_content(
        case, {}, {}, {}, 'synthetic-session', source_raw, policy=policy)
    assert content == '\n'.join(lines[:12])
    assert rendered == '\n'.join(str(number) + '\t' + line
                                 for number, line in enumerate(lines[:12], 1))
    assert (count, total) == (12, 23)


def test_registered_source_read_count_still_matches_captured_bytes():
    source_raw = b'one\ntwo\nthree'
    case = consumer.trace_cases(
        cases_with_source_read(offset=1, limit=3), 'stop-source_write',
        source_write_read_variant='bounded')[0]
    policy = {'readonly_lookups': {'bounded_reads': {SOURCE: 4}}}
    with pytest.raises(ValueError):
        consumer._read_content(case, {}, {}, {}, 'synthetic-session', source_raw, policy=policy)


def test_source_variants_verify_complete_native_refusal_lifecycle(fixture):
    trace = 'stop-source_write'
    prefix = 'traces/' + trace + '/'
    source_path = fixture['expected']['source']['path']
    lines = fixture['source_raw'].decode().split('\n')
    variants = {
        'whole': {'file_path': source_path},
        'bounded': {'file_path': source_path, 'offset': 1, 'limit': 12},
        'allow_large': {'file_path': source_path, 'allow_large': True},
    }
    with permission_orchestration.loaded_permission_inputs() as (controls, _sources):
        with loaded_consumer('native_shared_permissions') as verified:
            for variant, payload in variants.items():
                value = fabricated_native_refusal(
                    fixture, 'source_write', source_read_succeeded=True)
                events = rows(value, prefix + 'transcript.jsonl')
                ledger = rows(value, prefix + 'control.jsonl')
                before_count = len(events)
                rejection = ledger[-1]
                before_locations = rejection['call_line'], rejection['result_line']

                read_call, read_callback, read_result = events[2:5]
                read_call['message']['content'][0]['input'] = deepcopy(payload)
                read_callback['request']['input']['tool_input'] = deepcopy(payload)
                ledger[2]['request'] = deepcopy(read_callback)
                selected = lines[:12] if variant == 'bounded' else lines
                read_result['message']['content'][0]['content'] = '\n'.join(
                    str(number) + '\t' + line for number, line in enumerate(selected, 1))
                read_result['tool_use_result'] = {
                    'type': 'text',
                    'file': {'filePath': source_path, 'content': '\n'.join(selected),
                             'numLines': len(selected), 'startLine': 1, 'totalLines': len(lines)},
                }

                call = events[rejection['call_line'] - 1]
                result = events[rejection['result_line'] - 1]
                assert call['message']['content'][0]['id'] == 'source_write'
                assert result['message']['content'][0]['tool_use_id'] == 'source_write'
                rejection['call_sha256'] = consumer._sha(encoded(call))
                rejection['result_sha256'] = consumer._sha(encoded(result))
                assert len(events) == before_count
                assert (rejection['call_line'], rejection['result_line']) == before_locations
                put_rows(value, prefix + 'transcript.jsonl', events)
                put_rows(value, prefix + 'control.jsonl', ledger)
                raw = {name: member['text'].encode() for name, member in value['members'].items()}

                summary, observed, launch = verified._trace(
                    fixture['expected'], fixture['selection'], trace, raw, controls,
                    source_write_read_variant=variant)
                assert summary['mode'] == 'native_refused_before_callback'
                assert summary['protection'] == 'native_binary'
                assert launch['exit_code'] == 0
                assert [case['observed_mode'] for case in observed] == [
                    'allowed', 'native_refused_before_callback']
                assert observed[0]['input_sha256'] == consumer._sha(encoded(payload))
                assert observed[0]['result_sha256'] == consumer._sha(encoded(read_result))
                assert observed[1]['callback_id'] is None
                assert observed[1]['protection'] == 'native_binary'

                if variant == 'whole':
                    assert verified._trace(
                        fixture['expected'], fixture['selection'], trace, raw, controls)[0] == summary
                else:
                    with pytest.raises(ValueError, match='call differs from exact scripted case'):
                        verified._trace(fixture['expected'], fixture['selection'], trace, raw, controls)
