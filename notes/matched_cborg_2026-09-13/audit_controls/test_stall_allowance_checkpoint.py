"""A worker checkpoint of a source whose worker stall debits the allowance absorbed (#2519).

Built from the adversarial review's reproduction of PR #2517."""
from copy import deepcopy
from decimal import Decimal
import os
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]

from audit_controls import prepare, registration, worker_checkpoint
from audit_controls.test_context_preparation import ancestry, save  # noqa: F401
from audit_controls.test_source_metadata_upgrade import metadata_ancestry  # noqa: F401
from audit_controls.test_worker_checkpoint import freeze, sha, ref
from audit_controls.test_stall_policy import AUTHORIZATION
from budgeted_cborg import attempt_identity, BudgetStop, Ledger, STALL_DEBIT_BASIS

POLICY = {'kind': 'bounded_in_attempt_v1', 'count_attempts': 3, 'max_stall_debits': 4,
          'stall_allowance_usd': '5',
          'authorization': {**AUTHORIZATION, 'authorized_max_stall_debits': 4,
                            'authorized_stall_allowance_usd': '5'}}


def _ledger_admits(tmp_path):
    """The live ledger admits exactly these worker rows under stage cap 12 + allowance 5."""
    ledger = Ledger(tmp_path / 'probe.json', manifest_sha256='x', total_cap=500, attempt_cap=5,
                    attempt_caps_usd={'x:job': '20'}, stall_allowance_usd='5')
    for i in range(3):
        t = ledger.reserve('x:job', Decimal('4'), f'b{i}', stage_cap='12')
        ledger.debit_unconfirmed(t, maximum=4, evidence={})
    t = ledger.reserve('x:job', Decimal('0.10'), 'ok', stage_cap='12')
    ledger.settle(t, Decimal('0.10'), response_sha256='r', usage={})
    return True


def build(metadata_ancestry, tmp_path, monkeypatch, *, with_stalls, allowance='5'):
    from audit_controls import batch_native, checkpoint_eligibility
    monkeypatch.setattr(checkpoint_eligibility, 'verify', lambda *args: {'zero_terminal_source_check': True})
    monkeypatch.setattr(batch_native, 'verify_checkpoint_context', lambda *args: None)
    args = deepcopy(metadata_ancestry[0])
    selected = dict(audit_batch_format=True, audit_batch_navigation=True,
                    audit_worker_navigation=True, durable_sequence_claim=True,
                    native_stall_policy=deepcopy(POLICY), native_api_timeout_ms=3600000,
                    native_api_force_idle_timeout=False)
    path = prepare.prepare(**args, destination=tmp_path/'source',
        audit_batches={'kind':'fresh_context_integrated_v1', 'worker_total_cap_usd':'12'}, **selected)
    source = registration.read_json(path); identity = sha(path)
    assert source['native_stall_policy']['stall_allowance_usd'] == allowance
    job = source['job']; attempt = Path(job['attempt_dir']); owner_id = attempt_identity(identity, job['id'])
    before = registration.read_json(source['budget']['continuation']['checkpoint'])['requests']
    rows = deepcopy(before); closures = []
    first = True
    for index, child in enumerate(source['audit_batches']['children']):
        root = Path(child['attempt_dir']); root.mkdir(parents=True)
        if child['kind'] == 'integration': continue
        save(child['proposal_path'], {'synthetic':'worker science is never accepted by this fixture'})
        mine = []
        if first and with_stalls:
            for s in range(3):
                mine.append({'id': f'stall-{index}-{s}', 'attempt': owner_id, 'status': 'settled', 'cost_usd': '4',
                             'reserved_usd': '4', 'settlement_basis': STALL_DEBIT_BASIS,
                             'attempt_cap_usd': '20', 'stage_cap_usd': '12'})
        first = False
        mine.append({'id':f'synthetic-{index}', 'attempt':owner_id, 'status':'settled', 'cost_usd':'0.10',
               'attempt_cap_usd':'20', 'stage_cap_usd':'12'})
        rows.extend(mine)
        closure = save(root/'closed.json', {'status':'completed_proposal', 'registration_sha256':identity,
            'job_id':job['id'], 'child_id':child['id'], 'billing_attempt':owner_id,
            'runtime':{'exit_code':0,'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0},
            'request_rows':mine})
        closures.append({'id':child['id'],'closure':ref(closure)})
    ledger = save(source['budget']['ledger_path'], {'manifest_sha256':identity,
        'additional_cap_usd':source['budget']['additional_usd'], 'attempt_cap_usd':source['budget']['per_attempt_usd'],
        'attempt_caps_usd':{owner_id:'20'}, 'stall_allowance_usd': allowance, 'requests':rows,
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
    return args


def test_a_source_without_stalls_is_accepted(metadata_ancestry, tmp_path, monkeypatch):
    args = build(metadata_ancestry, tmp_path, monkeypatch, with_stalls=False)
    assert prepare.prepare(**args, destination=tmp_path/'next').exists()


def test_worker_stalls_the_allowance_absorbed_do_not_refuse_the_checkpoint(metadata_ancestry, tmp_path, monkeypatch):
    # The live ledger admits exactly these worker rows under a $12 stage cap and a $5 allowance...
    assert _ledger_admits(tmp_path)
    args = build(metadata_ancestry, tmp_path, monkeypatch, with_stalls=True)
    # ...and the checkpoint reads their spend the same way: $12.10 plain, $7.10 counted.
    assert prepare.prepare(**args, destination=tmp_path/'next').exists()


def test_worker_stalls_beyond_the_allowance_still_refuse(metadata_ancestry, tmp_path, monkeypatch):
    global POLICY
    monkeypatch.setitem(POLICY, 'stall_allowance_usd', '0.05')
    monkeypatch.setitem(POLICY['authorization'], 'authorized_stall_allowance_usd', '0.05')
    args = build(metadata_ancestry, tmp_path, monkeypatch, with_stalls=True, allowance='0.05')
    with pytest.raises(BudgetStop, match='cumulative reservation ceiling'):
        prepare.prepare(**args, destination=tmp_path/'next')
