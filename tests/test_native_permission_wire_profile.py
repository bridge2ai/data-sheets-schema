"""Reviewed raw scripted-wire fixtures; never native execution or qualification.

Historical traces remain behavioural failures. Mutations affect test copies
only; original physical bytes, line numbers and recorded digests stay intact.
"""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_permission_wire as wire


_PACK = None


def pack():
    global _PACK
    if _PACK is None:
        _PACK = json.loads((Path(__file__).parent / 'fixtures/native_permission_2_1_325/retained.json').read_bytes())
    return _PACK


def decoded(record):
    raw = base64.b64decode(record['raw_base64'], validate=True)
    assert len(raw) == record['decoded_bytes']
    assert hashlib.sha256(raw).hexdigest() == record['decoded_sha256']
    return raw


def context(label='r4/settled'):
    files = pack()['traces'][label]['files']
    raw = decoded(files['transcript.jsonl'])
    events = [json.loads(line) for line in raw.splitlines()]
    controls = [json.loads(line) for line in decoded(files['control.jsonl']).splitlines()]
    clean = [{key: value for key, value in row.items() if key != 'at'} for row in controls]
    launch = json.loads(decoded(files['launch.before.json']))
    policy = json.loads(decoded(files['evidence_root/projection.json']))['probe_policy']
    runtime = {'executable': deepcopy(launch['executable']), 'model': 'claude-opus-5[1m]',
        'auxiliary_models': [], 'effort': 'high', 'limits': {'contextWindow': 1000000, 'maxOutputTokens': 64000},
        'limits_basis': json.dumps({'kind': 'd4d_native_u4b_provisional_runtime_basis', 'version': 2,
            'model_aliases': {'requested': 'claude-opus-5[1m]', 'returned': 'claude-opus-5', 'reported': 'claude-opus-5'}})}
    return {'raw': raw, 'events': events, 'clean': clean, 'launch': launch, 'policy': policy, 'runtime': runtime}


def begin(value, *, directories=None):
    # Empty is the independently recorded old grant: this exercises wire
    # recognition only. The qualifying consumer always requires [effect_root].
    return wire.begin_trace(value['events'], value['clean'], value['runtime'], value['launch'], value['policy'],
                            additional_directories=[] if directories is None else directories)


def case_at(value, index, mode='allowed'):
    block = value['events'][index]['message']['content'][0]
    return {'id': block['id'], 'tool': block['name'], 'input': deepcopy(block['input']), 'mode': mode}


def test_retained_bytes_and_reviewed_frames_preserve_physical_identity():
    retained = pack()
    companion_raw = decoded(retained['reviewed_companion'])
    assert hashlib.sha256(companion_raw).hexdigest() == wire.COMPANION_SHA256
    companion = json.loads(companion_raw)
    for trace in retained['traces'].values():
        assert trace['qualification_expected'] == 'refuse'
        for record in trace['files'].values():
            decoded(record)
    for label, frames in companion['wire_frames'].items():
        transcript = decoded(retained['traces'][label + '/settled']['files']['transcript.jsonl'])
        lines = transcript.splitlines(keepends=True)
        for frame in frames.values():
            raw = base64.b64decode(frame['raw_base64'], validate=True)
            assert len(raw) == frame['decoded_bytes_including_newline']
            assert hashlib.sha256(raw).hexdigest() == frame['decoded_sha256_including_newline']
            assert raw == lines[frame['physical_line'] - 1]


def test_reviewed_profile_identity_and_raw_physical_prefix():
    for label in ('r4/settled', 'round1_plan06/settled', 'r4/stop-future_response_write',
                  'round1_plan06/stop-source_write'):
        value = context(label)
        before = value['raw']
        profile = begin(value)
        assert profile.offset == 3 and profile.session == value['events'][2]['session_id']
        case = case_at(value, 3)
        profile.call(value['events'][3], case, 0)
        profile.callback(value['events'][4], case)
        assert value['raw'] == before
        assert json.loads(before.splitlines()[3]) == value['events'][3]
        with pytest.raises(ValueError, match='init differs: additional_directories'):
            begin(value, directories=[value['launch']['effect_root']])


def test_profile_requires_all_three_executable_identity_fields():
    for field, changed in (('version', '2.1.325'), ('init_version', '2.1.324'), ('sha256', '0' * 64)):
        value = context()
        value['runtime']['executable'][field] = changed
        assert wire.profile(value['runtime']) is False
        with pytest.raises(ValueError, match='unreviewed executable identity'):
            begin(value)


def test_initialization_mutations_do_not_select_a_different_wire_profile():
    for change in ('missing_ui', 'extra_ui', 'reordered', 'repeated_init', 'ui_kind', 'ui_session',
                   'ack_join', 'pending', 'payload', 'pid_bool', 'styles_dir', 'tools', 'cwd',
                   'model', 'init_uuid', 'grant', 'unknown_field'):
        value = context()
        events = value['events']
        if change == 'missing_ui':
            del events[0]
        elif change == 'extra_ui':
            events.insert(0, deepcopy(events[0]))
        elif change == 'reordered':
            events[0], events[1] = events[1], events[0]
        elif change == 'repeated_init':
            events[1] = deepcopy(events[2])
        elif change == 'ui_kind':
            events[0]['event'] = 'ui.other'
        elif change == 'ui_session':
            events[0]['session_id'] = '00000000-0000-0000-0000-000000000099'
        elif change == 'ack_join':
            value['clean'][1]['frame']['response']['pending_permission_requests'] = ['pending']
        elif change == 'pending':
            events[1]['response']['pending_permission_requests'] = ['pending']
            value['clean'][1]['frame'] = deepcopy(events[1])
        elif change == 'payload':
            events[1]['response']['response']['hooks_applied'] = False
            value['clean'][1]['frame'] = deepcopy(events[1])
        elif change == 'pid_bool':
            events[1]['response']['response']['pid'] = True
        elif change == 'styles_dir':
            events[1]['response']['response']['user_output_styles_dir'] += '/foreign'
        elif change == 'tools':
            events[2]['tools'] = ['Read', 'Write', 'Bash']
        elif change == 'cwd':
            events[2]['cwd'] += '-foreign'
        elif change == 'model':
            events[2]['model'] = 'claude-opus-5[1m]'
        elif change == 'init_uuid':
            events[2]['uuid'] = events[0]['uuid']
        elif change == 'grant':
            events[2]['additional_directories'] = [str(Path(value['launch']['effect_root']).parent)]
        else:
            events[2]['unreviewed'] = True
        with pytest.raises(ValueError):
            begin(value)


def test_raw_calls_callbacks_and_success_annotations_match_reviewed_wire():
    value = context()
    profile = begin(value)
    for ordinal, index in ((0, 3), (1, 6)):
        case = case_at(value, index)
        profile.call(value['events'][index], case, ordinal)
        profile.callback(value['events'][index + 1], case)
        profile.result(value['events'][index + 2], case, ('prescribed', 'independently checked by consumer'))
    denied_index = 59
    case = case_at(value, denied_index, mode='native_denied')
    decision = value['clean'][18]
    assert decision['request']['request']['input']['tool_use_id'] == case['id']
    profile.call(value['events'][denied_index], case, 16)
    profile.callback(value['events'][denied_index + 1], case)
    profile.result(value['events'][denied_index + 2], case, ('not_prescribed', decision['basis']))


def test_callback_identity_scope_and_scripted_call_mutations_refuse():
    for change in ('uuid', 'timestamp', 'ordinal', 'call_model', 'call_input', 'callback_id',
                   'callback_session', 'callback_cwd', 'callback_effort', 'callback_input',
                   'callback_tool_id', 'transcript_path', 'duplicate_request', 'changed_prompt'):
        value = context()
        case = case_at(value, 3)
        profile = begin(value)
        call, callback = deepcopy(value['events'][3:5])
        if change == 'uuid':
            call['uuid'] = value['events'][0]['uuid']
        elif change == 'timestamp':
            call['timestamp'] = '2026-11-21T12:00:00-08:00'
        elif change == 'ordinal':
            call['message']['id'] = 'd4d_permission_1'
        elif change == 'call_model':
            call['message']['model'] = 'foreign-model'
        elif change == 'call_input':
            call['message']['content'][0]['input']['file_path'] += '.foreign'
        elif change == 'callback_id':
            callback['request_id'] = 'not-a-uuid'
        elif change == 'callback_session':
            callback['request']['input']['session_id'] = '00000000-0000-0000-0000-000000000099'
        elif change == 'callback_cwd':
            callback['request']['input']['cwd'] += '-foreign'
        elif change == 'callback_effort':
            callback['request']['input']['effort'] = 'high'
        elif change == 'callback_input':
            callback['request']['input']['tool_input']['file_path'] += '.foreign'
        elif change == 'callback_tool_id':
            callback['request']['tool_use_id'] += '-foreign'
        elif change == 'transcript_path':
            callback['request']['input']['transcript_path'] += '.foreign'
        else:
            profile.callback(callback, case)
            if change == 'changed_prompt':
                callback['request_id'] = '00000000-0000-0000-0000-000000000098'
                callback['request']['input']['prompt_id'] = '00000000-0000-0000-0000-000000000099'
        with pytest.raises(ValueError):
            profile.call(call, case, 0)
            profile.callback(callback, case)


def test_success_and_denial_annotations_do_not_replace_results():
    for change in ('annotation_id', 'annotation_decision', 'read_error', 'result_role',
                   'result_extra', 'denial_basis', 'denial_wrapper'):
        value = context()
        index = 59 if change.startswith('denial') else 3
        case = case_at(value, index, 'native_denied' if index == 59 else 'allowed')
        result = deepcopy(value['events'][index + 2])
        classification = ('not_prescribed', value['clean'][18]['basis']) if index == 59 else ('prescribed', 'source')
        if change == 'annotation_id':
            result['tool_result_meta'][0]['id'] += '-foreign'
        elif change == 'annotation_decision':
            result['tool_result_meta'][0]['permission_decision']['decision'] = 'reject'
        elif change == 'read_error':
            result['message']['content'][0]['is_error'] = True
        elif change == 'result_role':
            result['message']['role'] = 'assistant'
        elif change == 'result_extra':
            result['persisted_output'] = {}
        elif change == 'denial_basis':
            classification = ('not_prescribed', 'different reason')
        else:
            result['tool_use_result'] = {}
        with pytest.raises(ValueError):
            begin(value).result(result, case, classification)


def test_historical_required_effect_failures_and_terminal_denials_stay_failures():
    for label in ('r4/settled', 'round1_plan06/settled'):
        value = context(label)
        events = value['events']
        for identity in ('request_receipt_read', 'response_receipt_write'):
            index = next(index for index, event in enumerate(events) if event.get('type') == 'assistant'
                         and event['message']['content'][0].get('id') == identity)
            case = case_at(value, index)
            result = next(event for event in events if event.get('type') == 'user'
                          and event['message']['content'][0].get('tool_use_id') == identity)
            with pytest.raises(ValueError):
                begin(value).result(result, case, ('prescribed', 'required effect'))
        calls = [event for event in events if event.get('type') == 'assistant'
                 and event['message']['content'][0]['type'] == 'tool_use']
        cases = [{'id': event['message']['content'][0]['id'], 'tool': event['message']['content'][0]['name'],
                  'input': event['message']['content'][0]['input'],
                  'mode': 'native_denied' if number >= 16 else 'allowed'} for number, event in enumerate(calls)]
        assert len(cases) == 19 and len(events[-1]['permission_denials']) == 11
        with pytest.raises(ValueError, match='permission_denials'):
            begin(value).terminal(events[-1], cases)
    value = context('round1_plan06/settled')
    with pytest.raises(ValueError):
        begin(value).result(value['events'][8], case_at(value, 6), ('prescribed', 'required stage'))


def test_scripted_terminal_accounting_and_completion_are_closed():
    value = context()
    # Independent manufactured terminal for the three intended cases only;
    # the retained eleven-denial terminal remains untouched above.
    terminal = deepcopy(value['events'][-1])
    calls = [event for event in value['events'] if event.get('type') == 'assistant'
             and event['message']['content'][0]['type'] == 'tool_use']
    cases = [{'id': event['message']['content'][0]['id'], 'tool': event['message']['content'][0]['name'],
              'input': deepcopy(event['message']['content'][0]['input']),
              'mode': 'native_denied' if number >= 16 else 'allowed'} for number, event in enumerate(calls)]
    terminal['permission_denials'] = [{'tool_name': case['tool'], 'tool_use_id': case['id'], 'tool_input': case['input']}
                                     for case in cases if case['mode'] == 'native_denied']
    profile = begin(value)
    profile.completion(value['events'][-2], len(cases))
    profile.terminal(terminal, cases)
    for change in ('timing_bool', 'usage', 'second_model', 'pending', 'subagent', 'turns', 'completion'):
        changed = deepcopy(terminal)
        if change == 'timing_bool':
            changed['duration_ms'] = True
        elif change == 'usage':
            changed['usage']['input_tokens'] = 1
        elif change == 'second_model':
            changed['modelUsage']['foreign'] = {}
        elif change == 'pending':
            changed['queued_turn_count'] = 1
        elif change == 'subagent':
            changed['subagent_stats']['spawned'] = 1
        elif change == 'turns':
            changed['num_turns'] = 99
        else:
            changed['result'] = 'KEEP_GOING'
        with pytest.raises(ValueError):
            begin(value).terminal(changed, cases)
