"""U3C-R2-3: saved/live advance acknowledgements rederive the same effects.

These synthetic captured streams exercise real typed stages, Trace joins and
the capture reader. They do not claim native execution admission or a complete
phase/helper/record lifetime. No successful production verdict is mocked.
"""
from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from data_sheets_schema import native_shared_capture as capture
from data_sheets_schema import native_shared_capture_orchestration as capture_orchestration
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_observations as observed
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_shared_streams as streams
from tests.native_shared_captured_fixture import _pool, _prefix, v2_case
from tests.test_native_shared_observations import POLICY, events, initial
from tests.test_native_shared_stages import case, artifact, append, publish
from tests.test_typed_audit import supplied


COMMAND = '/neutral/python -m data_sheets_schema.native_shared_stage advance --registration /neutral/selection.json'


def _member(item, ordinal):
    return evidence.PoolMember(item, c.canonical({
        'exists': True, 'regular': True, 'symlink': False, 'links': 1,
        'device': 0, 'inode': ordinal, 'size': item.pin.bytes, 'mtime_ns': 0}))


@pytest.fixture
def advance(case):
    selection, execution, phase1, history = v2_case(case)
    policy = deepcopy(POLICY)
    policy['native_shared_helpers'] = {'advance': COMMAND}
    native, parent, runtime = initial()
    parent[0]['policy_sha256'] = c.sha(json.dumps(policy, sort_keys=True, separators=(',', ':')).encode())
    transcript, control = _prefix('transcript', native), _prefix('control', parent)
    initial_pool = _pool(execution, transcript, control)
    session, sent, ack, initialized = observed.initialization(
        transcript, control, policy=policy, runtime=runtime)
    init = artifact('observation', selection.role('observations_root') + '/000000.json',
        capture.observation_bytes('initialized', selection, execution.execution.pin.sha256,
            execution.attempt_id, session, transcript, control,
            {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack),
             'native_init': asdict(initialized), 'stream_files': streams.stream_files(initial_pool.members)}))
    execution = replace(execution, init_observation=init)
    seal = artifact('phase1_seal', phase1.seal.pin.path, c.canonical({
        'kind': 'd4d_native_shared_phase1_seal', 'version': 1,
        'selection_sha256': selection.registration.pin.sha256,
        'execution_sha256': execution.execution.pin.sha256, 'session_id': session,
        'full': c.pin_dict(phase1.full.pin), 'original_receipt': c.pin_dict(phase1.original_receipt.pin),
        'observation': c.pin_dict(phase1.full_seal_observation.pin)}))
    phase1 = replace(phase1, seal=seal)
    rows = [c.strict_json(item.raw) for item in history.records]
    rows[1]['payload']['init_observation'] = c.pin_dict(init.pin)
    rows[2]['payload']['seal'] = c.pin_dict(seal.pin)
    empty = replace(history, records=(), journal=artifact('journal', history.journal.pin.path,
        stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
            execution_sha256=execution.execution.pin.sha256, attempt_id=execution.attempt_id, records=())))
    records, journal = stage.append_records(selection, execution, empty,
        tuple((row['record_type'], c.canonical(row['payload'])) for row in rows))
    before = append(empty, records, journal)
    proposal = stage.prepare_next(selection, execution, phase1, before)
    assert proposal.state == 'request_ready'
    after = publish(before, proposal)
    state = stage.prepare_next(selection, execution, phase1, after).state
    assert state == 'awaiting_response'
    result = {'kind': c.KINDS['advance_result'], 'version': 1,
        'selection_sha256': selection.registration.pin.sha256,
        'execution_sha256': execution.execution.pin.sha256,
        'attempt_id': execution.attempt_id, 'session_id': session,
        'advance_tool_use_id': 'tool-1', 'before_history_sha256': before.journal.pin.sha256,
        'after_history_sha256': after.journal.pin.sha256, 'state': state,
        'publications': [c.pin_dict(item.artifact.pin) for item in proposal.publications]}
    return selection, execution, phase1, before, after, init, policy, native, parent, runtime, result


def captured_run(advance, change=None, *, saved=True):
    selection, execution, phase1, before, after, init, policy, native, parent, runtime, expected = advance
    result = deepcopy(expected)
    if change in ('kind', 'attempt_id', 'session_id', 'advance_tool_use_id'):
        result[change] = 'foreign'
    elif change == 'version':
        result[change] = True
    elif change in ('selection_sha256', 'execution_sha256'):
        result[change] = 'f' * 64
    elif change == 'before_history_sha256':
        result[change] = after.journal.pin.sha256  # Another real existing prefix.
    elif change == 'after_history_sha256':
        result[change] = before.journal.pin.sha256
    elif change == 'state':
        result[change] = 'assembly_complete'
    elif change == 'missing_publication':
        result['publications'].pop(0)
    elif change == 'duplicate_publication':
        result['publications'].insert(0, result['publications'][0])
    elif change == 'extra_key':
        result['claimed_verified'] = True
    elif change is not None:
        raise AssertionError(change)

    calls, decisions, _ = events()
    calls[0]['message']['content'][0].update(name='Bash', input={'command': COMMAND})
    calls[1]['request']['input'].update(tool_name='Bash', tool_input={'command': COMMAND})
    decisions[0]['request'] = deepcopy(calls[1])
    # Both channels agree with the forged inner acknowledgement. All raw event,
    # prefix, outer observation and pool hashes below are then rebuilt normally.
    text = c.canonical(result).decode('utf-8')
    calls[-1]['message']['content'][0]['content'] = text
    calls[-1]['tool_use_result'] = {'stdout': text, 'stderr': '', 'exitCode': 0}
    admitted_transcript = _prefix('transcript', native + calls[:2])
    transcript = _prefix('transcript', native + calls)
    control = _prefix('control', parent + decisions)
    trace = observed.Trace(transcript, control, session_id=execution.session_id,
        policy=policy, runtime=runtime)
    settled = trace.settled('tool-1')
    admitted = observed.Trace(admitted_transcript, control, session_id=execution.session_id,
        policy=policy, runtime=runtime).current_advance('tool-1', COMMAND)
    admission = artifact('observation', selection.role('observations_root') + '/000002.json',
        capture.observation_bytes('advance_admitted', selection, execution.execution.pin.sha256,
            execution.attempt_id, execution.session_id, admitted_transcript, control,
            {'call': capture.call_document(admitted), 'before_history_sha256': before.journal.pin.sha256}))
    acknowledgement = artifact('observation', selection.role('observations_root') + '/000003.json',
        capture.observation_bytes('advance_settled', selection, execution.execution.pin.sha256,
            execution.attempt_id, execution.session_id, transcript, control,
            {'call': capture.call_document(settled.call), 'result': asdict(settled.result),
             'result_event': asdict(settled.result_event), 'advance_result': result}))
    observations = (init, admission, acknowledgement) if saved else (init, admission)
    pool = _pool(execution, transcript, control)
    artifacts = (execution.execution, execution.started, execution.binding_artifact,
        phase1.full, phase1.original_receipt, phase1.seal, phase1.full_seal_observation,
        after.journal, *after.records, *after.artifacts, *observations)
    # Keep the actual captured pool strict; repeated references do not create
    # ambiguous competing versions of a role/path.
    unique = {(item.pin.role, item.pin.path): item for item in artifacts}
    pool = evidence.CapturePool(pool.members + tuple(_member(item, i + 10)
        for i, item in enumerate(unique.values())), pool.stream_bindings)
    reader = capture._Reader(selection, pool=pool)
    run = capture._CapturedRun(selection, {'runtime': runtime}, {'policy': policy}, None,
        reader, pool, transcript, control, execution, after, observations, phase1)
    return run, result


def test_saved_advance_reconstructs_real_publications_and_accepts_valid_control(advance):
    run, result = captured_run(advance)
    checked = capture._checked_observations(run)
    assert len(checked) == 3
    assert checked[-1][1]['payload']['advance_result'] == result
    assert result['state'] == 'awaiting_response'
    assert {row['role'] for row in result['publications']} == {'request', 'record', 'journal'}


CASES = [
    *[(name, 'acknowledgement identity differs') for name in
      ('kind', 'version', 'selection_sha256', 'execution_sha256', 'attempt_id',
       'session_id', 'advance_tool_use_id', 'before_history_sha256')],
    ('after_history_sha256', 'reconstructed resulting journal'),
    ('state', 'reconstructed resulting state'),
    ('missing_publication', 'every freshly derived actual effect'),
    ('duplicate_publication', 'every freshly derived actual effect'),
    ('extra_key', 'advance acknowledgement'),
]


@pytest.mark.parametrize('change,message', CASES)
@pytest.mark.parametrize('saved', [True, False], ids=['saved', 'live'])
def test_rehashed_foreign_advance_result_refuses_before_publication(advance, change, message, saved):
    run, result = captured_run(advance, change, saved=saved)
    # The raw join alone passes, so the assertion reaches semantic validation.
    trace = run.trace()
    observed.helper_result(trace, trace.settled('tool-1'), result)
    with pytest.raises(ValueError, match=message):
        if saved:
            capture._checked_observations(run)
        else:
            capture_orchestration.observe_advance_settled(run, 'tool-1')


def test_saved_advance_settlement_cannot_be_repeated(advance):
    run, _ = captured_run(advance)
    previous = run.observations[-1]
    duplicate = artifact('observation', run.selection.role('observations_root') + '/000004.json', previous.raw)
    run.observations += (duplicate,)
    with pytest.raises(ValueError, match='earlier selected admission'):
        capture._checked_observations(run)
