"""PR6302 observed failed Bash status controls, 2026-11-22.

The retained line-eight result is unchanged real evidence. Mutations below are
explicit software controls, not native runs or successful probe qualification.
"""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observations
from data_sheets_schema import native_wire_2_1_325 as wire
from tests import test_native_production_wire_round2_2_1_325 as round2


prohibit_transports = round2.prohibit_transports


def retained_failure():
    rows, events, controls, policy, runtime = round2.retained('settled')
    event = events[7]
    block = event['message']['content'][0]
    assert block['tool_use_id'] == 'stage_receipt' and block['is_error'] is True
    return rows, events, controls, policy, runtime, event, block


def mutated_trace(events, controls, policy, runtime):
    """Encode explicitly changed copies; never replace the retained raw rows."""
    transcript = round2.prefix('transcript', [c.canonical(row) + b'\n' for row in events])
    control = round2.prefix('control', [c.canonical(row) + b'\n' for row in controls])
    return observations.Trace(transcript, control, session_id=events[1]['session_id'],
                              policy=policy, runtime=runtime)


def test_retained_failure_keeps_observed_status_opaque_output_and_physical_joins():
    rows, events, controls, policy, runtime, event, block = retained_failure()
    original = deepcopy(event)
    status, merged = wire.missing_numeric_bash_failure(event, block, runtime)
    assert status == 1 and merged == block['content'].split('\n', 1)[1]
    assert merged.startswith('{"argv":') and '\nzsh:1: operation not permitted:' in merged
    assert wire.FAILURE_STATUS_BASIS == 'is_error_true_exit_code_2_1_325'
    assert event == original and json.loads(rows[7]) == event
    transcript = round2.prefix('transcript', rows[:8])
    control = round2.prefix('control', controls[:4])
    trace = observations.Trace(transcript, control, session_id=events[1]['session_id'],
                               policy=policy, runtime=runtime)
    assert trace.denial('stage_receipt') is None and trace.denied_ids() == set()
    evidence = trace.settled('stage_receipt')
    assert evidence.call.call == observations.reference(transcript, 6, 0)
    assert evidence.call.callback == observations.reference(transcript, 7)
    assert evidence.call.admission == observations.reference(control, 4)
    assert evidence.result == observations.reference(transcript, 8, 0)
    assert evidence.result_event == observations.reference(transcript, 8)
    assert trace.transcript.raw == b''.join(rows[:8])
    assert trace.control.raw == b''.join(controls[:4])
    assert trace.results['stage_receipt'][2]['is_error'] is True
    with pytest.raises(ValueError, match='errored'):
        observations.helper_result(trace, evidence, {})


def test_observed_positive_status_is_not_limited_to_one_or_parsed_as_json(status):
    _, _, _, _, runtime, event, block = retained_failure()
    block['content'] = 'Exit code ' + str(status) + '\n{"ok":true}\nnot separate stderr'
    event['tool_use_result'] = 'Error: ' + block['content']
    assert wire.missing_numeric_bash_failure(event, block, runtime) == (
        status, '{"ok":true}\nnot separate stderr')


test_observed_positive_status_is_not_limited_to_one_or_parsed_as_json = pytest.mark.parametrize(
    'status', [1, 2, 127, 255])(test_observed_positive_status_is_not_limited_to_one_or_parsed_as_json)


def test_failure_status_prefix_must_be_an_observed_positive_integer(prefix):
    _, _, _, _, runtime, event, block = retained_failure()
    block['content'] = prefix + '{"ok":true}'
    event['tool_use_result'] = 'Error: ' + block['content']
    with pytest.raises(ValueError, match='status, wrapper or permission metadata'):
        wire.missing_numeric_bash_failure(event, block, runtime)


test_failure_status_prefix_must_be_an_observed_positive_integer = pytest.mark.parametrize(
    'prefix', ['Exit code 0\n', 'Exit code -1\n', 'Exit code 1.0\n',
               'Exit code true\n', 'Exit code 01\n', 'Exit code 1', 'Exit code 1\r\n'])(
        test_failure_status_prefix_must_be_an_observed_positive_integer)


def test_failure_requires_exact_error_envelope_and_accepted_metadata(mutation):
    _, _, _, _, runtime, event, block = retained_failure()
    annotation = event['tool_result_meta'][0]
    if mutation == 'wrapper':
        event['tool_use_result'] = block['content']
    elif mutation == 'successful_flag':
        block['is_error'] = False
    elif mutation == 'integer_flag':
        block['is_error'] = 1
    elif mutation == 'missing_flag':
        del block['is_error']
    elif mutation == 'denied_metadata':
        annotation['permission_decision']['decision'] = 'reject'
    elif mutation == 'hook_metadata':
        annotation['permission_decision']['source'] = 'hook'
    elif mutation == 'other_reason':
        annotation['permission_decision']['reason_type'] = 'other'
    elif mutation == 'annotation_id':
        annotation['id'] = 'other'
    elif mutation == 'nonexecution':
        annotation['non_execution_kind'] = 'permission-rule'
    elif mutation == 'missing_metadata':
        del event['tool_result_meta']
    elif mutation == 'extra_metadata':
        event['tool_result_meta'].append(deepcopy(annotation))
    elif mutation == 'extra_envelope':
        event['exitCode'] = 0
    elif mutation == 'child':
        event['parent_tool_use_id'] = 'other'
    elif mutation == 'other_role':
        event['message']['role'] = 'assistant'
    elif mutation == 'extra_message':
        event['message']['extra'] = True
    elif mutation == 'extra_block':
        event['message']['content'].append(deepcopy(block))
    elif mutation == 'block_field':
        block['stdout'] = '{}'
    elif mutation == 'invalid_uuid':
        event['uuid'] = 'not-a-uuid'
    elif mutation == 'invalid_session':
        event['session_id'] = event['session_id'].upper()
    elif mutation == 'missing_timestamp':
        del event['timestamp']
    elif mutation == 'timestamp_offset':
        event['timestamp'] = '2026-11-22T01:36:21+01:00'
    else:
        event['timestamp'] = 'not-a-timeZ'
    with pytest.raises(ValueError):
        wire.missing_numeric_bash_failure(event, block, runtime)


test_failure_requires_exact_error_envelope_and_accepted_metadata = pytest.mark.parametrize(
    'mutation', ['wrapper', 'successful_flag', 'integer_flag', 'missing_flag',
        'denied_metadata', 'hook_metadata', 'other_reason', 'annotation_id',
        'nonexecution', 'missing_metadata', 'extra_metadata', 'extra_envelope',
        'child', 'other_role', 'extra_message', 'extra_block', 'block_field',
        'invalid_uuid', 'invalid_session', 'missing_timestamp', 'timestamp_offset',
        'invalid_timestamp'])(test_failure_requires_exact_error_envelope_and_accepted_metadata)


def test_other_identity_and_existing_numeric_metadata_keep_their_reader(mutation):
    _, _, _, _, runtime, event, block = retained_failure()
    if mutation == 'no_runtime':
        runtime = None
    elif mutation == 'version':
        runtime['executable']['version'] = '2.1.324 (Claude Code)'
    elif mutation == 'init_version':
        runtime['executable']['init_version'] = '2.1.324'
    elif mutation == 'executable_hash':
        runtime['executable']['sha256'] = '0' * 64
    else:
        event['tool_use_result'] = {'exitCode': 1, 'stdout': '', 'stderr': 'failed'}
    assert wire.missing_numeric_bash_failure(event, block, runtime) is None


test_other_identity_and_existing_numeric_metadata_keep_their_reader = pytest.mark.parametrize(
    'mutation', ['no_runtime', 'version', 'init_version', 'executable_hash', 'numeric'])(
        test_other_identity_and_existing_numeric_metadata_keep_their_reader)


def test_missing_status_prefix_does_not_receive_failure_exemption():
    _, events, controls, policy, runtime, event, block = retained_failure()
    block['content'] = block['content'].split('\n', 1)[1]
    event['tool_use_result'] = 'Error: ' + block['content']
    assert wire.missing_numeric_bash_failure(event, block, runtime) is None
    trace = mutated_trace(events[:8], [json.loads(row) for row in controls[:4]], policy, runtime)
    with pytest.raises(ValueError, match='refusal wrapper or permission metadata'):
        trace.denial('stage_receipt')


def test_failure_exemption_requires_the_exact_prescribed_callback(mutation):
    _, events, controls, policy, runtime, _, _ = retained_failure()
    events = events[:8]
    controls = [json.loads(row) for row in controls[:4]]
    if mutation == 'missing_decision':
        controls.pop()
    elif mutation == 'denied_decision':
        decision = controls[-1]
        decision['classification'] = 'not_prescribed'
        decision['basis'] = 'software control denied admission'
        decision['response']['response']['response'] = {'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
            'permissionDecisionReason': 'Outside the registered tool policy: ' + decision['basis']}}
    elif mutation == 'callback_id':
        events[6]['request']['input']['tool_use_id'] = 'different-call'
    elif mutation == 'decision_callback_id':
        controls[-1]['request']['request_id'] = 'different-callback'
    elif mutation == 'result_before_callback':
        events[6], events[7] = events[7], events[6]
    else:
        events[5]['message']['content'][0]['name'] = 'Read'
        events[6]['request']['input']['tool_name'] = 'Read'
        controls[-1]['request'] = deepcopy(events[6])
    with pytest.raises(ValueError):
        mutated_trace(events, controls, policy, runtime).denial('stage_receipt')


test_failure_exemption_requires_the_exact_prescribed_callback = pytest.mark.parametrize(
    'mutation', ['missing_decision', 'denied_decision', 'callback_id',
                 'decision_callback_id', 'result_before_callback', 'not_bash'])(
        test_failure_exemption_requires_the_exact_prescribed_callback)


def test_same_id_denial_before_or_after_failure_remains_fatal(position):
    _, events, controls, policy, runtime, event, _ = retained_failure()
    events = events[:8]
    denial = {'type': 'system', 'subtype': 'permission_denied', 'tool_name': 'Bash',
        'tool_use_id': 'stage_receipt', 'decision_reason_type': 'rule',
        'decision_reason': 'software-only contradictory denial',
        'message': 'Permission to use Bash denied.',
        'uuid': '2b318c80-a96c-400a-9386-566b4b70f0fa', 'session_id': event['session_id']}
    events.insert(position, denial)
    with pytest.raises(ValueError, match='permission denial'):
        trace = mutated_trace(events, [json.loads(row) for row in controls[:4]], policy, runtime)
        trace.denial('stage_receipt')


test_same_id_denial_before_or_after_failure_remains_fatal = pytest.mark.parametrize(
    'position', [7, 8])(test_same_id_denial_before_or_after_failure_remains_fatal)


def test_actual_hook_denial_remains_denied_with_full_retained_history():
    rows, events, controls, policy, runtime, _, _ = retained_failure()
    transcript = round2.prefix('transcript', rows)
    control = round2.prefix('control', controls)
    trace = observations.Trace(transcript, control, session_id=events[1]['session_id'],
                               policy=policy, runtime=runtime)
    for identity in ('arbitrary_python', 'modified_draft', 'modified_stage'):
        line, _, block = trace.results[identity]
        assert wire.missing_numeric_bash_failure(trace.frames[line], block, runtime) is None
        result = trace.denial(identity)
        assert result['classification'] == 'not_prescribed' and result['tool'] == 'Bash'
    assert trace.denied_ids() == {'arbitrary_python', 'modified_draft', 'modified_stage'}
