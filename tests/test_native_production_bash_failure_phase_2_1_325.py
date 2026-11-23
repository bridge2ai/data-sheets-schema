"""PR 6302 P1: admitted Bash failures remain failures, 2026-11-22.

One result is unchanged retained round-2 evidence. Other turns and phase
prerequisites are explicit software controls; no native process is invoked.
"""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import native_wire_2_1_325 as wire
from tests import test_native_production_wire_adapter_2_1_325 as attribution_controls
from tests.test_native_production_wire_round2_2_1_325 import retained
from tests.test_native_shared_phase import Trace, decision
from tests.test_source_attribution_preflight import inputs as preflight_inputs  # noqa: F401


prohibit_transports = attribution_controls.prohibit_transports


def _retained_failure():
    rows, events, _, _, runtime = retained('settled')
    result = events[7]
    block = result['message']['content'][0]
    assert result == json.loads(rows[7]) and block['content'].startswith('Exit code 1\n')
    identity = block['tool_use_id']
    call = next(event for event in events if event.get('type') == 'assistant'
                and any(item.get('id') == identity for item in event['message']['content']))
    return call, result, runtime


def _phase(kind):
    """Use the existing ordered fixture to establish software prerequisites."""
    trace = Trace()
    if kind in ('phase1_receipts', 'full_schema', 'full_terms'):
        trace.helper('chunk_check'); trace.helper('source_scope')
        trace.write('full'); trace.write('receipt')
        trace.helper('full_schema'); trace.helper('full_terms')
    elif kind == 'advance':
        trace.initial()
    elif kind == 'original_source_inventory':
        trace.initial()
        trace.helper('advance', after=decision(number=2))
        trace.helper('derive_core'); trace.helper('core_schema'); trace.helper('pair')
    else:
        trace.assembly(); trace.final_checks()
        if kind in ('draft', 'final_evidence'):
            trace.helper('final_source_inventory'); trace.write('report')
        if kind == 'final_evidence':
            trace.helper('draft')
    _, template, runtime = _retained_failure()
    trace.state.runtime = deepcopy(runtime)
    trace.state._session = template['session_id']
    return trace


def _phase_call(trace, kind):
    identity = 'constructed-call-' + str(trace.state._index)
    command = next(command for command, name in trace.state.commands.items() if name == kind)
    event = {'type': 'assistant', 'session_id': trace.state._session,
        'message': {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': identity,
            'name': 'Bash', 'input': {'command': command}}]}}
    trace.state.observe(event, stage_decision=trace.current)
    return identity


def _failure(identity, *, code=1, output='ordinary failed helper\n'):
    _, original, _ = _retained_failure()
    result = deepcopy(original)
    block = result['message']['content'][0]
    block.update(tool_use_id=identity, is_error=True, content='Exit code ' + str(code) + '\n' + output)
    result['tool_use_result'] = 'Error: ' + block['content']
    result['tool_result_meta'][0]['id'] = identity
    return result


def _success(identity, text):
    result = _failure(identity)
    result['message']['content'][0].update(is_error=False, content=text)
    result['tool_use_result'] = {'stdout': text, 'stderr': '', 'interrupted': False,
                               'isImage': False, 'noOutputExpected': False}
    return result


def _denial(identity):
    _, result, _ = _retained_failure()
    return {'type': 'system', 'subtype': 'permission_denied', 'tool_name': 'Bash',
        'tool_use_id': identity, 'decision_reason_type': 'other',
        'decision_reason': 'constructed denial contradiction', 'message': 'constructed denied Bash',
        'uuid': result['uuid'], 'session_id': result['session_id']}


def _receipt_payload():
    return {'mode': 'initial_structure', 'structure_passed': True,
        'floors': 'pending', 'floor_acceptance_claimed': False,
        'summary': None, 'reason': None, 'findings': [], 'structural_checks': {},
        'native_initial_inputs': {'selection_sha256': 'a' * 64,
            'full_sha256': 'b' * 64, 'receipt_sha256': 'c' * 64},
        'receipt_completion_policy': None}


def _assert_failure_record(record, identity, code, output):
    assert record['tool_use_id'] == identity and type(record['exit_code']) is int
    assert record['exit_code'] == code and record['stdout'] is None
    assert record['merged_output'] == output
    assert record['status_basis'] == wire.FAILURE_STATUS_BASIS
    assert 'stderr' not in record and 'exit_status' not in record


def test_retained_line_eight_records_actual_failure_without_sealing():
    trace = _phase('phase1_receipts')
    call, result, _ = _retained_failure()
    before = deepcopy(result)
    command = call['message']['content'][0]['input']['command']
    trace.state.commands[command] = 'phase1_receipts'
    trace.state.observe(call, stage_decision=trace.current)
    assert trace.state.observe(result, stage_decision=trace.current) == ()
    block = result['message']['content'][0]
    _assert_failure_record(trace.state.report()['checks'][-1], block['tool_use_id'], 1,
                           block['content'].split('\n', 1)[1])
    assert not trace.state.report()['phase1_sealed']
    assert 'phase1_receipts' not in trace.state.report()['current_checks']
    assert trace.state.report()['passed'] and result == before


def test_initial_receipt_failure_keeps_merged_json_uncredited_and_allows_later_success(code):
    trace = _phase('phase1_receipts')
    raw = json.dumps(_receipt_payload())
    identity = _phase_call(trace, 'phase1_receipts')
    assert trace.state.observe(_failure(identity, code=code, output=raw)) == ()
    _assert_failure_record(trace.state.report()['checks'][-1], identity, code, raw)
    assert not trace.state._phase1_sealed and not trace.state._has('phase1_receipts')
    identity = _phase_call(trace, 'phase1_receipts')
    assert trace.state.observe(_success(identity, raw)) == ('seal_phase1',)
    assert trace.state._has('phase1_receipts') and trace.state.report()['passed']


test_initial_receipt_failure_keeps_merged_json_uncredited_and_allows_later_success = pytest.mark.parametrize(
    'code', [1, 2, 17])(test_initial_receipt_failure_keeps_merged_json_uncredited_and_allows_later_success)


def test_draft_exit_one_then_success_recovers_without_json_credit():
    trace = _phase('draft')
    raw = json.dumps({'checked': True, 'passed': True, 'protocol_version': 7})
    identity = _phase_call(trace, 'draft')
    assert trace.state.observe(_failure(identity, output=raw), stage_decision=trace.current) == ()
    _assert_failure_record(trace.state.report()['checks'][-1], identity, 1, raw)
    assert not trace.state._has('draft') and trace.state.report()['passed']
    with pytest.raises(ValueError, match='current passing draft'):
        trace.state.before('Bash', {'command': next(command for command, kind in trace.state.commands.items()
                                                  if kind == 'final_evidence')}, stage_decision=trace.current)
    identity = _phase_call(trace, 'draft')
    assert trace.state.observe(_success(identity, raw), stage_decision=trace.current) == ()
    assert trace.state._has('draft') and trace.state.report()['passed']


def test_validator_failure_invalidates_prior_pass_then_allows_success(kind, text):
    trace = _phase(kind)
    assert trace.state._has(kind)
    identity = _phase_call(trace, kind)
    assert trace.state.observe(_failure(identity, code=3)) == ()
    assert not trace.state._has(kind) and trace.state.report()['passed']
    identity = _phase_call(trace, kind)
    assert trace.state.observe(_success(identity, text)) == ()
    assert trace.state._has(kind) and trace.state.report()['passed']


test_validator_failure_invalidates_prior_pass_then_allows_success = pytest.mark.parametrize(
    'kind,text', [('full_schema', 'No issues found\n'), ('full_terms', '✅ Validation passed\n')]
)(test_validator_failure_invalidates_prior_pass_then_allows_success)


def test_terminal_and_unusable_phase_failures_remain_sticky(kind, code):
    trace = _phase(kind)
    identity = _phase_call(trace, kind)
    with pytest.raises(ValueError, match='terminal source|unusable exit|failed stage'):
        trace.state.observe(_failure(identity, code=code), stage_decision=trace.current)
    _assert_failure_record(trace.state.report()['checks'][-1], identity, code, 'ordinary failed helper\n')
    assert not trace.state._has(kind) and not trace.state.report()['passed']
    with pytest.raises(ValueError, match='history already failed'):
        _phase_call(trace, kind)


test_terminal_and_unusable_phase_failures_remain_sticky = pytest.mark.parametrize(
    'kind,code', [('original_source_inventory', 1), ('audit_evidence', 1),
                  ('final_source_inventory', 1), ('final_evidence', 1), ('advance', 1), ('draft', 2)]
)(test_terminal_and_unusable_phase_failures_remain_sticky)


def test_phase_refuses_denial_or_wrong_identity_failure(mutation):
    trace = _phase('phase1_receipts')
    identity = _phase_call(trace, 'phase1_receipts')
    result, denials = _failure(identity), None
    if mutation == 'native_denial':
        trace.state.observe(_denial(identity))
    elif mutation == 'classified_denial':
        denials = {identity: {'classification': 'not_prescribed', 'basis': 'constructed', 'tool': 'Bash'}}
    elif mutation == 'denial_meta':
        result['tool_result_meta'][0]['permission_decision']['decision'] = 'reject'
    elif mutation == 'wrong_runtime':
        trace.state.runtime['executable']['sha256'] = '0' * 64
    else:
        trace.state.runtime = None
    with pytest.raises(ValueError):
        trace.state.observe(result, denials=denials)
    assert not trace.state._has('phase1_receipts') and not trace.state._phase1_sealed
    assert not trace.state.report()['passed']


test_phase_refuses_denial_or_wrong_identity_failure = pytest.mark.parametrize(
    'mutation', ['native_denial', 'classified_denial', 'denial_meta', 'wrong_runtime', 'absent_runtime']
)(test_phase_refuses_denial_or_wrong_identity_failure)


def _attribution_failure(selected, commands, *, kind='draft', code=1, output='failed checker\n', denial=False):
    identity = 'constructed-attribution-' + str(selected.index)
    result = _failure(identity, code=code, output=output)
    selected.observe({'type': 'assistant', 'session_id': result['session_id'],
        'message': {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': identity,
            'name': 'Bash', 'input': {'command': commands[kind]}}]}})
    if denial:
        selected.observe(_denial(identity))
    selected.observe(result)
    return identity


def test_attribution_draft_failure_recovers_only_after_current_input_proofs(tmp_path, preflight_inputs):
    selected, payload, paths, commands = attribution_controls.attribution_control(tmp_path, preflight_inputs)
    raw = json.dumps(payload)
    identity = _attribution_failure(selected, commands, output=raw)
    _assert_failure_record(selected.observations[-1], identity, 1, raw)
    assert not selected.observations[-1]['reported_passed']
    assert not selected.observations[-1]['verified_against_current_saved_bytes']
    assert selected.accepted is None and not selected.terminal and selected.problems == []
    attribution_controls.attribution_turn(selected, 'draft', payload, commands)
    report = selected.report(complete=True)
    assert report['draft_gate_passed'] and report['problems'] == []
    assert report['observations'][-1]['input_sha256'] == payload['input_sha256']
    assert report['observations'][-1]['verified_against_current_saved_bytes'] is True
    paths['full'].write_bytes(b'description: Changed after retried draft.\n')
    report = selected.report(complete=True)
    assert not report['draft_gate_passed'] and any('current saved bytes' in item for item in report['problems'])


def test_attribution_retry_cannot_bypass_input_hashes_or_draft_limit(tmp_path, preflight_inputs, mutation):
    selected, payload, _, commands = attribution_controls.attribution_control(tmp_path, preflight_inputs)
    _attribution_failure(selected, commands)
    if mutation == 'input_hash':
        payload['input_sha256']['bundle'] = '0' * 64
    else:
        selected.reg['max_draft_checks'] = 1
    attribution_controls.attribution_turn(selected, 'draft', payload, commands)
    report = selected.report(complete=True)
    assert not report['draft_gate_passed'] and report['problems']


test_attribution_retry_cannot_bypass_input_hashes_or_draft_limit = pytest.mark.parametrize(
    'mutation', ['input_hash', 'draft_limit'])(test_attribution_retry_cannot_bypass_input_hashes_or_draft_limit)


def test_attribution_failure_does_not_recover_after_terminal_denial_or_wrong_identity(
        tmp_path, preflight_inputs, mutation):
    selected, payload, _, commands = attribution_controls.attribution_control(tmp_path, preflight_inputs)
    kind, code = 'draft', 1
    if mutation == 'wrong_runtime':
        selected.runtime['executable']['sha256'] = '0' * 64
    elif mutation == 'absent_runtime':
        selected.runtime = None
    elif mutation == 'draft_two':
        code = 2
    elif mutation in ('evidence', 'source_inventory', 'final_evidence'):
        kind = mutation
        if kind == 'final_evidence':
            attribution_controls.attribution_turn(selected, 'draft', payload, commands)
    _attribution_failure(selected, commands, kind=kind, code=code, denial=mutation == 'denial')
    assert selected.terminal and selected.accepted is None and selected.problems
    attribution_controls.attribution_turn(selected, 'draft', payload, commands)
    report = selected.report(complete=True)
    assert not report['draft_gate_passed'] and report['terminal_failure_observed']


test_attribution_failure_does_not_recover_after_terminal_denial_or_wrong_identity = pytest.mark.parametrize(
    'mutation', ['wrong_runtime', 'absent_runtime', 'draft_two', 'evidence', 'source_inventory',
                 'final_evidence', 'denial']
)(test_attribution_failure_does_not_recover_after_terminal_denial_or_wrong_identity)
