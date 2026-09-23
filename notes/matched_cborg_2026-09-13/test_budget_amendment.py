"""Synthetic immutable budget authority and exact ledger import tests."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

import budget_amendment as amendment
from budgeted_cborg import BudgetStop, Ledger


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def make_fixture(root, *, generation=None, generation_path=None, rows=None):
    """Reusable wholly invented proof; an existing synthetic origin is optional."""
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    if generation_path is None:
        generation_path = root/'origin.json'
        if generation is None:
            generation = {'repository': str(root), 'budget': {'additional_usd': 400,
                'per_attempt_usd': 5, 'ledger_path': str(root/'original-billing.json')}}
        origin_ref = write(generation_path, generation)
    else:
        generation_path = Path(generation_path)
        actual = json.loads(generation_path.read_bytes())
        if generation is None:
            generation = actual
        assert actual == generation
        origin_ref = {'path': str(generation_path), 'sha256': hashlib.sha256(generation_path.read_bytes()).hexdigest()}
    ledger_path = root/'anchor/billing.json'
    previous = {'kind': 'd4d_native_audit_continuation', 'parent': {'registration': str(generation_path)},
        'sequence_state': str(root/'live-owner.json'),
        'budget': {'additional_usd': 400, 'per_attempt_usd': 5, 'ledger_path': str(ledger_path),
                   'continuation': {'sha256': 'c'*64}}}
    previous_ref = write(root/'anchor/registration.json', previous)
    if rows is None:
        rows = [{'id': 'synthetic-settled', 'attempt': 'old-job', 'status': 'settled', 'cost_usd': '2', 'synthetic_integer': 1},
                {'id': 'synthetic-unknown-fee', 'attempt': 'old-job', 'status': 'settled', 'cost_usd': '3',
                 'accounting_basis': 'registered_stall_policy_full_reservation_debit',
                 'provider_charge_confirmed': False, 'provider_charge_usd': None}]
    ledger = {'manifest_sha256': previous_ref['sha256'], 'additional_cap_usd': '400',
              'attempt_cap_usd': '5', 'requests': deepcopy(rows)}
    ledger_ref = write(ledger_path, ledger)
    owner = {'schema_version': 1, 'registration_sha256': previous_ref['sha256'],
             'ledger_path': str(ledger_path), 'source_registration_sha256': origin_ref['sha256'],
             'parent_checkpoint_sha256': 'c'*64}
    owner_ref = write(root/'anchor/sequence_claim/owner.json', owner)
    authority = {'kind': 'audit_sequence_additional_budget_authorization_receipt', 'schema_version': 1,
        'authorization': {'additional_budget_authorized': True, 'currency': 'USD', 'user_quote': 'Approve synthetic $100',
            'prior_shared_cap_usd': '400', 'additional_authorized_usd': '100', 'new_shared_cap_usd': '500'},
        'predecessor': {'registration_path': previous_ref['path'], 'registration_sha256': previous_ref['sha256'],
            'ledger_path': ledger_ref['path'], 'ledger_sha256': ledger_ref['sha256'],
            'canonical_owner_sha256': owner_ref['sha256'], 'registered_predecessor_shared_cap_usd': '400',
            'sequence_settled_rows': len(rows), 'sequence_accounted_usd': str(sum((Decimal(r['cost_usd']) for r in rows), Decimal(0)))}}
    proof = {'kind': amendment.KIND, 'origin_registration': origin_ref, 'predecessor_registration': previous_ref,
             'predecessor_ledger': ledger_ref, 'predecessor_owner': owner_ref,
             'authorization': write(root/'authority.json', authority), 'prior_total_usd': '400',
             'increase_usd': '100', 'total_usd': '500', 'default_attempt_usd': '5'}
    manifest = {'repository': str(root), 'parent': {'registration': str(generation_path)},
                'budget': {'additional_usd': '500', 'per_attempt_usd': '5'}, amendment.KEY: proof,
                'pinned_files': {proof[k]['path']: proof[k]['sha256'] for k in amendment.REFS}}
    manifest['pinned_files'][str(Path(amendment.__file__).resolve())] = hashlib.sha256(Path(amendment.__file__).read_bytes()).hexdigest()
    return proof, generation, ledger, manifest


def test_positive_proof_and_immutable_ledger_import(tmp_path):
    proof, origin, previous, manifest = make_fixture(tmp_path)
    before = {k: Path(proof[k]['path']).read_bytes() for k in amendment.REFS}
    assert amendment.effective_total(manifest, origin) == Decimal(500)
    assert len(amendment.paths(manifest)) == 6
    bridge = amendment.ledger_bridge(manifest, previous, checkpoint_sha256=proof['predecessor_ledger']['sha256'])
    ledger = Ledger(tmp_path/'next/billing.json', manifest_sha256='d'*64, total_cap=500,
                    attempt_caps_usd={'fresh-job': 40})
    for _ in range(2):
        ledger.continue_from(proof['predecessor_ledger']['path'], expected_sha256=proof['predecessor_ledger']['sha256'],
                             expected_cost_usd='5', **bridge)
    state = json.loads(ledger.path.read_bytes())
    assert state['additional_cap_usd'] == '500' and state['requests'] == previous['requests']
    assert 'budget_amendment_sha256' in state['continued_from']
    assert before == {k: Path(proof[k]['path']).read_bytes() for k in amendment.REFS}


@pytest.mark.parametrize('value', [None, False, True, {}, [], 'increase', {'kind': amendment.KIND}])
def test_bad_selector(value):
    with pytest.raises(BudgetStop): amendment.selection(value)


@pytest.mark.parametrize('key,value', [('total_usd', '600'), ('increase_usd', '0'), ('prior_total_usd', True),
    ('default_attempt_usd', 'NaN'), ('total_usd', '5e2'), ('default_attempt_usd', '0'), ('increase_usd', '-100')])
def test_bad_amounts(tmp_path, key, value):
    proof, _, _, _ = make_fixture(tmp_path); proof[key] = value
    with pytest.raises(BudgetStop): amendment.selection(proof)


@pytest.mark.parametrize('which', ['origin_registration', 'predecessor_registration', 'predecessor_ledger',
                                  'predecessor_owner', 'authorization'])
def test_unpinned_or_changed_authority(tmp_path, which):
    proof, origin, _, manifest = make_fixture(tmp_path)
    manifest['pinned_files'].pop(proof[which]['path'])
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)
    assert amendment.effective_total(manifest, origin, require_pins=False) == 500
    Path(proof[which]['path']).write_bytes(b'changed')
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin, require_pins=False)


def test_explicit_null_not_legacy(tmp_path):
    _, origin, _, manifest = make_fixture(tmp_path); manifest[amendment.KEY] = None
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)


def test_no_proof_keeps_old_cap_and_import_rule(tmp_path):
    proof, origin, _, manifest = make_fixture(tmp_path); del manifest[amendment.KEY]
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)
    manifest['budget']['additional_usd'] = 400
    assert amendment.effective_total(manifest, origin) == 400 and amendment.paths(manifest) == set()
    ledger = Ledger(tmp_path/'new.json', manifest_sha256='a'*64, total_cap=500)
    with pytest.raises(BudgetStop, match='different budget caps'):
        ledger.continue_from(proof['predecessor_ledger']['path'], expected_sha256=proof['predecessor_ledger']['sha256'], expected_cost_usd=5)
    assert not ledger.path.exists()


def test_manifest_origin_and_caps_cannot_change(tmp_path):
    _, origin, _, manifest = make_fixture(tmp_path)
    for key, value in [('additional_usd', '600'), ('per_attempt_usd', '6')]:
        changed = deepcopy(manifest); changed['budget'][key] = value
        with pytest.raises(BudgetStop): amendment.effective_total(changed, origin)
    manifest['parent']['registration'] = str(tmp_path/'another-origin.json')
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)


def test_inheritance_and_shared_origin(tmp_path):
    proof, origin, _, manifest = make_fixture(tmp_path)
    successor = {'budget': deepcopy(manifest['budget']), 'pinned_files': dict(manifest['pinned_files']),
                 'budget_sequence': {'origin': {'registration': deepcopy(proof['origin_registration'])}}}
    amendment.inherit(manifest, successor)
    assert amendment.effective_total(successor, origin) == 500
    assert successor[amendment.KEY] == proof and successor[amendment.KEY] is not proof
    successor[amendment.KEY]['total_usd'] = '600'
    with pytest.raises(BudgetStop): amendment.inherit(manifest, successor)
    with pytest.raises(BudgetStop): amendment.inherit({}, manifest)


def test_later_same_cap_carries_rows_without_reapplying_increase(tmp_path):
    proof, origin, previous, manifest = make_fixture(tmp_path)
    first = Ledger(tmp_path/'first.json', manifest_sha256='d'*64, total_cap=500)
    first.continue_from(proof['predecessor_ledger']['path'], expected_sha256=proof['predecessor_ledger']['sha256'],
                        expected_cost_usd='5', budget_amendment=proof)
    state = json.loads(first.path.read_bytes()); first_ref = {'path': str(first.path), 'sha256': hashlib.sha256(first.path.read_bytes()).hexdigest()}
    bridge = amendment.ledger_bridge(manifest, state, checkpoint_sha256=first_ref['sha256'])
    assert bridge == {'budget_amendment': proof}
    second = Ledger(tmp_path/'second.json', manifest_sha256='e'*64, total_cap=500)
    second.continue_from(first.path, expected_sha256=first_ref['sha256'], expected_cost_usd='5', **bridge)
    carried = json.loads(second.path.read_bytes())
    assert carried['additional_cap_usd'] == '500' and carried['requests'] == previous['requests']
    assert 'budget_amendment_sha256' not in carried['continued_from']
    carried['requests'][1]['provider_charge_confirmed'] = 0
    write(second.path, carried)
    with pytest.raises(BudgetStop, match='continued billing history changed'):
        second.continue_from(first.path, expected_sha256=first_ref['sha256'], expected_cost_usd='5', **bridge)


@pytest.mark.parametrize('mutation', ['id', 'cost', 'unknown', 'drop', 'duplicate', 'pending', 'cap', 'wrong_anchor'])
def test_history_tamper_and_wrong_first_anchor_rejected(tmp_path, mutation):
    proof, _, previous, manifest = make_fixture(tmp_path)
    changed = deepcopy(previous); checkpoint = proof['predecessor_ledger']['sha256']
    if mutation == 'id': changed['requests'][0]['id'] = 'other'
    elif mutation == 'cost': changed['requests'][0]['cost_usd'] = '0'
    elif mutation == 'unknown': changed['requests'][1]['provider_charge_confirmed'] = True
    elif mutation == 'drop': changed['requests'].pop()
    elif mutation == 'duplicate': changed['requests'].append(deepcopy(changed['requests'][0]))
    elif mutation == 'pending': changed['requests'][0]['status'] = 'pending'
    elif mutation == 'cap': changed['additional_cap_usd'] = '600'
    elif mutation == 'wrong_anchor': checkpoint = '0'*64
    with pytest.raises(BudgetStop): amendment.validate_predecessor(manifest, changed, checkpoint_sha256=checkpoint)


@pytest.mark.parametrize('path,value', [(('authorization','additional_budget_authorized'),False),
    (('authorization','additional_budget_authorized'),1), (('authorization','currency'),'EUR'),
    (('authorization','user_quote'),' '), (('authorization','new_shared_cap_usd'),'600'),
    (('predecessor','canonical_owner_sha256'),'0'*64), (('predecessor','sequence_settled_rows'),True),
    (('predecessor','sequence_accounted_usd'),'4'), (('predecessor','registration_sha256'),'0'*64)])
def test_self_consistent_rehashed_authority_still_requires_exact_scope(tmp_path, path, value):
    proof, origin, _, manifest = make_fixture(tmp_path)
    file = Path(proof['authorization']['path']); authority = json.loads(file.read_bytes())
    authority[path[0]][path[1]] = value; proof['authorization'] = write(file, authority)
    manifest['pinned_files'][str(file)] = proof['authorization']['sha256']
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)


def test_live_owner_path_and_symlink_alias_refused(tmp_path):
    proof, _, _, _ = make_fixture(tmp_path)
    owner = Path(proof['predecessor_owner']['path']); alias = tmp_path/'owner-alias.json'; alias.symlink_to(owner)
    proof['predecessor_owner']['path'] = str(alias)
    with pytest.raises(BudgetStop): amendment.selection(proof)


def test_default_cap_and_unrelated_increase_not_ledger_escape(tmp_path):
    proof, _, _, _ = make_fixture(tmp_path)
    for cap, default in [(600, 5), (500, 6), (400, 5)]:
        ledger = Ledger(tmp_path/f'{cap}-{default}.json', manifest_sha256='f'*64, total_cap=cap, attempt_cap=default)
        with pytest.raises(BudgetStop): ledger.continue_from(proof['predecessor_ledger']['path'],
            expected_sha256=proof['predecessor_ledger']['sha256'], expected_cost_usd=5, budget_amendment=proof)
        assert not ledger.path.exists()


@pytest.mark.parametrize('payload', [b'null', b'[]', b'false', b'"private"', b'{broken', b'\xff', b'{"x":1,"x":2}'])
def test_malformed_evidence_is_fixed_budget_stop(tmp_path, payload):
    proof, origin, _, manifest = make_fixture(tmp_path)
    authority = Path(proof['authorization']['path']); authority.write_bytes(payload)
    proof['authorization']['sha256'] = hashlib.sha256(payload).hexdigest()
    manifest['pinned_files'][str(authority)] = proof['authorization']['sha256']
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)


def test_malformed_nested_evidence_is_budget_stop(tmp_path):
    proof, origin, _, manifest = make_fixture(tmp_path)
    path = Path(proof['predecessor_registration']['path'])
    value = json.loads(path.read_bytes()); value['budget'] = []
    proof['predecessor_registration'] = write(path, value)
    manifest['pinned_files'][str(path)] = proof['predecessor_registration']['sha256']
    with pytest.raises(BudgetStop, match='malformed amendment evidence structure'):
        amendment.effective_total(manifest, origin)


@pytest.mark.parametrize('row,key,value', [(1, 'provider_charge_confirmed', 0), (0, 'synthetic_integer', 1.0)])
def test_later_cap_preserves_exact_historical_json_types(tmp_path, row, key, value):
    proof, _, previous, manifest = make_fixture(tmp_path)
    changed = deepcopy(previous); changed['additional_cap_usd'] = '500'; changed['manifest_sha256'] = 'd'*64
    changed['requests'][row][key] = value
    ref = write(tmp_path/'later.json', changed)
    with pytest.raises(BudgetStop, match='rewrites or drops historical rows'):
        amendment.validate_predecessor(manifest, changed, checkpoint_sha256=ref['sha256'])
    ledger = Ledger(tmp_path/'target.json', manifest_sha256='e'*64, total_cap=500)
    with pytest.raises(BudgetStop, match='rewrites or drops historical rows'):
        ledger.continue_from(ref['path'], expected_sha256=ref['sha256'], expected_cost_usd='5', budget_amendment=proof)
    assert not ledger.path.exists()


@pytest.mark.parametrize('target', ['rows', 'identity'])
def test_repeated_amended_import_rejects_typed_destination_mutation(tmp_path, target):
    proof, _, _, _ = make_fixture(tmp_path)
    ledger = Ledger(tmp_path/'new.json', manifest_sha256='d'*64, total_cap=500)
    args = {'expected_sha256': proof['predecessor_ledger']['sha256'], 'expected_cost_usd': '5', 'budget_amendment': proof}
    ledger.continue_from(proof['predecessor_ledger']['path'], **args)
    state = json.loads(ledger.path.read_bytes())
    if target == 'rows': state['requests'][1]['provider_charge_confirmed'] = 0
    else: state['continued_from']['requests'] = 2.0
    raw = write(ledger.path, state)
    with pytest.raises(BudgetStop, match='continued billing history changed'):
        ledger.continue_from(proof['predecessor_ledger']['path'], **args)
    assert hashlib.sha256(ledger.path.read_bytes()).hexdigest() == raw['sha256']
