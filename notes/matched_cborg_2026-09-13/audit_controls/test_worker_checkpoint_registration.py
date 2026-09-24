"""Real offline preparation with synthetic stopped-source metadata.

The old generation fixture stubs its historical replay. The zero-check scanner
and integration-context equivalence guard have separate real-envelope/renderer
suites; worker typed closure has runtime tests.
No model or actual experiment artifacts are used here.
"""
from copy import deepcopy
from decimal import Decimal
import os
from pathlib import Path
import sys

import pytest

from audit_controls import prepare, registration, worker_checkpoint
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_worker_checkpoint import freeze, sha, ref
from budgeted_cborg import attempt_identity, BudgetStop


@pytest.fixture
def prepared_source(metadata_ancestry, tmp_path, monkeypatch):
    from audit_controls import batch_native, checkpoint_eligibility
    monkeypatch.setattr(checkpoint_eligibility, 'verify', lambda *args: {'zero_terminal_source_check': True})
    monkeypatch.setattr(batch_native, 'verify_checkpoint_context', lambda *args: None)
    args = deepcopy(metadata_ancestry[0])
    selected = dict(audit_batch_format=True, audit_batch_navigation=True,
                    audit_worker_navigation=True, durable_sequence_claim=True)
    path = prepare.prepare(**args, destination=tmp_path/'source',
        audit_batches={'kind':'fresh_context_integrated_v1', 'worker_total_cap_usd':'12'}, **selected)
    source = registration.read_json(path); identity = sha(path)
    job = source['job']; attempt = Path(job['attempt_dir']); owner_id = attempt_identity(identity, job['id'])
    before = registration.read_json(source['budget']['continuation']['checkpoint'])['requests']
    rows = deepcopy(before); closures = []
    for index, child in enumerate(source['audit_batches']['children']):
        root = Path(child['attempt_dir']); root.mkdir(parents=True)
        if child['kind'] == 'integration': continue
        save(child['proposal_path'], {'synthetic':'worker science is never accepted by this fixture'})
        row = {'id':f'synthetic-{index}', 'attempt':owner_id, 'status':'settled', 'cost_usd':'0.10',
               'attempt_cap_usd':'20', 'stage_cap_usd':'12'}
        rows.append(row)
        closure = save(root/'closed.json', {'status':'completed_proposal', 'registration_sha256':identity,
            'job_id':job['id'], 'child_id':child['id'], 'billing_attempt':owner_id,
            'runtime':{'exit_code':0,'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0},
            'request_rows':[row]})
        closures.append({'id':child['id'],'closure':ref(closure)})
    ledger = save(source['budget']['ledger_path'], {'manifest_sha256':identity,
        'additional_cap_usd':source['budget']['additional_usd'], 'attempt_cap_usd':source['budget']['per_attempt_usd'],
        'attempt_caps_usd':{owner_id:'20'}, 'requests':rows,
        'stopped_attempts':{owner_id:{'paid_request':False,'denied_reservation_usd':'20'}}})
    result = save(attempt/'result.json', {'status':'stopped','scope':'phase3_audit_only','error_type':'BudgetStop',
        'registration_sha256':identity,'job_id':job['id'],
        'runtime':{'proxy_shutdown_complete':True,'unfinished_handlers':0}})
    owner_value = {'schema_version':1,'registration_sha256':identity,'ledger_path':str(ledger),
        'parent_checkpoint_sha256':source['budget']['continuation']['sha256'],
        'source_registration_sha256':sha(source['parent']['registration'])}
    owner = save(path.parent/'sequence_claim/owner.json',owner_value)
    previous = save(path.parent/'sequence_claim/predecessor.json',{'synthetic':'old consumed owner'})
    claim = save(path.parent/'sequence_claim/manifest.json',{'schema_version':1,'kind':'observed_sequence_owner_transition',
        'protocol':'durable_sequence_claim_v1','stage':'audit','claiming_registration_path':str(path),
        'claiming_registration_sha256':identity,'canonical_state_path':source['sequence_state'],
        'owner_sha256':sha(owner),'predecessor_absent':False,'predecessor_sha256':sha(previous),
        'origin':{'registration_sha256':sha(source['parent']['registration']),
                  'ledger_path':registration.read_json(source['parent']['registration'])['budget']['ledger_path']},
        'implementation_sha256':sha(Path(source['repository'])/worker_checkpoint.CONTROL_RELATIVE/'sequence_claim.py')})
    os.link(claim,path.parent/'sequence_claim/ready.json')
    save(source['sequence_state'],owner_value)
    inventory = save(tmp_path/'inventory.json',freeze(path.parent))
    proof = {'kind':worker_checkpoint.KIND,'source_registration':ref(path),'source_ledger':ref(ledger),
        'source_owner':ref(owner),'source_claim':ref(claim),'source_result':ref(result),
        'source_inventory':ref(inventory),'workers':closures}
    args.update(job_id='synthetic_checkpoint',continuation_checkpoint=str(ledger),
                audit_worker_checkpoint=proof,**selected)
    return args, source, path


def test_real_preparer_creates_only_integration_static_inputs(prepared_source,tmp_path,monkeypatch):
    from audit_controls import batch_native
    args,source,original = prepared_source
    checked_contexts = []
    monkeypatch.setattr(batch_native, 'verify_checkpoint_context',
                        lambda manifest, evidence: checked_contexts.append(evidence.sha256))
    frozen = freeze(original.parent); state = Path(source['sequence_state']).read_bytes()
    path = prepare.prepare(**args,destination=tmp_path/'next')
    manifest = registration.validate_registration(path)
    block = manifest['audit_batches']
    assert block['kind'] == worker_checkpoint.BATCH_KIND
    assert [c['id'] for c in block['children']] == ['integration']
    assert 'worker_total_cap_usd' not in block
    assert Path(block['plan_path']).read_bytes() == Path(source['audit_batches']['plan_path']).read_bytes()
    assert {p.name for p in (path.parent/'batch-inputs').iterdir()} == {'integration'}
    assert not (path.parent/'attempts').exists() and not (path.parent/'billing.json').exists()
    assert not (path.parent/'sequence_claim').exists()
    assert freeze(original.parent) == frozen and Path(source['sequence_state']).read_bytes() == state
    assert worker_checkpoint.validate(manifest).sha256 == sha(original)
    assert checked_contexts == [sha(original), sha(original)]
    # #2391: the controller wrapper is not the integration model's input.
    plan = registration.read_json(path.parent/'offline_plan.json')
    assert plan['new_worker_count'] == 0
    assert plan['inherited_worker_count'] == len(source['audit_batches']['children']) - 1
    assert plan['historical_accounted_usd'] == manifest['budget']['continuation']['cost_usd']
    assert plan['historical_costs_preserved'] is True
    assert plan['integration_attempt_cap_usd'] == '20'
    assert 'worker_total_cap_usd' not in plan
    rows = plan['audit_batch_inputs']
    assert [r['id'] for r in rows] == ['integration']
    system_bytes = len(Path(block['children'][0]['system_prompt']).read_bytes())
    user_bytes = len(Path(block['integration_base']).read_bytes())
    assert rows[0]['system_bytes'] == system_bytes
    assert rows[0]['known_user_bytes'] == user_bytes
    assert plan['inline_instruction_bytes'] == user_bytes
    assert plan['input_estimate_tokens'] == (system_bytes + user_bytes + 3) // 4
    assert plan['controller_instruction_bytes'] == len(Path(manifest['job']['instruction']).read_bytes())
    assert rows[0]['dynamic_proposal_inputs_pending'] is True
    assert plan['complete_workload_cost_estimate_available'] is False


def test_stale_owner_refused_before_destination_creation(prepared_source,tmp_path):
    args,source,_ = prepared_source
    save(source['sequence_state'],{'synthetic':'legitimate newer owner'})
    with pytest.raises(BudgetStop,match='current sequence owner'):
        prepare.prepare(**args,destination=tmp_path/'absent')
    assert not (tmp_path/'absent').exists()


def test_changed_target_scientific_code_refused_before_destination_creation(
        prepared_source,tmp_path,monkeypatch):
    """#2388: preflight must compare the proposed checkout, not source to itself."""
    import shutil
    args,source,_ = prepared_source
    original_repository = Path(source['repository'])
    target_repository = tmp_path/'target_repository'
    target_repository.mkdir()
    for name in source['pinned_files']:
        path = Path(name)
        if not path.is_relative_to(original_repository):
            continue
        relative = path.relative_to(original_repository)
        if relative.parts[0] in ('src','.claude') or str(relative) in ('pyproject.toml','poetry.lock'):
            target = target_repository/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    changed = target_repository/'src/data_sheets_schema/audit_batch_context.py'
    changed.write_bytes(changed.read_bytes()+b'\n# changed synthetic scientific rendering\n')
    args['repository'] = target_repository
    monkeypatch.chdir(target_repository)
    with pytest.raises(BudgetStop,match='scientific implementation bytes'):
        prepare.prepare(**args,destination=tmp_path/'absent')
    assert not (tmp_path/'absent').exists()


@pytest.mark.parametrize('change', ['missing_claim','missing_navigation','fresh_batches','different_parent','changed_native'])
def test_checkpoint_selection_is_explicit_and_preflight_is_readonly(prepared_source,tmp_path,change):
    args,source,_=prepared_source
    if change=='missing_claim':args['durable_sequence_claim']=False
    elif change=='missing_navigation':args['audit_worker_navigation']=False
    elif change=='fresh_batches':args['audit_batches']={'kind':'fresh_context_integrated_v1','worker_total_cap_usd':'12'}
    elif change=='different_parent':args['parent_job_id']='foreign'
    else:args['native_api_timeout_ms']=3600000
    with pytest.raises(BudgetStop):prepare.prepare(**args,destination=tmp_path/'absent')
    assert not (tmp_path/'absent').exists()


@pytest.mark.parametrize('value',[None,{},False])
def test_active_selector_refused_by_other_phases(tmp_path,value):
    from finalization_controls import registration as final
    from evaluation_controls import registration as evaluation
    import run_api_canary
    path=save(tmp_path/'registration.json',{'audit_worker_checkpoint':value})
    with pytest.raises(BudgetStop,match='audit-only'):final.validate_registration(path)
    manifest=registration.read_json(path)
    for validate in (evaluation.verify_manifest,run_api_canary.verify):
        with pytest.raises(BudgetStop,match='audit-only'):validate(manifest,path,sha(path))
