"""Offline fabricated authority + ordinary Python CLI, never live permission.

The public verifier/consumer are real. Fabricated saved native observations,
review/CI/owner evidence and a patched private auth observation are test data,
not evidence authorizing any real launch. Every generation helper is genuine.
"""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import sys

import pytest

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_execution as execute
from data_sheets_schema import native_execution_registration as registration
from data_sheets_schema import native_execution_authority as authority
from tests.test_native_attempt_supervisor import make_case
from tests.test_native_execution_permissions import fabricated_manifest


def make_native_case(root, mode='correction', awake=False):
    case=make_case(root)
    spec=replace(case['spec'],reasoning_effort='medium')
    instruction=root/'instruction.md';instruction.write_text(spec.instruction)
    selected=composition.composition(draft._encoded(draft.registration(spec)),instruction)
    composition_path=root/'composition.json';composition_path.write_bytes(draft._encoded(selected))
    fake=root/'python-fake-cli'
    fake.write_bytes(('#!'+sys.executable+'\n').encode()+(
        Path(__file__).parent/'fixtures/native_execution/fake_cli.py').read_bytes())
    fake.chmod(0o700)
    (root/'test-mode.txt').write_text(mode)
    runtime={'route':registration.ROUTE,'executable':{'path':str(fake),
        'sha256':draft._sha(fake.read_bytes()),'version':'SYNTHETIC TEST CLI ONLY','init_version':'synthetic-test-1'},
        'model':'synthetic-test-model','auxiliary_models':[],'effort':spec.reasoning_effort,
        'limits':{'contextWindow':100000,'maxOutputTokens':10000},'limits_basis':'Synthetic software test assertion',
        'provider':spec.provider,'auth':{'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty',
            'subscriptionType':'synthetic-test-subscription','expected_api_key_source':'none'},
        'environment':{'PATH':str(Path(sys.executable).parent)+':/usr/bin:/bin','HOME':str(root),
            'LANG':'en_US.UTF-8','CLAUDE_SECURESTORAGE_CONFIG_DIR':'','CLAUDE_CODE_DISABLE_1M_CONTEXT':'1'},
        'deadline_seconds':180,'budget_guard_usd':'1.0',
        'keep_awake':{'policy':'macos_iokit_ims_v1' if awake else 'not_applicable','host_platform':'darwin' if awake else sys.platform,
            'basis':'Ordinary local Python fixture, not a production native or paid generation run'}}
    system=root/'system.txt';system.write_text('Explicitly synthetic software test. No actual native executable or provider.\n')
    controls=composition.load_controls()
    effective=system.read_text()+controls['native_command_policy'].command_guidance(selected['policy'])
    expected=registration.permission_expectation(runtime,selected,spec,effective,root/'native-attempt/cli_config')
    fabricated=fabricated_manifest(expected,root/'fabricated-probe',spec.bundle.read_bytes())
    probe=root/'fabricated-permission.json';probe.write_bytes(draft._encoded(fabricated['manifest']))
    value=registration.registration(composition_path,system,permission_probe_path=probe,
        attempt_id='native-attempt',attempt_directory=root/'native-attempt',evidence_directory=root/'native-evidence',runtime=runtime)
    assert value['argv'].count('--input-format') == 1  # supplied by the frozen permission helper
    raw=draft._encoded(value)
    binding={'registration_sha256':draft._sha(raw),'attempt_id':value['attempt_id'],
        'source_commit':value['dependencies']['base']['source_commit'],
        'dependencies_sha256':draft._sha(draft._encoded(value['dependencies']))}
    review={**binding,'kind':'d4d_native_execution_review','version':1,'reviewer':'synthetic-independent-reviewer',
        'author':'synthetic-author','independent':True,'decision':'approved','reviewed_at':'synthetic-time',
        'evidence':'Invented software test, NOT an actual independent review'}
    ci={**binding,'kind':'d4d_native_execution_ci','version':1,'checks':{name:{
        'head_sha':binding['source_commit'],'status':'completed','conclusion':'success',
        'details_url':'https://github.com/bridge2ai/data-sheets-schema/actions/SYNTHETIC-NOT-A-REAL-RUN'}
        for name in execute.REQUIRED_CHECKS}}
    review_path=root/'fabricated-review.json';review_path.write_bytes(draft._encoded(review))
    ci_path=root/'fabricated-ci.json';ci_path.write_bytes(draft._encoded(ci))
    word={**binding,'kind':'d4d_native_execution_launch_authorization','version':1,
        'owner':'synthetic-test-owner','authorized_at':'synthetic-time','word':'AUTHORIZE_ONE_NATIVE_ATTEMPT',
        'review_sha256':draft._sha(review_path.read_bytes()),'ci_sha256':draft._sha(ci_path.read_bytes()),
        'permission_probe_sha256':value['permission_probe_sha256']}
    launch_path=root/'fabricated-owner.json';launch_path.write_bytes(draft._encoded(word))
    return {**case,'spec':spec,'value':value,'raw':raw,'kwargs':{
        'review_path':review_path,'ci_path':ci_path,'launch_word_path':launch_path}}


def fake_observation(value):
    """The ONLY auth/version test seam; no native subprocess is invoked."""
    runtime=value['runtime']
    return {'checked':True,'passed':True,'observed_at':'EXPLICITLY SYNTHETIC TEST ONLY',
        'binary':registration.executable_identity(runtime['executable']['path']),
        'version':runtime['executable']['version'],
        'auth':{k:runtime['auth'][k] for k in ('loggedIn','authMethod','apiProvider','subscriptionType')},
        'environment_sha256':draft._sha(draft._encoded(value['environment'])),
        'scope':'FABRICATED OFFLINE TEST observation, never real permission/auth/provider evidence.'}


@pytest.fixture
def case(tmp_path,monkeypatch):
    monkeypatch.chdir(authority.ROOT)
    return make_native_case(tmp_path/'native')


@pytest.mark.parametrize('mode',['correction','no_correction'])
def test_actual_closed_consumer_real_helpers_complete(case,monkeypatch,mode):
    (case['root']/'test-mode.txt').write_text(mode)
    monkeypatch.setattr(execute,'_probe_runtime',fake_observation)
    with authority.loaded_dependencies(case['value']['dependencies']) as modules:
        def trap(*a,**k):pytest.fail('historical launcher, auth, or provider factory invoked')
        for name,attrs in [('prepare_direct',['auth_evidence']),('run_direct_canary',['main']),
                           ('run_api_canary',['main']),('budgeted_cborg',['cborg_client'])]:
            for attr in attrs:
                if hasattr(modules[name],attr):monkeypatch.setattr(modules[name],attr,trap)
        result=execute.launch(case['raw'],**case['kwargs'])
    assert result['runtime_gates_passed'],json.dumps(result,indent=2)
    assert result['state']=='completed_pending_independent_review'
    assert set(result['gates'])==set(execute.gates.GATES)
    assert result['gates']['live_attribution']['result']['checks']==(2 if mode=='correction' else 1)
    assert not any(result['gates']['receipts']['floors'].values())
    assert execute.read_final(case['raw'])==result
    assert result['scientific_acceptance']=='not_assessed'
    with pytest.raises(ValueError,match='new|resume'):
        execute.launch(case['raw'],**case['kwargs'])
    if mode=='no_correction':
        # Every validation gate must consume sealed captured bytes or exact
        # private projections, not silently reread the original input files.
        with authority.loaded_dependencies(case['value']['dependencies']) as modules:
            prepared=execute.gates.capture(case['value'],modules,registration_raw=case['raw'],
                authority_inputs={**{k:str(v) for k,v in case['kwargs'].items()},
                                  'system':case['value']['system_path'],'permission':case['value']['permission_probe']})
            projections=execute.shared.project(prepared,case['root']/'sealed-check-projections')
            original_read=Path.read_bytes
            def trapped(path):
                if str(path.resolve()) in prepared['snapshot'].raw:
                    raise AssertionError('uncaptured original file read during gate validation')
                return original_read(path)
            with monkeypatch.context() as local:
                local.setattr(Path,'read_bytes',trapped)
                checked=execute.gates.check(prepared,projections,{**case['value']['runtime'],
                    'attempt_directory':case['value']['attempt_directory']},modules,
                    exit_code=result['child_exit_code'],shutdown=result['shutdown'],
                    live=result['gates']['live_attribution']['result'],first_stop=None,
                    runtime_authority=result['runtime_observation'],keep_awake=result['keep_awake'])
            assert all(row['checked'] and row['passed'] for row in checked.values()),checked
        generated=Path(result['additional_report']['path'])
        generated.write_bytes(generated.read_bytes()+b'\n')
        with pytest.raises(ValueError,match='replay report'):execute.read_final(case['raw'])


@pytest.mark.parametrize('mode',['protected_correction','contradictory_exit','unknown_usage'])
def test_real_callback_and_usage_failures_stay_failed(case,monkeypatch,mode):
    (case['root']/'test-mode.txt').write_text(mode)
    monkeypatch.setattr(execute,'_probe_runtime',fake_observation)
    result=execute.launch(case['raw'],**case['kwargs'])
    assert result['runtime_gates_passed'] is False
    assert result['state']=='failed'
    assert (case['root']/'native-attempt/transcript.jsonl').is_file()
    assert execute.read_final(case['raw'])==result
    if mode=='unknown_usage':
        assert not result['gates']['accounting']['passed']
        assert result['gates']['terminal']['terminal']['usage']['input_tokens'] is None
    else:assert result['first_stop'] is not None


@pytest.mark.parametrize('missing',['review_path','ci_path','launch_word_path'])
def test_missing_authority_refuses_before_any_reservation(case,monkeypatch,missing):
    case['kwargs'][missing].write_text('{}')
    monkeypatch.setattr(execute,'_probe_runtime',lambda v:pytest.fail('runtime observation called'))
    with pytest.raises(ValueError):execute.launch(case['raw'],**case['kwargs'])
    assert not (case['root']/'native-attempt').exists()


@pytest.mark.parametrize('mutation',['wrong_head','pending','missing_check','independence','owner_word','probe_pin'])
def test_exact_authority_cannot_be_weakened(case,monkeypatch,mutation):
    key='ci_path' if mutation in ('wrong_head','pending','missing_check') else 'review_path' if mutation=='independence' else 'launch_word_path'
    path=case['kwargs'][key];data=draft._json(path.read_bytes())
    if mutation=='wrong_head':data['source_commit']='f'*40
    elif mutation=='pending':data['checks']['test']['status']='pending'
    elif mutation=='missing_check':del data['checks']['test']
    elif mutation=='independence':data['independent']=False
    elif mutation=='owner_word':data['word']='approved in general'
    elif mutation=='probe_pin':data['permission_probe_sha256']='0'*64
    path.write_bytes(draft._encoded(data))
    monkeypatch.setattr(execute,'_probe_runtime',lambda v:pytest.fail('native call before authority'))
    with pytest.raises(ValueError):execute.launch(case['raw'],**case['kwargs'])
    assert not (case['root']/'native-attempt').exists()


@pytest.mark.parametrize('key',['route','model','effort','limits','limits_basis','auth','environment',
                                'deadline_seconds','budget_guard_usd','keep_awake','provider','executable','auxiliary_models'])
def test_missing_runtime_choice_has_no_default(case,key):
    runtime=deepcopy(case['value']['runtime']);del runtime[key]
    with pytest.raises(ValueError):registration.validate_runtime(runtime)


@pytest.mark.parametrize('change',['deadline_bool','context_bool','negative_budget','budget_nan','budget_number',
    'runtime_flag','model_flag','aux_duplicate','unknown_env','relative_path','auth_false','auth_bool_alias',
    'awake_unknown','source_hash','source_symlink','version_blank'])
def test_runtime_contract_rejects_ambiguous_or_unpinned_choices(case,change,tmp_path):
    runtime=deepcopy(case['value']['runtime'])
    if change=='deadline_bool':runtime['deadline_seconds']=True
    elif change=='context_bool':runtime['limits']['contextWindow']=True
    elif change=='negative_budget':runtime['budget_guard_usd']='-1'
    elif change=='budget_nan':runtime['budget_guard_usd']='NaN'
    elif change=='budget_number':runtime['budget_guard_usd']=1
    elif change=='runtime_flag':runtime['argv']=['--dangerously-skip-permissions']
    elif change=='model_flag':runtime['model']='--other-flag'
    elif change=='aux_duplicate':runtime['auxiliary_models']=['same','same']
    elif change=='unknown_env':runtime['environment']['ANTHROPIC_BASE_URL']='http://elsewhere'
    elif change=='relative_path':runtime['environment']['PATH']='relative:/bin'
    elif change=='auth_false':runtime['auth']['loggedIn']=False
    elif change=='auth_bool_alias':runtime['auth']['loggedIn']=1
    elif change=='awake_unknown':runtime['keep_awake']['policy']='best_effort'
    elif change=='source_hash':runtime['executable']['sha256']='a'*64
    elif change=='source_symlink':
        target=tmp_path/'alias';target.symlink_to(runtime['executable']['path']);runtime['executable']['path']=str(target)
    elif change=='version_blank':runtime['executable']['version']=''
    with pytest.raises(ValueError):registration.validate_runtime(runtime)


def test_auth_failure_keeps_one_spent_attempt_and_known_evidence(case,monkeypatch):
    def fail(value):raise RuntimeError('mock auth failed; no native subprocess invoked')
    monkeypatch.setattr(execute,'_probe_runtime',fail)
    result=execute.launch(case['raw'],**case['kwargs'])
    assert not result['runtime_gates_passed'] and result['first_stop']
    assert (case['root']/'native-attempt/started.json').exists()
    assert (case['root']/'native-attempt/runtime-observation.json').exists()
    assert execute.read_final(case['raw'])==result
    with pytest.raises(ValueError,match='new|resume'):execute.launch(case['raw'],**case['kwargs'])


@pytest.mark.parametrize('boundary',['attempt_parent','registration.json','started.json','evidence_parent'])
def test_reservation_failures_never_dispatch_and_never_resume(case,monkeypatch,boundary):
    real_write=execute.durable_new;real_sync=execute._sync_directory
    count=0
    def sync(path):
        nonlocal count
        count+=1
        if boundary=='attempt_parent' and count==1 or boundary=='evidence_parent' and count==2:
            raise OSError('injected parent durability failure')
        return real_sync(path)
    def write(path,raw):
        if Path(path).name==boundary:raise OSError('injected start durability failure')
        return real_write(path,raw)
    monkeypatch.setattr(execute,'_sync_directory',sync)
    monkeypatch.setattr(execute,'durable_new',write)
    monkeypatch.setattr(execute,'_probe_runtime',lambda v:pytest.fail('dispatch admission before durable start'))
    with pytest.raises(OSError,match='durability'):execute.launch(case['raw'],**case['kwargs'])
    assert (case['root']/'native-attempt').exists()
    with pytest.raises(ValueError,match='new|resume'):execute.launch(case['raw'],**case['kwargs'])


def test_actual_historical_launcher_refuses_new_kind_before_native_or_auth(case,tmp_path):
    import subprocess
    directory=tmp_path/'old-guard';directory.mkdir()
    value={**draft._json(case['raw']),'code_commit':case['value']['dependencies']['base']['source_commit']}
    raw=draft._encoded(value);digest=draft._sha(raw)
    (directory/'registration.json').write_bytes(raw)
    (directory/'review.json').write_bytes(draft._encoded({'verdict':'approve','ci_conclusion':'success',
        'registration_sha256':digest,'allowed_jobs':['test_job'],'ci_head':value['code_commit'],
        'ci_run_id':1,'independent_review_sha256':'a'*64}))
    (directory/'word.json').write_bytes(draft._encoded({'registration_sha256':digest,'exact_response':'synthetic only'}))
    before={str(p):p.read_bytes() for p in directory.iterdir()}
    program=r'''
import runpy,sys,subprocess
from pathlib import Path
root,folder=map(Path,sys.argv[1:]);sys.path.insert(0,str(root/'notes/claudecode_direct'))
ns=runpy.run_path(str(root/'notes/claudecode_direct/run_direct_canary.py'));g=ns['main'].__globals__
def trap(*a,**k):raise AssertionError('historical launcher reached native/auth/child path')
g['verify_environment']=lambda:None
for module,name in [(g['preparation'],'auth_evidence'),(g['native'],'execute_child'),
                     (subprocess,'Popen'),(subprocess,'check_output')]:setattr(module,name,trap)
try:ns['main'](['--registration',str(folder/'registration.json'),'--review',str(folder/'review.json'),
               '--job','test_job','--launch-word',str(folder/'word.json')])
except g['BudgetStop'] as exc:assert str(exc)=='not a direct-arm registration',str(exc)
else:raise AssertionError('historical launcher admitted the new kind')
'''
    proc=subprocess.run([sys.executable,'-c',program,str(authority.ROOT),str(directory)],
                        cwd=authority.ROOT,capture_output=True,text=True)
    assert proc.returncode==0,(proc.stdout,proc.stderr)
    assert {str(p):p.read_bytes() for p in directory.iterdir()}==before


def test_api_and_neutral_consumers_keep_explicit_refusals(case):
    from data_sheets_schema import api_runner as api
    from data_sheets_schema import native_attempt_supervisor as neutral
    with pytest.raises(ValueError,match='offline-only'):api.execute(case['spec'],client=object())
    with pytest.raises(ValueError,match='neutral-only'):neutral.verified(case['raw'])


@pytest.mark.parametrize('failure',['acquire','release','none'])
def test_keep_awake_actual_consumer_lifecycle_uses_only_fake_iokit(tmp_path,monkeypatch,failure):
    monkeypatch.chdir(authority.ROOT)
    case=make_native_case(tmp_path/'awake',mode='no_correction',awake=True)
    monkeypatch.setattr(execute,'_platform',lambda:'darwin')
    monkeypatch.setattr(execute,'_probe_runtime',fake_observation)
    events=[]
    class FakeIOKit:
        def create(self,kind):
            events.append(('create',kind))
            if failure=='acquire' and len(events)==2:raise RuntimeError('synthetic acquisition refusal')
            return len(events)
        def release(self,identity):
            # Acquisition failure has no child; successful acquisition must
            # remain held until actual child shutdown and transcript capture.
            if failure!='acquire':
                transcript=case['root']/'native-attempt/transcript.jsonl'
                assert transcript.exists() and '"type": "result"' in transcript.read_text()
                assert (case['root']/'native-evidence/attribution-replay.json').exists()
            events.append(('release',identity))
            return 7 if failure=='release' else 0
    with authority.loaded_dependencies(case['value']['dependencies']) as modules:
        monkeypatch.setattr(modules['run_direct_canary_awake'],'_IOKit',FakeIOKit)
        result=execute.launch(case['raw'],**case['kwargs'])
    assert result['runtime_gates_passed'] is (failure=='none'),json.dumps(result,indent=2)
    assert any(e[0]=='release' for e in events)
    assert result['keep_awake']['releases']
    assert execute.read_final(case['raw'])==result


def test_registration_output_cannot_consume_its_own_future_attempt(case):
    value=case['value']
    with pytest.raises(ValueError,match='reservation'):
        registration.write_registration(case['root']/'native-attempt',composition_path=value['composition'],
            system_path=value['system_path'],permission_probe_path=value['permission_probe'],
            attempt_id=value['attempt_id'],attempt_directory=value['attempt_directory'],
            evidence_directory=value['evidence_directory'],runtime=value['runtime'])
    assert not (case['root']/'native-attempt').exists()


@pytest.mark.parametrize('boundary',['final.json','published.json'])
def test_interrupted_publication_never_certifies_or_reuses_spent_attempt(case,monkeypatch,boundary):
    def auth_failure(value):raise RuntimeError('synthetic auth refusal, no native call')
    monkeypatch.setattr(execute,'_probe_runtime',auth_failure)
    real=execute.durable_new
    def interrupted(path,raw):
        if Path(path).name==boundary:raise OSError('injected publication interruption')
        return real(path,raw)
    monkeypatch.setattr(execute,'durable_new',interrupted)
    with pytest.raises(OSError,match='publication interruption'):
        execute.launch(case['raw'],**case['kwargs'])
    assert (case['root']/'native-attempt/started.json').is_file()
    assert (case['root']/'native-attempt/runtime-observation.json').is_file()
    assert not (case['root']/'native-evidence/published.json').exists()
    assert (case['root']/'native-evidence/final.json').exists() is (boundary=='published.json')
    with pytest.raises((ValueError,OSError)):execute.read_final(case['raw'])
    with pytest.raises(ValueError,match='new|resume'):execute.launch(case['raw'],**case['kwargs'])
