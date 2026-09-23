"""Real offline audit preparation with synthetic budget-amendment ancestry.

The imported ancestry fixture stubs historical acceptance and repository
attestation only. Preparation, proof validation, rendering, registration and
ledger import stay real. No provider or production evidence is accessed.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from audit_controls import prepare, registration
from audit_controls.test_context_preparation import ancestry, save
import budget_amendment as amendment


def reference(path):
    return {'path': str(path), 'sha256': registration.sha(path)}


@pytest.fixture
def approved(ancestry, tmp_path):
    args, _, _, state = ancestry
    origin_path = args['parent_registration']
    origin = registration.read_json(origin_path)
    origin['budget']['per_job_attempt_usd'][args['parent_job_id']] = '40'
    save(origin_path, origin)
    previous_path = prepare.prepare(**args, destination=tmp_path/'previous', attempt_cap='40')
    previous = registration.read_json(previous_path)
    checkpoint = registration.read_json(args['reconciled_checkpoint'])
    rows = deepcopy(checkpoint['requests']) + [{
        'id': 'synthetic-full-reservation-debit', 'status': 'settled',
        'attempt': registration.sha(previous_path) + ':' + previous['job']['id'],
        'reserved_usd': '2.50', 'cost_usd': '2.50', 'request_sha256': 'a' * 64,
        'settlement_basis': 'registered_stall_policy_full_reservation_debit',
        'provider_charge_confirmed': False, 'provider_charge_usd': None,
        'provider_usage_is_final': False,
    }]
    ledger_path = save(previous['budget']['ledger_path'], {
        'manifest_sha256': registration.sha(previous_path), 'additional_cap_usd': '400',
        'attempt_cap_usd': '5', 'requests': rows,
    })
    owner = {'schema_version': 1, 'registration_sha256': registration.sha(previous_path),
        'ledger_path': str(ledger_path), 'source_registration_sha256': registration.sha(origin_path),
        'parent_checkpoint_sha256': previous['budget']['continuation']['sha256']}
    owner_path = save(previous_path.parent/'sequence_claim/owner.json', owner)
    save(state, owner)
    authority = save(tmp_path/'approval.json', {
        'kind': 'audit_sequence_additional_budget_authorization_receipt', 'schema_version': 1,
        'authorization': {'additional_budget_authorized': True, 'currency': 'USD',
            'user_quote': 'synthetic approval: add $100', 'prior_shared_cap_usd': '400',
            'additional_authorized_usd': '100', 'new_shared_cap_usd': '500'},
        'predecessor': {'registration_path': str(previous_path),
            'registration_sha256': registration.sha(previous_path), 'ledger_path': str(ledger_path),
            'ledger_sha256': registration.sha(ledger_path), 'canonical_owner_sha256': registration.sha(owner_path),
            'sequence_settled_rows': len(rows), 'sequence_accounted_usd': '3.75',
            'registered_predecessor_shared_cap_usd': '400'},
    })
    proof = {'kind': amendment.KIND, 'origin_registration': reference(origin_path),
        'predecessor_registration': reference(previous_path), 'predecessor_ledger': reference(ledger_path),
        'predecessor_owner': reference(owner_path), 'authorization': reference(authority),
        'prior_total_usd': '400', 'increase_usd': '100', 'total_usd': '500', 'default_attempt_usd': '5'}
    immutable = {p: p.read_bytes() for p in (
        origin_path, previous_path, ledger_path, owner_path, authority, state, args['reconciled_checkpoint'])}
    return {'args': {**args, 'attempt_cap': '40', 'continuation_checkpoint': ledger_path},
        'proof': proof, 'rows': rows, 'immutable': immutable, 'state': state}


def amended(approved, target):
    path = prepare.prepare(**approved['args'], destination=target, budget_amendment=approved['proof'])
    return path, registration.validate_registration(path)


def unchanged(approved):
    assert all(path.read_bytes() == raw for path, raw in approved['immutable'].items())


def test_real_prepare_registration_and_ledger_preserve_history_with_new_absolute_cap(approved, tmp_path):
    path, manifest = amended(approved, tmp_path/'amended')
    assert manifest['budget_amendment'] == approved['proof']
    assert manifest['budget']['additional_usd'] == '500'
    assert manifest['budget']['per_attempt_usd'] == '5'
    assert manifest['budget']['per_job_attempt_usd'] == {manifest['job']['id']: '40'}
    assert manifest['sequence_state'] == str(approved['state'])
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not Path(manifest['job']['attempt_dir']).exists()
    assert not (path.parent/'sequence_claim').exists()
    unchanged(approved)

    ledger = registration.open_audit_ledger(manifest, path, registration.sha(path))
    imported = registration.read_json(ledger.path)
    assert imported['additional_cap_usd'] == '500'
    assert imported['attempt_cap_usd'] == '5'
    assert imported['requests'] == approved['rows']
    assert sum(Decimal(row['cost_usd']) for row in imported['requests']) == Decimal('3.75')
    assert imported['requests'][-1]['provider_charge_confirmed'] is False
    assert imported['requests'][-1]['provider_charge_usd'] is None
    assert imported['continued_from']['checkpoint_sha256'] == approved['proof']['predecessor_ledger']['sha256']
    # Reopening imports the same prefix once, never adds another $100 or row.
    registration.open_audit_ledger(manifest, path, registration.sha(path))
    assert registration.read_json(ledger.path) == imported
    unchanged(approved)
    assert not (path.parent/'sequence_claim').exists()


def test_authority_is_pinned_but_not_delivered_to_the_scientific_model(approved, tmp_path):
    path, manifest = amended(approved, tmp_path/'private_authority')
    proof_paths = amendment.paths(manifest)
    assert proof_paths <= registration.required_paths(manifest)
    for proof_path in proof_paths:
        assert manifest['pinned_files'][str(proof_path)] == registration.sha(proof_path)
        assert str(proof_path) not in manifest['job']['readable_inputs']
        for role in ('instruction', 'system_prompt'):
            assert str(proof_path) not in Path(manifest['job'][role]).read_text()
    without = deepcopy(manifest)
    without.pop('budget_amendment')
    without['budget']['additional_usd'] = '400'
    assert prepare.render_instruction(manifest) == prepare.render_instruction(without)
    assert prepare.render_system(manifest) == prepare.render_system(without)
    for role, render in [('instruction', prepare.render_instruction), ('system_prompt', prepare.render_system)]:
        text = Path(manifest['job'][role]).read_text()
        assert text == render(without)
        assert 'synthetic approval: add $100' not in text
        assert 'additive_sequence_budget_v1' not in text
    assert set(manifest['job']['readable_inputs']) == set(manifest['inputs'].values()) | {
        manifest['job']['instruction'], manifest['job']['system_prompt']}
    unchanged(approved)


@pytest.mark.parametrize('damage', ['wrong_origin', 'wrong_checkpoint', 'unauthorized', 'wrong_owner', 'unsettled'])
def test_invalid_authority_or_predecessor_refused_before_destination(approved, tmp_path, damage):
    proof = deepcopy(approved['proof'])
    args = dict(approved['args'])
    if damage == 'wrong_origin':
        # Same bytes at another canonical path are not the registered origin.
        other = tmp_path/'other_origin.json'
        other.write_bytes(Path(proof['origin_registration']['path']).read_bytes())
        proof['origin_registration'] = reference(other)
    elif damage == 'wrong_checkpoint':
        other = registration.read_json(args['continuation_checkpoint'])
        other['unrelated_checkpoint_marker'] = True
        args['continuation_checkpoint'] = save(tmp_path/'other_checkpoint.json', other)
    elif damage == 'unauthorized':
        other = registration.read_json(proof['authorization']['path'])
        other['authorization']['additional_budget_authorized'] = False
        proof['authorization'] = reference(save(tmp_path/'no_approval.json', other))
    elif damage == 'wrong_owner':
        other = registration.read_json(proof['predecessor_owner']['path'])
        other['registration_sha256'] = 'f' * 64
        proof['predecessor_owner'] = reference(save(tmp_path/'wrong_owner.json', other))
    else:
        other = registration.read_json(args['continuation_checkpoint'])
        other['requests'][-1]['status'] = 'pending'
        args['continuation_checkpoint'] = save(tmp_path/'pending_checkpoint.json', other)
    target = tmp_path/'must_not_exist'
    with pytest.raises(registration.BudgetStop):
        prepare.prepare(**args, destination=target, budget_amendment=proof)
    assert not target.exists()
    unchanged(approved)


@pytest.mark.parametrize('damage', ['raise_cap', 'lower_cap', 'drop_proof', 'change_default',
    'unpin_authorization', 'unpin_implementation', 'read_approval', 'repin_unapproved_authority'])
def test_registration_refuses_amendment_tampering(approved, tmp_path, damage):
    path, manifest = amended(approved, tmp_path/'tamper')
    if damage in ('raise_cap', 'lower_cap'):
        manifest['budget']['additional_usd'] = '600' if damage == 'raise_cap' else '400'
    elif damage == 'drop_proof':
        manifest.pop('budget_amendment')
    elif damage == 'change_default':
        manifest['budget']['per_attempt_usd'] = '6'
    elif damage == 'unpin_authorization':
        manifest['pinned_files'].pop(manifest['budget_amendment']['authorization']['path'])
    elif damage == 'unpin_implementation':
        manifest['pinned_files'].pop(str(Path(amendment.__file__).resolve()))
    elif damage == 'read_approval':
        manifest['job']['readable_inputs'].append(manifest['budget_amendment']['authorization']['path'])
    else:
        authority = registration.read_json(manifest['budget_amendment']['authorization']['path'])
        authority['authorization']['additional_budget_authorized'] = False
        replacement = save(tmp_path/'coherently_pinned_unapproved.json', authority)
        manifest['budget_amendment']['authorization'] = reference(replacement)
        manifest['pinned_files'][str(replacement)] = registration.sha(replacement)
    save(path, manifest)
    with pytest.raises(registration.BudgetStop):
        registration.validate_registration(path)
    assert not Path(manifest['budget']['ledger_path']).exists()
    unchanged(approved)


@pytest.mark.parametrize('raw', ['null', '[]', 'true', '{}', '{',
    '{"kind":"first","kind":"second"}', '{"amount":NaN}', '{"amount":1e999}'])
def test_cli_rejects_malformed_or_null_amendment_before_prepare(tmp_path, monkeypatch, raw):
    proof = tmp_path/'bad_proof.json'
    proof.write_text(raw)
    target = tmp_path/'never_created'
    argv = ['prepare', '--budget-amendment', str(proof), '--destination', str(target)]
    for option in ('parent-registration', 'parent-overlay', 'parent-job-id', 'reconciliation-receipt',
                   'reconciled-checkpoint', 'job-id'):
        argv += ['--'+option, 'synthetic-unused']
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setattr(prepare, 'prepare', lambda **kwargs: pytest.fail('invalid CLI proof reached preparation'))
    with pytest.raises((registration.BudgetStop, ValueError)):
        prepare.main()
    assert not target.exists()


def test_cli_passes_exact_valid_proof_to_real_preparation(approved, tmp_path, monkeypatch, capsys):
    proof = save(tmp_path/'selection.json', approved['proof'])
    target = tmp_path/'cli_amended'
    argv = ['prepare', '--budget-amendment', str(proof), '--destination', str(target)]
    for key, value in approved['args'].items():
        argv += ['--'+key.replace('_', '-'), str(value)]
    monkeypatch.setattr(sys, 'argv', argv)
    prepare.main()
    report = json.loads(capsys.readouterr().out)
    path = target/'registration.json'
    assert report == {'registration': str(path), 'sha256': registration.sha(path)}
    assert registration.validate_registration(path)['budget_amendment'] == approved['proof']
    assert not (target/'billing.json').exists()
    unchanged(approved)


def test_legacy_preparation_keeps_original_cap_and_exact_scientific_rendering(ancestry, tmp_path):
    path = prepare.prepare(**ancestry[0], destination=tmp_path/'legacy')
    manifest = registration.validate_registration(path)
    assert 'budget_amendment' not in manifest
    assert manifest['budget']['additional_usd'] == '400'
    assert manifest['budget']['per_attempt_usd'] == '5'
    assert str(Path(amendment.__file__).resolve()) not in manifest['pinned_files']
    assert Path(manifest['job']['instruction']).read_bytes() == prepare.render_instruction(manifest).encode()
    assert registration.sha(manifest['job']['system_prompt']) == 'c7e9e0d18b0ee55a1b3cc276d77eb7605bcfbc2753bda28f24e268d82cfedc8b'
    assert ancestry[2] == {p: Path(p).read_bytes() for p in ancestry[2]}
    assert not Path(manifest['budget']['ledger_path']).exists()


@pytest.fixture
def amended_predecessor(approved, tmp_path):
    path, manifest = amended(approved, tmp_path/'first_amended')
    ledger = registration.open_audit_ledger(manifest, path, registration.sha(path))
    args = {**approved['args'], 'continuation_checkpoint': ledger.path}
    return path, manifest, args


def equivalent_authority_at_another_path(approved, tmp_path):
    proof = deepcopy(approved['proof'])
    replacement = tmp_path/'same_approval_new_identity.json'
    replacement.write_bytes(Path(proof['authorization']['path']).read_bytes())
    proof['authorization'] = reference(replacement)
    return proof


def test_real_later_audit_pins_and_preserves_exact_immediate_amendment(amended_predecessor, approved, tmp_path):
    previous_path, previous, args = amended_predecessor
    before = {p: p.read_bytes() for p in (previous_path, Path(previous['budget']['ledger_path']))}
    path = prepare.prepare(**args, destination=tmp_path/'later', budget_amendment=approved['proof'])
    manifest = registration.validate_registration(path)
    assert manifest['pinned_files'][str(previous_path)] == registration.sha(previous_path)
    assert previous_path in registration.required_paths(manifest)
    assert manifest['budget_amendment'] == previous['budget_amendment']
    assert str(previous_path) not in manifest['job']['readable_inputs']
    assert str(previous_path) not in Path(manifest['job']['instruction']).read_text()
    ledger = registration.open_audit_ledger(manifest, path, registration.sha(path))
    carried = registration.read_json(ledger.path)
    assert carried['additional_cap_usd'] == '500'
    assert carried['requests'] == approved['rows']
    assert 'budget_amendment_sha256' not in carried['continued_from']
    assert all(p.read_bytes() == raw for p, raw in before.items())
    unchanged(approved)


def test_real_later_prepare_rejects_different_valid_proof_before_destination(amended_predecessor, approved, tmp_path):
    _, _, args = amended_predecessor
    proof = equivalent_authority_at_another_path(approved, tmp_path)
    # This is independently valid authority for the same cap; the rejection
    # must specifically bind immediate predecessor identity, not bad proof.
    candidate = {'parent': {'registration': str(args['parent_registration'])},
        'budget_amendment': proof, 'budget': {'additional_usd': '500', 'per_attempt_usd': '5'}}
    assert amendment.effective_total(candidate, registration.read_json(args['parent_registration']), require_pins=False) == 500
    target = tmp_path/'must_not_exist'
    with pytest.raises(registration.BudgetStop, match='inherited budget amendment'):
        prepare.prepare(**args, destination=target, budget_amendment=proof)
    assert not target.exists()
    unchanged(approved)


@pytest.mark.parametrize('damage', ['replacement', 'drop', 'missing_predecessor_pin'])
def test_later_registration_and_ledger_open_reject_changed_inheritance(amended_predecessor, approved, tmp_path, damage):
    previous_path, _, args = amended_predecessor
    target = tmp_path/'later_tamper'
    path = prepare.prepare(**args, destination=target, budget_amendment=approved['proof'])
    manifest = registration.read_json(path)
    if damage == 'replacement':
        proof = equivalent_authority_at_another_path(approved, tmp_path)
        manifest['budget_amendment'] = proof
        manifest['pinned_files'][proof['authorization']['path']] = proof['authorization']['sha256']
        assert amendment.effective_total(manifest, registration.read_json(args['parent_registration'])) == 500
    elif damage == 'drop':
        manifest.pop('budget_amendment')
    else:
        manifest['pinned_files'].pop(str(previous_path))
    save(path, manifest)
    for check in (lambda: registration.validate_registration(path),
                  lambda: registration.open_audit_ledger(manifest, path, registration.sha(path))):
        with pytest.raises(registration.BudgetStop):
            check()
        assert not (target/'billing.json').exists()
        assert not (target/'billing.json.lock').exists()
        assert not (target/'sequence_claim').exists()
    unchanged(approved)


@pytest.mark.parametrize('damage', ['wrong_ledger', 'wrong_origin', 'wrong_registration_sha'])
def test_immediate_predecessor_metadata_must_match_checkpoint(amended_predecessor, approved, tmp_path, damage):
    previous_path, previous, args = amended_predecessor
    checkpoint = registration.read_json(args['continuation_checkpoint'])
    candidate = {'parent': {'registration': str(args['parent_registration'])},
        'budget_amendment': deepcopy(approved['proof']),
        'budget': {'continuation': {'checkpoint': str(args['continuation_checkpoint']),
                                  'sha256': registration.sha(args['continuation_checkpoint'])}}}
    changed = deepcopy(previous)
    if damage == 'wrong_ledger':
        changed['budget']['ledger_path'] = str(tmp_path/'unrelated.json')
    elif damage == 'wrong_origin':
        changed['parent']['registration'] = str(tmp_path/'unrelated-origin.json')
    else:
        changed['unrelated_registration_marker'] = True
    save(previous_path, changed)
    if damage != 'wrong_registration_sha':
        # Coherently rebind the source/checkpoint so the metadata check, not
        # merely an earlier hash mismatch, catches the wrong ledger or origin.
        checkpoint['manifest_sha256'] = registration.sha(previous_path)
        save(args['continuation_checkpoint'], checkpoint)
        candidate['budget']['continuation']['sha256'] = registration.sha(args['continuation_checkpoint'])
    with pytest.raises(registration.BudgetStop, match='immediate predecessor or origin'):
        registration.validate_budget_amendment_predecessor(candidate, checkpoint, require_pins=False)
    unchanged(approved)


def test_reconciled_checkpoint_selects_exact_source_registration_metadata(amended_predecessor, approved, tmp_path):
    previous_path, previous, args = amended_predecessor
    source_ledger = args['continuation_checkpoint']
    checkpoint = save(tmp_path/'reconciled/new_checkpoint.json', registration.read_json(source_ledger))
    bridge = {'source_registration': str(previous_path), 'source_ledger': str(source_ledger),
        'receipt': str(tmp_path/'synthetic_accounting_receipt.json'),
        'result': str(Path(previous['job']['attempt_dir'])/'result.json')}
    candidate = {'parent': {'registration': str(args['parent_registration'])},
        'budget_amendment': deepcopy(approved['proof']),
        'budget': {'continuation': {'checkpoint': str(checkpoint), 'sha256': registration.sha(checkpoint),
                                  'reconciliation': bridge}},
        'pinned_files': {str(previous_path): registration.sha(previous_path), str(checkpoint): registration.sha(checkpoint)}}
    assert not checkpoint.with_name('registration.json').exists()
    assert registration.validate_budget_amendment_predecessor(candidate, registration.read_json(checkpoint)) == previous_path
    # This metadata helper deliberately does not decode receipt/result bodies;
    # the existing reconciliation validator remains responsible for them.
    assert not Path(bridge['receipt']).exists() and not Path(bridge['result']).exists()
    unchanged(approved)
