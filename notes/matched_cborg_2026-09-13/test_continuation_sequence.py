"""Offline ownership/closure fixtures; no scientific acceptance or paid calls."""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import json
import hashlib
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from filelock import FileLock, Timeout

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import continuation_sequence as sequence
from budgeted_cborg import BudgetStop, Ledger


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sequence.canonical(value) + b'\n')
    return {'path': str(path), 'sha256': sequence.sha(path)}


def repin(manifest, reference, value):
    reference.update(save(Path(reference['path']), value))
    manifest['pinned_files'][reference['path']] = reference['sha256']


def finish_registration(manifest, registration):
    save(registration, manifest)
    return sequence.sha(registration)


def fixture(tmp_path, cost='2.1'):
    root = tmp_path.resolve()
    generation_path = root/'origin/registration.json'
    origin_ledger = root/'origin/billing.json'
    generation = {'repository': str(root/'origin'),
        'budget': {'ledger_path': str(origin_ledger), 'additional_usd': '400', 'per_attempt_usd': '5'},
        'generation': {'jobs': [{'id':'frozen'}]}}
    origin_ref = save(generation_path, generation)
    save(origin_ledger, {'historical': 'left untouched'})
    audit_path = root/'audit/registration.json'
    audit_ledger = root/'audit/billing.json'
    audit = {'kind':'d4d_native_audit_continuation', 'parent':{'registration':str(generation_path)},
        'budget':{'ledger_path':str(audit_ledger)}, 'job':{'id':'audit','audit_path':str(root/'audit/audit.json')}}
    audit_ref = save(audit_path, audit)
    ledger = Ledger(audit_ledger, manifest_sha256=audit_ref['sha256'], total_cap='400', attempt_cap='5')
    remaining,index=Decimal(cost),0
    while remaining:
        amount=min(remaining,Decimal(5));index+=1
        ticket = ledger.reserve(audit_ref['sha256']+f':previous{index}', amount, 'earlier-request')
        ledger.settle(ticket, amount, response_sha256='earlier-response', usage={'observed':'retained'})
        remaining-=amount
    artifact = save(root/'audit/audit.json', {'synthetic':'audit fixture, not scientific acceptance'})
    result = {'scope':'phase3_audit_only','job_id':'audit','registration_sha256':audit_ref['sha256'],
        'status':'completed_pending_independent_review','unresolved_requests':[],
        'validation':{'schema_version':1,'passed':True,'checked':True,'job_id':'audit',
                      'audit_sha256':artifact['sha256'],'findings':[],'errors':[]},
        'runtime':{'exit_code':0,'proxy_shutdown_complete':True,'unfinished_handlers':0},
        'audit_path':artifact['path'], 'audit_sha256':artifact['sha256']}
    result_ref = save(root/'audit/result.json', result)
    ledger_ref = {'path':str(audit_ledger),'sha256':sequence.sha(audit_ledger)}
    acceptance = {'verdict':'accept','registration_sha256':audit_ref['sha256'],
        'result_sha256':result_ref['sha256'],'ledger_sha256':ledger_ref['sha256'],
        'artifacts':{artifact['path']:artifact['sha256']}}
    acceptance_ref = save(root/'accepted-audit.json', acceptance)
    state_path = origin_ledger.with_name('audit_sequence.json')
    state = {'schema_version':1,'registration_sha256':audit_ref['sha256'],
        'ledger_path':str(audit_ledger), 'source_registration_sha256':origin_ref['sha256']}
    save(state_path,state)
    snapshot_ref = save(root/'old-state.json',state)
    predecessor = {'stage':'audit','registration':audit_ref,'ledger':ledger_ref,'state':snapshot_ref,
        'result':result_ref,'acceptance':acceptance_ref}
    registration = root/'phase4/registration.json'
    manifest = {'kind':'synthetic_future_finalization','job':{'id':'finish'},
        'budget':{'additional_usd':'400','per_attempt_usd':'5','ledger_path':str(registration.parent/'billing.json'),
            'continuation':{'checkpoint':str(audit_ledger),'sha256':ledger_ref['sha256'],'cost_usd':cost}},
        'budget_sequence':{'protocol':sequence.PROTOCOL,'stage':'reconciliation','state_path':str(state_path),
            'origin':{'registration':origin_ref,'ledger_path':str(origin_ledger)},
            'predecessor':deepcopy(predecessor),'audit_origin':deepcopy(predecessor)},
        'pinned_files':{str(Path(sequence.__file__).resolve()):sequence.sha(sequence.__file__)}}
    for ref in (origin_ref,audit_ref,ledger_ref,result_ref,acceptance_ref,snapshot_ref,artifact):
        manifest['pinned_files'][ref['path']]=ref['sha256']
    seal_ref = save(root/'audit-closed.json',sequence.seal_document(manifest))
    manifest['budget_sequence']['seal']=seal_ref
    manifest['pinned_files'][seal_ref['path']]=seal_ref['sha256']
    finish_registration(manifest,registration)
    return manifest,registration,state_path


def enter(manifest,registration):
    return sequence.owned_sequence(manifest,registration,sequence.sha(registration))


def refresh_audit_origin(manifest):
    """Pin an internally consistent negative fixture, not a stale-file refusal."""
    predecessor=manifest['budget_sequence']['predecessor']
    acceptance=sequence.read(predecessor['acceptance']['path'])
    acceptance.update(result_sha256=predecessor['result']['sha256'],ledger_sha256=predecessor['ledger']['sha256'])
    repin(manifest,predecessor['acceptance'],acceptance)
    manifest['budget_sequence']['audit_origin']=deepcopy(predecessor)
    manifest['budget']['continuation']['sha256']=predecessor['ledger']['sha256']
    repin(manifest,manifest['budget_sequence']['seal'],sequence.seal_document(manifest))


def test_carries_actual_history_once_and_preserves_originals(tmp_path):
    m,r,state=fixture(tmp_path)
    original={name:Path(name).read_bytes() for name in m['pinned_files']}
    with enter(m,r) as owner:
        assert sequence.read(owner.ledger.path)['requests']==sequence.read(m['budget']['continuation']['checkpoint'])['requests']
        before=owner.ledger.path.read_bytes()
        with pytest.raises(Timeout):
            with FileLock(str(state)+'.lock',timeout=0):pass
        for attempt in ('unregistered',sequence.sha(r)+':unknown'):
            with pytest.raises(BudgetStop,match='unregistered'):owner.reserve(attempt,'.01','request')
    with pytest.raises(BudgetStop,match='no longer held'):owner.verify_admission()
    with enter(m,r) as reopened:
        assert reopened.ledger.path.read_bytes()==before
    assert {name:Path(name).read_bytes() for name in original}==original


def test_worker_thread_admission_shares_lock_and_expires_after_exit(tmp_path):
    m,r,_=fixture(tmp_path)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with enter(m,r) as owner:
            pool.submit(owner.verify_admission).result()
            ticket=pool.submit(owner.reserve,sequence.sha(r)+':finish','.01','request').result()
            owner.ledger.settle(ticket,'.01',response_sha256='response',usage={})
        with pytest.raises(BudgetStop,match='no longer held'):pool.submit(owner.verify_admission).result()


def test_two_children_cannot_fork_remaining_allocation(tmp_path):
    m,r,state=fixture(tmp_path,'399.98')
    sibling=deepcopy(m);sr=tmp_path/'sibling/registration.json'
    sibling['budget']['ledger_path']=str(sr.parent/'billing.json');finish_registration(sibling,sr)
    with enter(m,r) as owner:
        ticket=owner.reserve(sequence.sha(r)+':finish','.02','request')
        owner.ledger.settle(ticket,'.02',response_sha256='response',usage={})
    sealed=state.read_bytes()
    with pytest.raises(BudgetStop,match='another successor'):
        with enter(sibling,sr):pass
    assert not Path(sibling['budget']['ledger_path']).exists() and state.read_bytes()==sealed
    with enter(m,r) as owner:
        with pytest.raises(BudgetStop,match='exceeds remaining'):owner.reserve(sequence.sha(r)+':finish','.01','another')


@pytest.mark.parametrize('change',['missing_acceptance','wrong_acceptance','stopped','unknown_handlers','live_handlers','unfinished_shutdown','unresolved','pending_ledger'])
def test_no_handoff_without_exact_accepted_complete_settled_predecessor(tmp_path,change):
    m,r,state=fixture(tmp_path)
    p=m['budget_sequence']['predecessor']
    if change in {'missing_acceptance','wrong_acceptance'}:
        value=sequence.read(p['acceptance']['path'])
        if change=='missing_acceptance':value['verdict']='pending'
        else:value['registration_sha256']='other'
        repin(m,p['acceptance'],value)
    elif change=='pending_ledger':
        value=sequence.read(p['ledger']['path']);value['requests'][0]['status']='pending';repin(m,p['ledger'],value)
    else:
        value=sequence.read(p['result']['path'])
        if change=='stopped':value['status']='stopped'
        elif change=='unknown_handlers':value['runtime']['unfinished_handlers']=None
        elif change=='live_handlers':value['runtime']['unfinished_handlers']=1
        elif change=='unfinished_shutdown':value['runtime']['proxy_shutdown_complete']=False
        else:value['unresolved_requests']=['unknown']
        repin(m,p['result'],value)
    refresh_audit_origin(m);finish_registration(m,r)
    before=state.read_bytes()
    with pytest.raises(BudgetStop):
        with enter(m,r):pass
    assert state.read_bytes()==before and not Path(m['budget']['ledger_path']).exists()


@pytest.mark.parametrize('change',['manifest','cap','extra_cap','carried_row','continued_from','state','missing_state'])
def test_live_recheck_rejects_changed_owner_or_ledger(tmp_path,change):
    m,r,state=fixture(tmp_path)
    with enter(m,r) as owner:
        value=sequence.read(owner.ledger.path)
        if change=='manifest':value['manifest_sha256']='other'
        elif change=='cap':value['additional_cap_usd']='800'
        elif change=='extra_cap':value['attempt_caps_usd']={'invented':'100'}
        elif change=='carried_row':value['requests'][0]['usage']={'changed':True}
        elif change=='continued_from':value['continued_from']['requests']=0
        elif change=='missing_state':state.unlink()
        else:save(state,{'kind':'tampered'})
        if change not in {'state','missing_state'}:save(owner.ledger.path,value)
        with pytest.raises((BudgetStop,OSError)):owner.reserve(sequence.sha(r)+':finish','.01','no-spend')
        assert len(sequence.read(owner.ledger.path)['requests'])==1


@pytest.mark.parametrize('point',['before_replace','after_replace'])
def test_crash_does_not_activate_two_owners_or_adopt_orphan_ledger(tmp_path,monkeypatch,point):
    m,r,state=fixture(tmp_path)
    before=state.read_bytes();real=sequence._replace_state
    def crash(path,value):
        if point=='after_replace':real(path,value)
        raise OSError('synthetic process failure boundary')
    monkeypatch.setattr(sequence,'_replace_state',crash)
    with pytest.raises(BudgetStop):
        with enter(m,r):pytest.fail('must not admit')
    monkeypatch.setattr(sequence,'_replace_state',real)
    if point=='before_replace':
        assert state.read_bytes()==before
        with pytest.raises(BudgetStop):
            with enter(m,r):pass
    else:
        assert sequence.read(state)['active_tip']['registration_sha256']==sequence.sha(r)
        with enter(m,r) as owner:owner.verify_admission()  # status/ownership reentry, no attempt resumed
    assert len(sequence.read(m['budget']['ledger_path'])['requests'])==1


def test_durability_precedes_activation_and_lock_inode_is_preserved(tmp_path,monkeypatch):
    m,r,state=fixture(tmp_path);lockpath=Path(str(state)+'.lock')
    with FileLock(str(lockpath)):pass
    inode=lockpath.stat().st_ino;events=[]
    real_sync,real_replace=sequence._sync,sequence._replace_state
    def sync(path):events.append(('sync',str(path)));return real_sync(path)
    def replace(path,value):events.append(('replace',str(path)));return real_replace(path,value)
    monkeypatch.setattr(sequence,'_sync',sync);monkeypatch.setattr(sequence,'_replace_state',replace)
    with enter(m,r):pass
    assert events.index(('sync',m['budget']['ledger_path']))<events.index(('replace',str(state)))
    assert events[-1]==('sync',str(state.parent)) and lockpath.stat().st_ino==inode


def evaluation_successor(manifest,registration,state_path):
    root=registration.parent.parent
    full=save(root/'final/full.json',{'synthetic':'full'})
    core=save(root/'final/core.json',{'synthetic':'core'})
    artifacts={item['path']:item['sha256'] for item in (full,core)}
    result=save(root/'phase4/result.json',{'scope':'phase4_reconciliation','job_id':'finish',
        'registration_sha256':sequence.sha(registration),'status':'completed_pending_independent_review',
        'unresolved_requests':[],'validation':{'passed':True},'artifacts':artifacts,
        'runtime':{'proxy_shutdown_complete':True,'unfinished_handlers':0}})
    ledger={'path':manifest['budget']['ledger_path'],'sha256':sequence.sha(manifest['budget']['ledger_path'])}
    acceptance=save(root/'accepted-final.json',{'verdict':'accept','registration_sha256':sequence.sha(registration),
        'result_sha256':result['sha256'],'ledger_sha256':ledger['sha256'],'artifacts':artifacts})
    snapshot=save(root/'phase4-state.json',sequence.read(state_path))
    m=deepcopy(manifest);r=root/'evaluation/registration.json'
    predecessor={'stage':'reconciliation','registration':{'path':str(registration),'sha256':sequence.sha(registration)},
        'ledger':ledger,'state':snapshot,'result':result,'acceptance':acceptance}
    m['budget_sequence'].update(stage='evaluation',predecessor=predecessor)
    m.pop('job');m['evaluation_jobs']=[{'id':'primary'},{'id':'repeat'}]
    m['budget'].update(ledger_path=str(r.parent/'billing.json'),
        continuation={'checkpoint':ledger['path'],'sha256':ledger['sha256'],
                      'cost_usd':str(sequence._rows(sequence.read(ledger['path'])))})
    for ref in [full,core,*[value for value in predecessor.values() if isinstance(value,dict)]]:
        m['pinned_files'][ref['path']]=ref['sha256']
    finish_registration(m,r)
    return m,r


def test_phase4_handoff_to_multiple_evaluation_jobs_keeps_audit_sealed(tmp_path):
    m,r,state=fixture(tmp_path)
    with enter(m,r) as first:
        ticket=first.reserve(sequence.sha(r)+':finish','.02','finalization')
        first.ledger.settle(ticket,'.02',response_sha256='response',usage={'complete':True})
    legacy={key:sequence.read(state)[key] for key in sequence._legacy_fields(m,sequence.digest(m['budget_sequence']['origin']))}
    e,er=evaluation_successor(m,r,state)
    for job in ('primary','repeat'):
        with enter(e,er) as owner:
            ticket=owner.reserve(sequence.sha(er)+':'+job,'.01',job)
            owner.ledger.settle(ticket,'.01',response_sha256='response',usage={})
    assert len(sequence.read(e['budget']['ledger_path'])['requests'])==4
    assert all(sequence.read(state)[key]==value for key,value in legacy.items())
    with pytest.raises(BudgetStop):
        with enter(m,r):pass


@pytest.mark.parametrize('change',['new_namespace','copied_origin','symlink','stale_ledger','wrong_source_caps'])
def test_transfer_cannot_relocate_ancestry_or_repin_different_budget(tmp_path,change):
    m,r,state=fixture(tmp_path);before=state.read_bytes()
    if change=='new_namespace':m['budget_sequence']['state_path']=str(tmp_path/'other/audit_sequence.json')
    elif change=='copied_origin':
        original=m['budget_sequence']['origin']['registration']
        copied=save(tmp_path/'copied-origin.json',sequence.read(original['path']))
        m['budget_sequence']['origin']['registration']=copied;m['pinned_files'][copied['path']]=copied['sha256']
    elif change=='symlink':
        link=tmp_path/'linked-state.json';link.symlink_to(state);m['budget_sequence']['state_path']=str(link)
    elif change=='stale_ledger':
        source=Path(m['budget']['continuation']['checkpoint']);source.write_bytes(source.read_bytes()+b'\n')
    else:m['budget']['additional_usd']='800'
    finish_registration(m,r)
    with pytest.raises(BudgetStop):
        with enter(m,r):pass
    assert state.read_bytes()==before and not Path(m['budget']['ledger_path']).exists()


def test_locked_predecessor_blocks_transfer_before_destination_ledger(tmp_path):
    m,r,state=fixture(tmp_path);before=state.read_bytes()
    with FileLock(str(state)+'.lock',timeout=0):
        with pytest.raises(BudgetStop,match='Timeout'):
            with enter(m,r):pass
    assert state.read_bytes()==before and not Path(m['budget']['ledger_path']).exists()


def test_caller_error_is_preserved_and_owner_expires(tmp_path):
    m,r,_=fixture(tmp_path);error=OSError('synthetic caller failure')
    with pytest.raises(OSError) as observed:
        with enter(m,r) as owner:raise error
    assert observed.value is error
    with pytest.raises(BudgetStop):owner.verify_admission()


@pytest.mark.parametrize('change',['missing','identity','caps','prefix','negative_new_cost','unknown_new_attempt'])
def test_reopen_requires_existing_intact_descendant_ledger(tmp_path,change):
    m,r,_=fixture(tmp_path)
    with enter(m,r) as owner:
        ticket=owner.reserve(sequence.sha(r)+':finish','.01','request')
        owner.ledger.settle(ticket,'.01',response_sha256='response',usage={})
    ledger=owner.ledger.path;value=sequence.read(ledger)
    if change=='missing':ledger.unlink()
    elif change=='identity':value['manifest_sha256']='other'
    elif change=='caps':value['additional_cap_usd']='800'
    elif change=='prefix':value['requests'][0]['cost_usd']='0'
    elif change=='negative_new_cost':value['requests'][-1]['cost_usd']='-1'
    else:value['requests'][-1]['attempt']=sequence.sha(r)+':unregistered'
    if change!='missing':save(ledger,value)
    with pytest.raises(BudgetStop):
        with enter(m,r):pytest.fail('changed accounting reopened')


@pytest.mark.parametrize('change',['kind','schema_version','registration_sha256','ledger_path'])
def test_matching_active_tip_cannot_reopen_a_changed_legacy_seal(tmp_path,change):
    m,r,state=fixture(tmp_path)
    with enter(m,r):pass
    value=sequence.read(state)
    if change=='kind':value.pop('kind')
    elif change=='schema_version':value[change]=1
    elif change=='registration_sha256':value[change]=m['budget_sequence']['audit_origin']['registration']['sha256']
    else:value[change]=m['budget_sequence']['audit_origin']['ledger']['path']
    save(state,value)
    with pytest.raises(BudgetStop,match='seal changed'):
        with enter(m,r):pytest.fail('matching owner bypassed permanent legacy seal')


@pytest.mark.parametrize('change',['missing','object','empty','cost','checkpoint','extra'])
def test_reopen_requires_exact_complete_activation_state(tmp_path,change):
    m,r,state=fixture(tmp_path)
    with enter(m,r):pass
    ledger_before=Path(m['budget']['ledger_path']).read_bytes()
    value=sequence.read(state)
    if change=='missing':value.pop('transfers')
    elif change=='object':value['transfers']={}
    elif change=='empty':value['transfers']=[]
    elif change=='cost':value['transfers'][0]['settled_cost_usd']='0'
    elif change=='checkpoint':value['transfers'][0]['checkpoint_sha256']='different'
    else:value['unregistered_annotation']='not the registered activation'
    save(state,value)
    with pytest.raises(BudgetStop):
        with enter(m,r) as owner:owner.reserve(sequence.sha(r)+':finish','.01','must-not-reserve')
    assert Path(m['budget']['ledger_path']).read_bytes()==ledger_before


@pytest.mark.parametrize('target',['state','lock','new_ledger','ledger_lock','ledger_temporary'])
def test_mutable_destinations_cannot_alias_pinned_inputs_before_any_write(tmp_path,target):
    m,r,state=fixture(tmp_path)
    ledger=Path(m['budget']['ledger_path'])
    selected={'state':state,'lock':Path(str(state)+'.lock'),'new_ledger':ledger,
              'ledger_lock':Path(str(ledger)+'.lock'),'ledger_temporary':ledger.with_suffix('.tmp')}[target]
    if target!='state':save(selected,{'immutable':'must survive even lock acquisition'})
    m['pinned_files'][str(selected)]=sequence.sha(selected)
    if target=='state':
        m['budget_sequence']['predecessor']['state']={'path':str(state),'sha256':sequence.sha(state)}
        refresh_audit_origin(m)
    finish_registration(m,r)
    before={name:Path(name).read_bytes() for name in m['pinned_files']}
    state_before=state.read_bytes()
    with pytest.raises(BudgetStop):
        with enter(m,r):pytest.fail('mutable target overwrote an immutable input')
    assert {name:Path(name).read_bytes() for name in before}==before
    assert state.read_bytes()==state_before
    if target!='new_ledger':assert not ledger.exists()


@pytest.mark.parametrize('change',['unchecked','errors','findings','wrong_hash','wrong_job','missing_checked','missing_errors'])
def test_audit_validator_closure_must_be_checked_clean_and_exact(tmp_path,change):
    m,r,state=fixture(tmp_path);p=m['budget_sequence']['predecessor']
    result=sequence.read(p['result']['path']);validation=result['validation']
    if change=='unchecked':validation['checked']=False
    elif change=='errors':validation['errors']=['checker did not complete']
    elif change=='findings':validation['findings']=[{'kind':'contradiction'}]
    elif change=='wrong_hash':validation['audit_sha256']='0'*64
    elif change=='wrong_job':validation['job_id']='different'
    elif change=='missing_checked':validation.pop('checked')
    else:validation.pop('errors')
    repin(m,p['result'],result);refresh_audit_origin(m);finish_registration(m,r)
    before=state.read_bytes()
    with pytest.raises(BudgetStop):
        with enter(m,r):pytest.fail('contradictory validator receipt admitted')
    assert state.read_bytes()==before and not Path(m['budget']['ledger_path']).exists()


@pytest.mark.parametrize('exit_code',[None,False,True,1,-1,'0',0.0,'missing'])
def test_audit_exit_must_be_typed_integer_zero_before_handoff(tmp_path,exit_code):
    m,r,state=fixture(tmp_path);p=m['budget_sequence']['predecessor']
    result=sequence.read(p['result']['path'])
    if exit_code=='missing':result['runtime'].pop('exit_code')
    else:result['runtime']['exit_code']=exit_code
    # The accepted bytes and every downstream reference are coherently repinned;
    # rejection must concern the contradiction, not an outdated hash.
    repin(m,p['result'],result);refresh_audit_origin(m);finish_registration(m,r)
    original={name:Path(name).read_bytes() for name in m['pinned_files']}
    state_before=state.read_bytes()
    with pytest.raises(BudgetStop,match='audit predecessor lacks successful native integer-zero exit'):
        with enter(m,r):pytest.fail('contradictory native completion admitted')
    assert state.read_bytes()==state_before and not Path(m['budget']['ledger_path']).exists()
    assert original=={name:Path(name).read_bytes() for name in original}


def test_valid_pure_audit_report_needs_no_nested_registration_hash(tmp_path):
    from audit_controls.contract import validate_audit
    from audit_controls.test_contract import audit_fixture
    actual_dir=tmp_path/'actual-validator';actual_dir.mkdir()
    actual,_=audit_fixture(actual_dir)
    actual['job']['id']='audit'
    report=validate_audit(actual)
    assert report['passed'] and report['checked'] and report['evidence']['assertions_checked']==2
    assert 'registration_sha256' not in report
    m,r,_=fixture(tmp_path/'accounting');p=m['budget_sequence']['predecessor']
    result=sequence.read(p['result']['path'])
    Path(result['audit_path']).write_bytes(Path(actual['job']['audit_path']).read_bytes())
    m['pinned_files'][result['audit_path']]=report['audit_sha256']
    result.update(validation=report,audit_sha256=report['audit_sha256'])
    repin(m,p['result'],result)
    acceptance=sequence.read(p['acceptance']['path'])
    acceptance['artifacts']={result['audit_path']:report['audit_sha256']}
    repin(m,p['acceptance'],acceptance);refresh_audit_origin(m);finish_registration(m,r)
    with enter(m,r) as owner:owner.verify_admission()


def test_lock_hardlink_to_immutable_evidence_is_rejected_before_truncation(tmp_path):
    m,r,state=fixture(tmp_path)
    immutable=Path(m['budget_sequence']['predecessor']['state']['path'])
    lock=Path(str(state)+'.lock');lock.hardlink_to(immutable)
    before=immutable.read_bytes();state_before=state.read_bytes()
    with pytest.raises(BudgetStop,match='overlaps immutable'):
        with enter(m,r):pass
    assert immutable.read_bytes()==before and state.read_bytes()==state_before
    assert not Path(m['budget']['ledger_path']).exists()


@pytest.mark.parametrize('target', ['sequence_lock', 'ledger_lock'])
def test_mutable_lock_hardlink_to_state_is_rejected_before_truncation(tmp_path, target):
    m,r,state=fixture(tmp_path)
    ledger=Path(m['budget']['ledger_path'])
    lock=Path(str(state if target=='sequence_lock' else ledger)+'.lock')
    lock.hardlink_to(state)
    before=state.read_bytes()
    with pytest.raises(BudgetStop,match='mutable accounting destinations overlap'):
        with enter(m,r):pytest.fail('aliased mutable destinations admitted')
    assert state.read_bytes()==before and lock.read_bytes()==before
    assert not ledger.exists()


@pytest.mark.parametrize('change',['missing','object','cost'])
def test_repinning_damaged_predecessor_history_cannot_activate_evaluation(tmp_path,change):
    m,r,state=fixture(tmp_path)
    with enter(m,r):pass
    value=sequence.read(state)
    if change=='missing':value.pop('transfers')
    elif change=='object':value['transfers']={}
    else:value['transfers'][0]['settled_cost_usd']='0'
    save(state,value)
    e,er=evaluation_successor(m,r,state)  # internally pinned bad snapshot
    before=state.read_bytes()
    with pytest.raises(BudgetStop):
        with enter(e,er):pytest.fail('repinned broken lineage admitted')
    assert state.read_bytes()==before and not Path(e['budget']['ledger_path']).exists()


def historical_guard(version):
    """Execute exact checked-in historical function bodies, not a test mirror."""
    fixtures=sequence.read(BASE/'historical_sequence_guards.json')
    entry=fixtures[version]
    assert hashlib.sha256(entry['functions'].encode()).hexdigest()==entry['functions_sha256']
    namespace={'contextmanager':contextmanager,'FileLock':FileLock,'BudgetStop':BudgetStop,'json':json,'Path':Path,
        'sha':sequence.sha,'read_json':sequence.read,'canonical_path':sequence.path,
        'canonical_json':lambda value:sequence.canonical(value).decode(),
        'parent_path':lambda parent,value:Path(value) if Path(value).is_absolute() else Path(parent['repository'])/value,
        'parent_job':lambda manifest:(sequence.read(manifest['parent']['registration']),{}),
        'pinned':lambda manifest,value,*args:Path(value)}
    exec(compile(entry['functions'],entry['source'], 'exec'),namespace)
    return namespace['sequence_guard']


@pytest.mark.parametrize('version',['2108','2113'])
def test_actual_historical_guard_admits_before_and_refuses_after_seal(tmp_path,version):
    m,r,state=fixture(tmp_path);guard=historical_guard(version)
    candidate={'parent':{'registration':m['budget_sequence']['origin']['registration']['path'],'repository':str(tmp_path)},
        'sequence_state':str(state),'budget':{'ledger_path':str(tmp_path/'legacy-child/billing.json'),
            'continuation':deepcopy(m['budget']['continuation'])}}
    original=state.read_bytes()
    with guard(candidate,'legacy-child'):pass
    state.write_bytes(original)
    with enter(m,r):pass
    sealed=state.read_bytes()
    with pytest.raises(BudgetStop):
        with guard(candidate,'legacy-child'):pytest.fail('old controller admitted')
    seal=m['budget_sequence']['seal']
    candidate['budget']['continuation'].update(checkpoint=seal['path'],sha256=seal['sha256'])
    with pytest.raises(BudgetStop):
        with guard(candidate,'legacy-other'):pytest.fail('seal treated as accounting')
    if version=='2113':
        candidate['budget']['continuation']['reconciliation']={
            'source_registration':seal['path'],'source_ledger':seal['path'],'receipt':seal['path'],'result':seal['path']}
        with pytest.raises(BudgetStop):
            with guard(candidate,'legacy-bridge'):pytest.fail('seal treated as an audit registration')
    assert state.read_bytes()==sealed and not Path(candidate['budget']['ledger_path']).exists()
