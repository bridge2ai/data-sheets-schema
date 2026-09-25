"""A chained increase through real audit preparation, registration and ledger import (#2468).

Builds on the v2 fixture: a first-amended audit at $500, a second at $600,
then a chained link to $800. Every artifact and request is invented; no
provider or study evidence is used.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import hashlib
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import budget_amendment as amendment
from budgeted_cborg import BudgetStop, attempt_identity
from audit_controls import registration
from audit_controls.test_context_preparation import ancestry, save  # noqa: F401  (fixture)
from audit_controls.test_budget_amendment_registration import reference
from audit_controls.test_second_budget_amendment_registration import prepare_second, second_approved  # noqa: F401


def chained(c, tmp_path, *, increase='200', quote='increase the budget by $200'):
    """Run the $600 audit once, then prove a chained increase on its settled ledger."""
    path, m = prepare_second(c, tmp_path / 'second')
    identity = registration.sha(path)
    with registration.sequence_guard(m, identity):
        ledger = registration.open_audit_ledger(m, path, identity)
        ticket = ledger.reserve(attempt_identity(identity, m['job']['id']), '.02', 'chain-synthetic')
        ledger.settle(ticket, '.01', response_sha256='synthetic', usage={})
    previous = registration.read_json(ledger.path)
    owner = path.parent / 'sequence_claim/owner.json'
    total = str(Decimal('600') + Decimal(increase))
    authority = save(tmp_path / 'chain-authority.json', {
        'kind': 'audit_sequence_additional_budget_authorization_receipt',
        'schema_version': amendment.CHAIN_RECEIPT_VERSION,
        'lineage': {'origin_registration': deepcopy(c['proof']['origin_registration']),
                    'prior_amendment_sha256': hashlib.sha256(amendment._canonical(c['proof'])).hexdigest(),
                    'original_shared_cap_usd': '400'},
        'authorization': {'additional_budget_authorized': True, 'currency': 'USD', 'user_quote': quote,
                          'prior_shared_cap_usd': '600', 'additional_authorized_usd': increase,
                          'new_shared_cap_usd': total},
        'predecessor': {'registration_path': str(path), 'registration_sha256': identity,
                        'ledger_path': str(ledger.path), 'ledger_sha256': registration.sha(ledger.path),
                        'canonical_owner_sha256': registration.sha(owner),
                        'sequence_settled_rows': len(previous['requests']),
                        'sequence_accounted_usd': str(sum((Decimal(r['cost_usd']) for r in previous['requests']),
                                                          Decimal(0))),
                        'registered_predecessor_shared_cap_usd': '600'}})
    proof = {'kind': amendment.CHAIN_KIND, 'origin_registration': deepcopy(c['proof']['origin_registration']),
             'predecessor_registration': reference(path), 'predecessor_ledger': reference(ledger.path),
             'predecessor_owner': reference(owner), 'authorization': reference(authority),
             'prior_total_usd': '600', 'increase_usd': increase, 'total_usd': total, 'default_attempt_usd': '5',
             'prior_amendment': deepcopy(c['proof']), 'authorization_quote': quote}
    return proof, ledger.path, previous


def test_real_chained_audit_imports_the_full_history_once_at_the_new_cap(second_approved, tmp_path):
    c = second_approved
    proof, checkpoint, previous = chained(c, tmp_path)
    path, m = prepare_second(c, tmp_path / 'chained', continuation_checkpoint=checkpoint, budget_amendment=proof)
    assert m['budget_amendment'] == proof and m['budget']['additional_usd'] == '800'
    identity = registration.sha(path)
    with registration.sequence_guard(m, identity):
        ledger = registration.open_audit_ledger(m, path, identity)
        imported = registration.read_json(ledger.path)
        assert imported['additional_cap_usd'] == '800' and imported['attempt_cap_usd'] == '5'
        assert amendment._canonical(imported['requests']) == amendment._canonical(previous['requests'])
        assert imported['continued_from']['budget_amendment_sha256'] == hashlib.sha256(
            amendment._canonical(proof)).hexdigest()
        registration.open_audit_ledger(m, path, identity)
        assert registration.read_json(ledger.path) == imported


@pytest.mark.parametrize('damage', ['as_v2', 'stale_prior', 'wrong_quote'])
def test_real_chained_preparation_refuses_a_proof_that_does_not_bind_its_predecessor(second_approved, tmp_path, damage):
    c = second_approved
    proof, checkpoint, _ = chained(c, tmp_path)
    if damage == 'as_v2':
        proof['kind'] = 'additive_sequence_budget_v2'          # a v2 takes only a v1 prior
    elif damage == 'stale_prior':
        proof['prior_amendment'] = deepcopy(c['first'])       # skips the $600 link
    else:
        proof['authorization_quote'] = 'a different response approving $200'   # states the amount; the receipt disagrees
    with pytest.raises(BudgetStop):
        prepare_second(c, tmp_path / 'refused', continuation_checkpoint=checkpoint, budget_amendment=proof)
    assert not (tmp_path / 'refused').exists()
