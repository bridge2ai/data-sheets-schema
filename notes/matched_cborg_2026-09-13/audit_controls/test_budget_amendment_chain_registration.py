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


# --- a link anchored on a real reconciliation (#2502, #2577) ---------------------------------------

from audit_controls.test_registration import accounting  # noqa: F401,E402  (fixture)
from audit_controls.test_reconcile_stopped import reconcile, stopped, successor_of  # noqa: F401,E402


def test_the_anchor_proof_accepts_the_bytes_reconcile_stopped_writes(stopped):
    """The relations a reconciled anchor proves hold for the receipt and checkpoint the tool
    writes, and the registration's own recomputation accepts the same files."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    bridge = {'source_ledger': reference(first['budget']['ledger_path']), 'receipt': reference(value['receipt'])}
    proof = {'reconciliation': deepcopy(bridge), 'predecessor_registration': reference(reg),
             'predecessor_ledger': reference(value['checkpoint'])}
    anchored = registration.read_json(value['checkpoint'])
    assert amendment._reconciled_anchor(proof, first, anchored, {'predecessor': {'reconciliation': bridge}}) == bridge
    successor, _ = successor_of(m, reg, first, value)
    assert registration.validate_audit_reconciliation(successor) == anchored
    # A receipt from another stop does not settle this one.
    other = registration.read_json(value['receipt'])
    other['request_id'] = 'another-request'
    forged = save(reg.parent.parent / 'forged_receipt.json', other)
    proof['reconciliation']['receipt'] = reference(forged)
    anchored['reconciled_from']['receipt_sha256'] = proof['reconciliation']['receipt']['sha256']
    next(row for row in anchored['requests'] if row['id'] == request_id)['reconciliation_receipt_sha256'] = \
        proof['reconciliation']['receipt']['sha256']
    with pytest.raises(BudgetStop, match='receipt does not settle'):
        amendment._reconciled_anchor(proof, first, anchored, {'predecessor': deepcopy(proof)})


# --- the operator path end to end (#2633) ----------------------------------------------------------

REAL_AUDIT_RECONCILIATION = registration.validate_audit_reconciliation
STALLED_REQUEST = b'{"synthetic": "stalled request"}\n'


def stopped_second(c, tmp_path):
    """The $600 audit, run once: one settled row, then one pending row it stopped on."""
    path, m = prepare_second(c, tmp_path / 'second')
    identity = registration.sha(path)
    attempt = attempt_identity(identity, m['job']['id'])
    with registration.sequence_guard(m, identity):
        ledger = registration.open_audit_ledger(m, path, identity)
        ticket = ledger.reserve(attempt, '.02', 'chain-synthetic')
        ledger.settle(ticket, '.01', response_sha256='synthetic', usage={})
        request_id = ledger.reserve(attempt, Decimal('2.4535'), hashlib.sha256(STALLED_REQUEST).hexdigest())
        ledger.stop_attempt(attempt, 'upstream HTTP response did not confirm a completed charge')
    folder = Path(m['job']['attempt_dir']) / 'children' / 'worker_0001' / 'requests' / request_id
    folder.mkdir(parents=True)
    (folder / 'request.json').write_bytes(STALLED_REQUEST)
    save(folder / 'admission.json', {'reserved_usd': '2.4535'})
    save(Path(m['job']['attempt_dir']) / 'result.json', {
        'registration_sha256': identity, 'job_id': m['job']['id'], 'scope': 'phase3_audit_only',
        'status': 'stopped', 'unresolved_requests': [request_id],
        'runtime': {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}})
    return path, m, ledger.path


def test_real_chained_audit_anchored_on_a_reconciled_stop(second_approved, tmp_path, tmp_path_factory, monkeypatch):
    """#2502/#2633: the $600 audit stops on one pending row; reconcile_stopped settles it; a
    chained +$200 proof anchored on that reconciled checkpoint is prepared, registered and
    imported. The fixture stubs the reconciliation check, so the real one is restored first."""
    from audit_controls import reconcile_stopped as tool
    c = second_approved
    monkeypatch.setattr(registration, 'validate_audit_reconciliation', REAL_AUDIT_RECONCILIATION)
    path, m, own_ledger = stopped_second(c, tmp_path)
    value = tool.reconcile(path, tmp_path_factory.mktemp('recon') / 'reconciliation',
                           recorded_at='2026-09-25T19:00:00+00:00')
    checkpoint = Path(value['checkpoint'])
    reconciled = registration.read_json(checkpoint)
    owner = path.parent / 'sequence_claim/owner.json'
    quote = 'increase the budget by $200'
    bridge = {'source_ledger': reference(own_ledger), 'receipt': reference(value['receipt'])}
    authority = save(tmp_path / 'chain-authority.json', {
        'kind': 'audit_sequence_additional_budget_authorization_receipt',
        'schema_version': amendment.CHAIN_RECEIPT_VERSION,
        'lineage': {'origin_registration': deepcopy(c['proof']['origin_registration']),
                    'prior_amendment_sha256': hashlib.sha256(amendment._canonical(c['proof'])).hexdigest(),
                    'original_shared_cap_usd': '400'},
        'authorization': {'additional_budget_authorized': True, 'currency': 'USD', 'user_quote': quote,
                          'prior_shared_cap_usd': '600', 'additional_authorized_usd': '200',
                          'new_shared_cap_usd': '800'},
        'predecessor': {'registration_path': str(path), 'registration_sha256': registration.sha(path),
                        'ledger_path': str(checkpoint), 'ledger_sha256': registration.sha(checkpoint),
                        'canonical_owner_sha256': registration.sha(owner),
                        'sequence_settled_rows': len(reconciled['requests']),
                        'sequence_accounted_usd': str(sum((Decimal(r['cost_usd']) for r in reconciled['requests']),
                                                          Decimal(0))),
                        'registered_predecessor_shared_cap_usd': '600', 'reconciliation': deepcopy(bridge)}})
    proof = {'kind': amendment.CHAIN_KIND, 'origin_registration': deepcopy(c['proof']['origin_registration']),
             'predecessor_registration': reference(path), 'predecessor_ledger': reference(checkpoint),
             'predecessor_owner': reference(owner), 'authorization': reference(authority),
             'prior_total_usd': '600', 'increase_usd': '200', 'total_usd': '800', 'default_attempt_usd': '5',
             'prior_amendment': deepcopy(c['proof']), 'authorization_quote': quote, 'reconciliation': bridge}
    new_path, new = prepare_second(c, tmp_path / 'chained', continuation_checkpoint=str(checkpoint),
                                   continuation_source_registration=str(path),
                                   continuation_reconciliation_receipt=value['receipt'], budget_amendment=proof)
    assert new['budget_amendment'] == proof and new['budget']['additional_usd'] == '800'
    assert new['budget']['continuation']['reconciliation']['receipt'] == value['receipt']
    assert registration.validate_registration(new_path) == new
    assert registration.validate_audit_reconciliation(new) == reconciled
    identity = registration.sha(new_path)
    with registration.sequence_guard(new, identity):
        ledger = registration.open_audit_ledger(new, new_path, identity)
        imported = registration.read_json(ledger.path)
    assert imported['additional_cap_usd'] == '800' and imported['attempt_cap_usd'] == '5'
    assert amendment._canonical(imported['requests']) == amendment._canonical(reconciled['requests'])
    assert imported['continued_from']['budget_amendment_sha256'] == hashlib.sha256(amendment._canonical(proof)).hexdigest()
