"""Real offline second-amendment registration/ledger tests (#2426).

The inherited fixture stubs only historical generation acceptance and uncommitted
code attestation. All new proof validation, preparation, rendering, registration,
sequence claims, reservations and accounting import are real. Every artifact and
request is invented; no provider or actual study evidence is used.
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
from audit_controls import prepare, registration
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_budget_amendment_registration import reference
from test_budget_amendment import make_fixture

SECOND_KIND = 'additive_sequence_budget_v2'


def refs(value):
    """Typed metadata references, including the embedded exact first proof."""
    if type(value) is dict:
        if set(value) == {'path', 'sha256'}:
            yield value
        else:
            for child in value.values():
                yield from refs(child)
    elif type(value) is list:
        for child in value:
            yield from refs(child)


@pytest.fixture
def second_approved(ancestry, tmp_path):
    args, example, _, state = ancestry
    origin_path = args['parent_registration']
    generation = registration.read_json(origin_path)
    generation['budget']['per_job_attempt_usd'][args['parent_job_id']] = '400'
    generation['generation']['jobs'][0]['bundle'] = generation['generation']['jobs'][0]['input_identity']['bundle']['path']
    generation['model'] = {'model': 'claude-opus-5', 'route_model': 'vertex_ai/claude-opus-5'}
    generation['budget']['prices_per_token'].update(cache_write=.00000625, cache_read=.0000005)
    generation['claude_version'] = '2.1.272 (Claude Code)'
    version_only = tmp_path/'version-only'
    version_only.write_text('#!/bin/sh\nprintf \"%s\\n\" \"2.1.272 (Claude Code)\"\n')
    version_only.chmod(0o700)
    overlay = registration.read_json(args['parent_overlay'])
    overlay.update(claude_executable=str(version_only), claude_version=generation['claude_version'])
    save(args['parent_overlay'], overlay)
    args = {**args, 'native_api_timeout_ms': 3600000, 'native_api_force_idle_timeout': False}
    save(origin_path, generation)
    checkpoint = registration.read_json(args['reconciled_checkpoint'])
    for row in checkpoint['requests']:
        row['attempt'] = 'synthetic-generation-owner'
    save(args['reconciled_checkpoint'], checkpoint)
    rows = deepcopy(checkpoint['requests']) + [
            {'id': f'synthetic-history-{i:04}', 'attempt': 'invented-old-owner',
             'status': 'settled', 'cost_usd': '.01', 'typed_integer': i}
            for i in range(210)]
    for row in rows[-2:]:
        row.update(cost_usd='2.50', reserved_usd='2.50',
            settlement_basis='registered_stall_policy_full_reservation_debit',
            provider_charge_confirmed=False, provider_charge_usd=None,
            provider_usage_is_final=False, released_excess_reservation_usd='0')
    first, _, _, _ = make_fixture(tmp_path/'first-authority', generation=generation,
                                 generation_path=origin_path, rows=rows)
    save(state, registration.read_json(first['predecessor_owner']['path']))
    initial_args = {**args, 'continuation_checkpoint': first['predecessor_ledger']['path'],
                    'attempt_cap': '40', 'durable_sequence_claim': True}
    prior_path = prepare.prepare(**initial_args, destination=tmp_path/'first-amended',
                                 budget_amendment=first)
    prior = registration.validate_registration(prior_path)
    identity = registration.sha(prior_path)
    with registration.sequence_guard(prior, identity):
        ledger = registration.open_audit_ledger(prior, prior_path, identity)
        for i in range(46):
            amount = '2.50' if i == 45 else '.01'
            ticket = ledger.reserve(attempt_identity(identity, prior['job']['id']), amount,
                                    f'synthetic-request-{i}')
            if i == 45:
                ledger.debit_unconfirmed(ticket, maximum=6, evidence={'synthetic': 'timeout'})
            else:
                ledger.settle(ticket, amount, response_sha256='synthetic-response', usage={})
    previous = registration.read_json(ledger.path)
    assert len(previous['requests']) == 257
    owner_path = prior_path.parent/'sequence_claim/owner.json'
    quote = 'Synthetic explicit approval: add $100; new total $600 and audit ceiling $60.'
    authority = save(tmp_path/'second-authority.json', {
        'kind': 'audit_sequence_additional_budget_authorization_receipt', 'schema_version': 2,
        'lineage': {'origin_registration': deepcopy(first['origin_registration']),
            'prior_amendment_sha256': hashlib.sha256(amendment._canonical(first)).hexdigest(),
            'original_shared_cap_usd': '400'},
        'authorization': {'additional_budget_authorized': True, 'currency': 'USD',
            'user_quote': quote, 'prior_shared_cap_usd': '500',
            'additional_authorized_usd': '100', 'new_shared_cap_usd': '600'},
        'predecessor': {'registration_path': str(prior_path),
            'registration_sha256': identity, 'ledger_path': str(ledger.path),
            'ledger_sha256': registration.sha(ledger.path),
            'canonical_owner_sha256': registration.sha(owner_path),
            'sequence_settled_rows': len(previous['requests']),
            'sequence_accounted_usd': str(sum((Decimal(r['cost_usd']) for r in previous['requests']), Decimal(0))),
            'registered_predecessor_shared_cap_usd': '500'},
    })
    proof = {'kind': SECOND_KIND, 'origin_registration': reference(origin_path),
        'predecessor_registration': reference(prior_path), 'predecessor_ledger': reference(ledger.path),
        'predecessor_owner': reference(owner_path), 'authorization': reference(authority),
        'prior_total_usd': '500', 'increase_usd': '100', 'total_usd': '600',
        'default_attempt_usd': '5', 'prior_amendment': deepcopy(first), 'authorization_quote': quote}
    immutable = {Path(r['path']): Path(r['path']).read_bytes() for r in refs(proof)}
    return {'args': {**args, 'attempt_cap': '60', 'durable_sequence_claim': True,
                     'continuation_checkpoint': ledger.path},
        'proof': proof, 'first': first, 'prior_path': prior_path, 'prior': prior,
        'rows': previous['requests'], 'state': state, 'state_bytes': state.read_bytes(),
        'immutable': immutable, 'example': example}


def prepare_second(case, destination, **overrides):
    args = {**case['args'], **overrides}
    proof = args.pop('budget_amendment', case['proof'])
    path = prepare.prepare(**args, destination=destination, budget_amendment=proof)
    return path, registration.validate_registration(path)


def unchanged(case, *, state=True):
    assert all(p.read_bytes() == raw for p, raw in case['immutable'].items())
    if state:
        assert case['state'].read_bytes() == case['state_bytes']


def test_real_second_prepare_and_ledger_import_full_history_once(second_approved, tmp_path):
    c = second_approved
    path, m = prepare_second(c, tmp_path/'second')
    assert m['budget_amendment'] == c['proof']
    assert m['budget']['additional_usd'] == '600'
    assert m['budget']['per_attempt_usd'] == '5'
    assert m['budget']['per_job_attempt_usd'] == {m['job']['id']: '60'}
    assert registration.read_json(m['parent']['registration'])['budget']['per_job_attempt_usd'][m['parent']['job_id']] == '400'
    assert not Path(m['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
    unchanged(c)
    with registration.sequence_guard(m, registration.sha(path)):
        ledger = registration.open_audit_ledger(m, path, registration.sha(path))
        imported = registration.read_json(ledger.path)
        assert imported['additional_cap_usd'] == '600'
        assert imported['attempt_cap_usd'] == '5'
        assert amendment._canonical(imported['requests']) == amendment._canonical(c['rows'])
        assert len(imported['requests']) == 257
        assert len({r['id'] for r in imported['requests']}) == 257
        assert imported['continued_from']['checkpoint_sha256'] == c['proof']['predecessor_ledger']['sha256']
        assert 'budget_amendment_sha256' in imported['continued_from']
        registration.open_audit_ledger(m, path, registration.sha(path))
        assert registration.read_json(ledger.path) == imported
        assert imported['requests'][-1]['provider_charge_confirmed'] is False
        assert imported['requests'][-1]['provider_charge_usd'] is None
        assert imported['requests'][-1]['released_excess_reservation_usd'] == '0'
        assert (path.parent/'sequence_claim/owner.json').read_bytes() == c['state'].read_bytes()
    unchanged(c, state=False)


def test_real_same_cap_next_audit_preserves_second_proof_without_credit(second_approved, tmp_path):
    c = second_approved
    first_path, first = prepare_second(c, tmp_path/'second')
    with registration.sequence_guard(first, registration.sha(first_path)):
        ledger = registration.open_audit_ledger(first, first_path, registration.sha(first_path))
        ticket = ledger.reserve(attempt_identity(registration.sha(first_path), first['job']['id']), '.02', 'new-synthetic')
        ledger.settle(ticket, '.01', response_sha256='synthetic', usage={})
    before = Path(ledger.path).read_bytes()
    path, m = prepare_second(c, tmp_path/'same-cap', continuation_checkpoint=ledger.path)
    assert m['budget_amendment'] == first['budget_amendment'] == c['proof']
    with registration.sequence_guard(m, registration.sha(path)):
        successor = registration.open_audit_ledger(m, path, registration.sha(path))
        carried = registration.read_json(successor.path)
        assert carried['additional_cap_usd'] == '600' and len(carried['requests']) == 258
        assert carried['requests'] == registration.read_json(ledger.path)['requests']
        assert 'budget_amendment_sha256' not in carried['continued_from']
        registration.open_audit_ledger(m, path, registration.sha(path))
        assert registration.read_json(successor.path) == carried
    assert Path(ledger.path).read_bytes() == before
    unchanged(c, state=False)


@pytest.mark.parametrize('damage', ['different_live_owner', 'missing_owner', 'already_consumed'])
def test_real_sequence_guard_refuses_stale_tip_before_claim_or_ledger(second_approved, tmp_path, damage):
    c = second_approved; path, m = prepare_second(c, tmp_path/'second')
    if damage == 'missing_owner': c['state'].unlink()
    else:
        value = registration.read_json(c['state'])
        if damage == 'already_consumed': value['registration_sha256'] = registration.sha(path)
        else:
            value['registration_sha256'] = 'f'*64
            value['ledger_path'] = str(tmp_path/'unrelated-tip.json')
        save(c['state'], value)
    before = c['state'].read_bytes() if c['state'].exists() else None
    with pytest.raises(BudgetStop):
        with registration.sequence_guard(m, registration.sha(path)):
            pytest.fail('stale owner reached ledger admission')
    assert (c['state'].read_bytes() if c['state'].exists() else None) == before
    assert not Path(m['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
    unchanged(c, state=False)


@pytest.mark.parametrize('damage', ['wrong_immutable_owner', 'changed_quote', 'drop_prior', 'different_prior', 'stale_checkpoint'])
def test_invalid_second_proof_refused_before_destination(second_approved, tmp_path, damage):
    c = second_approved; proof = deepcopy(c['proof']); overrides = {}
    if damage == 'wrong_immutable_owner':
        value = registration.read_json(proof['predecessor_owner']['path']); value['registration_sha256'] = 'f'*64
        proof['predecessor_owner'] = reference(save(tmp_path/'wrong-owner.json', value))
    elif damage == 'changed_quote': proof['authorization_quote'] = 'Different synthetic authority'
    elif damage == 'drop_prior': proof.pop('prior_amendment')
    elif damage == 'different_prior':
        prior = proof['prior_amendment']; old = Path(prior['authorization']['path'])
        replacement = tmp_path/'equivalent-first-authority.json'; replacement.write_bytes(old.read_bytes())
        prior['authorization'] = reference(replacement)
    else: overrides['continuation_checkpoint'] = c['first']['predecessor_ledger']['path']
    destination = tmp_path/'must-not-exist'
    with pytest.raises(BudgetStop): prepare_second(c, destination, budget_amendment=proof, **overrides)
    assert not destination.exists(); unchanged(c)


@pytest.mark.parametrize('damage', ['drop', 'change_total', 'change_default', 'change_prices', 'unpin_first_authority', 'typed_history_change'])
def test_prepared_registration_or_import_refuses_tampered_authority(second_approved, tmp_path, damage):
    c = second_approved; path, m = prepare_second(c, tmp_path/'second')
    if damage == 'drop': m.pop('budget_amendment')
    elif damage == 'change_total': m['budget']['additional_usd'] = '700'
    elif damage == 'change_default': m['budget']['per_attempt_usd'] = '6'
    elif damage == 'change_prices': m['budget']['prices_per_token']['input'] = '0.0000001'
    elif damage == 'unpin_first_authority': m['pinned_files'].pop(c['first']['authorization']['path'])
    else:
        ledger = registration.read_json(c['proof']['predecessor_ledger']['path'])
        ledger['requests'][1]['typed_integer'] = False  # False == 0 must still fail exact typed binding.
        save(c['proof']['predecessor_ledger']['path'], ledger)
    save(path, m)
    with pytest.raises(BudgetStop): registration.validate_registration(path)
    if damage != 'change_prices':
        with pytest.raises(BudgetStop): registration.open_audit_ledger(m, path, registration.sha(path))
    assert not Path(m['budget']['ledger_path']).exists()
    assert c['state'].read_bytes() == c['state_bytes']


def test_transitive_financial_evidence_is_pinned_but_never_model_readable(second_approved, tmp_path):
    path, m = prepare_second(second_approved, tmp_path/'second')
    assert amendment.paths(m) <= registration.required_paths(m)
    prompt = Path(m['job']['instruction']).read_text(); system = Path(m['job']['system_prompt']).read_text()
    for r in refs(second_approved['proof']):
        assert m['pinned_files'][r['path']] == r['sha256']
        assert r['path'] not in m['job']['readable_inputs']
        assert r['path'] not in prompt and r['path'] not in system
    assert second_approved['proof']['authorization_quote'] not in prompt + system
    unchanged(second_approved)
