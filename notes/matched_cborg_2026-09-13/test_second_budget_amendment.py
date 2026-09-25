"""Synthetic second-increase authority, history and once-only import tests."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

import budget_amendment as amendment
from budgeted_cborg import BudgetStop, Ledger
from test_budget_amendment import make_fixture, write


def canonical(value):
    # Independent serialization, rather than obtaining expected digests from
    # the implementation under test.
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def second_authority(proof, origin, ledger):
    return {'kind': 'audit_sequence_additional_budget_authorization_receipt', 'schema_version': 2,
        'authorization': {'additional_budget_authorized': True, 'currency': 'USD',
            'user_quote': proof['authorization_quote'], 'prior_shared_cap_usd': proof['prior_total_usd'],
            'additional_authorized_usd': proof['increase_usd'], 'new_shared_cap_usd': proof['total_usd']},
        'lineage': {'origin_registration': deepcopy(proof['origin_registration']),
            'prior_amendment_sha256': hashlib.sha256(canonical(proof['prior_amendment'])).hexdigest(),
            'original_shared_cap_usd': str(Decimal(str(origin['budget']['additional_usd'])))},
        'predecessor': {'registration_path': proof['predecessor_registration']['path'],
            'registration_sha256': proof['predecessor_registration']['sha256'],
            'ledger_path': proof['predecessor_ledger']['path'], 'ledger_sha256': proof['predecessor_ledger']['sha256'],
            'canonical_owner_sha256': proof['predecessor_owner']['sha256'],
            'registered_predecessor_shared_cap_usd': proof['prior_total_usd'],
            'sequence_settled_rows': len(ledger['requests']),
            'sequence_accounted_usd': str(sum((Decimal(r['cost_usd']) for r in ledger['requests']), Decimal(0)))}}


def make_second_fixture(root, *, first=None):
    """Return proof/origin/immediate500ledger/600manifest; all files invented."""
    root = Path(root)
    if first is None:
        origin = {'budget': {'additional_usd': 400, 'per_attempt_usd': 5,
            'per_job_attempt_usd': {'generation': 400},
            'prices_per_token': {'input': '0.000005', 'output': '0.000025'}}}
        first = make_fixture(root/'first', generation=origin)
    prior, origin, initial, _ = first
    ledger_path = root/'immediate/billing.json'
    previous = {'kind': 'd4d_native_audit_continuation',
        'parent': {'registration': prior['origin_registration']['path']},
        'sequence_state': str(root/'live-owner.json'), amendment.KEY: deepcopy(prior),
        'budget': {'additional_usd': '500', 'per_attempt_usd': '5',
            'per_job_attempt_usd': {'preceding-integration': '20'}, 'ledger_path': str(ledger_path),
            'continuation': {'sha256': prior['predecessor_ledger']['sha256']}}}
    if 'prices_per_token' in origin['budget']:
        previous['budget']['prices_per_token'] = deepcopy(origin['budget']['prices_per_token'])
    previous_ref = write(root/'immediate/registration.json', previous)
    ledger = {'manifest_sha256': previous_ref['sha256'], 'additional_cap_usd': '500',
        'attempt_cap_usd': '5', 'requests': deepcopy(initial['requests']) + [
            {'id': 'later-ordinary', 'attempt': 'preceding-integration', 'status': 'settled', 'cost_usd': '0.75'},
            {'id': 'later-debit', 'attempt': 'preceding-integration', 'status': 'settled', 'cost_usd': '2.50',
             'accounting_basis': 'registered_stall_policy_full_reservation_debit',
             'provider_charge_confirmed': False, 'provider_charge_usd': None}],
        'stopped_attempts': {'preceding-integration': {'reason': 'synthetic stop'}}}
    owner = {'schema_version': 1, 'registration_sha256': previous_ref['sha256'],
        'ledger_path': str(ledger_path), 'source_registration_sha256': prior['origin_registration']['sha256'],
        'parent_checkpoint_sha256': prior['predecessor_ledger']['sha256']}
    owner_ref = write(root/'immediate/sequence_claim/owner.json', owner)
    write(root/'live-owner.json', owner)
    proof = {'kind': amendment.SECOND_KIND, 'origin_registration': deepcopy(prior['origin_registration']),
        'predecessor_registration': previous_ref, 'predecessor_ledger': write(ledger_path, ledger),
        'predecessor_owner': owner_ref, 'prior_total_usd': '500', 'increase_usd': '100', 'total_usd': '600',
        'default_attempt_usd': '5', 'prior_amendment': deepcopy(prior),
        'authorization_quote': 'Approve the synthetic second $100 increase.'}
    proof['authorization'] = write(root/'second-authority.json', second_authority(proof, origin, ledger))
    manifest = {'parent': {'registration': prior['origin_registration']['path']}, amendment.KEY: proof,
        'budget': {'additional_usd': '600', 'per_attempt_usd': '5',
                   'per_job_attempt_usd': {'fresh-only': '60'}}, 'pinned_files': {}}
    repin(manifest)
    return proof, origin, ledger, manifest


def repin(manifest):
    proof = manifest[amendment.KEY]
    manifest['pinned_files'] = {node[key]['path']: node[key]['sha256']
        for node in (proof, proof['prior_amendment']) for key in amendment.REFS}
    implementation = Path(amendment.__file__).resolve()
    manifest['pinned_files'][str(implementation)] = hashlib.sha256(implementation.read_bytes()).hexdigest()


def rebind_documents(proof, origin, ledger, manifest, *, previous=None, owner=None):
    """Re-sign invented documents so negatives test semantics, not stale hashes."""
    if previous is not None:
        proof['predecessor_registration'] = write(proof['predecessor_registration']['path'], previous)
        ledger['manifest_sha256'] = proof['predecessor_registration']['sha256']
        if owner is None:
            owner = json.loads(Path(proof['predecessor_owner']['path']).read_bytes())
        owner['registration_sha256'] = proof['predecessor_registration']['sha256']
    if owner is not None:
        proof['predecessor_owner'] = write(proof['predecessor_owner']['path'], owner)
    proof['predecessor_ledger'] = write(proof['predecessor_ledger']['path'], ledger)
    proof['authorization'] = write(proof['authorization']['path'], second_authority(proof, origin, ledger))
    repin(manifest)


def test_second_increase_imports_all_rows_once_without_touching_old_documents(tmp_path):
    proof, origin, previous, manifest = make_second_fixture(tmp_path)
    paths = amendment.paths(manifest)
    assert len(paths) == 10  # implementation + nine immutable documents
    before = {p: p.read_bytes() for p in paths}
    live = (tmp_path/'live-owner.json').read_bytes()
    assert amendment.effective_total(manifest, origin) == Decimal(600)
    bridge = amendment.ledger_bridge(manifest, previous, checkpoint_sha256=proof['predecessor_ledger']['sha256'])
    ledger = Ledger(tmp_path/'fresh.json', manifest_sha256='a'*64, total_cap=600,
                    attempt_caps_usd={'fresh-only': 60})
    for _ in range(2):
        ledger.continue_from(proof['predecessor_ledger']['path'],
            expected_sha256=proof['predecessor_ledger']['sha256'], expected_cost_usd='8.25', **bridge)
    state = json.loads(ledger.path.read_bytes())
    assert canonical(state['requests']) == canonical(previous['requests'])
    assert state['continued_from']['budget_amendment_sha256'] == hashlib.sha256(canonical(proof)).hexdigest()
    assert state['additional_cap_usd'] == '600' and state['attempt_cap_usd'] == '5'
    assert before == {p: p.read_bytes() for p in paths}
    assert (tmp_path/'live-owner.json').read_bytes() == live


def test_same_cap_descendant_and_reopen_never_add_credit(tmp_path):
    proof, origin, previous, manifest = make_second_fixture(tmp_path)
    first = Ledger(tmp_path/'first600.json', manifest_sha256='a'*64, total_cap=600)
    first.continue_from(proof['predecessor_ledger']['path'], expected_sha256=proof['predecessor_ledger']['sha256'],
                        expected_cost_usd='8.25', budget_amendment=proof)
    first_ref = {'path': str(first.path), 'sha256': hashlib.sha256(first.path.read_bytes()).hexdigest()}
    imported = json.loads(first.path.read_bytes())
    bridge = amendment.ledger_bridge(manifest, imported, checkpoint_sha256=first_ref['sha256'])
    second = Ledger(tmp_path/'later600.json', manifest_sha256='b'*64, total_cap=600)
    for _ in range(2):
        second.continue_from(first.path, expected_sha256=first_ref['sha256'], expected_cost_usd='8.25', **bridge)
    state = json.loads(second.path.read_bytes())
    assert 'budget_amendment_sha256' not in state['continued_from']
    assert canonical(state['requests']) == canonical(previous['requests'])
    state['requests'][-1]['provider_charge_confirmed'] = 0
    write(second.path, state)
    with pytest.raises(BudgetStop, match='continued billing history changed'):
        second.continue_from(first.path, expected_sha256=first_ref['sha256'], expected_cost_usd='8.25', **bridge)


@pytest.mark.parametrize('mode', ['third', 'self', 'unknown', 'missing', 'extra'])
def test_nonrecursive_selection_refuses_before_document_read(tmp_path, monkeypatch, mode):
    proof, _, _, _ = make_second_fixture(tmp_path)
    if mode == 'third': proof['prior_amendment'] = deepcopy(proof)
    elif mode == 'self': proof['prior_amendment'] = proof
    elif mode == 'unknown': proof['prior_amendment']['kind'] = 'future_version'
    elif mode == 'missing': del proof['prior_amendment']
    else: proof['max_chain_depth'] = 8
    monkeypatch.setattr(amendment, '_read', lambda _: pytest.fail('selection read evidence'))
    with pytest.raises(BudgetStop): amendment.selection(proof)


@pytest.mark.parametrize('key,value', [('prior_total_usd', '400'), ('total_usd', '700'),
    ('increase_usd', '0'), ('default_attempt_usd', '6'), ('increase_usd', True),
    ('total_usd', 'NaN'), ('increase_usd', '1e2'), ('authorization_quote', ''), ('authorization_quote', ' ')])
def test_second_selection_rejects_cap_or_quote_escape(tmp_path, key, value):
    proof, _, _, _ = make_second_fixture(tmp_path); proof[key] = value
    with pytest.raises(BudgetStop): amendment.selection(proof)


@pytest.mark.parametrize('key', amendment.REFS[1:])
def test_old_authority_or_predecessor_cannot_be_reused(tmp_path, key):
    proof, _, _, _ = make_second_fixture(tmp_path)
    proof[key] = deepcopy(proof['prior_amendment'][key])
    with pytest.raises(BudgetStop): amendment.selection(proof)


@pytest.mark.parametrize('key', amendment.REFS)
def test_old_authority_is_transitively_pinned(tmp_path, key):
    proof, origin, _, manifest = make_second_fixture(tmp_path)
    manifest['pinned_files'].pop(proof['prior_amendment'][key]['path'])
    with pytest.raises(BudgetStop, match='unpinned'): amendment.effective_total(manifest, origin)
    assert amendment.effective_total(manifest, origin, require_pins=False) == 600


@pytest.mark.parametrize('mutation', ['drop', 'bool', 'float', 'id', 'cost', 'duplicate', 'pending', 'nonfinite'])
def test_rehashed_second_anchor_still_preserves_v1_history_and_settlement(tmp_path, mutation):
    proof, origin, previous, manifest = make_second_fixture(tmp_path)
    rows = previous['requests']
    if mutation == 'drop': rows.pop(0)
    elif mutation == 'bool': rows[1]['provider_charge_confirmed'] = 0
    elif mutation == 'float': rows[0]['synthetic_integer'] = 1.0
    elif mutation == 'id': rows[0]['id'] = 'relabelled'
    elif mutation == 'cost': rows[0]['cost_usd'] = '0'
    elif mutation == 'duplicate': rows.append(deepcopy(rows[-1]))
    elif mutation == 'pending': rows[-1]['status'] = 'pending'
    else: rows[-1]['cost_usd'] = 'NaN'
    rebind_documents(proof, origin, previous, manifest)
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)


@pytest.mark.parametrize('mutation', ['latest_drop', 'latest_relabel', 'unknown_flag', 'checkpoint_hash', 'rewind'])
def test_full_immediate_checkpoint_is_required_not_just_the_old_v1_prefix(tmp_path, mutation):
    proof, _, previous, manifest = make_second_fixture(tmp_path)
    supplied = deepcopy(previous); identity = proof['predecessor_ledger']['sha256']
    if mutation == 'latest_drop': supplied['requests'].pop()
    elif mutation == 'latest_relabel': supplied['requests'][-1]['attempt'] = 'new-owner'
    elif mutation == 'unknown_flag': supplied['requests'][-1]['provider_charge_confirmed'] = 0
    elif mutation == 'checkpoint_hash': identity = '0'*64
    else: supplied = json.loads(Path(proof['prior_amendment']['predecessor_ledger']['path']).read_bytes())
    with pytest.raises(BudgetStop): amendment.validate_predecessor(manifest, supplied, checkpoint_sha256=identity)


@pytest.mark.parametrize('mutation', ['dropped', 'different', 'origin', 'prices', 'cap', 'owner_float', 'owner_old'])
def test_exact_immediate_authority_and_consumed_owner_required(tmp_path, mutation):
    proof, origin, ledger, manifest = make_second_fixture(tmp_path)
    previous = json.loads(Path(proof['predecessor_registration']['path']).read_bytes())
    owner = json.loads(Path(proof['predecessor_owner']['path']).read_bytes())
    if mutation == 'dropped': previous.pop(amendment.KEY)
    elif mutation == 'different': previous[amendment.KEY]['authorization']['sha256'] = 'a'*64
    elif mutation == 'origin': previous['parent']['registration'] = str(tmp_path/'foreign.json')
    elif mutation == 'prices': previous['budget']['prices_per_token']['input'] = '0'
    elif mutation == 'cap': previous['budget']['per_attempt_usd'] = 60
    elif mutation == 'owner_float': owner['schema_version'] = 1.0
    else: owner['parent_checkpoint_sha256'] = 'f'*64
    rebind_documents(proof, origin, ledger, manifest, previous=previous, owner=owner)
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)


@pytest.mark.parametrize('section,key,value', [
    ('authorization', 'additional_budget_authorized', 1),
    ('authorization', 'user_quote', 'a different response'),
    ('authorization', 'currency', 'EUR'), ('authorization', 'new_shared_cap_usd', '700'),
    ('lineage', 'prior_amendment_sha256', '0'*64), ('lineage', 'original_shared_cap_usd', '500'),
    ('predecessor', 'sequence_settled_rows', 4.0), ('predecessor', 'sequence_accounted_usd', '5'),
    ('predecessor', 'canonical_owner_sha256', '0'*64)])
def test_new_authority_must_exactly_name_quote_lineage_and_full_tip(tmp_path, section, key, value):
    proof, origin, _, manifest = make_second_fixture(tmp_path)
    authority = json.loads(Path(proof['authorization']['path']).read_bytes())
    authority[section][key] = value
    proof['authorization'] = write(proof['authorization']['path'], authority); repin(manifest)
    with pytest.raises(BudgetStop): amendment.effective_total(manifest, origin)


def test_v2_does_not_autoselect_itself_or_grant_a_larger_ledger_default(tmp_path):
    proof, origin, previous, manifest = make_second_fixture(tmp_path)
    with pytest.raises(BudgetStop): amendment.inherit({amendment.KEY: proof['prior_amendment']}, manifest)
    target = {'budget': deepcopy(manifest['budget']), 'pinned_files': dict(manifest['pinned_files']),
        'budget_sequence': {'origin': {'registration': deepcopy(proof['origin_registration'])}}}
    amendment.inherit(manifest, target)
    assert amendment.effective_total(target, origin) == 600 and target[amendment.KEY] == proof
    for total, default in [(700, 5), (600, 60)]:
        ledger = Ledger(tmp_path/f'denied-{total}-{default}.json', manifest_sha256='f'*64,
                        total_cap=total, attempt_cap=default)
        with pytest.raises(BudgetStop):
            ledger.continue_from(proof['predecessor_ledger']['path'],
                expected_sha256=proof['predecessor_ledger']['sha256'], expected_cost_usd='8.25', budget_amendment=proof)
        assert not ledger.path.exists()


@pytest.mark.parametrize('prices', [None, {}])
def test_second_increase_cannot_hide_prices_by_omitting_both_copies(tmp_path, prices):
    generation = {'budget': {'additional_usd': 400, 'per_attempt_usd': 5}}
    if prices is not None:
        generation['budget']['prices_per_token'] = prices
    first = make_fixture(tmp_path/'first', generation=generation)
    _, origin, _, manifest = make_second_fixture(tmp_path/'second', first=first)
    with pytest.raises(BudgetStop, match='caps or prices'):
        amendment.effective_total(manifest, origin)
