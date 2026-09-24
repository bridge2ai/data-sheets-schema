"""Adversarial accounting seams for collective closed-worker continuation.

Every identity, charge and artifact in this file is synthetic. Shared-budget
history and sequence ownership stay real; scientific acceptance is not inferred
from these accounting tests.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE/'native_controls')]
from audit_controls import registration
from audit_controls.test_context_preparation import ancestry
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_worker_checkpoint_registration import prepared_source
from test_budget_amendment import make_fixture, write


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()


@pytest.fixture
def settled_history(tmp_path):
    """1851 invented settled rows, including two unknown-fee debits, total $469."""
    anchor = [{'id': 'anchor', 'attempt': 'older:job', 'status': 'settled',
               'cost_usd': '1', 'usage': {'output_tokens': 1}}]
    generation = {'repository': str(tmp_path), 'generation': {'jobs': [{'id': 'origin'}]},
        'budget': {'additional_usd': 400, 'per_attempt_usd': 5,
                   'ledger_path': str(tmp_path/'origin-billing.json')}}
    proof, _, _, base = make_fixture(tmp_path/'authority', generation=generation, rows=anchor)
    base['parent'].update(job_id='origin', reconciled_checkpoint=proof['predecessor_ledger']['path'])
    source_root = tmp_path/'source'
    source_path = source_root/'registration.json'
    source = {'kind': 'd4d_native_audit_continuation', 'parent': deepcopy(base['parent']),
        'budget_amendment': deepcopy(proof), 'job': {'id': 'old_batch'},
        'budget': {'additional_usd': '500', 'per_attempt_usd': '5',
                   'ledger_path': str(source_root/'billing.json')}}
    source_ref = write(source_path, source)
    old_attempt = source_ref['sha256'] + ':old_batch'
    rows = anchor + [{'id': f'ordinary-{i:04d}',
        'attempt': old_attempt if i >= 1721 else f'historical-{i//100}:job',
        'status': 'settled', 'cost_usd': '0.25', 'reserved_usd': '2',
        'request_sha256': f'{i:064x}', 'usage': {'output_tokens': i}}
        for i in range(1848)]
    rows += [{'id': f'unknown-fee-{i}', 'attempt': old_attempt, 'status': 'settled',
        'cost_usd': '3', 'reserved_usd': '3',
        'settlement_basis': 'registered_stall_policy_full_reservation_debit',
        'provider_charge_confirmed': False, 'provider_charge_usd': None,
        'provider_usage_is_final': False} for i in range(2)]
    checkpoint = {'manifest_sha256': source_ref['sha256'], 'additional_cap_usd': '500',
        'attempt_cap_usd': '5', 'attempt_caps_usd': {old_attempt: '40'}, 'requests': rows,
        'stopped_attempts': {old_attempt: {'reason': 'synthetic admitted-attempt stop'}}}
    checkpoint_ref = write(source_root/'billing.json', checkpoint)
    destination = tmp_path/'fresh'
    manifest = {**deepcopy(base), 'job': {'id': 'fresh_integration'},
        'budget': {'additional_usd': '500', 'per_attempt_usd': '5',
            'per_job_attempt_usd': {'fresh_integration': '20'},
            'ledger_path': str(destination/'billing.json'),
            'continuation': {'checkpoint': checkpoint_ref['path'],
                'sha256': checkpoint_ref['sha256'], 'cost_usd': '469.00'}}}
    manifest['pinned_files'].update({source_ref['path']: source_ref['sha256'],
                                  checkpoint_ref['path']: checkpoint_ref['sha256']})
    path = destination/'registration.json'
    ref = write(path, manifest)
    immutable = {p: p.read_bytes() for p in (source_path, Path(checkpoint_ref['path']),
        *(Path(proof[k]['path']) for k in ('origin_registration', 'predecessor_registration',
          'predecessor_ledger', 'predecessor_owner', 'authorization')))}
    return manifest, path, ref['sha256'], checkpoint, old_attempt, immutable


def open_history(case):
    manifest, path, identity, *_ = case
    return registration.open_audit_ledger(manifest, path, identity)


def test_exact_1851_rows_import_once_with_unknown_fees_and_new_integration_suffix(settled_history):
    manifest, _, identity, previous, old_attempt, immutable = settled_history
    ledger = open_history(settled_history)
    imported = registration.read_json(ledger.path)
    assert len(imported['requests']) == 1851
    assert canonical(imported['requests']) == canonical(previous['requests'])
    assert imported['additional_cap_usd'] == '500'
    assert 'budget_amendment_sha256' not in imported['continued_from']
    fresh = identity + ':fresh_integration'
    assert imported['attempt_caps_usd'] == {fresh: '20'}
    assert ledger.limit_for_attempt(old_attempt) == Decimal('5')
    assert sum(Decimal(row['cost_usd']) for row in imported['requests']
               if row['attempt'] == old_attempt) == Decimal('37.75')
    ticket = ledger.reserve(fresh, '20', 'b'*64)
    ledger.settle(ticket, '20', response_sha256='c'*64, usage={'output_tokens': 1})
    after = registration.read_json(ledger.path)
    open_history(settled_history)
    assert registration.read_json(ledger.path) == after
    assert len(after['requests']) == 1852
    assert canonical(after['requests'][:1851]) == canonical(previous['requests'])
    assert after['requests'][-1]['attempt'] == fresh
    assert sum(Decimal(row['cost_usd']) for row in after['requests']) == Decimal('489')
    assert sum(Decimal(row['cost_usd']) for row in after['requests']
               if row['attempt'] in (old_attempt, fresh)) == Decimal('57.75')
    assert Decimal('500') - sum(Decimal(row['cost_usd']) for row in after['requests']) == Decimal('11')
    for row in after['requests'][1849:1851]:
        assert row['provider_charge_confirmed'] is False
        assert row['provider_charge_usd'] is None
        assert row['provider_usage_is_final'] is False
    assert all(path.read_bytes() == raw for path, raw in immutable.items())
    assert manifest['budget_amendment']['increase_usd'] == '100'


@pytest.mark.parametrize('damage', ['typed_flag', 'drop', 'duplicate', 'repriced', 'reattributed'])
def test_reopen_rejects_rewriting_imported_history_without_modifying_source(settled_history, damage):
    ledger = open_history(settled_history)
    state = registration.read_json(ledger.path)
    if damage == 'typed_flag':
        state['requests'][-1]['provider_charge_confirmed'] = 0
    elif damage == 'drop':
        state['requests'].pop()
    elif damage == 'duplicate':
        state['requests'][1] = deepcopy(state['requests'][0])
    elif damage == 'repriced':
        state['requests'][-1]['cost_usd'] = '0'
    else:
        state['requests'][-1]['attempt'] = settled_history[2] + ':fresh_integration'
    write(ledger.path, state)
    with pytest.raises(registration.BudgetStop, match='continued billing history changed'):
        open_history(settled_history)
    assert all(path.read_bytes() == raw for path, raw in settled_history[-1].items())


def test_fresh_twenty_dollar_cap_does_not_refund_prior_cost_or_grant_extra_credit(settled_history):
    ledger = open_history(settled_history)
    identity = settled_history[2] + ':fresh_integration'
    before = registration.read_json(ledger.path)['requests']
    with pytest.raises(registration.BudgetStop):
        ledger.reserve(identity, '20.01', 'd'*64)
    state = registration.read_json(ledger.path)
    assert canonical(state['requests']) == canonical(before)
    assert state['additional_cap_usd'] == '500'
    assert state['stopped_attempts'][identity]['paid_request'] is False
    assert Decimal('500') - sum(Decimal(row['cost_usd']) for row in state['requests']) == Decimal('31')
    with pytest.raises(registration.BudgetStop, match='previously stopped'):
        ledger.reserve(identity, '1', 'e'*64)


@pytest.mark.parametrize('cap', ['600', '400'])
def test_selected_same_cap_authority_cannot_be_recredited_or_dropped(settled_history, cap):
    settled_history[0]['budget']['additional_usd'] = cap
    with pytest.raises(registration.BudgetStop):
        open_history(settled_history)
    assert not Path(settled_history[0]['budget']['ledger_path']).exists()


@pytest.fixture
def owned_history(settled_history, tmp_path):
    import sequence_claim
    manifest, path, _, previous, _, _ = settled_history
    manifest['sequence_state'] = str(tmp_path/'audit_sequence.json')
    manifest['sequence_claim'] = {'protocol': 'durable_sequence_claim_v1'}
    manifest['pinned_files'].update({str(p): registration.sha(p) for p in sequence_claim.IMPLEMENTATIONS})
    ref = write(path, manifest)
    owner = {'schema_version': 1, 'registration_sha256': previous['manifest_sha256'],
        'ledger_path': manifest['budget']['continuation']['checkpoint'],
        'source_registration_sha256': registration.sha(manifest['parent']['registration']),
        'parent_checkpoint_sha256': 'a'*64}
    state = Path(manifest['sequence_state'])
    write(state, owner)
    return manifest, path, ref['sha256'], state, owner


def test_real_sequence_guard_consumes_only_fresh_identity_and_preserves_source_checkpoint(owned_history):
    manifest, path, identity, state, previous = owned_history
    source = Path(manifest['budget']['continuation']['checkpoint'])
    before = source.read_bytes()
    owner_before = state.read_bytes()
    with registration.sequence_guard(manifest, identity):
        ledger = registration.open_audit_ledger(manifest, path, identity)
        assert len(registration.read_json(ledger.path)['requests']) == 1851
    after = state.read_bytes()
    assert registration.read_json(state)['registration_sha256'] == identity
    assert (path.parent/'sequence_claim/predecessor.json').read_bytes() == owner_before
    assert (path.parent/'sequence_claim/owner.json').read_bytes() == after
    with pytest.raises(registration.BudgetStop, match='already consumed'):
        with registration.sequence_guard(manifest, identity):
            pytest.fail('consumed operational attempt reopened')
    assert state.read_bytes() == after
    assert source.read_bytes() == before
    assert previous['registration_sha256'] != identity


@pytest.mark.parametrize('damage', ['advanced_tip', 'foreign_identity', 'foreign_origin', 'missing_owner'])
def test_sequence_stale_or_missing_tip_cannot_create_ledger_or_claim(owned_history, tmp_path, damage):
    manifest, path, identity, state, owner = owned_history
    if damage == 'advanced_tip':
        owner['ledger_path'] = str(tmp_path/'later/billing.json')
        owner['registration_sha256'] = 'f'*64
    elif damage == 'foreign_identity':
        owner['registration_sha256'] = 'e'*64
    elif damage == 'foreign_origin':
        owner['source_registration_sha256'] = 'd'*64
    else:
        state.unlink()
    if damage != 'missing_owner':
        write(state, owner)
    before = state.read_bytes() if state.exists() else None
    with pytest.raises(registration.BudgetStop):
        with registration.sequence_guard(manifest, identity):
            pytest.fail('a stale or missing owner entered mutable work')
    assert (state.read_bytes() if state.exists() else None) == before
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()


@pytest.fixture
def checkpoint_source(tmp_path, monkeypatch):
    from audit_controls.test_worker_checkpoint import make_fixture as source_fixture
    return source_fixture(tmp_path, monkeypatch)


def test_collective_source_proof_binds_every_worker_to_one_original_identity(checkpoint_source):
    from audit_controls import worker_checkpoint as checkpoint
    c = checkpoint_source
    before = {p: p.read_bytes() for p in c.root.rglob('*') if p.is_file()}
    source = checkpoint.validate(c.manifest)
    assert [worker['id'] for worker in source.workers] == [worker['id'] for worker in c.workers]
    assert source.sha256 == registration.sha(c.source_registration)
    assert all(ref['path'].startswith(str(c.root) + '/') for ref in source.closure_refs.values())
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert not Path(c.manifest['budget']['ledger_path']).exists()


@pytest.mark.parametrize('damage', ['foreign_one_worker', 'foreign_whole_proof', 'no_workers'])
def test_pinned_foreign_or_partial_worker_proof_cannot_replace_exact_predecessor(checkpoint_source,
                                                                              tmp_path, monkeypatch, damage):
    from audit_controls import worker_checkpoint as checkpoint
    from audit_controls.test_worker_checkpoint import make_fixture as source_fixture
    c = checkpoint_source
    other_root = tmp_path/'foreign'
    other_root.mkdir()
    other = source_fixture(other_root, monkeypatch)
    if damage == 'foreign_one_worker':
        c.manifest[checkpoint.KEY]['workers'][0] = deepcopy(other.proof['workers'][0])
    elif damage == 'foreign_whole_proof':
        c.manifest[checkpoint.KEY] = deepcopy(other.proof)
    else:
        c.manifest[checkpoint.KEY]['workers'] = []
    # A coherently pinned foreign identity must still fail. The zero-roster
    # selection fails before pin collection itself can succeed.
    if damage != 'no_workers':
        c.manifest['pinned_files'].update({str(p): registration.sha(p)
                                         for p in checkpoint.proof_paths(c.manifest)})
    with pytest.raises(registration.BudgetStop):
        checkpoint.validate(c.manifest)
    assert not Path(c.manifest['budget']['ledger_path']).exists()


def test_real_checkpoint_prepare_then_claim_imports_once_and_keeps_historical_owner_valid(prepared_source,
                                                                                       tmp_path):
    from audit_controls import prepare, worker_checkpoint as checkpoint
    from audit_controls.test_worker_checkpoint import freeze
    args, source, old_path = prepared_source
    source_before = freeze(old_path.parent)
    owner_path = Path(source['sequence_state'])
    owner_before = owner_path.read_bytes()
    path = prepare.prepare(**args, destination=tmp_path/'fresh-checkpoint')
    manifest = registration.validate_registration(path)
    identity = registration.sha(path)
    assert owner_path.read_bytes() == owner_before
    assert not Path(manifest['budget']['ledger_path']).exists()
    with registration.sequence_guard(manifest, identity):
        ledger = registration.open_audit_ledger(manifest, path, identity)
        prior = registration.read_json(source['budget']['ledger_path'])['requests']
        assert canonical(registration.read_json(ledger.path)['requests']) == canonical(prior)
        registration.open_audit_ledger(manifest, path, identity)
        assert canonical(registration.read_json(ledger.path)['requests']) == canonical(prior)
    assert checkpoint.validate(manifest).sha256 == registration.sha(old_path)
    assert (path.parent/'sequence_claim/predecessor.json').read_bytes() == owner_before
    assert source_before == freeze(old_path.parent)
    assert [child['id'] for child in manifest['audit_batches']['children']] == ['integration']


def test_owner_advance_after_real_preparation_blocks_checkpoint_launch_without_new_claim(prepared_source,
                                                                                     tmp_path):
    from audit_controls import prepare
    args, source, _ = prepared_source
    path = prepare.prepare(**args, destination=tmp_path/'prepared-before-race')
    manifest = registration.validate_registration(path)
    state = Path(source['sequence_state'])
    later = registration.read_json(state)
    later.update(registration_sha256='f'*64, ledger_path=str(tmp_path/'later/billing.json'))
    write(state, later)
    advanced = state.read_bytes()
    with pytest.raises(registration.BudgetStop, match='billing fork'):
        with registration.sequence_guard(manifest, registration.sha(path)):
            pytest.fail('a concurrently consumed source admitted a second successor')
    assert state.read_bytes() == advanced
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()


@pytest.fixture
def aggregate_accounting(tmp_path, monkeypatch):
    """Real aggregate accounting with typed child/source-proof seams isolated.

    Other tests exercise real proof and child closure. Here those seams provide
    invented receipts so each accounting counterexample reaches this gate.
    """
    from audit_controls import batch_native as runtime, worker_checkpoint as checkpoint
    root = tmp_path/'aggregate'
    child = root/'attempt/children/integration'
    child.mkdir(parents=True)
    source_ledger = tmp_path/'source-billing.json'
    historical = [{'id': 'old-worker', 'attempt': 'old:batch', 'status': 'settled',
                   'cost_usd': '3', 'provider_charge_confirmed': False,
                   'provider_charge_usd': None},
                  {'id': 'old-integration', 'attempt': 'old:batch', 'status': 'settled',
                   'cost_usd': '4'}]
    write(source_ledger, {'requests': historical})
    m = {checkpoint.KEY: {'source_ledger': {'path': str(source_ledger)}},
         'job': {'id': 'new', 'attempt_dir': str(root/'attempt'),
                 'audit_path': str(root/'audit.json'), 'deadline_seconds': 100},
         'budget': {'ledger_path': str(root/'billing.json'),
                    'per_job_attempt_usd': {'new': '20'}}}
    path = root/'registration.json'
    ref = write(path, m)
    identity = ref['sha256']
    current = [{'id': 'new-one', 'attempt': identity+':new', 'status': 'settled',
                'cost_usd': '2', 'attempt_cap_usd': '20'},
               {'id': 'new-two', 'attempt': identity+':new', 'status': 'settled',
                'cost_usd': '1', 'attempt_cap_usd': '20'}]
    write(m['budget']['ledger_path'], {'requests': deepcopy(historical+current)})
    closure = {'child_id': 'integration', 'closure_sha256': 'a'*64,
        'request_rows': deepcopy(current), 'evidence': {'batch_child': {'validation': {'passed': True}}},
        'frozen_evidence': {'files': {}}}
    inherited = [{'child_id': 'worker_0001', 'request_rows': [deepcopy(historical[0])]}]
    lineage = {'synthetic': 'old registration worker evidence, not scientific acceptance'}
    assembly = {'audit': {'sha256': 'b'*64}, 'lineage': {'path': str(root/'lineage.json')}}
    result = {'registration_sha256': identity, 'job_id': 'new', 'audit_sha256': 'b'*64,
        'validation': {'passed': True}, 'evidence': {
            'batch_children': [{'id': 'integration', 'closure_sha256': 'a'*64}],
            'worker_checkpoint': deepcopy(lineage), 'aggregate_elapsed_seconds': 1,
            'assembly': deepcopy(assembly)}}
    monkeypatch.setattr(runtime, '_identity', lambda manifest: identity)
    monkeypatch.setattr(runtime.output, 'configuration', lambda *args: {
        'children': [{'id': 'integration', 'attempt_dir': str(child)}]})
    monkeypatch.setattr(runtime, 'verify_child_closure', lambda *args: closure)
    monkeypatch.setattr(checkpoint, 'validate', lambda *args: SimpleNamespace(evidence_paths=frozenset({source_ledger})))
    monkeypatch.setattr(runtime.output, 'worker_closures', lambda *args: inherited)
    monkeypatch.setattr(runtime.output, 'checkpoint_lineage', lambda *args: lineage)
    monkeypatch.setattr(runtime.output, 'validate_output', lambda *args: assembly)
    monkeypatch.setattr(runtime.output, 'assembly_paths', lambda *args: (root/'assembly', root/'ready'))
    return SimpleNamespace(runtime=runtime, m=m, path=path, identity=identity,
        historical=historical, current=current, closure=closure, inherited=inherited, result=result)


def check_aggregate(case):
    return case.runtime.verify_aggregate_closure(case.m, case.path, case.result)


def test_aggregate_charges_only_new_integration_while_retaining_old_workers(aggregate_accounting):
    c = aggregate_accounting
    assert Path(c.m['job']['audit_path']) in check_aggregate(c)
    rows = registration.read_json(c.m['budget']['ledger_path'])['requests']
    assert sum(Decimal(row['cost_usd']) for row in rows) == Decimal('10')
    assert sum(Decimal(row['cost_usd']) for row in rows if row['attempt'] == c.identity+':new') == Decimal('3')
    assert rows[0]['provider_charge_confirmed'] is False


@pytest.mark.parametrize('damage', ['old_worker_id', 'old_integration_id', 'duplicate_new_id',
    'missing_current', 'unassigned_current', 'foreign_current', 'typed_prefix', 'dropped_prefix',
    'worker_stage_cap', 'wrong_attempt_cap', 'over_fresh_cap', 'unsettled', 'missing_lineage'])
def test_aggregate_refuses_reattribution_or_unaccounted_membership(aggregate_accounting, damage):
    c = aggregate_accounting
    state = registration.read_json(c.m['budget']['ledger_path'])
    if damage in ('old_worker_id', 'old_integration_id', 'duplicate_new_id'):
        identity = {'old_worker_id': 'old-worker', 'old_integration_id': 'old-integration',
                    'duplicate_new_id': 'new-one'}[damage]
        state['requests'][-1]['id'] = identity
        c.closure['request_rows'][-1]['id'] = identity
    elif damage == 'missing_current':
        c.closure['request_rows'].pop()
    elif damage == 'unassigned_current':
        state['requests'].append({**deepcopy(c.current[0]), 'id': 'unassigned-new-worker'})
    elif damage == 'foreign_current':
        state['requests'].append({**deepcopy(c.current[0]), 'id': 'foreign', 'attempt': 'foreign:job'})
    elif damage == 'typed_prefix':
        state['requests'][0]['provider_charge_confirmed'] = 0
    elif damage == 'dropped_prefix':
        state['requests'].pop(0)
    elif damage == 'worker_stage_cap':
        state['requests'][-1]['stage_cap_usd'] = '36'
    elif damage == 'wrong_attempt_cap':
        state['requests'][-1]['attempt_cap_usd'] = '40'
    elif damage == 'over_fresh_cap':
        state['requests'][-1]['cost_usd'] = '19'
    elif damage == 'unsettled':
        state['requests'][-1]['status'] = 'pending'
    else:
        c.result['evidence'].pop('worker_checkpoint')
    write(c.m['budget']['ledger_path'], state)
    with pytest.raises(registration.BudgetStop):
        check_aggregate(c)


@pytest.mark.parametrize('new_debits', [6, 7])
def test_new_attempt_debit_limit_counts_new_rows_without_erasing_old_debits(aggregate_accounting,
                                                                         monkeypatch, new_debits):
    c = aggregate_accounting
    basis = 'registered_stall_policy_full_reservation_debit'
    historical = deepcopy(c.historical)
    for row in historical:
        row.update(settlement_basis=basis, provider_charge_confirmed=False, provider_charge_usd=None)
    write(c.m['audit_worker_checkpoint']['source_ledger']['path'], {'requests': historical})
    c.inherited[0]['request_rows'] = [deepcopy(historical[0])]
    current = [{**deepcopy(c.current[0]), 'id': f'new-debit-{i}', 'cost_usd': '1',
        'settlement_basis': basis, 'provider_charge_confirmed': False, 'provider_charge_usd': None}
        for i in range(new_debits)]
    write(c.m['budget']['ledger_path'], {'requests': historical+current})
    c.closure['request_rows'] = deepcopy(current)
    monkeypatch.setattr(c.runtime, 'native_stall_policy', lambda manifest: {'max_stall_debits': 6})
    if new_debits == 6:
        check_aggregate(c)
        rows = registration.read_json(c.m['budget']['ledger_path'])['requests']
        assert sum(row.get('settlement_basis') == basis for row in rows) == 8
        assert canonical(rows[:2]) == canonical(historical)
        assert all(row['provider_charge_confirmed'] is False for row in rows)
    else:
        with pytest.raises(registration.BudgetStop, match='stall allowance'):
            check_aggregate(c)
