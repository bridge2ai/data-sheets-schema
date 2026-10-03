"""Invented scripted deliveries through the real selected API state machine.

No provider calls, scientific labels or replacement validators. The script
responds to the actual whole wire supplied by the production controller.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import receipt_completion as rc, typed_audit_runtime as runtime
from data_sheets_schema import typed_audit as typed, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeMessages, FakeResponse
from tests.test_evidence_generation_gate import specification
from tests.test_shared_generation_selection import registration_for, selected_spec
from tests.test_source_review import review_for

FULL = {'id': 'urn:sample', 'title': 'Sample dataset', 'name': 'sample',
        'description': 'A sample dataset is planned.', 'keywords': ['sample']}
SOURCE = {'c001': {'source': 'protocol.txt', 'text': 'A sample dataset is planned.'}}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    monkeypatch.setattr(api, 'MAX_ATTEMPTS', 1)


@pytest.fixture
def selected(tmp_path):
    base = specification(tmp_path)
    return selected_spec(base, registration_for(base))


def response(value):
    result = FakeResponse(value if isinstance(value, str) else json.dumps(value))
    result.stop_reason = 'end_turn'
    return result


class Script(FakeMessages):
    """Construct declarations only from the wire (not controller journals)."""
    def __init__(self, spec, *, fail=None, bad_report=False, omission_count=0):
        super().__init__()
        self.spec, self.fail = spec, fail
        self.bad_report, self.omission_count = bad_report, omission_count
        self.phases, self.count_calls = [], []
        self.full = deepcopy(FULL)

    def count_tokens(self, **kwargs):
        self.count_calls.append(deepcopy(kwargs))
        return SimpleNamespace(input_tokens=1000)

    def _carry(self, blocks, name):
        prefix = api.CARRY_LABEL.format(name=name)
        return next(s[len(prefix):] for s in blocks if s.startswith(prefix))

    def create(self, **kwargs):
        blocks = [p['text'] for p in kwargs['messages'][-1]['content']]
        stage_block = next((s for s in blocks if s.startswith('# Exact typed stage request\n\n')), None)
        if stage_block:
            inner = json.loads(stage_block.split('\n\n', 1)[1])
            kind = inner.get('kind')
            phase = { 'typed_audit_worker_request_v1': runtime.WORKER_PHASE,
                      'typed_audit_index_v1': runtime.INTEGRATION_PHASE}.get(kind, runtime.OMISSION_PHASE)
        elif rc.policy_text(version=2) in blocks:
            phase = rc.PHASE
        else:
            last = blocks[-1]
            phase = next((p for p in api.PHASES if last.startswith(api.phase_instruction(p, self.spec.render_version).split('\n')[0])), None)
            if last.startswith('Report re-check.'):
                phase = 'report_regate'
            if phase is None:
                raise AssertionError('unrecognized actual request: ' + last[:100])
        self.calls.append(deepcopy(kwargs))
        self.phases.append(phase)
        if self.fail == phase:
            raise RuntimeError('scripted transport failure')
        if phase == 'full':
            chunks = yaml.safe_load(self.spec.chunk_manifest.read_bytes())['chunks']
            receipt = {'bundle_md5': hashlib.md5(self.spec.bundle.read_bytes()).hexdigest(),
                'chunks': [{'id': c['id'], 'status': 'nothing_relevant', 'reason': 'Synthetic prior negative.'} for c in chunks]}
            return response(yaml.safe_dump(self.full) + '\n' + api.RECEIPT_MARK + '\n' + yaml.safe_dump(receipt))
        if phase == rc.PHASE:
            inventory = json.loads(blocks[0])
            return response(yaml.safe_dump({'rereceipt': [{'path': p, 'unsupported': True,
                'reason': 'Synthetic unknown support; independent judgment required.'} for p in inventory['requested_paths']]}))
        if phase == runtime.WORKER_PHASE:
            payload = inner['payload']
            context, stage = json.loads(payload['shared_context']), json.loads(payload['stage'])
            review = review_for(context['original_full'], chunks=SOURCE)
            review['values'] = [r for r in review['values'] if r['path'] in stage['assignment']['paths']]
            return response({'findings': [], 'summary': 'Synthetic declared support only.', 'source_review': review})
        if phase == runtime.OMISSION_PHASE:
            return response({'format': 'omission_inventory_v1', 'request_sha256': inner['request_sha256'],
                'chunks': [{'chunk': row['chunk'], 'status': 'no_omission', 'reason': 'No proposed omission.',
                            'candidates': []} for row in inner['payload']['chunks']]})
        if phase == runtime.INTEGRATION_PHASE:
            index = inner['index']
            return response({'kind': 'audit_integration_v2', 'proposal_index_sha256': index['sha256'],
                'retain_other_rows_from_index_sha256': index['sha256'], 'row_replacements': [],
                'finding_decisions': [], 'new_findings': [], 'summary': 'Synthetic declared integration.',
                'omission_dispositions': []})
        if phase == 'reconcile_full':
            return response(self._carry(blocks, 'Completed full record'))
        if phase in ('report', 'report_regate'):
            full = self._carry(blocks, 'Reconciled full record')
            review = review_for(full, 'final_full', chunks=SOURCE)
            claims = []
            if self.bad_report and phase == 'report':
                claims = [{'artifact': 'original_core', 'path': '@header', 'op': 'contains',
                           'quote': '# Phase 4 reconciliation: completed'}]
            payload = {'claims': claims, 'source_review': review}
            return response('# Reconciliation\n\n## Evidence assertions\n```json\n' + json.dumps(payload) +
                '\n```\n\n## Dispositions\n\n| slot | disposition | record | reason |\n|---|---|---|---|\n'
                '| `keywords` | retained | full | kept |\n')
        raise AssertionError(phase)


def client(spec, **kwargs):
    messages = Script(spec, **kwargs)
    result = SimpleNamespace(messages=messages, base_url='https://example.invalid', max_retries=2)
    result.with_options = lambda **options: SimpleNamespace(messages=messages,
        base_url=result.base_url, max_retries=options['max_retries'])
    return result


def files(spec):
    return {str(p): p.read_bytes() for p in spec.metadata_dir.rglob('*') if p.is_file()}


def test_real_complete_api_pipeline_and_completed_recheck(selected):
    c = client(selected)
    result = api.execute(selected, client=c)
    assert result['validation_problems'] == []
    phases = ['full', rc.PHASE, runtime.WORKER_PHASE, runtime.OMISSION_PHASE,
              runtime.INTEGRATION_PHASE, 'reconcile_full', 'report']
    assert c.messages.phases == phases
    assert [r['phase'] for r in result['usage']] == phases
    state = runtime._state(selected)
    assert state['state'] == 'accepted'
    assembly = rc._load(state['assembly'])
    checked = typed.check(assembly, derivations=typed.DerivationCache())
    assert checked['passed'] and checked['independently_reconstructed']
    audit = typed._unblob(assembly['audit']).decode()
    reconcile = c.messages.calls[phases.index('reconcile_full')]
    assert {'type': 'text', 'text': api.CARRY_LABEL.format(name='Audit findings') + audit} in reconcile['messages'][0]['content']
    for call in c.messages.calls[2:5]:
        assert {'type': 'text', 'text': rc.audit_carry(selected)} in call['messages'][0]['content']
    record = yaml.safe_load(selected.provenance_path.read_bytes())
    assert record['shared_generation']['assembly_sha256'] == assembly['sha256']
    assert record['receipt_completion']['counts']['unsupported'] > 0
    assert record['shared_generation']['scientific_support'] == 'unverified evaluator declarations'
    from data_sheets_schema import snapshot_store
    index = json.loads(snapshot_store.index_path(selected.provenance_path.parent, selected.project).read_bytes())
    audit_snapshot = next(row for row in index['snapshots'] if row['name'] == f'{selected.project}_audit.json')
    integration_id = next(row['usage_id'] for row in result['usage'] if row['phase'] == runtime.INTEGRATION_PHASE)
    assert audit_snapshot['usage_id'] == integration_id
    before = files(selected)
    again = client(selected)
    repeated = api.execute(replace(selected), client=again)
    assert repeated['already_complete'] and not again.messages.calls
    assert before == files(selected)
    assert_completed_mutations_refuse_without_calls(selected)
# Draft to apply only after immutable pipeline process ends.
class CandidatesScript(Script):
    def __init__(self, spec, *, drop=False, **kwargs):
        super().__init__(spec, **kwargs)
        self.drop = drop
        self.full['creators'] = [{'name': 'sample'}]
        self.candidates = []

    def create(self, **kwargs):
        result = super().create(**kwargs)
        phase = self.phases[-1]
        blocks = [p['text'] for p in kwargs['messages'][-1]['content']]
        if phase == runtime.OMISSION_PHASE:
            inner = json.loads(next(s for s in blocks if s.startswith('# Exact typed stage request\n\n')).split('\n\n', 1)[1])
            value = json.loads(result.content[0].text)
            chunk = next(row for row in inner['payload']['chunks'] if row['source'] == 'protocol.txt')
            self.quote = {'source': 'protocol.txt', 'chunk': chunk['chunk'], 'quote': 'A sample dataset is planned.'}
            self.candidates = [{'id': f'candidate-{i}', 'kind': 'omission', 'source': 'protocol.txt',
                'quote': self.quote['quote'], 'target': {'owner': '', 'slot_chain': ['description']},
                'missing_information': 'Proposed description detail for mechanical lineage testing.',
                'scope_basis': 'The fictional passage names the release; novelty is unverified.'} for i in range(2)]
            next(row for row in value['chunks'] if row['chunk'] == chunk['chunk']).update(
                status='omission', candidates=self.candidates)
            return response(value)
        if phase == runtime.INTEGRATION_PHASE:
            value = json.loads(result.content[0].text)
            value['omission_dispositions'] = [{'candidate_id': c['id'], 'action': 'drop' if self.drop else 'retain',
                'reason': 'Synthetic disposition; no scientific adjudication.',
                'evidence': [self.quote] if self.drop else []} for c in self.candidates]
            if not self.drop:
                value['new_findings'] = [{'severity': 'medium', 'record': 'full', 'slot': 'description',
                    'issue': 'A merged draft omission finding.', 'kind': 'omission',
                    'omission_candidates': [c['id'] for c in self.candidates], 'evidence': [self.quote]}]
            return response(value)
        return result


def scripted_client(messages):
    result = SimpleNamespace(messages=messages, base_url='https://example.invalid', max_retries=2)
    result.with_options = lambda **options: SimpleNamespace(messages=messages,
        base_url=result.base_url, max_retries=options['max_retries'])
    return result


def test_real_saved_response_settles_once_then_merged_omissions_and_role_regate(selected, monkeypatch):
    messages = CandidatesScript(selected, bad_report=True)
    c = scripted_client(messages)
    original_append = api._append_usage
    interrupted = []
    def append(spec, usage, row):
        if row['phase'] == runtime.WORKER_PHASE and not interrupted:
            interrupted.append(row['usage_id'])
            raise OSError('simulated interruption after durable complete response')
        return original_append(spec, usage, row)
    monkeypatch.setattr(api, '_append_usage', append)
    with pytest.raises(OSError, match='durable complete response'):
        api.execute(selected, client=c)
    assert messages.phases == ['full', rc.PHASE, runtime.WORKER_PHASE]
    state = runtime._state(selected)
    assert state['stages'][-1]['state'] == 'response_saved'
    assert ledger._read(selected)['pending_call']['usage_id'] == interrupted[0]
    originals = runtime._originals(selected)
    monkeypatch.setattr(api, '_append_usage', original_append)
    result = api.execute(replace(selected), client=c)
    assert result['validation_problems'] == []
    assert messages.phases.count(runtime.WORKER_PHASE) == 1
    assert messages.phases[-1] == 'report_regate'
    assert sum(row['usage_id'] == interrupted[0] for row in result['usage']) == 1
    assert runtime._originals(selected) == originals
    assembly = rc._load(runtime._state(selected)['assembly'])
    assert assembly['acceptance']['omission_counts']['retained'] == 2
    assert assembly['acceptance']['finding_counts']['omission'] == 1
    for phase in ('report', 'report_regate'):
        call = messages.calls[messages.phases.index(phase)]
        blocks = [p['text'] for p in call['messages'][0]['content']]
        context = json.loads(next(s for s in blocks if s.startswith(sg.SCHEMA_CONTEXT_HEADER)).split('\n\n', 1)[1])
        owner = next(row for row in context['owners'] if row['path'] == '/creators/0')
        assert yaml.safe_load(owner['whole_value_yaml']) == {'name': 'sample'}
        assert api.phase_instruction(phase, 25) in blocks
        runtime.require_request(selected, phase, call)
        for remove in (api.phase_instruction(phase, 25), sg.SCHEMA_CONTEXT_HEADER):
            damaged = deepcopy(call)
            damaged['messages'][0]['content'] = [part for part in damaged['messages'][0]['content']
                if not (part['text'] == remove or part['text'].startswith(remove))]
            with pytest.raises(ledger.UsageLedgerError):
                runtime.require_request(selected, phase, damaged)


def test_real_dropped_only_candidates_remain_counted(selected):
    messages = CandidatesScript(selected, drop=True)
    result = api.execute(selected, client=scripted_client(messages))
    assert result['validation_problems'] == []
    assembly = rc._load(runtime._state(selected)['assembly'])
    assert assembly['acceptance']['omission_counts']['dropped'] == 2
    assert assembly['acceptance']['omission_counts']['retained'] == 0
    assert assembly['acceptance']['finding_counts']['omission'] == 0
    assert len(assembly['lineage']['omission_candidates']) == 2
    assert all(row['final_finding_ordinal'] is None for row in assembly['lineage']['omission_candidates'])


@pytest.mark.parametrize('fault', ['transport', 'truncated', 'unknown_usage', 'malformed', 'missing_worker_value', 'missing_chunk'])
def test_actual_consumed_failure_retains_evidence_and_never_repurchases(selected, fault, monkeypatch):
    c = client(selected, fail=runtime.WORKER_PHASE if fault == 'transport' else None)
    create = c.messages.create
    def broken(**kwargs):
        result = create(**kwargs)
        phase = c.messages.phases[-1]
        if phase == runtime.WORKER_PHASE:
            if fault == 'truncated': result.stop_reason = 'max_tokens'
            elif fault == 'unknown_usage': result.usage.input_tokens = None
            elif fault == 'malformed': result.content[0].text = '{'
            elif fault == 'missing_worker_value':
                value = json.loads(result.content[0].text)
                value['source_review']['values'].pop()
                result.content[0].text = json.dumps(value)
        elif phase == runtime.OMISSION_PHASE and fault == 'missing_chunk':
            value = json.loads(result.content[0].text)
            value['chunks'].pop()
            result.content[0].text = json.dumps(value)
        return result
    monkeypatch.setattr(c.messages, 'create', broken)
    with pytest.raises((ValueError, RuntimeError, ledger.UsageLedgerError)):
        api.execute(selected, client=c)
    state = runtime._state(selected)
    assert state['state'] == 'failed'
    if fault != 'transport':
        delivered = rc._load(state['stages'][-1]['response'])
        assert delivered['text'] and delivered['usage_id']
    before = files(selected)
    retry = client(selected)
    with pytest.raises((ValueError, RuntimeError, ledger.UsageLedgerError)):
        api.execute(replace(selected), client=retry)
    assert not retry.messages.calls
    assert files(selected) == before


def assert_completed_mutations_refuse_without_calls(spec):
    """Every mutation uses only the test's owned captured artifacts/inputs."""
    baseline = files(spec)
    source_context = Path(sg.capture(spec).document()['inputs']['context']['path'])
    input_bytes = {spec.bundle: spec.bundle.read_bytes(), source_context: source_context.read_bytes()}
    for mutation in ('bundle', 'context', 'receipt', 'rehashed_packet', 'rehashed_assembly', 'usage', 'lost_progress'):
        data = ledger._read(spec)
        if mutation in ('bundle', 'context'):
            path = spec.bundle if mutation == 'bundle' else source_context
            path.write_bytes(input_bytes[path] + b'\n')
        elif mutation == 'receipt':
            path = api._receipt_path(spec)
            path.write_bytes(path.read_bytes() + b'\n# changed effective receipt\n')
        elif mutation.startswith('rehashed_'):
            key = mutation.split('_', 1)[1]
            pin = data['typed_audit'][key]
            value = rc._load(pin)
            if key == 'packet':
                value['requests']['shared_context'] += '\nchanged'
            else:
                value['acceptance']['scientific_support'] = 'forged approved'
            raw = sg.canonical(value)
            Path(pin['path']).write_bytes(raw)
            pin['sha256'] = sg.sha(raw)
            ledger._write(spec, data)
        elif mutation == 'usage':
            data['rows'][2]['input_tokens'] = True
            ledger._write(spec, data)
        else:
            spec.provenance_path.unlink()
            api._progress_path(spec).unlink(missing_ok=True)
        before = files(spec)
        retry = client(spec)
        try:
            with pytest.raises((ValueError, RuntimeError, ledger.UsageLedgerError)):
                api.execute(replace(spec), client=retry)
            assert not retry.messages.calls
            assert files(spec) == before
        finally:
            for path, raw in input_bytes.items(): path.write_bytes(raw)
            for path, raw in baseline.items(): Path(path).write_bytes(raw)
    assert files(spec) == baseline


def test_actual_cli_executes_then_refuses_reuse_without_calls(tmp_path, monkeypatch):
    import importlib
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    module = importlib.import_module('data_sheets_schema.cli.api')
    base = replace(specification(tmp_path), arm=module.ARMS['baseline'][0],
                   method=module.ARMS['baseline'][1], label='shared-cli-synthetic_rep1')
    reg = registration_for(base)
    selected = selected_spec(base, reg)
    peer = client(selected)
    monkeypatch.setattr(api, '_client', lambda: peer)
    args = ['api', 'run', '--project', selected.project, '--label', selected.label,
            '--out-dir', str(selected.out_dir), '--shared-generation-version', '1',
            '--shared-generation-registration', reg['registration_path'], '--yes']
    inputs = {p: p.read_bytes() for p in (selected.bundle, selected.chunk_manifest,
               Path(reg['inputs']['context']['path']), Path(reg['registration_path']))}
    result = CliRunner().invoke(cli, args)
    (tmp_path/'cli-first-output.txt').write_text(result.output)
    assert result.exit_code == 0, (result.output, result.exception)
    assert peer.messages.phases == ['full','full_receipt_completion','typed_audit_worker',
        'typed_audit_omission','typed_audit_integration','reconcile_full','report']
    assert selected.provenance_path.exists()
    before = files(selected)
    fresh = client(selected)
    monkeypatch.setattr(api, '_client', lambda: fresh)
    repeat = CliRunner().invoke(cli, args)
    (tmp_path/'cli-repeat-output.txt').write_text(repeat.output)
    assert repeat.exit_code == 1, repeat.output
    assert 'a run label is never reused' in repeat.output
    assert not fresh.messages.calls
    assert files(selected) == before
    assert all(p.read_bytes() == raw for p,raw in inputs.items())
