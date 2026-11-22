"""PR6302 P1 saved-history failure controls, 2026-11-22.

Retained failure envelopes are explicitly mutated into software helper cases.
No native command or authority admission runs; one case uses the real phase
reader and the remaining cases isolate the saved gate's phase-result joins.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_gate_primitives as gates
from data_sheets_schema import native_wire_2_1_325 as wire
from tests import test_native_production_wire_2_1_325 as production
from tests import test_native_production_wire_round2_2_1_325 as round2


prohibit_transports = round2.prohibit_transports


def failure_result(identity, *, code=1, merged='software failure diagnostic\n'):
    event = deepcopy(round2.retained('settled')[1][7])
    block = event['message']['content'][0]
    block.update(tool_use_id=identity, is_error=True,
                 content='Exit code ' + str(code) + '\n' + merged)
    event['tool_use_result'] = 'Error: ' + block['content']
    event['tool_result_meta'] = [{'id': identity, 'permission_decision': {
        'decision': 'accept', 'source': 'config', 'reason_type': 'rule'}}]
    return event


def gate_case(kind='draft', *, code=1, merged='software failure diagnostic\n'):
    _, events, _, _, runtime = round2.retained('settled')
    identity, command = 'software-history-failure', 'software helper ' + str(kind)
    helper = {None: 'full_schema', 'evidence': 'audit_evidence',
              'source_inventory': 'original_source_inventory'}.get(kind, kind)
    call = {'type': 'assistant', 'session_id': events[1]['session_id'], 'message': {
        'role': 'assistant', 'content': [{'type': 'tool_use', 'id': identity,
            'name': 'Bash', 'input': {'command': command}}]}}
    result = failure_result(identity, code=code, merged=merged)
    row = {'tool_use_id': identity, 'helper': helper, 'exit_code': code,
           'stdout': None, 'merged_output': merged, 'status_basis': wire.FAILURE_STATUS_BASIS}
    return {'events': events[:2] + [call, result, {'type': 'result'}],
        'state': SimpleNamespace(spec=object(), commands={command: kind}),
        'value': {'runtime': runtime}, 'policy': {'native_shared_helpers': {helper: command}},
        'phase_report': {'passed': True, 'problems': [], 'checks': [row]}}


def test_saved_history_preserves_observed_failure_without_json_credit():
    merged = '{"checked":true,"passed":true,"protocol_version":7}\n'
    for kind in ('draft', None):
        prepared = gate_case(kind, merged=merged)
        report = gates.tool_history(prepared)
        assert report['passed'] is True
        assert report['bash_results'] == [{'tool_use_id': 'software-history-failure',
            'helper_kind': kind, 'exit_code': 1, 'stdout': None,
            'merged_output': merged, 'status_basis': wire.FAILURE_STATUS_BASIS}]


def test_saved_history_joins_actual_phase_failure_then_later_schema_success():
    value = production.retained()
    state, call, success = production._schema_case(value)
    identity = call['message']['content'][0]['id']
    failed = failure_result(identity, code=2)
    failed['session_id'] = success['session_id']
    state.observe(call)
    state.observe(failed)
    assert 'full_schema' not in state._passed
    later_call, later_success = deepcopy(call), deepcopy(success)
    later_call['message']['content'][0]['id'] = identity + '-retry'
    later_success['message']['content'][0]['tool_use_id'] = identity + '-retry'
    state.observe(later_call)
    state.observe(later_success)
    command = call['message']['content'][0]['input']['command']
    prepared = {'events': value['events'][:3] + [call, failed, later_call, later_success,
        {'type': 'result'}], 'state': SimpleNamespace(spec=object(), commands={command: None}),
        'value': {'runtime': value['runtime']},
        'policy': {'native_shared_helpers': {'full_schema': command}},
        'phase_report': state.report()}
    report = gates.tool_history(prepared)
    assert report['passed'] and prepared['phase_report']['passed']
    first, second = report['bash_results']
    assert first['exit_code'] == 2 and first['stdout'] is None
    assert first['merged_output'] == 'software failure diagnostic\n'
    assert first['status_basis'] == wire.FAILURE_STATUS_BASIS
    assert second['exit_code'] is None and second['status_basis'] == wire.STATUS_BASIS


def test_saved_history_keeps_admitted_nonhelper_failure_without_success_credit():
    prepared = gate_case(None)
    prepared['policy']['native_shared_helpers'] = {}
    prepared['phase_report']['checks'][0]['helper'] = None
    report = gates.tool_history(prepared)
    row, = report['bash_results']
    assert row['helper_kind'] is None and row['exit_code'] == 1
    assert row['stdout'] is None and row['status_basis'] == wire.FAILURE_STATUS_BASIS


def test_saved_history_refuses_changed_failure_or_phase_join(mutation):
    prepared = gate_case()
    event = prepared['events'][-2]
    block = event['message']['content'][0]
    row = prepared['phase_report']['checks'][0]
    if mutation == 'missing_line':
        block['content'] = 'software failure diagnostic\n'
        event['tool_use_result'] = 'Error: ' + block['content']
    elif mutation in ('zero', 'noninteger'):
        block['content'] = block['content'].replace('Exit code 1',
            'Exit code ' + ('0' if mutation == 'zero' else 'unknown'))
        event['tool_use_result'] = 'Error: ' + block['content']
    elif mutation == 'wrapper':
        event['tool_use_result'] += 'changed'
    elif mutation == 'denial_meta':
        event['tool_result_meta'][0]['permission_decision']['decision'] = 'reject'
    elif mutation == 'denied_id':
        prepared['denied_tool_ids'] = ['software-history-failure']
    elif mutation == 'system_denial':
        denied = next(deepcopy(item) for item in production.retained()['events']
            if item.get('subtype') == 'permission_denied')
        denied.update(tool_use_id='software-history-failure', tool_name='Bash')
        prepared['events'].insert(-2, denied)
    elif mutation == 'runtime':
        prepared['value']['runtime']['executable']['sha256'] = '0' * 64
    elif mutation == 'missing_row':
        prepared['phase_report']['checks'] = []
    elif mutation == 'duplicate_row':
        prepared['phase_report']['checks'].append(deepcopy(row))
    elif mutation == 'failed_phase':
        prepared['phase_report']['passed'] = False
    elif mutation == 'wrong_helper':
        row['helper'] = 'another-helper'
    elif mutation == 'boolean_exit':
        row['exit_code'] = True
    elif mutation == 'wrong_exit':
        row['exit_code'] = 2
    elif mutation == 'missing_stdout':
        row.pop('stdout')
    elif mutation == 'invented_stdout':
        row['stdout'] = row['merged_output']
    elif mutation == 'wrong_output':
        row['merged_output'] += 'changed'
    elif mutation == 'wrong_basis':
        row['status_basis'] = wire.STATUS_BASIS
    else:
        prepared['policy']['native_shared_helpers'] = {}
    with pytest.raises(ValueError):
        gates.tool_history(prepared)


test_saved_history_refuses_changed_failure_or_phase_join = pytest.mark.parametrize('mutation', (
    'missing_line', 'zero', 'noninteger', 'wrapper', 'denial_meta', 'denied_id',
    'system_denial', 'runtime', 'missing_row', 'duplicate_row', 'failed_phase',
    'wrong_helper', 'boolean_exit', 'wrong_exit', 'missing_stdout', 'invented_stdout',
    'wrong_output', 'wrong_basis', 'missing_policy'))(
        test_saved_history_refuses_changed_failure_or_phase_join)


def test_saved_history_keeps_terminal_helpers_and_unusable_drafts_failed():
    for kind, code in (('draft', 2), ('evidence', 1), ('final_evidence', 1),
                       ('source_inventory', 1), ('advance', 1)):
        with pytest.raises(ValueError):
            gates.tool_history(gate_case(kind, code=code))
