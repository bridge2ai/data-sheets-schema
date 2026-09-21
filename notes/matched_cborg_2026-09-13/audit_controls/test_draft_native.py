"""Unmocked typed draft lifecycle and final evidence checks on synthetic inputs."""
import copy
import json
from pathlib import Path
import shlex
import threading
import time

import pytest

from . import contract, draft_output, native
from . import draft_history
from .test_staged_native import stage, Session


@pytest.fixture
def draft(stage):
    c = stage
    old = c.m.pop('audit_output')
    Path(old['parts'][0]).parent.rmdir()
    c.m.update(protocol_version=6, render_version=18,
               scientific_contract_transition={'kind': 'frozen_pair_draft_grammar_v1'})
    source = Path(c.m['inputs']['source_manifest'])
    source.write_text('projects:\n  EXAMPLE:\n    sources:\n      - id: protocol\n'
                      '        processed_file: protocol.txt\n        source_type: documentation\n')
    c.m['pinned_files'][str(source)] = native.sha(source)
    parent = c.reg.parent / 'parent.json'
    parent.write_text(json.dumps({'generation': {'jobs': [{'id': 'EXAMPLE', 'project': 'EXAMPLE',
        'input_identity': {'source_manifest': {'path': str(source), 'sha256': native.sha(source)}}}]}}))
    c.m['parent'] = {'registration': str(parent), 'job_id': 'EXAMPLE'}
    c.m['pinned_files'][str(parent)] = native.sha(parent)
    c.m['audit_drafting'] = draft_output.specification(c.m, c.reg)
    for row in c.m['audit_drafting']['rounds']:
        Path(row['parts'][0]).parent.mkdir(parents=True)
    c.reg.write_text(json.dumps(c.m))
    c.identity = native.sha(c.reg)
    c.policy = native.build_policy(c.m, c.reg)
    return c


class DraftSession(Session):
    def write(self, text):
        row = self.c.m['audit_drafting']['rounds'][self.history.round-1]
        path = Path(row['parts'][len(self.history.part_writes)])
        identity = self.call('Write', {'file_path': str(path), 'content': text})
        path.write_bytes(text.encode())
        self.result(identity, {'type': 'create', 'filePath': str(path), 'content': text})

    def check(self):
        number = self.history.round
        argv = self.c.m['audit_drafting']['rounds'][number-1]['check_argv']
        identity = self.call('Bash', {'command': shlex.join(argv)})
        receipt = draft_output.check_round(self.c.m, self.c.identity, number)
        stdout = draft_output.check_summary(self.c.m, receipt)
        self.result(identity, {'stdout': json.dumps(stdout), 'stderr': '', 'interrupted': False, 'exitCode': 0})
        return receipt

    def seal(self):
        argv = self.c.m['audit_drafting']['seal_argv']
        identity = self.call('Bash', {'command': shlex.join(argv)})
        receipt = draft_output.seal(self.c.m, self.c.identity)
        stdout = draft_output.seal_summary(self.c.m, receipt)
        self.result(identity, {'stdout': json.dumps(stdout), 'stderr': '', 'interrupted': False, 'exitCode': 0})


@pytest.mark.parametrize('correction', [False, True])
def test_complete_typed_drafting_sealing_and_real_source_validator(draft, correction):
    s = DraftSession(draft)
    s.history.verify_admission()
    if correction:
        s.write('{invalid initial JSON')
        failed = s.check()
        assert failed['grammar']['passed'] is False and s.history.round == 2
        s.history.verify_admission()
    s.prepare_parts()
    assert s.check()['grammar']['passed'] is True
    s.history.verify_admission()
    s.seal(); s.validate()
    result = s.finish()
    assert result['control']['checked'] and not result['control']['problems']
    assert result['phase3'] == s.history.finish()
    assert len(result['phase3']['audit_drafts']) == 1 + correction
    assert draft.target.read_bytes() == draft.text.encode()
    assert result['phase3']['audit_seal']['receipt']['round'] == 1 + correction
    if correction:
        first = draft.m['audit_drafting']['rounds'][0]['parts'][0]
        assert Path(first).read_bytes() == b'{invalid initial JSON'


def test_second_grammar_failure_is_terminal_without_sealing(draft):
    s = DraftSession(draft)
    s.write('null'); s.check(); s.write('[]')
    with pytest.raises(native.BudgetStop, match='final registered grammar draft failed'):
        s.check()
    with pytest.raises(native.BudgetStop):
        s.history.verify_admission()
    assert not draft.target.exists() and len(s.history.drafts) == 2


@pytest.mark.parametrize('damage', ['false-quote', 'false-record-hash', 'false-claim-text'])
def test_grammar_pass_does_not_bypass_terminal_scientific_rejection(draft, damage):
    audit = copy.deepcopy(draft.audit)
    if damage == 'false-quote':
        audit['findings'][0]['evidence'][1]['quote'] = 'An invented source quotation.'
    elif damage == 'false-record-hash':
        audit['source_review']['sha256'] = '0' * 64
    else:
        audit['source_review']['values'][0]['claims'][0]['text'] = 'An invented original quotation.'
    s = DraftSession(draft); s.write(json.dumps(audit))
    assert s.check()['grammar']['passed'] is True
    s.seal()
    identity = s.call('Bash', {'command': shlex.join(draft.m['job']['validator_argv'])})
    report = contract.validate_audit(draft.m)
    assert report['passed'] is False
    (draft.attempt / 'validation_failure.json').write_text(json.dumps(report))
    with pytest.raises(native.BudgetStop):
        s.result(identity, {'stdout': json.dumps(report), 'stderr': '', 'interrupted': False, 'exitCode': 1}, is_error=True)
    with pytest.raises(native.BudgetStop):
        s.history.verify_admission()
    assert draft.target.read_bytes() == json.dumps(audit).encode()


@pytest.mark.parametrize('when', ['no-parts-check', 'early-round2', 'early-seal', 'early-validator',
    'write-pending', 'grammar-passed-write', 'grammar-passed-read', 'after-seal-write', 'after-validator'])
def test_illegal_tool_order_cannot_advance(draft, when):
    s = DraftSession(draft)
    block = draft.m['audit_drafting']
    tool, payload = 'Bash', {'command': shlex.join(block['rounds'][0]['check_argv'])}
    if when == 'early-round2':
        payload['command'] = shlex.join(block['rounds'][1]['check_argv'])
    elif when == 'early-seal':
        payload['command'] = shlex.join(block['seal_argv'])
    elif when == 'early-validator':
        payload['command'] = shlex.join(draft.m['job']['validator_argv'])
    elif when == 'write-pending':
        s.call('Write', {'file_path': block['rounds'][0]['parts'][0], 'content': draft.text})
        tool, payload = 'Read', {'file_path': draft.m['job']['instruction']}
    elif when.startswith('grammar-passed') or when in {'after-seal-write', 'after-validator'}:
        s.prepare_parts(); s.check()
        if when in {'after-seal-write', 'after-validator'}:
            s.seal()
        if when == 'after-validator':
            s.validate()
        tool, payload = ('Read', {'file_path': draft.m['job']['instruction']}) if when == 'grammar-passed-read' else (
            'Write', {'file_path': block['rounds'][1]['parts'][0], 'content': draft.text})
    with pytest.raises(native.BudgetStop):
        s.call(tool, payload)
    assert s.history.problem


@pytest.mark.parametrize('helper', ['grammar', 'seal'])
def test_unobserved_typed_helper_result_never_admits_spending(draft, monkeypatch, helper):
    s = DraftSession(draft); s.prepare_parts()
    if helper == 'grammar':
        argv = draft.m['audit_drafting']['rounds'][0]['check_argv']
        s.call('Bash', {'command': shlex.join(argv)})
        draft_output.check_round(draft.m, draft.identity, 1)
    else:
        s.check()
        s.call('Bash', {'command': shlex.join(draft.m['audit_drafting']['seal_argv'])})
        draft_output.seal(draft.m, draft.identity)
    monkeypatch.setattr(draft_history, 'VALIDATOR_RESULT_WAIT_SECONDS', .001)
    with pytest.raises(native.BudgetStop, match='no observed typed result'):
        s.history.verify_admission()


@pytest.mark.parametrize('damage', ['stdout', 'is_error', 'interrupted', 'exit_bool', 'stderr_missing'])
def test_grammar_result_requires_exact_successful_execution_metadata(draft, damage):
    s = DraftSession(draft); s.prepare_parts()
    identity = s.call('Bash', {'command': shlex.join(draft.m['audit_drafting']['rounds'][0]['check_argv'])})
    receipt = draft_output.check_round(draft.m, draft.identity, 1)
    meta = {'stdout': json.dumps(draft_output.check_summary(draft.m, receipt)), 'stderr': '', 'interrupted': False, 'exitCode': 0}
    if damage == 'stdout': meta['stdout'] = '{}'
    if damage == 'interrupted': meta['interrupted'] = True
    if damage == 'exit_bool': meta['exitCode'] = False
    if damage == 'stderr_missing': del meta['stderr']
    with pytest.raises(native.BudgetStop):
        s.result(identity, meta, is_error=(damage == 'is_error'))
    assert s.history.drafts == []


def test_completed_first_draft_cannot_change_during_second_draft(draft):
    s = DraftSession(draft); s.write('null'); s.check(); s.write(draft.text)
    first = Path(draft.m['audit_drafting']['rounds'][0]['parts'][0])
    first.write_text('true')
    with pytest.raises((native.BudgetStop, ValueError, OSError)):
        s.history.verify_admission()


def test_grammar_result_flush_race_waits_for_actual_observation(draft):
    s = DraftSession(draft); s.prepare_parts()
    identity = s.call('Bash', {'command': shlex.join(draft.m['audit_drafting']['rounds'][0]['check_argv'])})
    receipt = draft_output.check_round(draft.m, draft.identity, 1)
    metadata = {'stdout': json.dumps(draft_output.check_summary(draft.m, receipt)), 'stderr': '', 'interrupted': False, 'exitCode': 0}
    sent = threading.Event()
    def flush():
        time.sleep(.03); s.result(identity, metadata); sent.set()
    thread = threading.Thread(target=flush); thread.start()
    s.history.verify_admission()
    thread.join()
    assert sent.is_set() and len(s.history.drafts) == 1
