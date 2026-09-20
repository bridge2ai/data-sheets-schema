"""Real staged history/control replay and descendant evidence, entirely offline."""
import copy
import json
from pathlib import Path
import shlex
import sys
import threading
import time
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import contract, native, output_parts as parts
from audit_controls.test_contract import audit_fixture
from native_control import initialize_frame, digest, hook_output, INIT_ID, CONTRACT
from native_file_policy import FileAccess


@pytest.fixture
def stage(tmp_path):
    m, audit = audit_fixture(tmp_path)
    old = Path(m['job']['attempt_dir'])
    condition = tmp_path / 'condition'; condition.mkdir()
    attempt = condition / 'attempts' / m['job']['id']; attempt.parent.mkdir()
    old.rename(attempt)
    output = attempt / 'output'
    target = output / 'audit.json'; target.unlink()
    instruction = condition / 'instruction.md'; instruction.write_text('Synthetic authoritative task.\n')
    system = condition / 'system.md'; system.write_text('Synthetic system.\n')
    reg = condition / 'registration.json'
    m.update(kind='d4d_native_audit_continuation', python=sys.executable, repository=str(tmp_path),
             model={'model': 'claude-opus-5'}, native_runtime={'version': '2.1.272 (Claude Code)',
             'context_window': 200000, 'max_output_tokens': 64000})
    m['job'].update(attempt_dir=str(attempt), output_dir=str(output), audit_path=str(target),
        instruction=str(instruction), system_prompt=str(system),
        readable_inputs=[*m['inputs'].values(), str(instruction), str(system)],
        validator_argv=[sys.executable, '-m', 'audit_controls.contract', '--registration', str(reg)])
    m['pinned_files'].update({str(p): native.sha(p) for p in (instruction, system)})
    parts.select(m, reg, True)
    (output / 'audit-parts').mkdir()
    reg.write_text(json.dumps(m))
    policy = native.build_policy(m, reg)
    return SimpleNamespace(m=m, audit=audit, reg=reg, identity=native.sha(reg), policy=policy,
                           attempt=attempt, target=target, text=json.dumps(audit, ensure_ascii=False))


class Session:
    def __init__(self, case):
        self.c = case
        self.history = native.make_history(case.m, case.identity, case.policy)
        self.events, self.records = [], []
        self.count = 0
        self.records.append({'kind': 'initialize_sent', 'frame': initialize_frame(), 'policy_sha256': digest(case.policy)})
        ack = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': INIT_ID, 'response': {}}}
        self.records.append({'kind': 'initialize_ack', 'frame': ack})
        self.emit(ack)
        self.emit({'type': 'system', 'subtype': 'init', 'session_id': '11111111-2222-4333-8444-555555555555',
                   'cwd': case.m['repository'], 'model': 'claude-opus-5', 'apiKeySource': 'ANTHROPIC_API_KEY',
                   'claude_code_version': '2.1.272', 'tools': ['Read', 'Write', 'Bash']})

    def emit(self, event):
        self.events.append(event)
        self.history.observe(event)

    def call(self, name, payload):
        self.count += 1
        identity = 'tool-' + str(self.count)
        self.emit({'type': 'assistant', 'session_id': '11111111-2222-4333-8444-555555555555', 'message': {'role': 'assistant',
                   'content': [{'type': 'tool_use', 'id': identity, 'name': name, 'input': payload}]}})
        classification, basis = (native.classify_command(payload['command'], self.c.policy['python'], [], self.c.policy)
            if name == 'Bash' else FileAccess(self.c.policy).classify(name, payload))
        assert classification == 'prescribed'
        callback = {'type': 'control_request', 'request_id': 'callback-' + identity, 'request': {
            'subtype': 'hook_callback', 'callback_id': CONTRACT['callback_id'], 'input': {
                'hook_event_name': 'PreToolUse', 'tool_name': name, 'tool_use_id': identity,
                'cwd': self.c.m['repository'], 'tool_input': payload}}}
        response = {'type': 'control_response', 'response': {'subtype': 'success',
                    'request_id': callback['request_id'], 'response': hook_output(classification, basis)}}
        self.records.append({'kind': 'decision', 'request': callback, 'response': response,
                             'classification': classification, 'basis': basis})
        self.emit(callback)
        return identity

    def result(self, identity, metadata, *, is_error=False):
        self.emit({'type': 'user', 'session_id': '11111111-2222-4333-8444-555555555555', 'tool_use_result': metadata,
            'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': identity,
                'is_error': is_error, 'content': metadata.get('stdout', 'Completed synthetic tool.')}]}})

    def write(self, text):
        path = Path(self.c.m['audit_output']['parts'][len(self.history.part_writes)])
        identity = self.call('Write', {'file_path': str(path), 'content': text})
        path.write_bytes(text.encode())
        self.result(identity, {'type': 'create', 'filePath': str(path), 'content': text})

    def prepare_parts(self):
        midpoint = len(self.c.text) // 2
        self.write(self.c.text[:midpoint]); self.write(self.c.text[midpoint:])

    def assemble(self):
        identity = self.call('Bash', {'command': shlex.join(self.c.m['audit_output']['assemble_argv'])})
        report = parts.assemble(self.c.m, self.c.identity)
        summary = parts.summary(self.c.m, report)
        self.result(identity, {'stdout': json.dumps(summary), 'stderr': '', 'interrupted': False, 'exitCode': 0})

    def validate(self):
        identity = self.call('Bash', {'command': shlex.join(self.c.m['job']['validator_argv'])})
        report = contract.validate_audit(self.c.m)
        assert report['passed'] is True, report
        report['registration_sha256'] = self.c.identity
        (self.c.attempt / 'validation.json').write_text(json.dumps(report))
        self.result(identity, {'stdout': json.dumps(report), 'stderr': '', 'interrupted': False, 'exitCode': 0})

    def finish(self):
        self.emit({'type': 'result', 'is_error': False, 'terminal_reason': 'completed', 'stop_reason': 'end_turn',
                   'permission_denials': [], 'modelUsage': {'claude-opus-5': {'contextWindow': 200000, 'maxOutputTokens': 64000}}})
        control = self.c.attempt / 'control.jsonl'
        control.write_text(''.join(json.dumps(r) + '\n' for r in self.records))
        check = native.check_control_history(self.events, control, self.c.policy, native.classify_command, None)
        assert check['checked'] and not check['problems'], check
        return native.inspect_transcript(self.events, self.c.policy, self.c.m, self.c.identity, control, None)


def test_two_parts_real_validator_and_unmocked_full_control_replay(stage):
    s = Session(stage); s.prepare_parts(); s.assemble(); s.validate()
    result = s.finish()
    assert result['control']['checked'] and result['control']['problems'] == []
    assert result['phase3'] == s.history.finish()
    assert len(result['phase3']['audit_parts']) == 2
    assert 'audit_write' not in result['phase3']
    assert stage.target.read_bytes() == stage.text.encode()
    assert all(event['part']['bytes'] <= 32768 for event in result['phase3']['audit_parts'])


@pytest.mark.parametrize('when', ['before_parts', 'part_pending', 'before_assembly_result', 'after_assembly', 'after_validator'])
def test_out_of_order_or_interleaved_tools_do_not_advance(stage, when):
    s = Session(stage)
    if when == 'before_parts':
        tool, payload = 'Bash', {'command': shlex.join(stage.m['job']['validator_argv'])}
    elif when == 'part_pending':
        s.call('Write', {'file_path': stage.m['audit_output']['parts'][0], 'content': 'first'})
        tool, payload = 'Read', {'file_path': stage.m['job']['instruction']}
    else:
        s.prepare_parts()
        if when == 'before_assembly_result':
            s.call('Bash', {'command': shlex.join(stage.m['audit_output']['assemble_argv'])})
            parts.assemble(stage.m, stage.identity)
            tool, payload = 'Bash', {'command': shlex.join(stage.m['job']['validator_argv'])}
        else:
            s.assemble()
            if when == 'after_validator':
                s.validate()
            tool, payload = 'Read', {'file_path': stage.m['job']['instruction']}
    with pytest.raises(native.BudgetStop):
        s.call(tool, payload)
    assert s.history.problem


def test_registered_reads_between_parts_remain_allowed(stage):
    s = Session(stage)
    s.write(stage.text[:10])
    identity = s.call('Read', {'file_path': stage.m['job']['instruction']})
    s.result(identity, {'type': 'text'})
    s.write(stage.text[10:]); s.assemble(); s.validate()
    assert s.finish()['control']['problems'] == []


@pytest.mark.parametrize('completed_parts', [0, 1])
def test_clean_pending_read_preserves_admission_and_completion(stage, completed_parts):
    s = Session(stage)
    s.history.verify_admission()
    if completed_parts:
        s.write(stage.text[:10])
    identity = s.call('Read', {'file_path': stage.m['job']['instruction']})
    s.history.verify_admission()
    assert identity in s.history.pending
    s.result(identity, {'type': 'text'})
    s.write(stage.text[10:] if completed_parts else stage.text)
    s.assemble(); s.validate()
    assert s.finish()['control']['problems'] == []


def test_pending_read_cannot_hide_changed_completed_part_at_admission(stage):
    s = Session(stage); s.write(stage.text[:10])
    s.call('Read', {'file_path': stage.m['job']['instruction']})
    Path(stage.m['audit_output']['parts'][0]).write_text('changed')
    with pytest.raises(native.BudgetStop, match='differ from completed native Writes'):
        s.history.verify_admission()


@pytest.mark.parametrize('extra', ['000001.txt', '.unobserved'])
@pytest.mark.parametrize('pending_read', [False, True])
def test_initial_roster_rejects_unobserved_part_or_hidden_entry(stage, extra, pending_read):
    s = Session(stage)
    if pending_read:
        s.call('Read', {'file_path': stage.m['job']['instruction']})
    (Path(stage.m['audit_output']['parts'][0]).parent / extra).write_text('unobserved')
    with pytest.raises(native.BudgetStop, match='differ from completed native Writes'):
        s.history.verify_admission()
    assert s.history.part_writes == []


@pytest.mark.parametrize('premature', ['audit', 'receipt', 'ready'])
@pytest.mark.parametrize('completed_parts', [0, 1])
def test_output_before_observed_assembly_blocks_admission(stage, premature, completed_parts):
    s = Session(stage)
    if completed_parts:
        s.write(stage.text[:10])
    path = {'audit': stage.target, 'receipt': parts.receipt_paths(stage.m)[0],
            'ready': parts.ready_path(stage.m)}[premature]
    path.write_text('premature')
    with pytest.raises(native.BudgetStop, match='no successful observed assembly'):
        s.history.verify_admission()


def test_admission_empty_roster_does_not_allow_empty_assembly(stage):
    s = Session(stage)
    s.history.verify_admission()
    with pytest.raises(native.BudgetStop, match='no completed prefix'):
        s.call('Bash', {'command': shlex.join(stage.m['audit_output']['assemble_argv'])})
    assert s.history.assembler is None
    assert not parts.receipt_paths(stage.m)[0].exists()
    assert not stage.target.exists()


@pytest.mark.parametrize('damage', ['part_changed', 'part_alias', 'extra_part', 'final_changed', 'receipt_changed'])
def test_changed_assembly_cannot_admit_another_paid_request(stage, damage):
    s = Session(stage); s.prepare_parts(); s.assemble()
    part = Path(stage.m['audit_output']['parts'][0])
    if damage == 'part_changed':
        part.write_text('changed')
    elif damage == 'part_alias':
        import os
        os.link(part, stage.attempt / 'alias')
    elif damage == 'extra_part':
        (part.parent / '.extra').write_text('extra')
    elif damage == 'final_changed':
        stage.target.write_text('changed')
    else:
        receipt, _ = parts.receipt_paths(stage.m)
        receipt.write_bytes(receipt.read_bytes() + b' ')
    with pytest.raises((native.BudgetStop, OSError)):
        s.history.verify_admission()


@pytest.mark.parametrize('tool', ['part', 'assembly'])
def test_paid_admission_waits_for_real_typed_result_flush(stage, tool):
    s = Session(stage)
    if tool == 'part':
        path = Path(stage.m['audit_output']['parts'][0])
        identity = s.call('Write', {'file_path': str(path), 'content': stage.text})
        path.write_text(stage.text)
        metadata = {'type': 'create', 'filePath': str(path), 'content': stage.text}
    else:
        s.prepare_parts()
        identity = s.call('Bash', {'command': shlex.join(stage.m['audit_output']['assemble_argv'])})
        report = parts.assemble(stage.m, stage.identity)
        metadata = {'stdout': json.dumps(parts.summary(stage.m, report)), 'stderr': '', 'interrupted': False, 'exitCode': 0}
    sent = threading.Event()
    def observe():
        time.sleep(.03); s.result(identity, metadata); sent.set()
    thread = threading.Thread(target=observe); thread.start()
    s.history.verify_admission()
    assert sent.is_set()
    thread.join()


def test_receipt_alone_never_admits_after_missing_assembly_result(stage, monkeypatch):
    s = Session(stage); s.prepare_parts()
    s.call('Bash', {'command': shlex.join(stage.m['audit_output']['assemble_argv'])})
    parts.assemble(stage.m, stage.identity)
    monkeypatch.setattr(native, 'VALIDATOR_RESULT_WAIT_SECONDS', .001)
    with pytest.raises(native.BudgetStop, match='no observed successful typed result'):
        s.history.verify_admission()


def test_part_file_alone_cannot_admit_before_typed_write_result(stage, monkeypatch):
    s = Session(stage)
    path = Path(stage.m['audit_output']['parts'][0])
    s.call('Write', {'file_path': str(path), 'content': stage.text})
    path.write_text(stage.text)
    monkeypatch.setattr(native, 'VALIDATOR_RESULT_WAIT_SECONDS', .001)
    with pytest.raises(native.BudgetStop, match='no observed successful typed result'):
        s.history.verify_admission()


def test_stale_readiness_blocks_admission_and_assembly(stage):
    s = Session(stage); s.prepare_parts()
    parts.ready_path(stage.m).write_text('stale')
    with pytest.raises(native.BudgetStop, match='no successful observed assembly'):
        s.history.verify_admission()
    with pytest.raises(native.BudgetStop, match='stale output or receipts'):
        s.call('Bash', {'command': shlex.join(stage.m['audit_output']['assemble_argv'])})


def test_assembly_typed_stdout_rejects_boolean_numeric_alias(stage):
    s = Session(stage); s.prepare_parts()
    identity = s.call('Bash', {'command': shlex.join(stage.m['audit_output']['assemble_argv'])})
    report = parts.assemble(stage.m, stage.identity)
    summary = parts.summary(stage.m, report); summary['passed'] = 1
    with pytest.raises(native.BudgetStop, match='stdout differs'):
        s.result(identity, {'stdout': json.dumps(summary), 'stderr': '', 'interrupted': False, 'exitCode': 0})


def test_descendant_provenance_is_bound_to_completed_result_before_pinning(stage):
    s = Session(stage); s.prepare_parts(); s.assemble(); s.validate()
    evidence = s.finish()
    result = {'registration_sha256': stage.identity, 'audit_sha256': native.sha(stage.target), 'evidence': evidence}
    expected = {Path(stage.m['audit_output']['parts'][i]) for i in range(2)} | {
        stage.attempt / 'assembly.json', stage.attempt / 'assembly_ready.json'}
    assert parts.closure_paths(stage.m, stage.reg, result) == expected
    receipt = stage.attempt / 'assembly.json'
    receipt.write_bytes(receipt.read_bytes() + b' ')
    with pytest.raises(native.BudgetStop, match='accepted result'):
        parts.closure_paths(stage.m, stage.reg, result)


@pytest.mark.parametrize('damage', [None, 'missing_part_pin', 'changed_part_repinned', 'missing_helper_pin'])
def test_real_shared_sequence_closure_requires_result_bound_staged_provenance(stage, tmp_path, damage):
    import continuation_sequence as sequence
    from test_continuation_sequence import fixture, save
    future, _, _ = fixture(tmp_path / 'lineage')
    predecessor = future['budget_sequence']['predecessor']
    original = sequence.read(predecessor['registration']['path'])
    stage.m.update(parent=original['parent'], budget=original['budget'])
    stage.reg.write_text(json.dumps(stage.m)); stage.identity = native.sha(stage.reg)
    s = Session(stage); s.prepare_parts(); s.assemble(); s.validate()
    evidence = s.finish()
    result = {'scope': 'phase3_audit_only', 'job_id': stage.m['job']['id'],
              'registration_sha256': stage.identity, 'status': 'completed_pending_independent_review',
              'unresolved_requests': [], 'validation': s.history.validation,
              'runtime': {'exit_code': 0, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0},
              'audit_path': str(stage.target), 'audit_sha256': native.sha(stage.target), 'evidence': evidence}
    predecessor['registration'] = {'path': str(stage.reg), 'sha256': stage.identity}
    predecessor['result'] = save(stage.attempt / 'result.json', result)
    ledger = sequence.read(predecessor['ledger']['path']); ledger['manifest_sha256'] = stage.identity
    predecessor['ledger'] = save(Path(predecessor['ledger']['path']), ledger)
    predecessor['acceptance'] = save(Path(predecessor['acceptance']['path']), {
        'verdict': 'accept', 'registration_sha256': stage.identity,
        'result_sha256': predecessor['result']['sha256'], 'ledger_sha256': predecessor['ledger']['sha256'],
        'artifacts': {str(stage.target): native.sha(stage.target)}})
    paths = parts.closure_paths(stage.m, stage.reg, result) | {Path(parts.__file__).resolve(), stage.target}
    future['pinned_files'].update({str(p): native.sha(p) for p in paths})
    future['pinned_files'].update({ref['path']: ref['sha256'] for ref in predecessor.values() if isinstance(ref, dict)})
    part = Path(stage.m['audit_output']['parts'][0])
    if damage == 'missing_part_pin':
        future['pinned_files'].pop(str(part))
    elif damage == 'changed_part_repinned':
        part.write_text('changed despite repinning'); future['pinned_files'][str(part)] = native.sha(part)
    elif damage == 'missing_helper_pin':
        future['pinned_files'].pop(str(Path(parts.__file__).resolve()))
    check = lambda: sequence._closure(future, predecessor, sequence.digest(future['budget_sequence']['origin']))
    if damage is None:
        observed, _, _ = check()
        assert observed == ledger
    else:
        with pytest.raises(native.BudgetStop):
            check()
