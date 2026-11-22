"""PR6302 optional probe prefix over unchanged round-two bytes, 2026-11-22.

These are wire-reader controls, never a replayed native execution or a passing
qualification. The real admitted Bash failures must remain failures.
"""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import native_shared_permission_wire as wire
from tests.test_native_permission_wire_profile import decoded
from tests.test_native_production_wire_round2_2_1_325 import PACK, TRACES


def context(name):
    value = json.loads(PACK.read_bytes())['traces'][name]
    assert value['qualification_expected'] == 'refuse'
    files = value['files']
    raw = decoded(files['transcript.jsonl'])
    controls = decoded(files['control.jsonl'])
    events = [json.loads(line) for line in raw.splitlines()]
    clean = [{key: item for key, item in row.items() if key != 'at'}
             for row in map(json.loads, controls.splitlines())]
    launch = json.loads(decoded(files['launch.before.json']))
    policy = json.loads(decoded(files['evidence_root/projection.json']))['probe_policy']
    runtime = {'executable': deepcopy(launch['executable']), 'model': events[1]['model'],
               'effort': 'high'}
    return raw, events, clean, launch, policy, runtime


def begin(data):
    _, events, clean, launch, policy, runtime = data
    return wire.begin_trace(events, clean, runtime, launch, policy,
                            additional_directories=[launch['effect_root']])


def test_real_round2_without_ui_keeps_first_call_and_callback_at_rows_three_four(name):
    data = context(name)
    raw, events, _, _, _, _ = data
    state = begin(data)
    assert state.offset == 2 and state.session == events[1]['session_id']
    block = events[2]['message']['content'][0]
    case = {'id': block['id'], 'tool': block['name'], 'input': block['input'], 'mode': 'allowed'}
    state.call(events[2], case, 0)
    state.callback(events[3], case)
    assert json.loads(raw.splitlines()[2]) == events[2]
    assert json.loads(raw.splitlines()[3]) == events[3]
    assert data[0] == raw


test_real_round2_without_ui_keeps_first_call_and_callback_at_rows_three_four = pytest.mark.parametrize(
    'name', TRACES)(test_real_round2_without_ui_keeps_first_call_and_callback_at_rows_three_four)


def test_no_ui_does_not_relax_ack_init_or_exact_identity():
    for mutation in ('no_ack', 'no_init', 'duplicate_ack', 'duplicate_init', 'swapped',
                     'ack_join', 'unknown_ack', 'unknown_init', 'wrong_grant', 'wrong_identity'):
        data = context('settled')
        _, events, clean, _, _, runtime = data
        original = events[2]['message']['content'][0]
        case = {'id': original['id'], 'tool': original['name'],
                'input': deepcopy(original['input']), 'mode': 'allowed'}
        if mutation == 'no_ack':
            del events[0]
        elif mutation == 'no_init':
            del events[1]
        elif mutation == 'duplicate_ack':
            events.insert(1, deepcopy(events[0]))
        elif mutation == 'duplicate_init':
            events.insert(2, deepcopy(events[1]))
        elif mutation == 'swapped':
            events[0], events[1] = events[1], events[0]
        elif mutation == 'ack_join':
            clean[1]['frame']['response']['request_id'] = 'foreign'
        elif mutation == 'unknown_ack':
            events[0]['unknown'] = True
        elif mutation == 'unknown_init':
            events[1]['unknown'] = True
        elif mutation == 'wrong_grant':
            events[1]['additional_directories'] = []
        else:
            runtime['executable']['sha256'] = '0' * 64
        with pytest.raises(ValueError):
            state = begin(data)
            # A duplicate init after otherwise valid startup must not become
            # the first scripted call, even though startup alone is valid.
            state.call(events[state.offset], case, 0)


def test_real_admitted_bash_errors_still_refuse_after_optional_startup():
    data = context('settled')
    calls, admitted_failures = {}, 0
    for event in data[1]:
        message = event.get('message', {})
        if type(message) is not dict:
            continue
        for block in message.get('content', []):
            if block.get('type') == 'tool_use':
                calls[block['id']] = block
            elif block.get('type') == 'tool_result':
                call = calls[block['tool_use_id']]
                metadata = event.get('tool_result_meta', [])
                admitted = (len(metadata) == 1
                    and metadata[0]['permission_decision']['decision'] == 'accept')
                if call['name'] == 'Bash' and admitted:
                    assert block['is_error'] is True
                    admitted_failures += 1
                    case = {'id': call['id'], 'tool': 'Bash', 'input': call['input'], 'mode': 'allowed'}
                    with pytest.raises(ValueError, match='result identity or success differs'):
                        begin(data).result(event, case, ('prescribed', 'retained admission'))
    assert admitted_failures == 7
