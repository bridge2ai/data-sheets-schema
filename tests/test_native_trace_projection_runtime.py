"""Trace projection regressions for the main CI failure, 2026-11-22.

Retained Write and Bash rows stay unchanged except for explicitly labeled
software mutations. These pure reader controls launch no process or transport.
"""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_observations as observed
from tests import test_native_shared_observations as legacy
from tests import test_native_write_success_2_1_325 as writes
from tests import test_native_production_bash_failure_wire_2_1_325 as failures


prohibit_transports = writes.prohibit_transports


def project(base, lines=None, *, cached=False):
    lines = base.transcript.lines if lines is None else lines
    later = [number for identity, (number, _) in base.decisions.items()
             if base.callbacks[identity][0] > lines]
    controls = min(later) - 1 if later else base.control.lines
    result = capture._prefix_trace(base, capture._through(base.transcript, lines),
        capture._through(base.control, controls), (2, 2), {} if cached else None)
    assert type(result) is observed.Trace
    return result


def check_write(trace, identity, response):
    evidence = trace.settled(identity)
    assert observed.first_response_write(trace, evidence, response,
        intent_input_json=evidence.call.input_json) == evidence
    return evidence


def test_legacy_bare_write_survives_real_projection(extent):
    native, parent, response = legacy.events('Write')
    # Software terminal makes the earlier projection a proper stream prefix.
    terminal = {'type': 'result', 'session_id': legacy.SESSION,
                'permission_denials': []}
    base = legacy.trace(native + [terminal], parent)
    projected = project(base, base.transcript.lines - 1 if extent == 'earlier' else None,
                        cached=extent == 'full_cached')
    assert projected is not base
    evidence = check_write(projected, 'tool-1', response)
    assert evidence == base.settled('tool-1')
    assert projected.denial('tool-1') is None and projected.denied_ids() == set()
    if extent == 'earlier':
        assert projected.terminal is None and base.terminal is not None


test_legacy_bare_write_survives_real_projection = pytest.mark.parametrize(
    'extent', ['earlier', 'full_cached'])(test_legacy_bare_write_survives_real_projection)


def write_projection(identity='reviewed', *, bare=False, cached=False):
    value = writes.context()
    later = writes.context(writes.WRITES[-1][0])
    runtime = deepcopy(value['runtime'])
    if identity == 'missing_sha256':
        runtime['executable'].pop('sha256')
    elif identity != 'reviewed':
        runtime['executable'][identity] = 'unreviewed'
    native = list(later['native'][:later['record']['result']['physical_line']])
    if bare:
        # Explicit software control for the historical bare presentation.
        event = deepcopy(value['event'])
        event['message']['content'][0]['content'] = (
            'File created successfully at: ' + value['response'].pin.path)
        native[value['record']['result']['physical_line'] - 1] = (
            observed.c.canonical(event) + b'\n')
    control = later['control'][:later['record']['decision']['physical_line']]
    base = observed.Trace(writes.prefix('transcript', b''.join(native)),
        writes.prefix('control', b''.join(control)), session_id=value['session'],
        policy=value['policy'], runtime=runtime)
    projected = project(base, None if cached else value['record']['result']['physical_line'],
                        cached=cached)
    assert projected is not base
    return value, runtime, base, projected


def test_retained_write_projection_preserves_exact_identity_gate(identity, bare, cached):
    value, _, base, projected = write_projection(identity, bare=bare, cached=cached)
    tool = value['call']['id']
    if bare or identity == 'reviewed':
        evidence = check_write(projected, tool, value['response'])
        assert evidence == base.settled(tool)
        assert evidence.result.line == value['record']['result']['physical_line']
        assert observed.event(projected.transcript, evidence.result_event) == (
            observed.event(base.transcript, evidence.result_event))
    else:
        with pytest.raises(ValueError, match='successful first file creation'):
            check_write(projected, tool, value['response'])


test_retained_write_projection_preserves_exact_identity_gate = pytest.mark.parametrize(
    'identity', ['reviewed', 'version', 'sha256', 'missing_sha256'])(
    pytest.mark.parametrize('bare', [False, True])(
    pytest.mark.parametrize('cached', [False, True])(
        test_retained_write_projection_preserves_exact_identity_gate)))


def test_projection_runtime_is_independent_of_constructor_input_and_base():
    value, supplied, base, projected = write_projection()
    tool = value['call']['id']
    supplied['executable']['sha256'] = 'caller changed after construction'
    check_write(base, tool, value['response'])
    base.runtime['executable']['sha256'] = 'base changed after projection'
    check_write(projected, tool, value['response'])
    with pytest.raises(ValueError, match='successful first file creation'):
        check_write(base, tool, value['response'])
    projected.runtime['executable']['sha256'] = 'projection identity is unreviewed'
    with pytest.raises(ValueError, match='successful first file creation'):
        check_write(projected, tool, value['response'])


def test_retained_admitted_bash_failure_and_hook_refusal_survive_projection():
    rows, events, controls, policy, runtime, _, _ = failures.retained_failure()
    base = observed.Trace(failures.round2.prefix('transcript', rows),
        failures.round2.prefix('control', controls), session_id=events[1]['session_id'],
        policy=policy, runtime=runtime)
    failed = project(base, 8)
    assert failed.denial('stage_receipt') is None and failed.denied_ids() == set()
    evidence = failed.settled('stage_receipt')
    assert evidence == base.settled('stage_receipt') and evidence.result.line == 8
    assert failed.transcript.raw == b''.join(rows[:8])
    with pytest.raises(ValueError, match='errored'):
        observed.helper_result(failed, evidence, {})
    refused = project(base, base.results['arbitrary_python'][0])
    assert refused.denial('arbitrary_python') == base.denial('arbitrary_python')
    assert refused.denial('arbitrary_python')['classification'] == 'not_prescribed'


def software_denial_trace(*, refusal):
    _, events, controls, policy, runtime, event, _ = failures.retained_failure()
    events = deepcopy(events[:8])
    denial = {'type': 'system', 'subtype': 'permission_denied', 'tool_name': 'Bash',
        'tool_use_id': 'stage_receipt', 'decision_reason_type': 'rule',
        'decision_reason': 'software projection boundary control',
        'message': 'Permission to use Bash denied.',
        'uuid': '2b318c80-a96c-400a-9386-566b4b70f0fa', 'session_id': event['session_id']}
    if refusal:
        # Software config refusal replaces the retained admitted execution failure.
        result = events[-1]
        result['message']['content'][0]['content'] = denial['message']
        result['tool_use_result'] = 'Error: ' + denial['message']
        result['tool_result_meta'] = [{'id': 'stage_receipt',
            'non_execution_kind': 'permission-rule', 'permission_decision': {
                'decision': 'reject', 'source': 'config', 'reason_type': 'rule'}}]
    events.insert(7, denial)
    parent = [json.loads(row) for row in controls[:4]]
    return failures.mutated_trace(events, parent, policy, runtime)


def test_permission_denials_are_bounded_to_the_projected_physical_prefix(refusal):
    base = software_denial_trace(refusal=refusal)
    before = project(base, 7)
    pending = project(base, 8)
    settled = project(base, cached=True)
    assert before._permission_denials == {}
    assert before.denied_ids() == set() and before.pending() == ('stage_receipt',)
    assert pending._permission_denials == {'stage_receipt': base.frames[8]}
    assert pending._permission_denials['stage_receipt'] is pending.frames[8]
    assert pending.denied_ids() == set() and pending.pending() == ('stage_receipt',)
    assert settled._permission_denials['stage_receipt'] is settled.frames[8]
    if refusal:
        denial = settled.denial('stage_receipt')
        assert denial['classification'] == 'prescribed' and denial['tool'] == 'Bash'
        assert settled.denied_ids() == {'stage_receipt'}
    else:
        with pytest.raises(ValueError, match='conflicts with a permission denial'):
            settled.denial('stage_receipt')
    # A prefix view must not delete future denial evidence from its source.
    assert base._permission_denials == {'stage_receipt': base.frames[8]}


test_permission_denials_are_bounded_to_the_projected_physical_prefix = pytest.mark.parametrize(
    'refusal', [False, True])(
        test_permission_denials_are_bounded_to_the_projected_physical_prefix)


def test_unmodified_full_prefix_reuses_the_existing_trace():
    native, parent, _ = legacy.events('Write')
    base = legacy.trace(native, parent)
    assert project(base) is base
