"""Pure synthetic event ordering; no native process or permission claim."""
import json
import shlex

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema.native_shared_phase import COMMAND_NAMES, PhaseState


def artifact(role):
    raw = b'neutral observed artifact'
    return c.CapturedArtifact(c.ArtifactPin(role, '/neutral/' + role, len(raw), c.sha(raw)), raw)


def decision(state='await_core', number=1):
    history = c.sha(str(number).encode())
    completion = None
    if state == 'assembly_complete':
        completion = c.StageCompletion(assembly=artifact('typed_assembly'), audit=artifact('audit'),
            packet=artifact('packet'), effective_receipt=artifact('effective_receipt'),
            receipt_carry=artifact('receipt_carry'), receipt_result=artifact('receipt_result'),
            typed_index=artifact('typed_index'), counts_json=b'{}', stage_origins_json=b'{}',
            selection_sha256='a' * 64, execution_sha256='b' * 64, attempt_id='attempt',
            session_id='session', history_sha256=history, core_seal_sha256='c' * 64,
            phase1_seal_sha256='d' * 64)
    return c.StageDecision(completion=completion, cursor=None, failure_json=None,
        history_sha256=history, publications=(), request=None, response=None,
        request_predecessor_history_sha256=None, sealed=(), state=state)


class Trace:
    def __init__(self):
        self.commands = {name: ('/neutral/python', '-m', 'neutral.helper', name) for name in COMMAND_NAMES}
        self.state = PhaseState(self.commands, full_path='/neutral/full', core_path='/neutral/core',
            receipt_path='/neutral/receipt', report_path='/neutral/report', working_directory='/neutral')
        self.state.observe({'type': 'system', 'subtype': 'init', 'session_id': 'session'})
        self.current = None
        self.number = 0
        self.events = []

    def call(self, name, inputs):
        self.number += 1
        identity = 'call-' + str(self.number)
        self.state.before(name, inputs, stage_decision=self.current)
        event = {'type': 'assistant', 'session_id': 'session', 'message': {'content': [
            {'type': 'tool_use', 'id': identity, 'name': name, 'input': inputs}]}}
        self.events.append((event, self.current))
        self.state.observe(event, stage_decision=self.current)
        return identity

    def result(self, identity, *, code=0, text='', bash=True, mutation=None, after=None):
        event = {'type': 'user', 'session_id': 'session', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': identity, 'is_error': bool(code), 'content': text}]}}
        if bash:
            event['tool_use_result'] = {'exitCode': code, 'stdout': text}
        if mutation:
            mutation(event)
        if after is not None:
            self.current = after
        self.events.append((event, self.current))
        return self.state.observe(event, stage_decision=self.current)

    def helper(self, name, *, code=0, value=None, after=None, mutation=None):
        before = self.current
        identity = self.call('Bash', {'command': shlex.join(self.commands[name])})
        if value is None and name.endswith('source_inventory'):
            value = {'artifact': 'original_full' if name.startswith('original') else 'final_full',
                     'sha256': 'e' * 64, 'values': []}
        elif value is None and name in ('audit_evidence', 'final_evidence'):
            value = {'checked': True, 'findings': [] if not code else [{'message': 'unfounded'}]}
        elif value is None and name == 'draft':
            value = {'checked': True, 'passed': not code, 'protocol_version': 7}
        elif value is None and name == 'advance':
            after = after or decision(number=self.number)
            value = {'kind': c.KINDS['advance_result'], 'version': 1,
                'selection_sha256': 'a' * 64, 'execution_sha256': 'b' * 64,
                'attempt_id': 'attempt', 'session_id': 'session', 'advance_tool_use_id': identity,
                'before_history_sha256': before.history_sha256,
                'after_history_sha256': after.history_sha256, 'state': after.state, 'publications': []}
        return self.result(identity, code=code, text=json.dumps(value) if value is not None else 'checked',
                           after=after, mutation=mutation)

    def write(self, role, *, path=None, code=0):
        identity = self.call('Write', {'file_path': path or '/neutral/' + role, 'content': 'neutral'})
        return self.result(identity, code=code, bash=False)

    def initial(self):
        self.helper('chunk_check'); self.helper('source_scope')
        self.write('full'); self.write('receipt')
        self.helper('full_schema'); self.helper('full_terms')
        assert self.helper('phase1_receipts') == ('seal_phase1',)
        self.current = decision()

    def core(self):
        self.helper('advance', after=decision(number=2))
        self.helper('derive_core'); self.helper('core_schema')
        assert self.helper('pair') == ('seal_core',)
        self.helper('original_source_inventory')

    def assembly(self):
        self.initial(); self.core()
        self.helper('advance', after=decision('assembly_complete', 3))
        self.helper('audit_evidence')

    def final_checks(self):
        self.helper('derive_final_core')
        self.helper('full_schema'); self.helper('full_terms')
        self.helper('core_schema'); self.helper('pair')
        self.helper('phase1_receipts'); self.helper('final_scope')

    def finish(self):
        self.helper('final_source_inventory'); self.write('report')
        self.helper('draft'); self.helper('final_evidence'); self.helper('recorder')
        event = {'type': 'result', 'session_id': 'session'}
        self.events.append((event, self.current))
        self.state.observe(event, stage_decision=self.current)


def test_complete_ordered_chain_and_detached_replay():
    trace = Trace()
    trace.assembly(); trace.write('full'); trace.final_checks(); trace.finish()
    report = trace.state.report(complete=True)
    assert report['passed'] and not report['problems'] and report['assembly_complete']
    clone = Trace()
    for event, current in trace.events:
        clone.state.observe(event, stage_decision=current)
    assert clone.state.report(complete=True) == report
    report['checks'].clear()
    assert trace.state.report()['checks']


def test_initial_correction_and_failed_draft_can_be_repaired():
    trace = Trace()
    trace.helper('chunk_check'); trace.helper('source_scope')
    trace.write('full'); trace.write('receipt')
    trace.helper('full_schema', code=1)
    with pytest.raises(ValueError, match='current full validation'):
        trace.helper('phase1_receipts')
    trace.write('full'); trace.helper('full_schema'); trace.helper('full_terms')
    assert trace.helper('phase1_receipts', code=1) == ()
    trace.write('receipt')
    assert trace.helper('phase1_receipts') == ('seal_phase1',)
    trace.current = decision(); trace.core()
    trace.helper('advance', after=decision('assembly_complete', 3)); trace.helper('audit_evidence')
    trace.final_checks(); trace.helper('final_source_inventory'); trace.write('report')
    trace.helper('draft', code=1)
    with pytest.raises(ValueError, match='passing draft'):
        trace.helper('final_evidence')
    with pytest.raises(ValueError, match='new settled final source inventory'):
        trace.write('report')
    trace.helper('final_source_inventory'); trace.write('report')
    trace.helper('draft'); trace.helper('final_evidence'); trace.helper('recorder')
    trace.state.observe({'type': 'result', 'session_id': 'session'})
    assert trace.state.report(complete=True)['passed']


@pytest.mark.parametrize('role', ['full', 'receipt', 'core'])
def test_sealed_original_and_direct_core_mutations_refuse(role):
    trace = Trace(); trace.initial()
    with pytest.raises(ValueError, match='sealed original|deterministic derive'):
        trace.write(role, path='./folder/../' + role)


@pytest.mark.parametrize('helper', ['derive_core', 'advance', 'original_source_inventory', 'audit_evidence',
                                   'draft', 'final_evidence', 'derive_final_core', 'recorder'])
def test_early_helpers_cannot_satisfy_future_boundaries(helper):
    trace = Trace()
    with pytest.raises(ValueError):
        trace.helper(helper)
    assert not trace.state.report(complete=True)['passed']


def test_core_pair_required_before_original_inventory_and_unsettled_result_does_not_count():
    trace = Trace(); trace.initial(); trace.helper('advance', after=decision(number=2)); trace.helper('derive_core')
    with pytest.raises(ValueError, match='sealed original pair'):
        trace.helper('original_source_inventory')
    identity = trace.call('Bash', {'command': shlex.join(trace.commands['core_schema'])})
    with pytest.raises(ValueError, match='overlaps an unsettled'):
        trace.state.observe({'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'name': 'Bash', 'id': 'overlap',
             'input': {'command': shlex.join(trace.commands['pair'])}}]}}, stage_decision=trace.current)
    assert not trace.state.report()['passed']
    assert identity in trace.state.report()['pending_tool_ids']


@pytest.mark.parametrize('change', ['missing', 'boolean', 'float', 'contradictory', 'error', 'stdout', 'background'])
def test_result_metadata_cannot_fabricate_a_pass(change):
    trace = Trace()
    def mutation(event):
        meta = event['tool_use_result']
        if change == 'missing': del meta['exitCode']
        elif change == 'boolean': meta['exitCode'] = False
        elif change == 'float': meta['exitCode'] = 0.0
        elif change == 'contradictory': meta['exit_code'] = 1
        elif change == 'error': event['message']['content'][0]['is_error'] = True
        elif change == 'stdout': meta['stdout'] = 'foreign'
        else: meta['backgroundTaskId'] = 'pending'
    with pytest.raises(ValueError):
        trace.helper('chunk_check', mutation=mutation)
    assert not trace.state.report()['passed']
    assert 'chunk_check' not in trace.state.report()['current_checks']


@pytest.mark.parametrize('helper', ['original_source_inventory', 'audit_evidence', 'final_evidence'])
def test_source_and_evidence_failures_are_terminal(helper):
    trace = Trace(); trace.initial(); trace.core()
    if helper != 'original_source_inventory':
        trace.helper('advance', after=decision('assembly_complete', 3))
    if helper == 'final_evidence':
        trace.helper('audit_evidence'); trace.final_checks()
        trace.helper('final_source_inventory'); trace.write('report'); trace.helper('draft')
    with pytest.raises(ValueError, match='terminal source'):
        trace.helper(helper, code=1)
    with pytest.raises(ValueError, match='already failed'):
        trace.write('full')
    assert trace.state.report()['terminal_failures']


@pytest.mark.parametrize('change', ['session', 'call', 'predecessor', 'state', 'history', 'execution', 'version'])
def test_advance_requires_exact_observed_call_and_fresh_post_publication_state(change):
    trace = Trace(); trace.initial(); trace.helper('advance', after=decision(number=2))
    def mutation(event):
        value = json.loads(event['tool_use_result']['stdout'])
        key, replacement = {
            'session': ('session_id', 'foreign'), 'call': ('advance_tool_use_id', 'foreign'),
            'predecessor': ('before_history_sha256', 'f' * 64), 'state': ('state', 'assembly_complete'),
            'history': ('after_history_sha256', 'f' * 64), 'execution': ('execution_sha256', 'f' * 64),
            'version': ('version', True)}[change]
        value[key] = replacement
        event['tool_use_result']['stdout'] = event['message']['content'][0]['content'] = json.dumps(value)
    with pytest.raises(ValueError):
        trace.helper('advance', after=decision(number=4), mutation=mutation)
    assert not trace.state.report()['assembly_complete']


def test_stored_complete_decision_without_actual_helper_result_does_not_complete():
    trace = Trace(); trace.initial(); trace.core()
    trace.current = decision('assembly_complete', 3)
    with pytest.raises(ValueError, match='observed assembly'):
        trace.helper('audit_evidence')
    assert not trace.state.report()['assembly_complete']


def test_current_full_and_report_epochs_invalidate_final_checks():
    trace = Trace(); trace.assembly(); trace.final_checks()
    trace.helper('final_source_inventory'); trace.write('report'); trace.helper('draft')
    trace.write('full')
    with pytest.raises(ValueError, match='current passing draft'):
        trace.helper('final_evidence')
    with pytest.raises(ValueError, match='current final checks'):
        trace.write('report')
    trace.final_checks(); trace.helper('final_source_inventory'); trace.write('report')
    with pytest.raises(ValueError, match='passing draft'):
        trace.helper('final_evidence')


def test_foreign_session_duplicate_result_and_premature_terminal_refuse():
    for mode in ('session', 'duplicate', 'terminal'):
        trace = Trace()
        if mode == 'session':
            event = {'type': 'assistant', 'session_id': 'foreign', 'message': {'content': []}}
        elif mode == 'duplicate':
            trace.helper('chunk_check')
            event = trace.events[-1][0]
        else:
            event = {'type': 'result', 'session_id': 'session'}
        with pytest.raises(ValueError): trace.state.observe(event)
        assert not trace.state.report(complete=True)['passed']


def test_unrecognized_bash_never_earns_helper_credit_and_background_refuses():
    trace = Trace()
    identity = trace.call('Bash', {'command': shlex.join(trace.commands['chunk_check']) + ' --foreign'})
    trace.result(identity, text='not phase evidence')
    with pytest.raises(ValueError):
        trace.state.before('Bash', {'command': shlex.join(trace.commands['chunk_check']), 'run_in_background': True})
    assert trace.state.report()['current_checks'] == []
    assert trace.state.report()['checks'][-1]['helper'] is None


@pytest.mark.parametrize('code', [0, 1])
def test_ordinary_readonly_bash_is_observed_but_not_a_phase_helper(code):
    trace = Trace()
    identity = trace.call('Bash', {'command': 'cat /neutral/full'})
    trace.result(identity, code=code, text='neutral lookup or refusal')
    report = trace.state.report()
    assert report['passed'] and report['pending_tool_ids'] == []
    assert report['current_checks'] == []
    assert report['checks'][-1]['helper'] is None
    assert report['checks'][-1]['exit_code'] == code
    with pytest.raises(ValueError, match='generation precedes'):
        trace.write('full')


def test_ordinary_bash_cannot_hide_missing_exit_or_overlap():
    trace = Trace()
    identity = trace.call('Bash', {'command': 'cat /neutral/full'})
    with pytest.raises(ValueError, match='exit aliases'):
        trace.result(identity, text='neutral', mutation=lambda event: event['tool_use_result'].pop('exitCode'))
    assert not trace.state.report()['passed']
    other = Trace(); other.call('Bash', {'command': 'cat /neutral/full'})
    with pytest.raises(ValueError, match='overlaps an unsettled'):
        other.state.observe({'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'next', 'name': 'Bash', 'input': {'command': 'cat /neutral/full'}}]}})


def test_callback_before_or_after_tool_frame_accepts_only_the_current_report_write():
    trace = Trace(); trace.assembly(); trace.final_checks(); trace.helper('final_source_inventory')
    inputs = {'file_path': '/neutral/report', 'content': 'neutral'}
    trace.state.before('Write', inputs, stage_decision=trace.current)
    identity = trace.call('Write', inputs)
    # Callback may follow the original assistant frame; that is still this
    # current write, not permission to spend the source inventory twice.
    trace.state.before('Write', inputs, stage_decision=trace.current)
    with pytest.raises(ValueError, match='new settled final source inventory'):
        trace.state.before('Write', {**inputs, 'content': 'different'}, stage_decision=trace.current)
    trace.result(identity, bash=False)
    with pytest.raises(ValueError, match='new settled final source inventory'):
        trace.state.before('Write', inputs, stage_decision=trace.current)


def test_final_checks_are_repeated_even_when_full_record_is_unchanged():
    trace = Trace(); trace.assembly()
    trace.helper('derive_final_core'); trace.helper('core_schema'); trace.helper('pair')
    with pytest.raises(ValueError, match='current full validation'):
        trace.helper('phase1_receipts')
    trace.helper('full_schema'); trace.helper('full_terms')
    trace.helper('phase1_receipts'); trace.helper('final_scope')
    trace.finish()
    assert trace.state.report(complete=True)['passed']


def test_result_content_json_can_differ_in_formatting_but_not_typed_values():
    trace = Trace(); trace.initial(); trace.core()
    def equivalent(event):
        event['message']['content'][0]['content'] = json.dumps(json.loads(event['tool_use_result']['stdout']), indent=2)
    trace.helper('advance', after=decision('assembly_complete', 3), mutation=equivalent)
    trace.helper('audit_evidence')
    assert trace.state.report()['assembly_complete']


def test_fresh_waiting_decision_without_settled_advance_is_not_a_core_boundary():
    trace = Trace(); trace.initial()
    with pytest.raises(ValueError, match='actual await_core'):
        trace.helper('derive_core')
    trace.helper('advance', after=decision(number=2))
    trace.helper('derive_core')
    assert 'derive_core' in trace.state.report()['current_checks']


def test_fresh_stage_regression_cannot_hide_after_observed_assembly():
    trace = Trace(); trace.assembly(); trace.current = decision(number=4)
    with pytest.raises(ValueError, match='regressed'):
        trace.write('full')
