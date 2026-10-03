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
    before = files(selected)
    again = client(selected)
    repeated = api.execute(replace(selected), client=again)
    assert repeated['already_complete'] and not again.messages.calls
    assert before == files(selected)
