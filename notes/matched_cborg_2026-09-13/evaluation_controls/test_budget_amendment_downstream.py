"""Authorized allocation inheritance; wholly synthetic inputs and no provider."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

import budget_amendment as amendment
from budgeted_cborg import BudgetStop
from test_budget_amendment import make_fixture
from test_source_pair import composite, build, save
import registration as registration
import source_pair
from finalization_controls import registration as final_registration
import continuation_sequence as sequence
import test_continuation_sequence as foundation


def budget_manifest(tmp_path, *, schema_version=2):
    proof, generation, anchor, manifest = make_fixture(tmp_path)
    manifest.update(schema_version=schema_version,
        source_pair={'original_generation': {'registration': deepcopy(proof['origin_registration'])}},
        budget_sequence={'origin': {'registration': deepcopy(proof['origin_registration'])}})
    return proof, generation, anchor, manifest


@pytest.mark.parametrize('selector', [None, {}, False])
def test_legacy_evaluation_cannot_select_an_amendment(tmp_path, selector):
    _, _, _, manifest = budget_manifest(tmp_path, schema_version=1)
    manifest[amendment.KEY] = selector
    with pytest.raises(BudgetStop, match='composite evaluation ancestry'):
        registration.allocation_total(manifest)


def test_effective_cap_requires_all_inherited_authority(tmp_path):
    proof, _, _, manifest = budget_manifest(tmp_path)
    assert registration.allocation_total(manifest) == Decimal('500')
    manifest['pinned_files'].pop(proof['authorization']['path'])
    with pytest.raises(BudgetStop):
        registration.allocation_total(manifest)


@pytest.mark.parametrize('damage', ['missing', 'extra', 'different'])
def test_phase4_rejects_lost_or_replaced_authority(tmp_path, damage):
    proof, _, _, _ = make_fixture(tmp_path)
    accepted={'job':{'id':'audit'}, 'budget':{'per_attempt_usd':'5',
        'per_job_attempt_usd':{'audit':'40'},'prices_per_token':{'input':'1'}},
        amendment.KEY:proof}
    manifest={'job':{'id':'phase4'}, 'budget':{'per_job_attempt_usd':{'phase4':'20'},
        'prices_per_token':{'input':'1'}}, amendment.KEY:deepcopy(proof)}
    final_registration.validate_budget_identity(manifest,accepted)
    if damage == 'missing':
        del manifest[amendment.KEY]
    elif damage == 'extra':
        del accepted[amendment.KEY]
    else:
        manifest[amendment.KEY]['total_usd']='600'
    with pytest.raises(BudgetStop, match='accepted budget amendment'):
        final_registration.validate_budget_identity(manifest,accepted)


@pytest.mark.parametrize('composite', ['amended'], indirect=True)
def test_real_composite_preparation_and_handoff_keep_one_increase(composite):
    phase=composite['phase']; proof=phase[amendment.KEY]
    immutable={Path(ref['path']):Path(ref['path']).read_bytes() for key,ref in proof.items()
               if key in amendment.REFS}
    old_ledger=Path(phase['budget']['ledger_path']); old_bytes=old_ledger.read_bytes()
    owner_before=composite['state'].read_bytes()
    result=build(composite); path=result['registration']; manifest=registration.read_json(path)
    assert manifest[amendment.KEY] == proof
    assert manifest['budget']['additional_usd'] == '500'
    assert manifest['budget']['per_attempt_usd'] == '5'
    assert 'per_job_attempt_usd' not in manifest['budget']
    assert registration.allocation_total(manifest) == Decimal('500')
    assert all(str(p) in manifest['pinned_files'] for p in amendment.paths(manifest))
    assert amendment.paths(manifest) <= registration.required_paths(manifest)
    spent=sum(Decimal(row['cost_usd']) for row in registration.read_json(old_ledger)['requests'])
    assert Decimal(result['report']['remaining_allocation_usd']) == Decimal('500')-spent
    assert result['report']['rubric_ratings'] == 20
    assert result['report']['semantic_repeat_ratings'] == 8
    assert composite['state'].read_bytes() == owner_before
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert registration.verify_manifest(manifest,path,registration.sha(path))
    with sequence.owned_sequence(manifest,path,registration.sha(path)) as owner:
        identity=registration.sha(path)+':'+manifest['evaluation_jobs'][0]['id']
        ticket=owner.reserve(identity,'.04','synthetic-evaluation')
        owner.ledger.settle(ticket,'.03',response_sha256='synthetic',usage={})
    rows=registration.read_json(manifest['budget']['ledger_path'])['requests']
    assert rows[:-1] == registration.read_json(old_ledger)['requests']
    assert old_ledger.read_bytes() == old_bytes
    assert all(p.read_bytes()==value for p,value in immutable.items())
    assert registration.read_json(proof['origin_registration']['path'])['budget']['additional_usd']=='400'
    assert registration.read_json(proof['predecessor_ledger']['path'])['additional_cap_usd']=='400'


@pytest.mark.parametrize('composite', ['amended'], indirect=True)
@pytest.mark.parametrize('damage', ['drop_proof','unapproved_cap','default_cap','missing_pin'])
def test_actual_composite_admission_refuses_changed_budget_authority(composite,damage):
    result=build(composite);path=result['registration'];manifest=registration.read_json(path)
    state_before=composite['state'].read_bytes()
    if damage=='drop_proof':
        del manifest[amendment.KEY]
    elif damage=='unapproved_cap':
        manifest['budget']['additional_usd']='600'
    elif damage=='default_cap':
        manifest['budget']['per_attempt_usd']='40'
    else:
        manifest['pinned_files'].pop(manifest[amendment.KEY]['authorization']['path'])
    save(path,manifest)
    with pytest.raises(BudgetStop):
        registration.verify_manifest(manifest,path,registration.sha(path))
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert composite['state'].read_bytes()==state_before


@pytest.mark.parametrize('composite', ['amended'], indirect=True)
def test_accepted_phase4_proof_cannot_be_replaced_by_another_valid_proof(composite):
    result=build(composite);manifest=registration.read_json(result['registration'])
    original=manifest[amendment.KEY]['origin_registration']
    replacement,_,_,proof_manifest=make_fixture(composite['destination']/'other-proof',
        generation_path=original['path'])
    manifest[amendment.KEY]=replacement
    manifest['pinned_files'].update(proof_manifest['pinned_files'])
    # The replacement is valid in isolation; accepted-source equality must reject it.
    assert registration.allocation_total(manifest)==500
    with pytest.raises(BudgetStop,match='accepted budget amendment'):
        source_pair.validate(manifest)


@pytest.mark.parametrize('damage', ['drop', 'replace'])
def test_real_sequence_handoff_cannot_drop_or_replace_inherited_proof(tmp_path,damage):
    manifest,path,state=foundation.fixture(tmp_path,amended=True)
    before=state.read_bytes()
    if damage=='drop':
        del manifest[amendment.KEY]
    else:
        origin=manifest[amendment.KEY]['origin_registration']
        proof,_,_,other=make_fixture(tmp_path/'other-authority',generation_path=origin['path'])
        manifest[amendment.KEY]=proof
        manifest['pinned_files'].update(other['pinned_files'])
    foundation.finish_registration(manifest,path)
    with pytest.raises(BudgetStop,match='inherited budget amendment'):
        with foundation.enter(manifest,path): pass
    assert state.read_bytes()==before
    assert not Path(manifest['budget']['ledger_path']).exists()
