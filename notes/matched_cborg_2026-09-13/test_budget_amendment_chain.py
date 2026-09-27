"""Chained budget increases after v1 and v2 (#2468); every document is invented."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

import budget_amendment as amendment
from budgeted_cborg import BudgetStop, Ledger
from test_budget_amendment import write
from test_second_budget_amendment import canonical, make_second_fixture, second_authority


def links(proof):
    """Independent traversal of the chain, oldest link first."""
    out = [proof]
    while 'prior_amendment' in out[-1]:
        out.append(out[-1]['prior_amendment'])
    return out[::-1]


def repin(manifest):
    manifest['pinned_files'] = {link[key]['path']: link[key]['sha256']
                                for link in links(manifest[amendment.KEY]) for key in amendment.REFS}
    implementation = Path(amendment.__file__).resolve()
    manifest['pinned_files'][str(implementation)] = hashlib.sha256(implementation.read_bytes()).hexdigest()


def chain_authority(proof, origin, ledger):
    value = second_authority(proof, origin, ledger)
    value['schema_version'] = amendment.CHAIN_RECEIPT_VERSION
    return value


def make_chain_fixture(root, *, prior=None, increase='200', quote='increase the budget by $200',
                       kind='d4d_native_audit_continuation'):
    """One chained link on `prior` (a fixture tuple): the immediate audit at the prior total,
    its settled ledger carrying every earlier row, and a manifest at the new total."""
    root = Path(root)
    if prior is None:
        prior = make_second_fixture(root / 'second')
    prior_proof, origin, prior_ledger, _ = prior
    old = Decimal(prior_proof['total_usd'])
    ledger_path = root / 'immediate/billing.json'
    previous = {'kind': kind,
        'parent': {'registration': prior_proof['origin_registration']['path']},
        'sequence_state': str(root / 'live-owner.json'), amendment.KEY: deepcopy(prior_proof),
        'budget': {'additional_usd': str(old), 'per_attempt_usd': '5', 'per_job_attempt_usd': {'preceding': '40'},
                   'prices_per_token': deepcopy(origin['budget']['prices_per_token']),
                   'ledger_path': str(ledger_path),
                   'continuation': {'sha256': prior_proof['predecessor_ledger']['sha256']}}}
    previous_ref = write(root / 'immediate/registration.json', previous)
    ledger = {'manifest_sha256': previous_ref['sha256'], 'additional_cap_usd': str(old), 'attempt_cap_usd': '5',
              'requests': deepcopy(prior_ledger['requests']) + [
                  {'id': f'link-{old}', 'attempt': 'preceding', 'status': 'settled', 'cost_usd': '1.25'}]}
    owner = {'schema_version': 1, 'registration_sha256': previous_ref['sha256'], 'ledger_path': str(ledger_path),
             'source_registration_sha256': prior_proof['origin_registration']['sha256'],
             'parent_checkpoint_sha256': prior_proof['predecessor_ledger']['sha256']}
    proof = {'kind': amendment.CHAIN_KIND, 'origin_registration': deepcopy(prior_proof['origin_registration']),
             'predecessor_registration': previous_ref, 'predecessor_ledger': write(ledger_path, ledger),
             'predecessor_owner': write(root / 'immediate/sequence_claim/owner.json', owner),
             'prior_total_usd': str(old), 'increase_usd': increase, 'total_usd': str(old + Decimal(increase)),
             'default_attempt_usd': '5', 'prior_amendment': deepcopy(prior_proof), 'authorization_quote': quote}
    proof['authorization'] = write(root / 'chain-authority.json', chain_authority(proof, origin, ledger))
    manifest = {'parent': {'registration': prior_proof['origin_registration']['path']}, amendment.KEY: proof,
                'budget': {'additional_usd': proof['total_usd'], 'per_attempt_usd': '5',
                           'per_job_attempt_usd': {'fresh': '60'}}, 'pinned_files': {}}
    repin(manifest)
    return proof, origin, ledger, manifest


def cost(ledger):
    return str(sum((Decimal(row['cost_usd']) for row in ledger['requests']), Decimal(0)))


def test_a_chained_increase_imports_every_row_once_and_leaves_old_evidence_alone(tmp_path):
    proof, origin, previous, manifest = make_chain_fixture(tmp_path)
    paths = amendment.paths(manifest)
    assert len(paths) == 14          # implementation, the shared origin and four documents per link
    before = {p: p.read_bytes() for p in paths}
    assert amendment.effective_total(manifest, origin) == Decimal(800)
    bridge = amendment.ledger_bridge(manifest, previous, checkpoint_sha256=proof['predecessor_ledger']['sha256'])
    ledger = Ledger(tmp_path / 'fresh.json', manifest_sha256='a' * 64, total_cap='800', attempt_cap='5')
    for _ in range(2):
        ledger.continue_from(proof['predecessor_ledger']['path'], expected_sha256=proof['predecessor_ledger']['sha256'],
                             expected_cost_usd=cost(previous), **bridge)
    state = json.loads(ledger.path.read_bytes())
    assert canonical(state['requests']) == canonical(previous['requests'])
    assert state['continued_from']['budget_amendment_sha256'] == hashlib.sha256(canonical(proof)).hexdigest()
    assert state['additional_cap_usd'] == '800'
    assert before == {p: p.read_bytes() for p in paths}


def test_a_second_chained_link_builds_on_the_first(tmp_path):
    first = make_chain_fixture(tmp_path / 'first')
    proof, origin, previous, manifest = make_chain_fixture(tmp_path / 'second', prior=first, increase='150',
                                                           quote='another $150')
    assert [link['kind'] for link in links(proof)] == [amendment.KIND, amendment.SECOND_KIND,
                                                       amendment.CHAIN_KIND, amendment.CHAIN_KIND]
    assert amendment.effective_total(manifest, origin) == Decimal(950)
    assert len(amendment.paths(manifest)) == 18
    bridge = amendment.ledger_bridge(manifest, previous, checkpoint_sha256=proof['predecessor_ledger']['sha256'])
    ledger = Ledger(tmp_path / 'fresh.json', manifest_sha256='b' * 64, total_cap='950', attempt_cap='5')
    ledger.continue_from(proof['predecessor_ledger']['path'], expected_sha256=proof['predecessor_ledger']['sha256'],
                         expected_cost_usd=cost(previous), **bridge)
    assert len(json.loads(ledger.path.read_bytes())['requests']) == len(previous['requests'])


def test_a_same_cap_descendant_carries_the_chain_without_adding_credit(tmp_path):
    proof, origin, previous, manifest = make_chain_fixture(tmp_path)
    first = Ledger(tmp_path / 'first800.json', manifest_sha256='a' * 64, total_cap='800', attempt_cap='5')
    first.continue_from(proof['predecessor_ledger']['path'], expected_sha256=proof['predecessor_ledger']['sha256'],
                        expected_cost_usd=cost(previous), budget_amendment=proof)
    imported = json.loads(first.path.read_bytes())
    identity = hashlib.sha256(first.path.read_bytes()).hexdigest()
    bridge = amendment.ledger_bridge(manifest, imported, checkpoint_sha256=identity)
    later = Ledger(tmp_path / 'later800.json', manifest_sha256='c' * 64, total_cap='800', attempt_cap='5')
    later.continue_from(first.path, expected_sha256=identity, expected_cost_usd=cost(previous), **bridge)
    assert 'budget_amendment_sha256' not in json.loads(later.path.read_bytes())['continued_from']
    for total in ('1000', '600'):
        refused = Ledger(tmp_path / f'refused{total}.json', manifest_sha256='d' * 64, total_cap=total, attempt_cap='5')
        with pytest.raises(BudgetStop):
            refused.continue_from(first.path, expected_sha256=identity, expected_cost_usd=cost(previous), **bridge)


def test_v1_and_v2_selections_are_unchanged_by_the_chain(tmp_path):
    proof, _, _, _ = make_chain_fixture(tmp_path)
    second = proof['prior_amendment']
    assert amendment.selection(second) == second and amendment.selection(second['prior_amendment'])
    # A v2 still takes exactly one v1; only the chained kind takes any prior.
    nested = deepcopy(second); nested['prior_amendment'] = deepcopy(second)
    with pytest.raises(BudgetStop):
        amendment.selection(nested)
    downgraded = deepcopy(second); downgraded['prior_amendment'] = deepcopy(proof)
    with pytest.raises(BudgetStop):
        amendment.selection(downgraded)


@pytest.mark.parametrize('mutation', ['quote', 'blank_quote', 'prior_total', 'default', 'origin', 'sum',
                                      'unknown_prior', 'reused_registration', 'reused_authority', 'extra_key'])
def test_a_chained_selection_refuses_before_reading_evidence(tmp_path, monkeypatch, mutation):
    proof, _, _, _ = make_chain_fixture(tmp_path)
    earliest = links(proof)[0]
    if mutation == 'quote': del proof['authorization_quote']
    elif mutation == 'blank_quote': proof['authorization_quote'] = ' '
    elif mutation == 'prior_total': proof['prior_total_usd'] = '500'; proof['total_usd'] = '700'
    elif mutation == 'default': proof['default_attempt_usd'] = '6'
    elif mutation == 'origin': proof['origin_registration'] = {'path': str(tmp_path / 'x.json'), 'sha256': 'a' * 64}
    elif mutation == 'sum': proof['total_usd'] = '900'
    elif mutation == 'unknown_prior': proof['prior_amendment']['kind'] = 'future_version'
    elif mutation == 'reused_registration': proof['predecessor_registration'] = deepcopy(earliest['predecessor_registration'])
    elif mutation == 'reused_authority': proof['authorization'] = {'path': str(tmp_path / 'copy.json'),
                                                                   'sha256': earliest['authorization']['sha256']}
    else: proof['max_chain_depth'] = 8
    monkeypatch.setattr(amendment, '_read', lambda _: pytest.fail('selection read evidence'))
    with pytest.raises(BudgetStop):
        amendment.selection(proof)


@pytest.mark.parametrize('mutation', ['receipt_version', 'quote', 'dropped_prior', 'changed_prior',
                                      'early_row_dropped', 'cap', 'owner'])
def test_a_chained_link_binds_its_receipt_predecessor_and_full_history(tmp_path, mutation):
    proof, origin, ledger, manifest = make_chain_fixture(tmp_path)
    previous = json.loads(Path(proof['predecessor_registration']['path']).read_bytes())
    owner = json.loads(Path(proof['predecessor_owner']['path']).read_bytes())
    authority = chain_authority(proof, origin, ledger)
    if mutation == 'receipt_version': authority['schema_version'] = 2
    elif mutation == 'quote': authority['authorization']['user_quote'] = 'a different response'
    elif mutation == 'dropped_prior': previous.pop(amendment.KEY)
    elif mutation == 'changed_prior': previous[amendment.KEY]['authorization_quote'] = 'rewritten'
    elif mutation == 'early_row_dropped': ledger['requests'].pop(0)
    elif mutation == 'cap': ledger['additional_cap_usd'] = '800'
    else: owner['parent_checkpoint_sha256'] = 'f' * 64
    proof['predecessor_registration'] = write(proof['predecessor_registration']['path'], previous)
    ledger['manifest_sha256'] = proof['predecessor_registration']['sha256']
    owner['registration_sha256'] = proof['predecessor_registration']['sha256']
    proof['predecessor_owner'] = write(proof['predecessor_owner']['path'], owner)
    proof['predecessor_ledger'] = write(proof['predecessor_ledger']['path'], ledger)
    if mutation not in ('receipt_version', 'quote'):
        authority = chain_authority(proof, origin, ledger)
    proof['authorization'] = write(proof['authorization']['path'], authority)
    repin(manifest)
    with pytest.raises(BudgetStop):
        amendment.effective_total(manifest, origin)


@pytest.mark.parametrize('depth', [0, 1, 2])
def test_every_link_of_the_chain_is_pinned(tmp_path, depth):
    proof, origin, _, manifest = make_chain_fixture(tmp_path)
    link = links(proof)[depth]
    manifest['pinned_files'].pop(link['authorization']['path'])
    with pytest.raises(BudgetStop, match='unpinned'):
        amendment.effective_total(manifest, origin)
    assert amendment.effective_total(manifest, origin, require_pins=False) == Decimal(800)


# --- review round (#2488, #2489) -------------------------------------------------------------------

def test_the_chain_kind_and_receipt_version_are_the_registered_ones():
    assert amendment.CHAIN_KIND == 'additive_sequence_budget_chain_v1'
    assert amendment.CHAIN_RECEIPT_VERSION == 3


def test_one_quoted_authorization_funds_one_increase(tmp_path):
    first = make_chain_fixture(tmp_path / 'first', quote='increase the budget by $200')
    # The same message recorded again as the next increase.
    again, _, _, _ = make_chain_fixture(tmp_path / 'again', prior=first, increase='200',
                                        quote='Increase the  budget by $200')
    with pytest.raises(BudgetStop, match='reuses an earlier authorization quote'):
        amendment.selection(again)
    # A link quoting the message behind the original v1 receipt, which only
    # the receipts carry: the proofs' quotes are distinct.
    v1_quote = json.loads(Path(links(first[0])[0]['authorization']['path']).read_bytes())['authorization']['user_quote']
    assert v1_quote == 'Approve synthetic $100'
    proof, origin, _, manifest = make_chain_fixture(tmp_path / 'v1', increase='100', quote=v1_quote)
    amendment.selection(proof)
    with pytest.raises(BudgetStop, match='reuses an earlier authorization quote'):
        amendment.effective_total(manifest, origin)


@pytest.mark.parametrize('quote', ['increase the budget', 'increase the budget by $2000',
                                   'increase the budget by $200.50', 'increase the budget by 200'])
def test_a_chained_quote_must_state_its_increase(tmp_path, quote):
    proof, _, _, _ = make_chain_fixture(tmp_path, increase='200', quote=quote)
    with pytest.raises(BudgetStop, match='does not state its increase or new cap'):
        amendment.selection(proof)


@pytest.mark.parametrize('quote', ['increase the budget by $200.', 'yes, $200.00 more',
                                   'raise the cap to $800', 'add $ 200 please',
                                   'increase the budget by $200 howerer we need to swtich development to native '
                                   'agentic, also for efficiency and speed'])
def test_ordinary_statements_of_the_increase_or_the_new_cap_are_accepted(tmp_path, quote):
    proof, _, _, _ = make_chain_fixture(tmp_path, increase='200', quote=quote)
    assert amendment.selection(proof)['total_usd'] == '800'


def test_a_thousands_separator_is_read(tmp_path):
    proof, _, _, _ = make_chain_fixture(tmp_path, increase='2000', quote='approve $2,000 more')
    assert amendment.selection(proof)['total_usd'] == '2600'


def test_the_chain_bound_is_sixteen_proofs():
    assert amendment.MAX_CHAIN_LINKS == 16


def test_matching_v1_and_v2_quotes_are_taken_as_validated(tmp_path):
    """Pre-chain history is not re-judged: only a chained link must quote a new message."""
    assert amendment._chain_quotes_are_new([(amendment.KIND, 'approve $100'),
                                            (amendment.SECOND_KIND, 'Approve  $100'),
                                            (amendment.CHAIN_KIND, 'increase the budget by $200')]) is None
    with pytest.raises(BudgetStop, match='reuses an earlier authorization quote'):
        amendment._chain_quotes_are_new([(amendment.KIND, 'approve $100'),
                                         (amendment.CHAIN_KIND, 'APPROVE $100')])


def test_an_overlong_chain_is_refused_before_it_is_walked(tmp_path, monkeypatch):
    proof, _, _, _ = make_chain_fixture(tmp_path)
    monkeypatch.setattr(amendment, '_read', lambda _: pytest.fail('selection read evidence'))
    deep = proof
    for i in range(amendment.MAX_CHAIN_LINKS + 2):
        deep = dict(deep, prior_amendment=deep, authorization_quote=f'link {i} $200')
    with pytest.raises(BudgetStop, match='longer than its bound'):
        amendment.selection(deep)


@pytest.mark.parametrize('mutation', ['live_owner', 'over_cap'])
def test_a_chained_link_refuses_the_live_owner_and_an_overspent_predecessor(tmp_path, mutation):
    proof, origin, ledger, manifest = make_chain_fixture(tmp_path)
    previous = json.loads(Path(proof['predecessor_registration']['path']).read_bytes())
    if mutation == 'live_owner':
        previous['sequence_state'] = proof['predecessor_owner']['path']
    else:
        ledger['requests'].append({'id': 'overspent', 'attempt': 'preceding', 'status': 'settled', 'cost_usd': '700'})
    proof['predecessor_registration'] = write(proof['predecessor_registration']['path'], previous)
    ledger['manifest_sha256'] = proof['predecessor_registration']['sha256']
    owner = json.loads(Path(proof['predecessor_owner']['path']).read_bytes())
    owner['registration_sha256'] = proof['predecessor_registration']['sha256']
    proof['predecessor_owner'] = write(proof['predecessor_owner']['path'], owner)
    proof['predecessor_ledger'] = write(proof['predecessor_ledger']['path'], ledger)
    proof['authorization'] = write(proof['authorization']['path'], chain_authority(proof, origin, ledger))
    repin(manifest)
    with pytest.raises(BudgetStop):
        amendment.effective_total(manifest, origin)


# --- the final review (#2500) --------------------------------------------------------------------

def _second_quoting(root, quote):
    """The v2 fixture with its quote replaced, receipt rewritten to match."""
    proof, origin, ledger, manifest = make_second_fixture(root)
    proof['authorization_quote'] = quote
    proof['authorization'] = write(proof['authorization']['path'], second_authority(proof, origin, ledger))
    manifest['pinned_files'] = {node[key]['path']: node[key]['sha256']
                                for node in (proof, proof['prior_amendment']) for key in amendment.REFS}
    implementation = Path(amendment.__file__).resolve()
    manifest['pinned_files'][str(implementation)] = hashlib.sha256(implementation.read_bytes()).hexdigest()
    return proof, origin, ledger, manifest


def test_matching_historical_receipt_quotes_do_not_block_a_new_link(tmp_path):
    """v1's and v2's receipts quoting one message was valid history (#2496)."""
    second = _second_quoting(tmp_path / 'second', 'Approve synthetic $100')
    assert amendment.effective_total(second[3], second[1]) == Decimal(600)
    proof, origin, _, manifest = make_chain_fixture(tmp_path / 'chain', prior=second)
    assert amendment.effective_total(manifest, origin) == Decimal(800)
    repeat, origin, _, manifest = make_chain_fixture(tmp_path / 'repeat', prior=second, increase='100',
                                                     quote='approve  SYNTHETIC $100')
    with pytest.raises(BudgetStop, match='reuses an earlier authorization quote'):
        amendment.selection(repeat)


def test_a_link_repeating_v2s_quote_is_refused(tmp_path):
    first = make_second_fixture(tmp_path / 'second')
    proof, _, _, _ = make_chain_fixture(tmp_path / 'chain', prior=first, increase='100',
                                        quote=first[0]['authorization_quote'])
    with pytest.raises(BudgetStop, match='reuses an earlier authorization quote'):
        amendment.selection(proof)


@pytest.mark.parametrize('quote', ['we are at $600', 'approve $2,00 more', 'approve $20,0 more'])
def test_the_prior_cap_or_a_malformed_amount_states_nothing(tmp_path, quote):
    proof, _, _, _ = make_chain_fixture(tmp_path, increase='200', quote=quote)
    with pytest.raises(BudgetStop, match='does not state its increase or new cap'):
        amendment.selection(proof)


def test_an_increase_may_be_anchored_on_a_transport_probe_and_on_nothing_else(tmp_path):
    """A probe is a lineage link (#2469): the next audit may carry an increase anchored on its ledger."""
    proof, origin, previous, manifest = make_chain_fixture(tmp_path / 'probe', kind='d4d_native_transport_probe_v1')
    assert amendment.effective_total(manifest, origin) == Decimal(800)
    amendment.ledger_bridge(manifest, previous, checkpoint_sha256=proof['predecessor_ledger']['sha256'])
    proof, origin, previous, manifest = make_chain_fixture(tmp_path / 'other', kind='d4d_native_generation')
    with pytest.raises(BudgetStop, match='exact prior authority'):
        amendment.effective_total(manifest, origin)


# --- an increase anchored on a reconciled checkpoint (#2502) -----------------------------------

def _keep(stage, document):
    return None


def stopped(ledger):
    """The row the reconciliation settles."""
    return next(row for row in ledger['requests'] if row['id'] == 'stopped-charge')


def make_reconciled_chain_fixture(root, *, proof_bridge=True, authority_bridge=True, edit=_keep,
                                  kind='d4d_native_audit_continuation'):
    """The immediate predecessor stopped with one pending row, which a receipt settled in a
    separate reconciled checkpoint; the chained link is anchored on that checkpoint.

    `edit(stage, document)` changes one document before it is hashed, so every later
    document names the changed bytes and only the edited relation is inconsistent."""
    root = Path(root)
    prior_proof, origin, prior_ledger, _ = make_second_fixture(root / 'second')
    old = Decimal(prior_proof['total_usd'])
    own_path = root / 'immediate/billing.json'
    previous = {'kind': kind,
        'parent': {'registration': prior_proof['origin_registration']['path']},
        'sequence_state': str(root / 'live-owner.json'), amendment.KEY: deepcopy(prior_proof),
        'budget': {'additional_usd': str(old), 'per_attempt_usd': '5', 'per_job_attempt_usd': {'preceding': '40'},
                   'prices_per_token': deepcopy(origin['budget']['prices_per_token']), 'ledger_path': str(own_path),
                   'continuation': {'sha256': prior_proof['predecessor_ledger']['sha256']}}}
    previous_ref = write(root / 'immediate/registration.json', previous)
    rows = deepcopy(prior_ledger['requests']) + [
        {'id': 'settled-link', 'attempt': 'preceding', 'status': 'settled', 'cost_usd': '1.25'},
        {'id': 'stopped-charge', 'attempt': 'preceding', 'status': 'pending', 'reserved_usd': '2.4535'},
        # another worker's charge, settled after the stop: the reconciled row need not be last
        {'id': 'after-stop', 'attempt': 'preceding-worker', 'status': 'settled', 'cost_usd': '0.5'}]
    own = {'manifest_sha256': previous_ref['sha256'], 'additional_cap_usd': str(old), 'attempt_cap_usd': '5',
           'requests': rows}
    reconciled = deepcopy(own)          # from the unedited ledger, so an edit to it breaks one relation
    edit('own', own)
    own_ref = write(own_path, own)
    # The fields every reconciliation receipt carries: the debit reconcile_stopped and a
    # probe write, and a confirmed charge.
    receipt = {'kind': 'user_authorized_full_reservation_debit', 'source_registration_sha256': previous_ref['sha256'],
               'source_ledger_sha256': own_ref['sha256'], 'request_id': 'stopped-charge', 'attempt': 'preceding',
               'previous_reservation_usd': '2.4535', 'budget_debit_usd': '2.4535'}
    edit('receipt', receipt)
    receipt_ref = write(root / 'reconciliation/debit_receipt.json', receipt)
    stopped(reconciled).update(status='settled', cost_usd='2.4535',
                                      settlement_basis='user_authorized_full_reservation_debit',
                                      reconciliation_receipt_sha256=receipt_ref['sha256'])
    reconciled['reconciled_from'] = {'checkpoint_sha256': own_ref['sha256'], 'receipt_sha256': receipt_ref['sha256'],
                                     'request_id': 'stopped-charge', 'previous_status': 'pending'}
    edit('reconciled', reconciled)
    anchor_ref = write(root / 'reconciliation/reconciled_billing.json', reconciled)
    owner = {'schema_version': 1, 'registration_sha256': previous_ref['sha256'], 'ledger_path': str(own_path),
             'source_registration_sha256': prior_proof['origin_registration']['sha256'],
             'parent_checkpoint_sha256': prior_proof['predecessor_ledger']['sha256']}
    proof = {'kind': amendment.CHAIN_KIND, 'origin_registration': deepcopy(prior_proof['origin_registration']),
             'predecessor_registration': previous_ref, 'predecessor_ledger': anchor_ref,
             'predecessor_owner': write(root / 'immediate/sequence_claim/owner.json', owner),
             'prior_total_usd': str(old), 'increase_usd': '200', 'total_usd': str(old + Decimal(200)),
             'default_attempt_usd': '5', 'prior_amendment': deepcopy(prior_proof),
             'authorization_quote': 'increase the budget by $200'}
    bridge = {'source_ledger': own_ref, 'receipt': receipt_ref}
    if proof_bridge:
        proof['reconciliation'] = deepcopy(bridge)
    edit('proof', proof)
    authority = chain_authority(proof, origin, reconciled)
    if authority_bridge:
        authority['predecessor']['reconciliation'] = deepcopy(proof.get('reconciliation', bridge))
    edit('authority', authority)
    proof['authorization'] = write(root / 'chain-authority.json', authority)
    manifest = {'parent': {'registration': prior_proof['origin_registration']['path']}, amendment.KEY: proof,
                'budget': {'additional_usd': proof['total_usd'], 'per_attempt_usd': '5',
                           'per_job_attempt_usd': {'fresh': '60'}}, 'pinned_files': {}}
    repin_all(manifest)
    return proof, origin, reconciled, manifest, authority


def repin_all(manifest):
    """Pin every link's references and each reconciliation's two."""
    repin(manifest)
    for link in links(manifest[amendment.KEY]):
        for ref in link.get('reconciliation', {}).values():
            manifest['pinned_files'][ref['path']] = ref['sha256']


@pytest.mark.parametrize('kind', ['d4d_native_audit_continuation', 'd4d_native_transport_probe_v1'],
                         ids=['audit', 'probe'])
def test_an_increase_may_be_anchored_on_a_reconciled_checkpoint(tmp_path, kind):
    """An audit's stop settled by reconcile_stopped, or a probe's by its own debit (#2636)."""
    proof, origin, reconciled, manifest, _ = make_reconciled_chain_fixture(tmp_path, kind=kind)
    assert amendment.effective_total(manifest, origin) == Decimal(800)
    bridge = amendment.ledger_bridge(manifest, reconciled, checkpoint_sha256=proof['predecessor_ledger']['sha256'])
    ledger = Ledger(tmp_path / 'fresh.json', manifest_sha256='a' * 64, total_cap='800', attempt_cap='5')
    anchor = proof['predecessor_ledger']
    ledger.continue_from(anchor['path'], expected_sha256=anchor['sha256'], expected_cost_usd=cost(reconciled), **bridge)
    imported = json.loads(ledger.path.read_bytes())
    assert imported['additional_cap_usd'] == '800' and imported['attempt_cap_usd'] == '5'
    assert canonical(imported['requests']) == canonical(reconciled['requests'])
    assert imported['continued_from']['checkpoint_sha256'] == anchor['sha256']
    assert imported['continued_from']['budget_amendment_sha256'] == hashlib.sha256(canonical(proof)).hexdigest()
    # A reopen imports nothing twice.
    ledger.continue_from(anchor['path'], expected_sha256=anchor['sha256'], expected_cost_usd=cost(reconciled), **bridge)
    assert json.loads(ledger.path.read_bytes()) == imported


def test_descendants_pin_the_reconciliation_the_link_rests_on(tmp_path):
    """#2576: the ledger it reconciled and the receipt that settled it are evidence of the chain."""
    proof, origin, _, manifest, _ = make_reconciled_chain_fixture(tmp_path)
    named = {Path(ref['path']) for ref in proof['reconciliation'].values()}
    assert named <= amendment.paths(manifest)
    assert named <= {Path(path) for path in amendment._chain_refs(proof)}
    for ref in proof['reconciliation'].values():
        pins = deepcopy(manifest)
        pins['pinned_files'].pop(ref['path'])
        with pytest.raises(BudgetStop, match='unpinned'):
            amendment.effective_total(pins, origin)


@pytest.mark.parametrize('proof_bridge, authority_bridge', [(False, True), (True, False), (False, False)],
                         ids=['proof_silent', 'receipt_silent', 'both_silent'])
def test_a_reconciled_anchor_is_named_by_both_the_proof_and_its_receipt(tmp_path, proof_bridge, authority_bridge):
    proof, origin, _, manifest, _ = make_reconciled_chain_fixture(
        tmp_path, proof_bridge=proof_bridge, authority_bridge=authority_bridge)
    with pytest.raises(BudgetStop, match='name the reconciliation it rests on'):
        amendment.effective_total(manifest, origin, require_pins=False)


def _other_receipt(stage, document):
    if stage == 'authority':
        document['predecessor']['reconciliation']['receipt'] = {'path': document['predecessor']['ledger_path'],
                                                                 'sha256': document['predecessor']['ledger_sha256']}


def _elsewhere(root):
    """The predecessor's own ledger, copied: the same bytes at another path."""
    def edit(stage, document):
        if stage == 'proof':
            source = document['reconciliation']['source_ledger']
            copy = write(Path(root) / 'copy/billing.json', json.loads(Path(source['path']).read_bytes()))
            document['reconciliation']['source_ledger'] = copy
    return edit


def _field(stage_name, update):
    def edit(stage, document):
        if stage == stage_name:
            update(document)
    return edit


RECONCILED_ANCHOR_GUARDS = {
    # the receipt names another reconciliation than the proof
    'receipt_disagrees': (_other_receipt, 'name the reconciliation it rests on'),
    # the reconciliation must be of the predecessor's own ledger
    'not_own_ledger': (None, "predecessor's own ledger"),
    # the anchored checkpoint says it was reconciled from exactly these
    'other_source': (_field('reconciled', lambda d: d['reconciled_from'].update(checkpoint_sha256='0' * 64)),
                     'reconciled from the named'),
    'other_receipt': (_field('reconciled', lambda d: d['reconciled_from'].update(receipt_sha256='0' * 64)),
                      'reconciled from the named'),
    'not_from_pending': (_field('reconciled', lambda d: d['reconciled_from'].update(previous_status='settled')),
                         'reconciled from the named'),
    'no_origin': (_field('reconciled', lambda d: d.pop('reconciled_from')), 'reconciled from the named'),
    'other_manifest': (_field('own', lambda d: d.update(manifest_sha256='0' * 64)), 'reconciled from the named'),
    # the rows: the same, in the same order, changed only in the one reconciled row
    'added_row': (_field('reconciled', lambda d: d['requests'].append(
        {'id': 'extra', 'attempt': 'x', 'status': 'settled', 'cost_usd': '0'})), "changes the predecessor's rows"),
    'earlier_row': (_field('reconciled', lambda d: d['requests'][0].update(cost_usd='0')),
                    'more than its one reconciled row'),
    'reordered': (_field('reconciled', lambda d: d['requests'].insert(0, d['requests'].pop(-2))),
                  'more than its one reconciled row'),
    'later_row': (_field('reconciled', lambda d: d['requests'][-1].update(cost_usd='0')),
                  'more than its one reconciled row'),
    'other_request': (_field('reconciled', lambda d: d['reconciled_from'].update(request_id='settled-link')),
                      'more than its one reconciled row'),
    # the settled row renamed, reconciled_from following it (#2637)
    'renamed_row': (_field('reconciled', lambda d: (stopped(d).update(id='renamed-charge'),
                                                   d['reconciled_from'].update(request_id='renamed-charge'))),
                    'more than its one reconciled row'),
    # the settled row renamed while reconciled_from still names the original request (#2637)
    'renamed_row_only': (_field('reconciled', lambda d: stopped(d).update(id='renamed-charge')),
                         'more than its one reconciled row'),
    # the source's pending row is another request than the settled one (#2637)
    'other_pending_row': (_field('own', lambda d: stopped(d).update(id='another-pending')),
                          'more than its one reconciled row'),
    'not_pending_before': (_field('own', lambda d: stopped(d).update(status='held')),
                           'more than its one reconciled row'),
    'not_settled_after': (_field('reconciled', lambda d: stopped(d).update(status='resolved')),
                          'more than its one reconciled row'),
    'over_reservation': (_field('reconciled', lambda d: stopped(d).update(cost_usd='9')),
                         'more than its one reconciled row'),
    # the receipt settles exactly that row of that ledger
    'receipt_other_registration': (_field('receipt', lambda d: d.update(source_registration_sha256='0' * 64)),
                                   'receipt does not settle'),
    'receipt_other_ledger': (_field('receipt', lambda d: d.update(source_ledger_sha256='0' * 64)),
                             'receipt does not settle'),
    'receipt_other_request': (_field('receipt', lambda d: d.update(request_id='settled-link')),
                              'receipt does not settle'),
    'receipt_other_attempt': (_field('receipt', lambda d: d.update(attempt='other')), 'receipt does not settle'),
    'receipt_other_reservation': (_field('receipt', lambda d: d.update(previous_reservation_usd='9')),
                                  'receipt does not settle'),
    'row_other_receipt': (_field('reconciled', lambda d: stopped(d).update(
        reconciliation_receipt_sha256='0' * 64)), 'receipt does not settle'),
    # and the caps are the predecessor's own
    'other_total_cap': (_field('own', lambda d: d.update(additional_cap_usd='450')), 'changes its caps'),
    'other_attempt_cap': (_field('own', lambda d: d.update(attempt_cap_usd='4')), 'changes its caps'),
}


@pytest.mark.parametrize('guard', list(RECONCILED_ANCHOR_GUARDS))
def test_a_reconciled_anchor_must_be_exactly_that_reconciliation(tmp_path, guard):
    """Each relation the anchor proves, broken alone: every other document names the changed bytes."""
    edit, match = RECONCILED_ANCHOR_GUARDS[guard]
    proof, origin, reconciled, manifest, _ = make_reconciled_chain_fixture(
        tmp_path, edit=edit or _elsewhere(tmp_path))
    with pytest.raises(BudgetStop, match=match):
        amendment.effective_total(manifest, origin)
    with pytest.raises(BudgetStop, match=match):
        amendment.ledger_bridge(manifest, reconciled, checkpoint_sha256=proof['predecessor_ledger']['sha256'])


@pytest.mark.parametrize('change, match', [
    (lambda r: r.update(extra={'path': r['receipt']['path'], 'sha256': r['receipt']['sha256']}), 'invalid budget amendment reconciliation'),
    (lambda r: r.pop('receipt'), 'invalid budget amendment reconciliation'),
    (lambda r: r['receipt'].update(size=1), 'invalid budget amendment reconciliation'),
    (lambda r: r['receipt'].update(sha256='A' * 64), 'invalid budget amendment reconciliation'),
    (lambda r: r['receipt'].update(path='relative/receipt.json'), 'canonical'),
    (lambda r: r.update(source_ledger=None), 'invalid budget amendment reconciliation'),
], ids=['extra_key', 'missing_key', 'extra_ref_key', 'bad_digest', 'relative_path', 'not_a_reference'])
def test_a_reconciliation_is_exactly_two_references_checked_before_reading(tmp_path, monkeypatch, change, match):
    proof, _, _, _, _ = make_reconciled_chain_fixture(tmp_path)
    change(proof['reconciliation'])
    monkeypatch.setattr(amendment, '_read', lambda _: pytest.fail('evidence read before selection'))
    with pytest.raises(BudgetStop, match=match):
        amendment.selection(proof)


def test_a_reconciliation_cannot_name_the_anchor_itself_or_earlier_evidence(tmp_path):
    proof, _, _, _, _ = make_reconciled_chain_fixture(tmp_path)
    for key, reused in (('source_ledger', proof['predecessor_ledger']),
                        ('receipt', proof['prior_amendment']['authorization'])):
        changed = deepcopy(proof)
        changed['reconciliation'][key] = deepcopy(reused)
        with pytest.raises(BudgetStop, match='reuses or conflicts'):
            amendment.selection(changed)


def test_a_link_on_its_predecessors_own_ledger_names_no_reconciliation(tmp_path):
    proof, origin, _, manifest = make_chain_fixture(tmp_path / 'plain')
    stray = {'source_ledger': write(tmp_path / 'stray/billing.json', {'requests': []}),
             'receipt': write(tmp_path / 'stray/receipt.json', {'kind': 'invented'})}
    proof['reconciliation'] = stray
    repin_all(manifest)
    with pytest.raises(BudgetStop, match='names no reconciliation'):
        amendment.effective_total(manifest, origin)


def test_a_v2_increase_is_never_anchored_on_a_reconciled_checkpoint(tmp_path):
    """Only a chained link may rest on a reconciliation: a v2 proof anchored on one is refused
    with its receipt naming the reconciliation, and it cannot carry one itself."""
    proof, origin, _, manifest = make_second_fixture(tmp_path / 'v2')
    previous = json.loads(Path(proof['predecessor_registration']['path']).read_bytes())
    ledger = json.loads(Path(proof['predecessor_ledger']['path']).read_bytes())
    own_path = Path(previous['budget']['ledger_path'])
    ledger['requests'][-1] = {**ledger['requests'][-1], 'status': 'pending', 'reserved_usd': '2.50'}
    ledger['requests'][-1].pop('cost_usd')
    own_ref = write(own_path, ledger)
    receipt_ref = write(tmp_path / 'v2/reconciliation/receipt.json', {'kind': 'invented'})
    reconciled = deepcopy(ledger)
    reconciled['requests'][-1].update(status='settled', cost_usd='2.50',
                                      reconciliation_receipt_sha256=receipt_ref['sha256'])
    reconciled['reconciled_from'] = {'checkpoint_sha256': own_ref['sha256'], 'receipt_sha256': receipt_ref['sha256'],
                                     'request_id': ledger['requests'][-1]['id'], 'previous_status': 'pending'}
    proof['predecessor_ledger'] = write(tmp_path / 'v2/reconciliation/reconciled_billing.json', reconciled)
    authority = second_authority(proof, origin, reconciled)
    authority['predecessor']['reconciliation'] = {'source_ledger': own_ref, 'receipt': receipt_ref}
    proof['authorization'] = write(Path(proof['authorization']['path']), authority)
    manifest[amendment.KEY] = proof
    with pytest.raises(BudgetStop, match='exact immediate ledger'):
        amendment.effective_total(manifest, origin, require_pins=False)
    carried = deepcopy(proof)
    carried['reconciliation'] = {'source_ledger': own_ref, 'receipt': receipt_ref}
    with pytest.raises(BudgetStop, match='unsupported second budget amendment selection'):
        amendment.selection(carried)


# --- review round 2 of #2570: #2634, #2635, #2637 ---------------------------------------------

def test_a_later_link_still_pins_an_earlier_links_reconciliation(tmp_path):
    """#2634: a +$150 link on the reconciled $800 link carries that link's source ledger and
    receipt in its own evidence, and refuses when they are unpinned."""
    first = make_reconciled_chain_fixture(tmp_path / 'reconciled')
    proof, origin, reconciled, manifest, _ = first
    later, origin, _, later_manifest = make_chain_fixture(tmp_path / 'later', prior=(proof, origin, reconciled, manifest),
                                                         increase='150', quote='increase the budget by $150')
    repin_all(later_manifest)
    assert amendment.effective_total(later_manifest, origin) == Decimal(950)
    earlier = {Path(ref['path']) for ref in proof['reconciliation'].values()}
    assert earlier <= amendment.paths(later_manifest)
    for ref in proof['reconciliation'].values():
        pins = deepcopy(later_manifest)
        pins['pinned_files'].pop(ref['path'])
        with pytest.raises(BudgetStop, match='unpinned'):
            amendment.effective_total(pins, origin)


def test_a_reconciliation_ref_cannot_reuse_an_earlier_identity_at_a_new_path(tmp_path):
    """#2634: the same bytes at another path are the same evidence; identity reuse is refused
    at selection, before any document is read."""
    proof, _, _, _, _ = make_reconciled_chain_fixture(tmp_path)
    earlier = proof['prior_amendment']['authorization']
    copy = tmp_path / 'copy' / 'receipt.json'
    copy.parent.mkdir()
    copy.write_bytes(Path(earlier['path']).read_bytes())
    changed = deepcopy(proof)
    changed['reconciliation']['receipt'] = {'path': str(copy), 'sha256': earlier['sha256']}
    with pytest.raises(BudgetStop, match='reuses earlier authority or predecessor identity'):
        amendment.selection(changed)


def test_a_confirmed_charge_below_its_reservation_is_accepted(tmp_path):
    """#2635: the registration's confirmed-charge path settles below the reservation."""
    def confirmed(stage, document):
        if stage == 'receipt':
            document.update(kind='user_confirmed_provider_charge_reconciliation', confirmed_complete_charge_usd='2.00')
        if stage == 'reconciled':
            stopped(document).update(cost_usd='2.00')
    proof, origin, reconciled, manifest, _ = make_reconciled_chain_fixture(tmp_path, edit=confirmed)
    assert stopped(reconciled)['cost_usd'] == '2.00' and stopped(reconciled)['reserved_usd'] == '2.4535'
    assert amendment.effective_total(manifest, origin) == Decimal(800)
    amendment.ledger_bridge(manifest, reconciled, checkpoint_sha256=proof['predecessor_ledger']['sha256'])


@pytest.mark.parametrize('value', [['source_ledger', 'receipt'], None, 'reconciliation'], ids=['list', 'null', 'string'])
def test_a_reconciliation_that_is_not_a_mapping_is_a_budget_stop(tmp_path, value):
    """#2637: refused as a BudgetStop, never a TypeError from indexing it."""
    proof, _, _, _, _ = make_reconciled_chain_fixture(tmp_path)
    proof['reconciliation'] = value
    with pytest.raises(BudgetStop, match='invalid budget amendment reconciliation'):
        amendment.selection(proof)
