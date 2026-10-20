"""Actual receipt7 subprocess in a disclosed partial ordinary-peer trajectory.

Four granted Bash prerequisites have synthetic settlements; two granted Writes
are real. The receipt CLI is actually launched with its registered argv/env and
must finish under the original owner. No final-stage/provider acceptance follows.
"""
import json
import os
from pathlib import Path
import sys

import pytest

from data_sheets_schema import native_owner_profile_v1 as profile
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_observations as observed
from data_sheets_schema import native_shared_receipts as native_receipts
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_stream_coordination_v1 as coordination
from data_sheets_schema import receipts
from tests.test_native_owner_stage_helper import (
    stage_helper_factory, FULL_RAW, SESSION, TERMINAL_REFUSAL)


def _selection_bytes(case):
    selection = case['selection']
    artifacts = (selection.registration, *selection.authority, selection.receipt_policy,
                 *(source for closure in selection.schemas for source in closure.sources))
    expected = {}
    for artifact in artifacts:
        path = Path(artifact.pin.path)
        assert path.read_bytes() == artifact.raw
        assert c.sha(artifact.raw) == artifact.pin.sha256
        if path in expected:
            assert expected[path] == artifact.raw
        expected[path] = artifact.raw
    for path in (case['peer'], case['instruction'], case['root'] / 'runtime.json',
                 case['root'] / 'composition.json', case['root'] / 'system.txt',
                 case['root'] / 'fabricated-permission.json',
                 case['attempt'] / 'registration.json', case['attempt'] / 'started.json'):
        expected[path] = path.read_bytes()
    return expected


def _prefix(case, role):
    path = case['attempt'] / (role + '.jsonl')
    raw = path.read_bytes()
    assert raw and raw.endswith(b'\n')
    return c.EvidencePrefix(role, str(path), raw, len(raw), c.sha(raw), raw.count(b'\n'))


def test_registered_receipt_process_reads_current_inputs_with_real_clock(stage_helper_factory):
    session = stage_helper_factory(helper_role='phase1_receipts')
    case = session.case
    assert case['helper_role'] == 'phase1_receipts' and case['mode'] == 'subprocess'
    assert profile._ACTIVE.get() is None and coordination.current_reader_budget() is None
    assert case['helper_command'] == case['composition']['policy']['native_shared_helpers']['phase1_receipts']
    assert case['helper_argv'][:3] == (case['composition']['policy']['python'], '-m', 'data_sheets_schema.cli')
    assert '--write' not in case['helper_argv'] and case['helper_argv'][-1] == '--strict'
    assert case['execution']['runtime']['deadline_seconds'] == 60
    with pytest.raises(ValueError):
        registration.verified(case['execution_raw'])
    original_inputs = _selection_bytes(case)
    expected = native_receipts.check_initial(case['selection'], full_raw=FULL_RAW,
                                             receipt_raw=case['receipt_raw'])
    assert expected['passed'] is True and expected['final_stage_complete'] is False
    assert expected['coverage_floor']['state'] == 'pending'
    assert session.dispatches == 0 and case['owner_raw_for_timing'] is None
    session.start().wait_finished()
    # The owner has finished even when it retained a primary operation error.
    # Preserve input bytes before checking that outcome; this never dispatches
    # a fallback or second attempt, and all failure artifacts remain in place.
    assert {path: path.read_bytes() for path in original_inputs} == original_inputs
    assert not session.owner_thread.is_alive()
    # A child success followed by an owner timeout is only a partial milestone.
    # This obligation additionally needs the actual receipt settlement, parent
    # seal and expected incomplete-terminal refusal under this same deadline.
    assert isinstance(session.error, case['controls']['budgeted_cborg'].BudgetStop)
    assert TERMINAL_REFUSAL in str(session.error)
    assert session.dispatches == 1 and session.report['state'] == 'failed'
    assert session.diagnostic_error is None
    diagnostic_raw = (session.root / 'owner-runner-report.json').read_bytes()
    assert len(diagnostic_raw) <= 128 * 1024
    diagnostic = c.strict_json(diagnostic_raw)
    assert diagnostic['report_available'] is True
    assert diagnostic['runner_report'] == session.report

    result = c.strict_json((session.root / 'helper-result.json').read_bytes())
    stdout = (session.root / 'helper-stdout.bin').read_bytes()
    stderr = (session.root / 'helper-stderr.bin').read_bytes()
    assert result['returncode'] == 0 and result['pid'] != os.getpid()
    assert result['argv'] == list(case['helper_argv']) and result['cwd'] == case['cwd']
    assert result['environment_sha256'] == c.sha(json.dumps(case['environment'], sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode())
    assert result['stdout_bytes'] == len(stdout) and result['stdout_sha256'] == c.sha(stdout)
    assert result['stderr_bytes'] == len(stderr) and result['stderr_sha256'] == c.sha(stderr)
    assert stderr == b''
    text = stdout.decode('utf-8')
    assert expected['summary'] in text and 'unchecked:' not in text
    floor = expected['coverage_floor']
    assert (f"registered receipt coverage: pending ({floor['with_receipt']}/{floor['receiptable']}); "
            f"registration {floor['registration_sha256']}") in text

    pending = c.strict_json((session.root / 'pending-receipt.json').read_bytes())
    assert pending == {'tool_use_id':'stage-fixture-7', 'argv':list(case['helper_argv']),
        'command':case['helper_command'], 'cwd':case['cwd'],
        'execution_sha256':c.sha(case['execution_raw'])}
    advance_marker = session.root / 'pending-advance.json'
    assert not advance_marker.exists() and not advance_marker.is_symlink()
    before = c.strict_json((session.root / 'receipt-readonly-before.json').read_bytes())
    after = c.strict_json((session.root / 'receipt-readonly-after.json').read_bytes())
    assert before == after
    paths = case['spec']._agentic_artifact_paths
    for role, raw in (('full', FULL_RAW), ('receipt', case['receipt_raw'])):
        assert before['files'][role] == {'path':paths[role], 'bytes':len(raw), 'sha256':c.sha(raw)}
        assert Path(paths[role]).read_bytes() == raw
    # The child did not publish a phase seal or journal transition. The actual
    # adapter later creates its seal only after consuming the receipt result.
    assert all(row['exists'] is False and row['is_symlink'] is False
               for row in before['forbidden'].values())
    for path in (Path(case['composition']['policy']['post_final_recorder']['destination']),
                 receipts.claims_path(Path(paths['core']).parent, case['spec'].project)):
        assert not path.exists() and not path.is_symlink()

    transcript, control = _prefix(case, 'transcript'), _prefix(case, 'control')
    trace = observed.Trace(transcript, control, session_id=SESSION,
        policy=case['composition']['policy'], runtime=case['execution']['runtime'])
    assert len(trace.calls) == len(trace.results) == 7 and trace.pending() == ()
    settled = trace.settled('stage-fixture-7')
    assert settled.call.tool_name == 'Bash'
    assert c.strict_json(settled.call.input_json) == {'command':case['helper_command']}
    line, _, block = trace.results['stage-fixture-7']
    assert block['content'] == text and block['is_error'] is False
    assert trace.frames[line]['tool_use_result'] == {'stdout':text, 'stderr':'', 'exitCode':0}
    assert trace.terminal is not None and trace.terminal > line
    for number, name in ((1,'chunk_check'), (2,'source_scope'), (5,'full_schema'), (6,'full_terms')):
        identity = 'stage-fixture-' + str(number)
        assert c.strict_json(trace.settled(identity).call.input_json) == {
            'command':case['composition']['policy']['native_shared_helpers'][name]}
        assert trace.results[identity][2]['content'] == (
            'Explicit synthetic prerequisite settlement; helper not executed.')
    assert all(trace.settled('stage-fixture-' + str(n)).call.tool_name == 'Write' for n in (3,4))

    journal_raw = Path(case['selection'].role('journal')).read_bytes()
    journal = c.strict_json(journal_raw)
    records = [c.strict_json(Path(row['path']).read_bytes()) for row in journal['records']]
    assert [row['record_type'] for row in records] == ['genesis','session_bound','phase1_sealed']
    assert before['files']['journal']['sha256'] != c.sha(journal_raw)
    observations = [c.strict_json(path.read_bytes()) for path in sorted(
        Path(case['selection'].role('observations_root')).glob('*.json'))]
    assert [(row['observation_type'],row['version']) for row in observations] == [
        ('initialized',2), ('phase1_sealed',1)]
    assert Path(case['selection'].role('phase1_full')).read_bytes() == FULL_RAW
    assert Path(case['selection'].role('phase1_receipt')).read_bytes() == case['receipt_raw']
    for role in ('phase1_core','core_seal','completion','effective_receipt'):
        path = Path(case['selection'].role(role))
        assert not path.exists() and not path.is_symlink()
    assert case['adapter']._initialized and not case['parent_scope'].live
    assert (session.root / 'received-instruction.bin').read_bytes() == original_inputs[case['instruction']]

    owner_raw = case['owner_raw_for_timing']
    assert type(owner_raw) is bytes and (case['attempt'] / 'stream-owner.json').read_bytes() == owner_raw
    owner = c.strict_json(owner_raw)
    assert owner['duration_ns'] == 60_000_000_000
    assert owner['deadline_ns'] - owner['start_ns'] == owner['duration_ns']
    assert owner['clock'] == 'monotonic_ns' and owner['clock_domain']['platform'] == sys.platform
    assert owner['execution_sha256'] == c.sha(case['execution_raw'])
    assert owner['started_sha256'] == c.sha(case['started_raw'])
    assert diagnostic['owner_sha256'] == c.sha(owner_raw)
    assert c.strict_json((case['attempt'] / 'stream-owner-stop.json').read_bytes()) == {
        'format':'native_stream_owner_stop_v1', 'owner_sha256':c.sha(owner_raw)}
    assert session.report['owner_published'] is True and session.report['stop_marker_published'] is True
    contract = case['controls']['native_control'].HISTORY_CONTRACT
    assert contract['callback_timeout_seconds'] == 2 and contract['observer_timeout_seconds'] == 120
    assert contract['runtime_callback_timeout_seconds'] == 125
