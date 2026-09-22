"""Synthetic batch histories and shared budgets; no provider contact."""
import copy
from contextlib import contextmanager, nullcontext
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shlex
import sys
import threading
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop, Ledger, CappedMessages, attempt_identity
from data_sheets_schema import audit_batches
from native_control import CONTRACT, INIT_ID, initialize_frame, digest
from native_file_policy import FileAccess
from . import batch_output as output, batch_native as runtime, native
from .batch_history import BatchHistory
from .test_staged_native import Session


@pytest.fixture
def batch(tmp_path):
    condition = tmp_path / 'condition'; condition.mkdir()
    attempt = condition / 'attempts' / 'SYNTHETIC'; attempt.mkdir(parents=True)
    target = attempt / 'output'; target.mkdir()
    original = condition / 'original.yaml'; original.write_text('description: Alpha.\nnotes: Beta.\n')
    common = condition / 'common.yaml'; common.write_text('id: https://example.org/common\nname: common\nclasses:\n  Dataset:\n    description: Synthetic schema authority.\n')
    schema = condition / 'schema.yaml'; schema.write_text('id: https://example.org/schema\nname: schema\nimports:\n  - common\n')
    p = audit_batches.make_plan(original.read_text(), max_paths=1)
    pp = condition / 'batch-plan.json'; pp.write_bytes(audit_batches.canonical_bytes(p))
    registration = condition / 'registration.json'
    parent = condition / 'generation.json'
    parent.write_text(json.dumps({'budget':{'ledger_path':str(condition/'generation-billing.json')},
        'generation':{'jobs':[{'id':'SOURCE','project':'EXAMPLE'}]}}))
    m = {'schema_version':1, 'kind': 'd4d_native_audit_continuation', 'protocol_version': 7, 'render_version': 20,
         'scientific_contract_transition': {'kind':'frozen_pair_integrated_batches_v1'},
         'parent':{'registration':str(parent),'job_id':'SOURCE'},
         'python': sys.executable, 'repository': str(tmp_path), 'profile':'neutral', 'model': {'model': 'claude-opus-5'},
         'native_runtime': {'version': '2.1.272 (Claude Code)', 'context_window': 200000, 'max_output_tokens': 64000},
         'inputs': {'original_full': str(original), 'original_core': str(original), 'full_schema':str(schema),'core_schema':str(schema)},
         'pinned_files': {str(p):native.sha(p) for p in (original,pp,common,schema)},
         'budget': {'per_job_attempt_usd': {'SYNTHETIC': '40'}, 'ledger_path': str(condition / 'billing.json')},
         'job': {'id': 'SYNTHETIC', 'attempt_dir': str(attempt), 'output_dir': str(target),
                 'audit_path': str(target / 'audit.json'), 'deadline_seconds': 21600,
                 'validator_argv': [sys.executable, '-m', 'audit_controls.contract', '--registration', str(registration)]}}
    m['audit_batches'] = output.specification(m, registration, worker_total_cap_usd='24')
    for r in m['audit_batches']['children']:
        Path(r['system_prompt']).parent.mkdir(parents=True)
        Path(r['system_prompt']).write_text('Synthetic persistent system.\n')
        if r['kind'] == 'worker': Path(r['instruction']).write_text('Synthetic complete child instruction.\n')
    Path(m['audit_batches']['integration_base']).write_text('Synthetic integration base.\n')
    registration.write_text(json.dumps(m))
    identity = native.sha(registration)
    owner = attempt_identity(identity, m['job']['id'])
    ledger = Ledger(m['budget']['ledger_path'], manifest_sha256=identity, total_cap=400, attempt_cap=40,
                    attempt_caps_usd={owner:40})
    ledger.require_resolved(owner)
    return SimpleNamespace(m=m, reg=registration, identity=identity, owner=owner, ledger=ledger, plan=p, attempt=attempt)


def proposal(batch, child_id):
    worker = next(w for w in batch.plan['workers'] if w['id'] == child_id)
    values = [r for r in batch.plan['inventory']['values'] if r['path'] in worker['paths']]
    rows = [{'path': r['path'], 'claims': [{'text': r['text'], 'verdict':'supported',
        'attributed_to':['protocol.txt'], 'claim_status':'fact', 'source_status':'fact',
        'reason':'Synthetic complete evidence.',
        'evidence':[{'source':'protocol.txt','chunk':'c001','quote':r['text']}]}]} for r in values]
    return {'findings':[], 'summary':'No synthetic findings.', 'source_review': {
        'artifact':'original_full','sha256':batch.plan['original_full_sha256'],'values':rows}}


class BatchSession(Session):
    def __init__(self, batch, child_id, *, existing=False, history=None):
        self.batch, self.child_id = batch, child_id
        self.row = output.child(batch.m, child_id)
        root = Path(self.row['attempt_dir']); root.mkdir(parents=True, exist_ok=True)
        if not existing:
            Path(self.row['output_dir']).mkdir()
            (root / 'cli_config').mkdir()
            for r in self.row['rounds']: Path(r['parts'][0]).parent.mkdir(parents=True)
        policy = runtime.build_policy(batch.m, batch.reg, child_id)
        self.c = SimpleNamespace(m=batch.m, identity=batch.identity, policy=policy, attempt=root)
        self.history = history or BatchHistory(batch.m, batch.identity, policy, child_id)
        self.events, self.records, self.count = [], [], 0
        self.records.append({'kind':'initialize_sent','frame':initialize_frame(),'policy_sha256':digest(policy)})
        ack = {'type':'control_response','response':{'subtype':'success','request_id':INIT_ID,'response':{}}}
        self.records.append({'kind':'initialize_ack','frame':ack}); self.emit(ack)
        self.emit({'type':'system','subtype':'init','session_id':'11111111-2222-4333-8444-555555555555',
            'cwd':batch.m['repository'],'model':'claude-opus-5','apiKeySource':'ANTHROPIC_API_KEY',
            'claude_code_version':'2.1.272','tools':['Read','Write','Bash']})

    def write(self, text):
        path = Path(self.row['rounds'][self.history.round-1]['parts'][len(self.history.part_writes)])
        identity = self.call('Write', {'file_path':str(path),'content':text})
        path.write_bytes(text.encode())
        self.result(identity, {'type':'create','filePath':str(path),'content':text})

    def check(self):
        number = self.history.round
        identity = self.call('Bash', {'command':shlex.join(self.row['rounds'][number-1]['check_argv'])})
        receipt = output.check_round(self.batch.m,self.batch.identity,self.child_id,number)
        self.result(identity, {'stdout':json.dumps(output.check_summary(self.batch.m,receipt)),
            'stderr':'','interrupted':False,'exitCode':0})
        return receipt

    def seal(self):
        identity = self.call('Bash', {'command':shlex.join(self.row['seal_argv'])})
        receipt = output.seal(self.batch.m,self.batch.identity,self.child_id)
        self.result(identity, {'stdout':json.dumps(output.seal_summary(self.batch.m,receipt)),
            'stderr':'','interrupted':False,'exitCode':0})

    def finish(self):
        self.emit({'type':'result','is_error':False,'terminal_reason':'completed','stop_reason':'end_turn',
            'permission_denials':[],'modelUsage':{'claude-opus-5':{'contextWindow':200000,'maxOutputTokens':64000}}})
        root = self.c.attempt
        (root/'control.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.records))
        (root/'transcript.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.events))
        return runtime._inspect(self.batch.m,self.batch.identity,self.row,self.c.policy)


@pytest.mark.parametrize('repair', [False,True])
def test_worker_two_sourceblind_drafts_and_unmocked_typed_replay(batch,repair):
    name = batch.plan['workers'][0]['id']
    session = BatchSession(batch,name)
    if repair:
        session.write('{')
        assert not session.check()['grammar']['passed']
    text = json.dumps(proposal(batch,name))
    session.write(text[:20]);session.write(text[20:])
    assert session.check()['grammar']['passed']
    session.seal()
    result = session.finish()
    assert result['batch_child']['child_id'] == name
    assert len(result['batch_child']['drafts']) == 1+repair
    assert 'validator' not in result['batch_child']
    assert not (batch.attempt/'validation.json').exists()
    assert output.verify_seal(batch.m,batch.identity,name)['proposal']['sha256'] == hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize('kind',['second_after_pass','early_seal','other_worker','early_round2','rewrite_part','after_seal'])
def test_illegal_worker_operation_cannot_advance_history(batch,kind):
    name = batch.plan['workers'][0]['id'];s=BatchSession(batch,name)
    if kind=='early_seal': argv=s.row['seal_argv']
    elif kind=='early_round2': argv=s.row['rounds'][1]['check_argv']
    elif kind=='other_worker':
        other=output.child(batch.m,batch.plan['workers'][1]['id'])
        with pytest.raises(BudgetStop):s.call('Write',{'file_path':other['rounds'][0]['parts'][0],'content':'x'})
        return
    else:
        s.write(json.dumps(proposal(batch,name)))
        if kind=='rewrite_part':
            with pytest.raises(BudgetStop):s.call('Write',{'file_path':s.row['rounds'][0]['parts'][0],'content':'x'})
            return
        s.check()
        if kind=='after_seal':s.seal()
        argv=s.row['rounds'][1]['check_argv']
    with pytest.raises(BudgetStop):s.call('Bash',{'command':shlex.join(argv)})


@pytest.mark.parametrize('damage',['part','snapshot','receipt','witness','extra_hidden'])
def test_sealed_proposal_tampering_refused(batch,damage):
    name=batch.plan['workers'][0]['id'];s=BatchSession(batch,name)
    s.write(json.dumps(proposal(batch,name)));s.check();s.seal()
    if damage=='part':Path(s.row['rounds'][0]['parts'][0]).write_text('tamper')
    elif damage=='snapshot':output.draft_path(batch.m,name,1).write_text('tamper')
    elif damage=='receipt':output.seal_paths(batch.m,name)[0].write_text('{}')
    elif damage=='witness':output.seal_paths(batch.m,name)[1].unlink()
    else:(Path(s.row['rounds'][0]['parts'][0]).parent/'.ignored').write_text('tamper')
    with pytest.raises((BudgetStop,FileNotFoundError)):output.verify_seal(batch.m,batch.identity,name)


def settle(ledger,owner,cost,*,stage=None):
    ticket=ledger.reserve(owner,Decimal(cost),'a'*64,**({'stage_cap':stage} if stage is not None else {}))
    ledger.settle(ticket,Decimal(cost),response_sha256='b'*64,usage={})
    return ticket


def test_worker_ceiling_atomic_and_canonical_cap_preserved_across_clients(batch):
    settle(batch.ledger,batch.owner,'10',stage='24')
    settle(batch.ledger,batch.owner,'14',stage='24')
    rows=json.loads(batch.ledger.path.read_text())['requests']
    assert {r['attempt_cap_usd'] for r in rows}=={'40'}
    assert {r['stage_cap_usd'] for r in rows}=={'24'}
    # Integration shares the same attempt but is admitted under its remaining parent cap.
    settle(batch.ledger,batch.owner,'16')
    assert sum(Decimal(r['cost_usd']) for r in json.loads(batch.ledger.path.read_text())['requests'])==40
    with pytest.raises(BudgetStop):batch.ledger.reserve(batch.owner,Decimal('.01'),'c'*64)


def test_pure_layout_cache_never_shares_mutable_selector_or_caches_plan_evidence(batch):
    expected=copy.deepcopy(batch.m['audit_batches'])
    first=output.specification(batch.m,batch.reg,worker_total_cap_usd='24')
    first['children'][0]['rounds'][0]['parts'][0]='tampered caller value'
    assert output.specification(batch.m,batch.reg,worker_total_cap_usd='24')==expected
    output.configuration(batch.m)
    path=Path(batch.m['audit_batches']['plan_path']);before=path.read_bytes()
    changed=json.loads(before);changed['workers'][0]['id']='worker_9999'
    path.write_text(json.dumps(changed))
    with pytest.raises((BudgetStop,ValueError)):output.configuration(batch.m)
    path.write_bytes(before)
    original=Path(batch.m['inputs']['original_full']);original.write_text('description: Changed original.\n')
    with pytest.raises((BudgetStop,ValueError)):output.configuration(batch.m)


def test_layout_cache_rechecks_all_manifest_paths_and_stage_ceiling(batch):
    output.configuration(batch.m)
    for field in ('python','worker_total_cap_usd','part'):
        changed=copy.deepcopy(batch.m)
        if field=='python':changed['python']='/another/python'
        elif field=='worker_total_cap_usd':changed['audit_batches']['worker_total_cap_usd']='24.0'
        else:changed['audit_batches']['children'][0]['rounds'][0]['parts'][0]+='.changed'
        if field=='worker_total_cap_usd':
            # Equivalent numeric ceilings remain distinct explicit strings,
            # but the exact layout must be rebuilt with the selected string.
            assert output.configuration(changed)['worker_total_cap_usd']=='24.0'
        else:
            with pytest.raises(BudgetStop):output.configuration(changed)


def test_worker_ceiling_denial_stops_whole_attempt_before_integration(batch):
    settle(batch.ledger,batch.owner,'23',stage='24')
    with pytest.raises(BudgetStop):batch.ledger.reserve(batch.owner,Decimal('2'),'c'*64,stage_cap='24')
    with pytest.raises(BudgetStop,match='previously stopped'):batch.ledger.reserve(batch.owner,Decimal('1'),'d'*64)
    assert len(json.loads(batch.ledger.path.read_text())['requests'])==1


@pytest.mark.parametrize('value',[True,False,'NaN','Infinity','0','-1','41',[],{}])
def test_stage_cap_invalid_values_never_create_a_paid_row(batch,value):
    with pytest.raises(BudgetStop):batch.ledger.reserve(batch.owner,Decimal('1'),'c'*64,stage_cap=value)
    assert json.loads(batch.ledger.path.read_text())['requests']==[]


def test_stall_debit_allowance_is_shared_by_all_fresh_children(batch):
    for index in range(6):
        ticket=batch.ledger.reserve(batch.owner,Decimal('1'),'a'*64,stage_cap='24')
        assert batch.ledger.debit_unconfirmed(ticket,maximum=6,evidence={'synthetic':True})==index+1
    ticket=batch.ledger.reserve(batch.owner,Decimal('1'),'b'*64)
    with pytest.raises(BudgetStop,match='allowance is exhausted'):
        batch.ledger.debit_unconfirmed(ticket,maximum=6,evidence={'synthetic':True})
    rows=json.loads(batch.ledger.path.read_text())['requests']
    assert rows[-1]['status']=='pending' and sum(r['status']=='settled' for r in rows)==6
    with pytest.raises(BudgetStop):batch.ledger.require_resolved(batch.owner)


def test_same_deadline_passed_to_all_children_and_stop_prevents_next(batch,monkeypatch):
    clock=[100.0];calls=[]
    clock_fn=lambda:clock[0]
    context=SimpleNamespace(manifest=batch.m,manifest_sha256=batch.identity,job=batch.m['job'],
        registration_path=batch.reg,ledger=batch.ledger,verify=lambda:None)
    def fake(c,row,deadline,**kwargs):
        calls.append((row['id'],deadline))
        clock[0]+=21601
        return {'child_id':row['id'],'closure_sha256':'x'*64}
    with pytest.raises(BudgetStop,match='deadline'):
        runtime.execute_job(context,clock=clock_fn,child_runner=fake)
    assert calls==[(batch.plan['workers'][0]['id'],21700)]
    # The same attempt's exclusive children directory prevents replay.
    with pytest.raises(FileExistsError):runtime.execute_job(context,clock=clock_fn,child_runner=fake)


@pytest.mark.parametrize('completion',[102,161])
def test_aggregate_closure_time_is_included_before_success(batch,monkeypatch,completion):
    batch.m['job']['deadline_seconds']=60;clock=[100.0]
    context=SimpleNamespace(manifest=batch.m,manifest_sha256=batch.identity,job=batch.m['job'],
        registration_path=batch.reg,ledger=batch.ledger,verify=lambda:None)
    monkeypatch.setattr(runtime,'prepare_integration',lambda *args:None)
    monkeypatch.setattr(output,'validate_output',lambda manifest:{'audit':{'sha256':'a'*64}})
    def closure(*args):clock[0]=completion
    monkeypatch.setattr(runtime,'verify_aggregate_closure',closure)
    def child(c,row,deadline,**kwargs):
        return {'child_id':row['id'],'closure_sha256':'b'*64,
            'evidence':{'batch_child':{'validation':{'passed':True}}}}
    if completion==161:
        with pytest.raises(BudgetStop,match='deadline'):
            runtime.execute_job(context,clock=lambda:clock[0],child_runner=child)
    else:
        result=runtime.execute_job(context,clock=lambda:clock[0],child_runner=child)
        assert result['evidence']['aggregate_elapsed_seconds']==2


@pytest.mark.parametrize('completion',[102,161])
def test_native_run_job_final_guard_covers_outer_verification(batch,monkeypatch,completion):
    from . import registration
    batch.m['job']['deadline_seconds']=60;batch.m['repository_commit']='synthetic'
    batch.reg.write_text(json.dumps(batch.m));batch.identity=native.sha(batch.reg)
    batch.owner=attempt_identity(batch.identity,batch.m['job']['id']);batch.ledger.path.unlink()
    batch.ledger=Ledger(batch.m['budget']['ledger_path'],manifest_sha256=batch.identity,total_cap=400,
        attempt_cap=40,attempt_caps_usd={batch.owner:40});batch.ledger.require_resolved(batch.owner)
    Path(batch.m['job']['output_dir']).rmdir();batch.attempt.rmdir()
    review=batch.reg.parent/'launch-review.json';review.write_text(json.dumps({
        'verdict':'approve','registration_sha256':batch.identity,'ci_conclusion':'success',
        'repository_commit':'synthetic','allowed_jobs':[batch.m['job']['id']]}))
    clock=[100.0];finished=[False]
    monkeypatch.setattr(native.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(registration,'validate_registration',lambda p:batch.m)
    def verify(*args):
        if finished[0]:clock[0]=completion
    monkeypatch.setattr(registration,'verify',verify)
    monkeypatch.setattr(registration,'sequence_guard',lambda *args:nullcontext())
    monkeypatch.setattr(registration,'open_audit_ledger',lambda *args:batch.ledger)
    monkeypatch.setattr(native,'build_policy',lambda *args:{})
    monkeypatch.setattr(native,'verify_runtime',lambda *args:Path('/synthetic/claude'))
    def adapter(context):
        row=batch.m['audit_batches']['children'][0];root=Path(row['attempt_dir']);root.mkdir(parents=True)
        closed={'exit_code':0,'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0}
        (root/'closed.json').write_text(json.dumps({'child_id':row['id'],'status':'completed_proposal',
            'registration_sha256':batch.identity,'runtime':closed}))
        Path(batch.m['job']['audit_path']).write_text('{}')
        finished[0]=True
        return {'validation':{'passed':True},'runtime':closed,'evidence':{'aggregate_elapsed_seconds':0}}
    if completion==161:
        with pytest.raises(BudgetStop,match='deadline'):native.run_job(batch.reg,review,adapter=adapter)
        result=json.loads((batch.attempt/'result.json').read_text())
        assert result['status']=='stopped' and result['stop_source']=='batch_deadline'
        assert len(result['batch_runtime_children'])==1
        assert result['runtime']['proxy_shutdown_complete'] is True
        assert result['runtime']['unfinished_handlers']==0
    else:
        result=native.run_job(batch.reg,review,adapter=adapter)
        assert result['status']=='completed_pending_independent_review'
        assert result['evidence']['aggregate_elapsed_seconds']==2


def test_proxy_rechecks_global_deadline_under_admission_lock():
    value=SimpleNamespace(deadline_guard=lambda:(_ for _ in ()).throw(BudgetStop('deadline')))
    with pytest.raises(BudgetStop,match='deadline'):runtime.BatchProxy.require_open(value)


@pytest.mark.parametrize('damage',[None,'omitted','unfinished','unknown_child','changed_receipt'])
def test_stopped_aggregate_requires_every_child_closed_and_bound(batch,damage):
    for child in batch.m['audit_batches']['children'][:2]:
        root=Path(child['attempt_dir']);root.mkdir(parents=True)
        (root/'stopped.json').write_text(json.dumps({'child_id':child['id'],
            'registration_sha256':batch.identity,'status':'stopped','runtime':{
                'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0}}))
    snapshots,aggregate=runtime.stopped_runtime_snapshot(batch.m)
    result={'batch_runtime_children':snapshots,'runtime':aggregate}
    if damage is None:
        assert len(runtime.require_closed_batch_runtime(batch.m,result))==2
        return
    if damage=='omitted':result['batch_runtime_children'].pop()
    elif damage=='unknown_child':(batch.attempt/'children'/'unregistered').mkdir()
    else:
        path=Path(snapshots[0]['receipt']['path']);receipt=json.loads(path.read_text())
        if damage=='unfinished':receipt['runtime']['unfinished_handlers']=1
        else:receipt['error_type']='Changed after result'
        path.write_text(json.dumps(receipt))
        if damage=='unfinished':
            result['batch_runtime_children'],result['runtime']=runtime.stopped_runtime_snapshot(batch.m)
    with pytest.raises(BudgetStop):runtime.require_closed_batch_runtime(batch.m,result)


@pytest.mark.parametrize('bad',[{'proxy_shutdown_complete':True,'unfinished_handlers':0},
    {'proxy_initialized':False,'proxy_shutdown_complete':True,'unfinished_handlers':0},
    {'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':False}])
def test_stopped_child_cannot_claim_closure_with_missing_or_contradictory_runtime(batch,bad):
    child=batch.m['audit_batches']['children'][0]
    root=Path(child['attempt_dir']);root.mkdir(parents=True)
    (root/'stopped.json').write_text(json.dumps({'child_id':child['id'],
        'registration_sha256':batch.identity,'status':'stopped','runtime':bad}))
    with pytest.raises(BudgetStop):runtime.stopped_runtime_snapshot(batch.m)


def test_child_reads_exact_pinned_schema_imports_and_selected_vocabulary(batch,monkeypatch):
    from data_sheets_schema import profiles
    vocabulary=batch.reg.parent/'vocabulary.json';vocabulary.write_text('{"terms":[]}')
    foreign=batch.reg.parent/'foreign.yaml';foreign.write_text('name: unrelated\n')
    selected=replace(profiles.NEUTRAL,name='synthetic',vocabulary_pin=vocabulary)
    monkeypatch.setitem(profiles.PROFILES,'synthetic',selected)
    batch.m['profile']='synthetic';batch.m['pinned_files'][str(vocabulary)]=native.sha(vocabulary)
    policy=runtime.build_policy(batch.m,batch.reg,batch.plan['workers'][0]['id'])
    access=FileAccess(policy)
    for path in (batch.reg.parent/'common.yaml',vocabulary):
        assert access.classify('Read',{'file_path':str(path)})[0]=='prescribed'
    assert access.classify('Read',{'file_path':str(foreign)})[0]=='not_prescribed'
    vocabulary.write_text('{"changed":true}')
    with pytest.raises(BudgetStop,match='registered input'):
        runtime.build_policy(batch.m,batch.reg,batch.plan['workers'][0]['id'])


def test_count_completing_after_deadline_cannot_reserve_paid_request(batch):
    clock=[0]
    class Counter:
        default_headers={}
        @property
        def messages(self):return self
        def count_tokens(self,**kwargs):
            clock[0]=101
            return SimpleNamespace(input_tokens=1)
    def guard():
        if clock[0]>=100:raise BudgetStop('deadline')
    proxy=runtime.BatchProxy(deadline_guard=guard,audit_history=SimpleNamespace(verify_admission=lambda:None),
        sdk=Counter(),ledger=batch.ledger,attempt=batch.owner,evidence=batch.attempt/'count-fixture',
        model='claude-opus-5',prices={'input':'0.000005','output':'0.000025','cache_write':'0.00000625','cache_read':'0.0000005'},
        verify=guard,provider_key='synthetic',base_url='https://api.cborg.lbl.gov',
        upstream=SimpleNamespace(close=lambda:None),stage_cap='24')
    with pytest.raises(BudgetStop,match='deadline'):
        proxy.messages.prepare({'model':'claude-opus-5','max_tokens':1000,'messages':[{'role':'user','content':'Synthetic'}]})
    assert runtime._own_rows(batch.m,batch.identity)==[]


def test_stage_ceiling_reaches_capped_admission_after_count(batch):
    counter=SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw:SimpleNamespace(input_tokens=1)))
    capped=CappedMessages(counter,ledger=batch.ledger,attempt=batch.owner,evidence=batch.attempt/'counter-fixture',
        model='claude-opus-5',prices={'input':'1','output':'1','cache_write':'1','cache_read':'1'},
        verify=lambda:None,stage_cap='24')
    with pytest.raises(BudgetStop,match='budget'):
        capped.prepare({'model':'claude-opus-5','max_tokens':1,'messages':[{'role':'user','content':'Synthetic'}]})
    assert runtime._own_rows(batch.m,batch.identity)==[]


def close_session(session):
    batch=session.batch;row=session.row;root=session.c.attempt
    evidence=session.finish()
    selected=synthetic_request(session)
    receipt={'schema_version':1,'job_id':batch.m['job']['id'],'registration_sha256':batch.identity,
        'billing_attempt':batch.owner,'child_id':row['id'],'status':'completed_proposal',
        'runtime':{'exit_code':0,'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0},
        'policy_sha256':runtime._digest(session.c.policy),'request_rows':selected,
        'initial_context':native.verify_initial_context(SimpleNamespace(attempt=root,job=row),selected),
        'evidence':evidence,'frozen_evidence':runtime._tree(root)}
    (root/'closed.json').write_text(json.dumps(receipt))
    return runtime.verify_child_closure(batch.m,batch.identity,row['id'])


def synthetic_request(session):
    batch=session.batch;row=session.row;root=session.c.attempt
    request={'model':'claude-opus-5','system':Path(row['system_prompt']).read_text(),
        'messages':[{'role':'user','content':Path(row['instruction']).read_text()}]}
    raw=json.dumps(request).encode()
    ticket=batch.ledger.reserve(batch.owner,Decimal('1'),hashlib.sha256(raw).hexdigest(),
        **({'stage_cap':'24'} if row['kind']=='worker' else {}))
    folder=root/'requests'/ticket;folder.mkdir(parents=True)
    (folder/'request.json').write_bytes(raw);(folder/'native_request.json').write_bytes(raw)
    response=b'{"synthetic_accounting_only":true}\n';(folder/'response.json').write_bytes(response)
    batch.ledger.settle(ticket,Decimal('1'),response_sha256=hashlib.sha256(response).hexdigest(),usage={})
    selected=[r for r in runtime._own_rows(batch.m,batch.identity) if r['id']==ticket]
    return selected


def test_real_child_controller_creates_fresh_closed_clients_and_canonical_owner(batch,monkeypatch):
    # Only the external process and network are replaced. Registered paths,
    # typed history, immutable helpers, ledger and closure replay are real.
    batch.m['provider_base_url']='https://api.cborg.lbl.gov'
    batch.m['budget']['prices_per_token']={'input':'1','output':'1','cache_write':'1','cache_read':'1'}
    batch.reg.write_text(json.dumps(batch.m));batch.identity=native.sha(batch.reg)
    batch.owner=attempt_identity(batch.identity,batch.m['job']['id'])
    batch.ledger.path.unlink()
    batch.ledger=Ledger(batch.m['budget']['ledger_path'],manifest_sha256=batch.identity,total_cap=400,
        attempt_cap=40,attempt_caps_usd={batch.owner:40});batch.ledger.require_resolved(batch.owner)
    clients=[];proxies=[];calls=[]
    class Client:
        closed=False
        def close(self):self.closed=True
    def providers(manifest,key):
        pair=(Client(),Client());clients.extend(pair);return pair
    class Proxy:
        def __init__(self,**kwargs):
            self.kw=kwargs;self.token='synthetic';self.failed=threading.Event()
            self.frozen=False;self.unfinished_handlers=None;proxies.append(self)
        @contextmanager
        def running(self):
            try:yield 'http://synthetic.invalid'
            finally:
                self.kw['sdk'].close();self.kw['upstream'].close()
                self.frozen=True;self.unfinished_handlers=0
    monkeypatch.setenv('CBORG_API_KEY','synthetic')
    monkeypatch.setattr(runtime,'provider_clients',providers)
    monkeypatch.setattr(runtime,'BatchProxy',Proxy)
    monkeypatch.setattr(native,'verify_runtime',lambda m:Path('/synthetic/claude'))
    def execute(argv,**kwargs):
        row=next(r for r in batch.m['audit_batches']['children'] if Path(r['attempt_dir'])==kwargs['attempt'])
        s=BatchSession(batch,row['id'],existing=True,history=kwargs['event_observer'].__self__)
        kwargs['verify_launch']();calls.append((row['id'],argv,kwargs))
        synthetic_request(s)
        s.write(json.dumps(proposal(batch,row['id'])));s.check();s.seal();s.finish()
        return 0
    monkeypatch.setattr(native,'execute_child',execute)
    context=SimpleNamespace(manifest=batch.m,manifest_sha256=batch.identity,job=batch.m['job'],
        registration_path=batch.reg,ledger=batch.ledger,verify=lambda:None)
    clock=[0]
    for row in batch.m['audit_batches']['children'][:-1]:
        receipt=runtime._execute_child(context,row,21600,clock=lambda:clock[0])
        assert receipt['runtime']['proxy_shutdown_complete'] is True
        clock[0]+=5
    assert len(proxies)==2 and len({id(c) for c in clients})==4 and all(c.closed for c in clients)
    assert {p.kw['attempt'] for p in proxies}=={batch.owner}
    assert all(p.kw['ledger'] is batch.ledger and p.kw['stage_cap']=='24' for p in proxies)
    assert [c[2]['deadline_seconds'] for c in calls]==[21600,21595]
    assert [c[1][c[1].index('--max-budget-usd')+1] for c in calls]==['24','23']
    assert len({c[2]['env']['CLAUDE_CONFIG_DIR'] for c in calls})==2
    assert sum(Decimal(r['cost_usd']) for r in runtime._own_rows(batch.m,batch.identity))==2


def read_rows(session, *, omit=None, damaged=False):
    for path,description in session.c.policy['batch_row_views'].items():
        if path==omit:continue
        lines=Path(path).read_text().split('\n')
        call=session.call('Read',{'file_path':path,'offset':1,'limit':len(lines)})
        numbered='\n'.join(f'{i}\t{line}' for i,line in enumerate(lines,1))
        session.emit({'type':'user','tool_use_result':{'type':'text','file':{'filePath':path,
            'content':'\n'.join(lines),'startLine':1,'numLines':len(lines),'totalLines':len(lines)}},
            'message':{'role':'user','content':[{'type':'tool_result','tool_use_id':call,'is_error':False,
                'content':'truncated' if damaged else numbered}]}})


@pytest.fixture
def assembled_batch(batch,monkeypatch):
    # Context rendering has its own schema/source fixture suite. This fixture
    # isolates controller provenance with an exact deterministic synthetic prompt.
    from . import batch_registration
    from data_sheets_schema import audit_batch_context
    monkeypatch.setattr(batch_registration,'scientific_arguments',lambda manifest:{})
    monkeypatch.setattr(audit_batch_context,'render_integration_context',
        lambda **kw:'Synthetic integrator '+audit_batches.object_sha256(kw['worker_index']))
    closed=[]
    for worker in batch.plan['workers']:
        s=BatchSession(batch,worker['id']);s.write(json.dumps(proposal(batch,worker['id'])));s.check();s.seal()
        closed.append(close_session(s))
    runtime.prepare_integration(batch.m,batch.identity)
    session=BatchSession(batch,'integration')
    index=audit_batches.build_index(batch.plan,output.proposals(batch.m))
    integration={'kind':'audit_integration_v1','proposal_index_sha256':index['sha256'],
        'retain_other_rows_from_index_sha256':index['sha256'],'row_replacements':[],
        'finding_decisions':[],'new_findings':[],'summary':'All synthetic rows retained after review.'}
    return SimpleNamespace(batch=batch,session=session,integration=integration,closed=closed)


def finish_integrator(case):
    b,s=case.batch,case.session
    read_rows(s);s.write(json.dumps(case.integration));assert s.check()['grammar']['passed'];s.seal()
    call=s.call('Bash',{'command':shlex.join(b.m['audit_batches']['assemble_argv'])})
    assembly=output.assemble_output(b.m,b.identity)
    s.result(call,{'stdout':json.dumps(output.assembly_summary(b.m,assembly)),
        'stderr':'','interrupted':False,'exitCode':0})
    call=s.call('Bash',{'command':shlex.join(b.m['job']['validator_argv'])})
    # Typed once-only receipt fixture, not a source validator invocation.
    report={'schema_version':1,'job_id':b.m['job']['id'],'registration_sha256':b.identity,
        'checked':True,'passed':True,'findings':[],'errors':[],'audit_sha256':native.sha(b.m['job']['audit_path'])}
    with (b.attempt/'validation.json').open('x') as f:json.dump(report,f)
    s.result(call,{'stdout':json.dumps(report),'stderr':'','interrupted':False,'exitCode':0})
    closed=case.closed+[close_session(s)]
    result={'registration_sha256':b.identity,'job_id':b.m['job']['id'],
        'audit_sha256':report['audit_sha256'],'validation':report,
        'evidence':{'batch_children':[{'id':r['child_id'],'closure_sha256':r['closure_sha256']} for r in closed],
                    'assembly':assembly,'aggregate_elapsed_seconds':120},
        'runtime':{'exit_code':0,'proxy_initialized':True,'proxy_shutdown_complete':True,'unfinished_handlers':0,'children_closed':len(closed)}}
    return result


@pytest.fixture
def accepted_batch(assembled_batch):
    case=assembled_batch
    case.result=finish_integrator(case)
    return case


def test_complete_real_typed_all_child_closure_and_deterministic_assembly(accepted_batch):
    b=accepted_batch.batch
    paths=runtime.verify_aggregate_closure(b.m,b.reg,accepted_batch.result)
    assert Path(b.m['job']['audit_path']) in paths
    assert len([p for p in paths if p.name=='closed.json'])==3
    final=json.loads(Path(b.m['job']['audit_path']).read_text())
    assert len(final['source_review']['values'])==2
    assert {r['attempt'] for r in runtime._own_rows(b.m,b.identity)}=={b.owner}


def test_aggregate_closure_rejects_mutation_omission_or_mixed_identity(accepted_batch):
    case=accepted_batch;b=case.batch
    expected=runtime.verify_aggregate_closure(b.m,b.reg,case.result)
    condition=b.reg.parent
    before_tree=runtime._tree(condition)
    def file_identity(path):
        info=path.stat()
        return info.st_dev,info.st_ino,info.st_nlink
    before_inodes={relative:file_identity(condition/relative) for relative in before_tree['files']}
    # Keep the ledger explicit even if a future fixture stores it outside the
    # condition. Restore bytes in place: copying a fixture would lose witness
    # hardlinks and create new evidence identities.
    ledger_bytes=b.ledger.path.read_bytes();ledger_inode=file_identity(b.ledger.path)
    original_result=copy.deepcopy(case.result)
    first=b.m['audit_batches']['children'][0]
    request=next((Path(first['attempt_dir'])/'requests').iterdir())/'request.json'
    files={'part_changed':Path(first['rounds'][0]['parts'][0]),'request_changed':request,
        'row_changed':next((case.session.c.attempt/'rows').iterdir()),
        'unresolved':b.ledger.path,'ledger_extra':b.ledger.path}
    for damage in ('missing_child','reordered_child','part_changed','request_changed','row_changed',
                   'unresolved','extra_child','ledger_extra','elapsed'):
        result=copy.deepcopy(original_result)
        target=files.get(damage);before=target.read_bytes() if target is not None else None
        extra=b.attempt/'children'/'unregistered';created=False
        try:
            if damage=='missing_child':result['evidence']['batch_children'].pop(0)
            elif damage=='reordered_child':result['evidence']['batch_children'].reverse()
            elif damage in ('part_changed','request_changed','row_changed'):target.write_text('changed')
            elif damage=='extra_child':extra.mkdir();created=True
            elif damage=='elapsed':result['evidence']['aggregate_elapsed_seconds']=21601
            else:
                ledger=json.loads(ledger_bytes)
                if damage=='unresolved':ledger['requests'][0]['status']='pending'
                else:ledger['requests'].append({**ledger['requests'][0],'id':'f'*32})
                target.write_text(json.dumps(ledger))
            with pytest.raises((BudgetStop,ValueError)):
                runtime.verify_aggregate_closure(b.m,b.reg,result)
        finally:
            if target is not None:target.write_bytes(before)
            if created:extra.rmdir()
            assert runtime._tree(condition)==before_tree,damage
            assert {relative:file_identity(condition/relative) for relative in before_inodes}==before_inodes,damage
            assert b.ledger.path.read_bytes()==ledger_bytes,damage
            assert file_identity(b.ledger.path)==ledger_inode,damage
            assert case.result==original_result,damage
    assert runtime.verify_aggregate_closure(b.m,b.reg,case.result)==expected


@pytest.mark.parametrize('damage',['unread_retained','truncated_read','failed_validator'])
def test_integrator_reads_all_retained_rows_and_stops_on_failed_validator(assembled_batch,damage):
    case=assembled_batch;b=case.batch;s=case.session
    if damage=='truncated_read':
        with pytest.raises(BudgetStop,match='Read'):read_rows(s,damaged=True)
        return
    if damage=='unread_retained':
        omit=next(iter(s.c.policy['batch_row_views']));read_rows(s,omit=omit)
        s.write(json.dumps(case.integration));s.check()
        with pytest.raises(BudgetStop,match='every prior worker row'):s.seal()
        return
    read_rows(s);s.write(json.dumps(case.integration));s.check();s.seal()
    call=s.call('Bash',{'command':shlex.join(b.m['audit_batches']['assemble_argv'])})
    assembly=output.assemble_output(b.m,b.identity)
    s.result(call,{'stdout':json.dumps(output.assembly_summary(b.m,assembly)),'stderr':'','interrupted':False})
    call=s.call('Bash',{'command':shlex.join(b.m['job']['validator_argv'])})
    with pytest.raises(BudgetStop,match='successful typed result'):
        s.result(call,{'stdout':'{}','stderr':'','interrupted':False},is_error=True)
    with pytest.raises(BudgetStop):s.history.verify_admission()
