"""Checkpoint layout, unchanged science and original worker closure identity.

These tests isolate the runtime seam with a checked-source object; proof and
preparation have separate tests. Worker closure replay and scientific assembly
remain real. All inputs are synthetic; no historical audit data is accessed.
"""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from budgeted_cborg import BudgetStop, Ledger, attempt_identity
from data_sheets_schema import audit_batches, audit_batch_context
from . import batch_native as runtime, batch_output as output, worker_checkpoint as checkpoint
from . import batch_registration, native
from .test_batch_runtime import batch, BatchSession, proposal, close_session
from tests.test_audit_batch_context import staged, proposals as context_proposals


def selected_manifest(old, registration, workers, closure_refs=None):
    """Strict descriptor plus detached source; document proof is tested elsewhere."""
    manifest = deepcopy(old)
    manifest['render_version'] = 23
    manifest['scientific_contract_transition'] = {'kind': 'frozen_pair_child_navigation_v1'}
    manifest['audit_batch_navigation'] = {'kind': 'explicit_child_reads_v1'}
    root = registration.parent
    source_root = Path(old['job']['attempt_dir']).parent.parent
    descriptor = {'kind': checkpoint.KIND}
    for key in checkpoint.REFS:
        descriptor[key] = {'path': str(source_root / (key + '.json')), 'sha256': 'a' * 64}
    descriptor['workers'] = [
        {'id': row['id'], 'closure': (closure_refs or {}).get(row['id'],
            {'path': str(Path(row['attempt_dir']) / 'closed.json'), 'sha256': 'b' * 64})}
        for row in workers]
    manifest[checkpoint.KEY] = descriptor
    manifest['job'] = {**manifest['job'], 'id': 'NEW_INTEGRATION',
        'attempt_dir': str(root / 'attempts/NEW_INTEGRATION'),
        'output_dir': str(root / 'attempts/NEW_INTEGRATION/output'),
        'audit_path': str(root / 'attempts/NEW_INTEGRATION/output/audit.json')}
    manifest['budget']['per_job_attempt_usd'] = {'NEW_INTEGRATION': '20'}
    manifest['audit_batches'] = output.specification(manifest, registration,
        plan_path=old['audit_batches']['plan_path'])
    source = SimpleNamespace(manifest=old, registration_path=source_root / 'registration.json',
        sha256='c' * 64, workers=tuple(workers),
        closure_refs={w['id']: w['closure'] for w in descriptor['workers']},
        proposal_refs={r['id']: {'path': r['proposal_path'],
            'sha256': hashlib.sha256(Path(r['proposal_path']).read_bytes()).hexdigest()}
            for r in workers}, proof_sha256='d' * 64, evidence_paths=frozenset())
    return manifest, source


@pytest.fixture
def closed_workers(batch):
    closed = []
    for worker in batch.plan['workers']:
        session = BatchSession(batch, worker['id'])
        session.write(json.dumps(proposal(batch, worker['id'])))
        assert session.check()['grammar']['passed']
        session.seal()
        closed.append(close_session(session))
    return closed


def configure(batch, closed, tmp_path, monkeypatch):
    workers = batch.m['audit_batches']['children'][:-1]
    refs = {r['child_id']: {'path': str(Path(w['attempt_dir']) / 'closed.json'),
                           'sha256': r['closure_sha256']} for w, r in zip(workers, closed)}
    path = tmp_path / 'new/registration.json'
    manifest, source = selected_manifest(batch.m, path, workers, refs)
    source.sha256 = batch.identity
    monkeypatch.setattr(checkpoint, 'validate', lambda m, **kw: source)
    # The detached source fixture is a renderer-20 closure seam. Exact selected
    # renderer-23 prompt equivalence has its own complete scientific fixture.
    monkeypatch.setattr(runtime, 'verify_checkpoint_context', lambda *args: None)
    return manifest, source


def test_checkpoint_layout_has_only_new_integration_and_no_worker_allowance(
        batch, closed_workers, tmp_path, monkeypatch):
    manifest, _ = configure(batch, closed_workers, tmp_path, monkeypatch)
    block = output.configuration(manifest)
    assert block['kind'] == output.CHECKPOINT_KIND
    assert [r['id'] for r in block['children']] == ['integration']
    assert 'worker_total_cap_usd' not in block
    assert output.plan(manifest) == batch.plan
    assert not Path(block['children'][0]['attempt_dir']).exists()
    with pytest.raises(BudgetStop, match='no new worker allowance'):
        output.specification(manifest, tmp_path / 'new/registration.json', worker_total_cap_usd='1')
    # Neither a layout-only switch nor a selector-less inherited claim is valid.
    del manifest[checkpoint.KEY]
    with pytest.raises(BudgetStop):
        output.configuration(manifest)


@pytest.mark.parametrize('damage', ['old_render', 'new_worker', 'worker_cap', 'no_batch'])
def test_inherited_mode_cannot_silently_change_layout(
        batch, closed_workers, tmp_path, monkeypatch, damage):
    manifest, _ = configure(batch, closed_workers, tmp_path, monkeypatch)
    if damage == 'old_render':
        manifest['render_version'] = 20
        manifest['scientific_contract_transition'] = {'kind': 'frozen_pair_integrated_batches_v1'}
        del manifest['audit_batch_navigation']
    elif damage == 'new_worker':
        manifest['audit_batches']['children'].insert(0, batch.m['audit_batches']['children'][0])
    elif damage == 'worker_cap':
        manifest['audit_batches']['worker_total_cap_usd'] = '1'
    else:
        del manifest['audit_batches']
    with pytest.raises(BudgetStop):
        output.configuration(manifest)


def test_workers_replay_under_original_identity_and_scientific_assembly_is_identical(
        batch, closed_workers, tmp_path, monkeypatch):
    manifest, source = configure(batch, closed_workers, tmp_path, monkeypatch)
    replayed = output.worker_closures(manifest, 'e' * 64)
    assert replayed == closed_workers
    index = audit_batches.build_index(batch.plan, output.proposals(manifest))
    integration = {'kind': 'audit_integration_v1', 'proposal_index_sha256': index['sha256'],
        'retain_other_rows_from_index_sha256': index['sha256'], 'row_replacements': [],
        'finding_decisions': [], 'new_findings': [], 'summary': 'Synthetic complete review.'}
    row = output.child(manifest, 'integration')
    path = Path(row['proposal_path']); path.parent.mkdir(parents=True)
    path.write_bytes(audit_batches.canonical_bytes(integration))
    real_seal = output.verify_seal
    def sealed(m, identity, child, *args):
        if m is manifest and child == 'integration':
            return {'proposal': {'path': str(path),
                                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}
        return real_seal(m, identity, child, *args)
    monkeypatch.setattr(output, 'verify_seal', sealed)
    expected_audit, expected_lineage = audit_batches.assemble(
        batch.plan, output.proposals(batch.m), path.read_bytes())
    raw, lineage_raw, receipt = output._assembled(manifest, 'e' * 64)
    assert raw == expected_audit
    assert json.loads(lineage_raw) == expected_lineage
    inherited = receipt['worker_checkpoint']
    assert inherited['source_registration']['sha256'] == batch.identity
    assert all(r['registration_sha256'] == batch.identity for r in inherited['workers'])
    assert receipt['registration_sha256'] == 'e' * 64
    assert [r['id'] for r in inherited['workers']] == [r['id'] for r in source.workers]
    with pytest.raises(BudgetStop, match='omits or changes'):
        output.checkpoint_lineage(manifest, replayed[:-1])
    # The unchanged old child verifier catches a mutated source closure even
    # when the detached proof seam is stubbed in this unit test.
    old_path = Path(source.closure_refs[source.workers[0]['id']]['path'])
    value = json.loads(old_path.read_bytes()); value['registration_sha256'] = 'e' * 64
    old_path.write_text(json.dumps(value))
    with pytest.raises(BudgetStop):
        output.worker_closures(manifest, 'e' * 64)


def test_fresh_integration_context_keeps_complete_worker_science_and_excludes_old_integration(
        batch, staged, tmp_path, monkeypatch):
    # Full real renderer with nested schema meanings and two source documents.
    paths, expected_index, _ = context_proposals(staged)
    old = deepcopy(batch.m)
    old['inputs'] = {k: str(v) for k, v in staged['files'].items()}
    plan_path = tmp_path / 'context-plan.json'
    plan_path.write_bytes(audit_batches.canonical_bytes(staged['plan']))
    old['pinned_files'][str(plan_path)] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    old['pinned_files'][str(staged['files']['original_full'])] = hashlib.sha256(
        staged['files']['original_full'].read_bytes()).hexdigest()
    old['audit_batches'] = output.specification(old, batch.reg,
        worker_total_cap_usd='24', plan_path=plan_path)
    workers = old['audit_batches']['children'][:-1]
    for row in workers:
        row['proposal_path'] = str(paths[row['id']])
    manifest, source = selected_manifest(old, tmp_path / 'fresh/registration.json', workers)
    monkeypatch.setattr(checkpoint, 'validate', lambda m, **kw: source)
    monkeypatch.setattr(output, 'worker_closures', lambda *args: [])
    monkeypatch.setattr(batch_registration, 'scientific_arguments', lambda m: {
        'inputs': staged['files'], 'profile': 'neutral', 'project': 'example', 'plan': staged['plan']})
    # Evidence is intentionally present in the old tree but has no model input permission.
    old_integration = Path(old['audit_batches']['children'][-1]['attempt_dir'])
    old_integration.mkdir(parents=True)
    for name in ('transcript.jsonl', 'control.jsonl', 'failed-draft.json', 'validation.json'):
        (old_integration / name).write_text('FORBIDDEN_OLD_INTEGRATION_' + name)
    current = output.child(manifest, 'integration')
    Path(current['attempt_dir']).parent.mkdir(parents=True)
    runtime.prepare_integration(manifest, 'e' * 64)
    actual = Path(current['instruction']).read_text()
    index, artifacts, views, bindings, args = runtime.integration_material(manifest)
    assert index == expected_index
    expected = audit_batch_context.render_integration_context(**args, worker_index=index,
        worker_artifacts=paths, row_artifacts=artifacts, audit_batch_navigation='explicit_child_reads_v1')
    assert actual == expected
    assert 'Second source context remains available.' in actual
    assert str(staged['files']['full_schema']) in actual
    assert 'Peak current for this controller.' in staged['files']['full_schema'].read_text()
    assert 'Synthetic source-supported omission' in actual
    assert 'FORBIDDEN_OLD_INTEGRATION' not in actual
    assert all(str(path) in actual for path in paths.values())
    assert all(not Path(p).is_relative_to(old_integration) for p in [*views, *map(str, paths.values())])
    runtime.verify_integration(manifest, 'e' * 64)


@pytest.mark.parametrize('stop', [False, True])
def test_orchestrator_launches_only_new_integration_and_names_inherited_workers(
        batch, closed_workers, tmp_path, monkeypatch, stop):
    manifest, source = configure(batch, closed_workers, tmp_path, monkeypatch)
    root = Path(manifest['job']['attempt_dir']); root.mkdir(parents=True)
    context = SimpleNamespace(manifest=manifest, manifest_sha256='e' * 64,
        job=manifest['job'], registration_path=tmp_path / 'new/registration.json',
        ledger=batch.ledger, verify=lambda: None)
    monkeypatch.setattr(runtime, 'prepare_integration', lambda *args: None)
    monkeypatch.setattr(output, 'validate_output', lambda m: {'audit': {'sha256': 'f' * 64}})
    candidates = []
    monkeypatch.setattr(runtime, 'verify_aggregate_closure', lambda m, path, result: candidates.append(result))
    calls = []
    def run(c, row, deadline, **kwargs):
        calls.append((row['id'], deadline))
        if stop:
            raise BudgetStop('synthetic new integration stop')
        return {'child_id': row['id'], 'closure_sha256': '1' * 64,
                'evidence': {'batch_child': {'validation': {'passed': True}}}}
    if stop:
        with pytest.raises(BudgetStop, match='synthetic new integration stop'):
            runtime.execute_job(context, clock=lambda: 100., child_runner=run)
        assert candidates == []
    else:
        result = runtime.execute_job(context, clock=lambda: 100., child_runner=run)
        assert result['runtime']['children_closed'] == 1
        assert result['evidence']['batch_children'] == [
            {'id': 'integration', 'closure_sha256': '1' * 64}]
        inherited = result['evidence']['worker_checkpoint']
        assert [w['id'] for w in inherited['workers']] == [w['id'] for w in source.workers]
        assert all(w['registration_sha256'] == batch.identity for w in inherited['workers'])
        assert len(candidates) == 1
    assert calls == [('integration', 21700.)]
    with pytest.raises(FileExistsError):
        runtime.execute_job(context, child_runner=run)


def test_every_paid_admission_rechecks_inherited_worker_closures_before_transport(
        batch, closed_workers, tmp_path, monkeypatch):
    manifest, source = configure(batch, closed_workers, tmp_path, monkeypatch)
    manifest['provider_base_url'] = 'https://synthetic.invalid'
    manifest['budget']['prices_per_token'] = {'input': '1', 'output': '1'}
    manifest['budget']['ledger_path'] = str(tmp_path / 'new/billing.json')
    Path(manifest['job']['attempt_dir']).joinpath('children').mkdir(parents=True)
    monkeypatch.setattr(batch_registration, 'scientific_arguments', lambda m: {})
    monkeypatch.setattr(audit_batch_context, 'render_integration_context',
        lambda **kw: 'Synthetic fresh integration ' + audit_batches.object_sha256(kw['worker_index']))
    registration = tmp_path / 'new/registration.json'
    registration.write_text(json.dumps(manifest))
    identity = native.sha(registration)
    runtime.prepare_integration(manifest, identity)
    row = output.child(manifest, 'integration')
    system = Path(row['system_prompt']); system.parent.mkdir(parents=True)
    system.write_text('Synthetic integration system.')
    owner = attempt_identity(identity, manifest['job']['id'])
    ledger = Ledger(manifest['budget']['ledger_path'], manifest_sha256=identity,
        total_cap=500, attempt_cap=40, attempt_caps_usd={owner: 20})
    ledger.require_resolved(owner)
    context = SimpleNamespace(manifest=manifest, manifest_sha256=identity,
        job=manifest['job'], registration_path=registration,
        ledger=ledger, verify=lambda: None)
    class Proxy:
        def __init__(self, **kwargs):
            self.kw = kwargs; self.token = 'synthetic'; self.failed = threading.Event()
            self.frozen = False; self.unfinished_handlers = None
        @contextmanager
        def running(self):
            try:
                yield 'http://synthetic.invalid'
            finally:
                self.frozen = True; self.unfinished_handlers = 0
    monkeypatch.setattr(runtime, 'BatchProxy', Proxy)
    monkeypatch.setattr(native, 'verify_runtime', lambda m: Path('/synthetic/claude'))
    reached = []
    def execute(argv, **kwargs):
        kwargs['verify_launch']()
        reached.append('initial_admission')
        old = Path(source.closure_refs[source.workers[0]['id']]['path'])
        value = json.loads(old.read_bytes()); value['registration_sha256'] = 'f' * 64
        old.write_text(json.dumps(value))
        kwargs['proxy'].kw['verify']()
        reached.append('transport_after_tamper')
        raise AssertionError('changed inherited evidence reached paid transport')
    monkeypatch.setattr(native, 'execute_child', execute)
    with pytest.raises(BudgetStop):
        runtime._execute_child(context, row, 21600, clock=lambda: 0.,
            client=SimpleNamespace(close=lambda: None), upstream=SimpleNamespace(close=lambda: None))
    assert reached == ['initial_admission']
    assert json.loads(ledger.path.read_bytes())['requests'] == []
