"""Fabricated permission records: software tests, NEVER native observations.

No native/auth/provider process executes. S/R/preparation/C and every selected
production source pin are genuine; the saved traces are explicitly fabricated.
These tests exercise observation parsing, not permission authenticity/admission.
"""
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import uuid

import pytest

from data_sheets_schema import native_shared_permissions as p
from data_sheets_schema import native_shared_permission_orchestration as permission_orchestration
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_effects as effects
from data_sheets_schema import native_shared_policy as command_policy
from data_sheets_schema import native_attribution_controller_v2 as composition
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as execution_v2
from data_sheets_schema import native_shared_controller_orchestration as shared_controller
from data_sheets_schema import native_shared_registration_orchestration as shared_registration
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_controller import declaration, synthetic_declaration
from tests.utils.native_shared_consumer_scope import loaded_consumer, command_guidance, observe_consumer_calls

_REAL_POPEN = subprocess.Popen


def encoded(value):
    return p._encoded(value)


def member(raw):
    if type(raw) is str:
        raw = raw.encode()
    return {'text': raw.decode(), 'sha256': p._sha(raw), 'bytes': len(raw)}


def put(value, name, data):
    value['members'][name] = member(encoded(data))


def get(value, name):
    return json.loads(value['members'][name]['text'])


def put_rows(value, name, rows):
    value['members'][name] = member(b''.join(encoded(row)+b'\n' for row in rows))


def rows(value, name):
    return [json.loads(line) for line in value['members'][name]['text'].splitlines()]


def fabricated_manifest(expected, selected, neutral_root, source_raw):
    """Reusable TEST-ONLY forged observation, not a launch permission proof."""
    with permission_orchestration.loaded_permission_inputs() as (controls, _controller_sources):
        with loaded_consumer('native_shared_permissions') as consumer:
            return _fabricated_manifest(expected, selected, neutral_root, source_raw, controls, consumer)


def _fabricated_manifest(expected, selected, neutral_root, source_raw, controls, p):
    from data_sheets_schema.native_model_aliases import model_aliases
    aliases = model_aliases(expected['runtime'])
    native = p._permission_protocol()
    files = {name: text.encode() for name,text in p.recipe_sources().items()}
    files.update({'policy.json': encoded(expected['policy']), 'selection.json': encoded(selected),
                  'source.before': source_raw, 'source.after': source_raw,
                  'version.txt': (expected['runtime']['executable']['version']+'\n').encode()})
    for index, trace in enumerate(p.TRACES):
        prefix = 'traces/' + trace + '/'
        parent = Path(neutral_root)/trace
        launch = {key: str(parent/key) for key in ('config_root','stub_root','effect_root','evidence_root')}
        probe_policy = p.projected_policy(expected, selected, launch['effect_root'])
        provider = 'http://127.0.0.1:18455'
        launch.update(cwd=expected['policy']['readonly_lookups']['repository'], argv=p.probe_argv(expected, probe_policy),
            environment={**expected['permission_environment'], 'CLAUDE_CONFIG_DIR': launch['config_root'],
                'PYTHONPATH': launch['stub_root'], 'ANTHROPIC_BASE_URL': provider,
                'ANTHROPIC_API_KEY': 'd4d-local-permission-probe-token'}, provider_url=provider,
            provider_source_sha256=p._sha(files['recipe/provider.py']),
            exit_code=0 if trace == 'settled' else -15,
            shutdown={'control_initialized': True, 'control_shutdown_complete': True,
                      'unfinished_control_workers': 0, 'child_reaped': True},
            executable=deepcopy(expected['runtime']['executable']))
        session = str(uuid.UUID(int=index+1))
        all_cases = p.probe_cases(expected, selected, launch, session)
        if trace == 'settled':
            files['cases.json'] = encoded([{k:v for k,v in case.items() if k != 'input'} for case in all_cases])
        cases = [x for x in all_cases if x['mode'] != 'observer_stopped'] if trace == 'settled' else [
            x for x in all_cases if x['id'] == trace[5:]]
        ack = {'type':'control_response','response':{'subtype':'success','request_id':native.initialization_id()}}
        init = {'type':'system','subtype':'init','model':expected['runtime']['model'],
                'claude_code_version':expected['runtime']['executable']['init_version'],
                'cwd':launch['cwd'],'tools':['Read','Write','Bash'], 'apiKeySource':'ANTHROPIC_API_KEY',
                'permissionMode':'dontAsk','session_id':session}
        events = [ack,init]
        control = [{'kind':'initialize_sent','policy_sha256':native.policy_digest(probe_policy),
                    'frame':native.initialize_frame(probe_policy['pretool_control'])},
                   {'kind':'initialize_ack','frame':ack}]
        for case in cases:
            identity = case['id']; result, view = p._classification(expected, selected, launch, session,
                                                                     case, controls)
            call = {'type':'assistant','session_id':session,'message':{'role':'assistant','model':aliases['returned'],
                    'content':[{'type':'tool_use','id':identity,'name':case['tool'],'input':case['input']}]}}
            callback = {'type':'control_request','request_id':'callback-'+identity,'request':{'subtype':'hook_callback',
                'callback_id':probe_policy['pretool_control']['callback_id'],'input':{'hook_event_name':'PreToolUse',
                'tool_name':case['tool'],'tool_use_id':identity,'cwd':launch['cwd'],'tool_input':case['input']}}}
            events += [call,callback]
            if case['mode'] == 'observer_stopped':
                stop = p.effect_stop(expected, probe_policy, case, view, call, callback, result)
                files[prefix+'effect-stop.json'] = encoded(stop)
                parent_stop = {'kind':'native_shared_permission_parent_stop','version':1,'outcome':'observer_stopped',
                    'effect_stop_sha256':p._sha(files[prefix+'effect-stop.json']),
                    'reason_code':'prohibited_file_effect','error_type':'BudgetStop'}
                files[prefix+'parent-stop.json'] = encoded(parent_stop)
                continue
            if case['mode'] == 'native_denied':
                text = 'Outside the registered tool policy: ' + result[1]
                metadata = {}; block = {'is_error': True}
            elif case['tool'] == 'Bash':
                role = 'stage' if identity.startswith('stage_') else identity
                text = encoded({'d4d_shared_permission_stub':role,
                                'argv':shlex.split(case['input']['command'])[3:]}).decode()
                metadata = {'stdout':text,'stderr':'','interrupted':False}; block = {'is_error': False}
            elif case['tool'] == 'Read':
                raw_text, text, count, total = p._read_content(case, expected, selected, launch, session, source_raw)
                metadata = {'type':'text','file':{'filePath':case['input']['file_path'],'content':raw_text,
                    'numLines':count,'startLine':1,'totalLines':total}}; block = {}
            else:
                text = 'File created successfully at: ' + case['input']['file_path']
                metadata = {'type':'create','filePath':case['input']['file_path'],'content':case['input']['content'],
                            'structuredPatch':[],'originalFile':None,'userModified':False}; block = {}
            block.update(type='tool_result',tool_use_id=identity,content=text)
            events.append({'type':'user','session_id':session,'message':{'role':'user','content':[block]},
                           'tool_use_result':metadata})
            control.append({'kind':'decision','request':callback,'classification':result[0],'basis':result[1],
                'response':{'type':'control_response','response':{'subtype':'success','request_id':callback['request_id'],
                            'response':native.hook_output(*result)}}})
        if trace == 'settled':
            events.append({'type':'assistant','session_id':session,
                'message':{'role':'assistant','content':[{'type':'text','text':'OFFLINE_COMPLETE'}]}})
            if aliases['requested'] != aliases['returned']:
                events[-1]['message']['model'] = aliases['returned']
            terminal = {'type':'result','session_id':session,'subtype':'success','is_error':False,
                'terminal_reason':'completed','stop_reason':'end_turn',
                'permission_denials':[{'tool_use_id':case['id'],'tool_name':case['tool'],'tool_input':case['input']}
                                     for case in cases if case['mode']=='native_denied']}
            if aliases['requested'] != aliases['returned']:
                terminal['modelUsage'] = {aliases['requested']: {
                    **expected['runtime']['limits'], 'inputTokens': 1, 'outputTokens': 1,
                    'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0}}
            events.append(terminal)
        outcome = {'kind':'native_shared_permission_outcome','version':1,
            'mode':'settled' if trace=='settled' else 'observer_stopped','session_id':session,
            'terminal_sha256':p._sha(encoded(events[-1])) if trace=='settled' else None,
            'parent_stop_sha256':None if trace=='settled' else p._sha(files[prefix+'parent-stop.json'])}
        files.update({prefix+'launch.json':encoded(launch),prefix+'config.json':b'{}',
            prefix+'projection.json':encoded(p.projection(expected, selected, launch, session)),
            prefix+'neutral.before.json':encoded(p._inventory(expected, selected, launch, session, completed=False)),
            prefix+'neutral.after.json':encoded(p._inventory(expected, selected, launch, session, completed=trace=='settled')),
            prefix+'transcript.jsonl':b''.join(encoded(row)+b'\n' for row in events),
            prefix+'control.jsonl':b''.join(encoded(row)+b'\n' for row in control),prefix+'outcome.json':encoded(outcome)})
    return {'kind':p.KIND,'version':1,'origin':p.ORIGIN,'binding':deepcopy(expected),
            'members':{name:member(raw) for name,raw in files.items()}}


@pytest.fixture(scope='module')
def fixture(tmp_path_factory, request):
    """Build genuine S/R/preparation/C once; only the saved observations are synthetic."""
    root = tmp_path_factory.mktemp('fabricated-shared-permission').resolve()
    isolation = isolated_modules.__wrapped__()
    names = next(isolation)
    try:
        with pytest.MonkeyPatch.context() as patch:
            from data_sheets_schema import api_runner as api
            patch.setattr(api, 'CONCAT_DIR', root / 'outputs')
            small_doc = synthetic_declaration.__wrapped__(root, patch)
            doc = declaration.__wrapped__(small_doc, patch)
            spec = native_spec.__wrapped__(doc, root, patch)
            source = inputs.__wrapped__(spec, names, root, patch)
            runtime = c.strict_json(source['runtime_path'].read_bytes())
            runtime['budget_guard_usd'] = '01.50'
            if getattr(request, 'param', None) == 'u4b_aliases':
                # Only the saved consumer's alias boundary is under test.
                # This deliberately minimal declaration is not U4b prepared
                # runtime evidence or public execution-registration acceptance.
                from data_sheets_schema import native_model_aliases as aliases
                runtime['model'] = aliases.REQUESTED
                runtime['auxiliary_models'] = []
                runtime['limits_basis'] = json.dumps({'kind': aliases.KIND, 'version': 2,
                    'model_aliases': {'requested': aliases.REQUESTED, 'returned': aliases.RETURNED}})
            source['runtime_path'].write_bytes(c.canonical(runtime))
            prepared = execution_v2.prepare(source['selection'], source['runtime_path'], **source['kwargs'])
            instruction = root / 'instruction.md'
            instruction.write_bytes(prepared['registration']['instruction'].encode())
            composed = shared_controller.compose(c.canonical(prepared), instruction_path=instruction)
            _, replay, capture = shared_controller.reconstruct_composition(c.canonical(composed))
            selected = capture.document()
            expected = shared_registration.permission_expectation(runtime, composed, replay,
                'Synthetic saved observations only.' + command_guidance(composed['policy']),
                root / 'attempt' / 'cli_config', authority.dependency_identity())
            source_raw = capture.raw(selected['inputs']['bundle']['path'])
            value = fabricated_manifest(expected, selected, root / 'isolated-probes', source_raw)
            yield {'root': root, 'expected': expected, 'selection': selected,
                'manifest': value, 'source_raw': source_raw}
    finally:
        isolation.close()


@pytest.fixture(autouse=True)
def prohibit_real_transports(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('native/provider/auth/network transport forbidden in saved-verifier tests')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    def git_only(argv, *args, **kwargs):
        if not isinstance(argv, (list, tuple)) or Path(argv[0]).name != 'git' or kwargs.get('shell'):
            return forbidden()
        return _REAL_POPEN(argv, *args, **kwargs)
    monkeypatch.setattr(subprocess, 'Popen', git_only)


def verify(value, expected):
    return permission_orchestration.verify_saved_probe(encoded(value), expected=expected)


def test_complete_seven_trace_observation_is_only_software_verification(fixture):
    targets = {('native_shared_permissions', name): ()
               for name in ('_authority', '_trace_body', 'probe_argv')}
    with observe_consumer_calls(targets) as calls:
        result = verify(fixture['manifest'], fixture['expected'])
    assert set(targets) <= {key for key, _ in calls}
    assert result['checked'] is result['passed'] is True
    assert len(result['cases']) == 25 and len(result['traces']) == 7
    modes = [case['observed_mode'] for case in result['cases']]
    assert modes.count('allowed') == 16 and modes.count('native_denied') == 3 and modes.count('observer_stopped') == 6
    assert {x['state'] for x in result['derived_nonresponse_checks']} == set(p.NONRESPONSE)
    assert 'observation authenticity' in result['unassessed'] and 'provider billing' in result['unassessed']
    assert len(result['members']) == 74 + len(p.recipe_sources())
    assert set(result['preservation'])=={'source_sha256','neutral_before_sha256','neutral_after_sha256','changed_response_roles'}
    for moment in ('before','after'):
        pins=[{'trace_id':name,'sha256':fixture['manifest']['members']['traces/'+name+'/neutral.'+moment+'.json']['sha256']}
              for name in p.TRACES]
        assert result['preservation']['neutral_'+moment+'_sha256']==p._sha(encoded(pins))


@pytest.mark.parametrize('name', ['source.before','cases.json','recipe/provider.py',
    'traces/stop-source_write/effect-stop.json','traces/stop-source_write/parent-stop.json',
    'traces/settled/transcript.jsonl','traces/stop-stale_response_write/outcome.json'])
def test_missing_required_evidence_refuses(fixture, name):
    value = deepcopy(fixture['manifest']); del value['members'][name]
    with pytest.raises(ValueError):verify(value, fixture['expected'])


@pytest.mark.parametrize('field,value', [('version',True),('origin','mock'),('kind','d4d_native_saved_permission_probe')])
def test_protocol_and_legacy_shape_never_fall_back(fixture, field, value):
    changed = deepcopy(fixture['manifest']); changed[field] = value
    with pytest.raises(ValueError):verify(changed,fixture['expected'])


@pytest.mark.parametrize('field,value', [('effect_root','/unregistered/effect'),
    ('production_policy_sha256','0'*64),('probe_policy_sha256','0'*64),('role_recipe_sha256','0'*64)])
def test_rehashed_projection_cannot_change_authority(fixture, field, value):
    changed = deepcopy(fixture['manifest']); name='traces/settled/projection.json'
    projection=get(changed,name);projection[field]=value;put(changed,name,projection)
    with pytest.raises(ValueError):verify(changed,fixture['expected'])


@pytest.mark.parametrize('change', ['future_grant','result_after_stop','missing_callback','wrong_reason','parent_cause',
                                  'changed_effect','unfinished','unreaped','exit_bool','zero_exit'])
def test_stopped_cases_require_actual_callback_cause_and_no_effect(fixture, change):
    value=deepcopy(fixture['manifest']);prefix='traces/stop-future_response_write/'
    if change=='future_grant':
        data=rows(value,prefix+'control.jsonl');data.append({'kind':'decision','classification':'prescribed'});put_rows(value,prefix+'control.jsonl',data)
    elif change in ('result_after_stop','missing_callback'):
        data=rows(value,prefix+'transcript.jsonl')
        if change=='missing_callback':data.pop()
        else:data.append({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'future_response_write','content':'ok'}]}})
        put_rows(value,prefix+'transcript.jsonl',data)
    elif change=='wrong_reason':
        data=get(value,prefix+'effect-stop.json');data['reason_code']='deadline';put(value,prefix+'effect-stop.json',data)
    elif change=='parent_cause':
        data=get(value,prefix+'parent-stop.json');data['effect_stop_sha256']='0'*64;put(value,prefix+'parent-stop.json',data)
    elif change=='changed_effect':
        data=get(value,prefix+'neutral.after.json');data['files'][0]['text']='changed';put(value,prefix+'neutral.after.json',data)
    else:
        data=get(value,prefix+'launch.json')
        if change=='unfinished':data['shutdown']['unfinished_control_workers']=1
        elif change=='unreaped':data['shutdown']['child_reaped']=False
        elif change=='exit_bool':data['exit_code']=False
        else:data['exit_code']=0
        put(value,prefix+'launch.json',data)
    with pytest.raises(ValueError):verify(value,fixture['expected'])


@pytest.mark.parametrize('change', ['child_session','wrong_model','parent','terminal_error','error_subtype',
    'denied_tool','denied_input','duplicate_denial','extra_tool','post_terminal','all_denied'])
def test_realistic_optional_frames_do_not_hide_contradictions(fixture, change):
    value=deepcopy(fixture['manifest']);name='traces/settled/transcript.jsonl';data=rows(value,name)
    if change=='child_session':data[2]['session_id']=str(uuid.UUID(int=888))
    elif change=='wrong_model':data[2]['message']['model']='foreign'
    elif change=='parent':data[2]['parent_tool_use_id']='subagent'
    elif change=='terminal_error':data[-1]['error']='failure'
    elif change=='error_subtype':data[-1]['subtype']='error_during_execution'
    elif change=='denied_tool':data[-1]['permission_denials'][0]['tool_name']='Read'
    elif change=='denied_input':data[-1]['permission_denials'][0]['tool_input']={'command':'foreign'}
    elif change=='duplicate_denial':data[-1]['permission_denials'][1]=data[-1]['permission_denials'][0]
    elif change=='extra_tool':data.insert(-1,deepcopy(data[2]))
    elif change=='post_terminal':data.append(deepcopy(data[-2]))
    else:data[4]['message']['content'][0]['is_error']=True
    put_rows(value,name,data)
    with pytest.raises(ValueError):verify(value,fixture['expected'])


@pytest.mark.parametrize('case_id,field,value', [
    ('source_read','numLines',True),('source_read','startLine',1.0),
    ('request_worker_read','content','partial'),('request_worker_read','filePath','/foreign'),
])
def test_observed_read_requires_exact_content_and_typed_ranges(fixture,case_id,field,value):
    changed=deepcopy(fixture['manifest']);name='traces/settled/transcript.jsonl';data=rows(changed,name)
    result=next(x for x in data if x.get('type')=='user' and x['message']['content'][0]['tool_use_id']==case_id)
    result['tool_use_result']['file'][field]=value;put_rows(changed,name,data)
    with pytest.raises(ValueError):verify(changed,fixture['expected'])


@pytest.mark.parametrize('suffix', ['-foreign', '/another-file', '\nadditional text'])
def test_rehashed_write_success_text_must_name_exact_metadata_path(fixture, suffix):
    changed = deepcopy(fixture['manifest'])
    name = 'traces/settled/transcript.jsonl'
    data = rows(changed, name)
    result = next(row for row in data if row.get('type') == 'user'
        and row['message']['content'][0]['tool_use_id'] == 'response_worker_write')
    metadata = deepcopy(result['tool_use_result'])
    block = result['message']['content'][0]
    assert block['content'] == 'File created successfully at: ' + metadata['filePath']
    block['content'] += suffix
    put_rows(changed, name, data)
    # Member hashes are rebuilt, so refusal must come from the exact result
    # join rather than a stale envelope digest or changed native file metadata.
    assert changed['members'][name]['sha256'] == p._sha(changed['members'][name]['text'].encode())
    assert result['tool_use_result'] == metadata
    with pytest.raises(ValueError, match='Write success names another path'):
        verify(changed, fixture['expected'])


@pytest.mark.parametrize('value', [False,0.0,True,'0',None])
def test_supplied_helper_exit_alias_is_not_coerced(fixture,value):
    changed=deepcopy(fixture['manifest']);name='traces/settled/transcript.jsonl';data=rows(changed,name)
    result=next(x for x in data if x.get('type')=='user' and x['message']['content'][0]['tool_use_id']=='stage_receipt')
    result['tool_use_result'].update(exitCode=0,exit_code=value);put_rows(changed,name,data)
    with pytest.raises(ValueError):verify(changed,fixture['expected'])


@pytest.mark.parametrize('change', ['extra_env','different_argv','old_policy','same_root','source_changed','wrong_stub','omitted_case'])
def test_rehashed_launch_sources_and_roster_refuse(fixture,change):
    value=deepcopy(fixture['manifest']);name='traces/settled/launch.json';data=get(value,name)
    if change=='extra_env':data['environment']['BASH_ENV']='/host/file';put(value,name,data)
    elif change=='different_argv':data['argv'].append('--dangerously-skip-permissions');put(value,name,data)
    elif change=='same_root':data['effect_root']=data['stub_root'];put(value,name,data)
    elif change=='old_policy':
        name='traces/settled/control.jsonl';control=rows(value,name);control[0]['policy_sha256']=p._sha(encoded(fixture['expected']['policy']));put_rows(value,name,control)
    elif change=='source_changed':value['members']['source.after']=member('changed\n')
    elif change=='wrong_stub':value['members']['stubs/data_sheets_schema/native_shared_stage.py']=member('raise RuntimeError()\n')
    else:
        data=get(value,'cases.json');data.pop();put(value,'cases.json',data)
    with pytest.raises(ValueError):verify(value,fixture['expected'])


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'"\\ud800"',b'\xff',b'['*65+b'0'+b']'*65])
def test_strict_raw_parser_rejects_ambiguous_unbounded_or_non_utf8(raw):
    with pytest.raises(ValueError):p._json(raw)


@pytest.mark.parametrize('budget', ['0','0.0','1e2','NaN','-1','+1',' 1',1,True,1.0])
def test_budget_spelling_is_not_normalized(fixture,budget):
    expected=deepcopy(fixture['expected']);expected['runtime']['budget_guard_usd']=budget
    with pytest.raises(ValueError):permission_orchestration.probe_argv(expected,expected['policy'])


def test_budget_spelling_and_absent_null_file_map_are_preserved(fixture):
    expected=deepcopy(fixture['expected']);selected=fixture['selection']
    argv = permission_orchestration.probe_argv(expected,expected['policy'])
    assert argv[argv.index('--max-budget-usd')+1]=='01.50'
    for absent in (True,False):
        if absent:expected['policy']['readonly_lookups'].pop('write_paths',None)
        else:expected['policy']['readonly_lookups']['write_paths']=None
        projected=p.projected_policy(expected,selected,'/neutral-stage')
        assert ('write_paths' in projected['readonly_lookups']) is (not absent)
        if not absent:assert projected['readonly_lookups']['write_paths'] is None


def test_unprovable_explicit_write_map_refuses_instead_of_dropping_keys(fixture):
    expected=deepcopy(fixture['expected']);selected=fixture['selection']
    expected['policy']['readonly_lookups']['write_paths']={selected['stage_root']+'/responses/000001.bin':512}
    with pytest.raises(ValueError,match='complete ordinary Write domain'):
        p.projected_policy(expected,selected,'/neutral-stage')


def test_complete_role_projection_and_unsupported_path_refusal(fixture):
    expected=deepcopy(fixture['expected']);selected=fixture['selection'];lookup=expected['policy']['readonly_lookups']
    fixed=[str(Path(selected['stage_root'])/relative) for role,relative in c.ROLE_RELATIVE_PATHS.items() if not role.endswith('_root')]
    original=list(lookup['inputs']);lookup['inputs']+=fixed
    projected=p.projected_policy(expected,selected,'/neutral-stage')
    assert projected['readonly_lookups']['inputs']==original+[path.replace(selected['stage_root'],'/neutral-stage',1) for path in fixed]
    lookup['inputs'].append(selected['stage_root']+'/unregistered.json')
    with pytest.raises(ValueError,match='unknown stage-owned'):
        p.projected_policy(expected,selected,'/neutral-stage')


def test_source_prefix_is_honest_permission_evidence_but_requests_cannot_fragment(fixture):
    value=deepcopy(fixture['manifest']);name='traces/settled/transcript.jsonl';data=rows(value,name)
    result=next(x for x in data if x.get('type')=='user' and x['message']['content'][0]['tool_use_id']=='source_read')
    first=fixture['source_raw'].decode().split('\n')[0]
    result['tool_use_result']['file'].update(content=first,numLines=1)
    result['message']['content'][0]['content']='1\t'+first
    put_rows(value,name,data)
    assert verify(value,fixture['expected'])['passed'] is True
    result=next(x for x in data if x.get('type')=='user' and x['message']['content'][0]['tool_use_id']=='request_receipt_read')
    result['tool_use_result']['file']['numLines']=1
    put_rows(value,name,data)
    with pytest.raises(ValueError,match='exact complete captured range'):
        verify(value,fixture['expected'])


@pytest.mark.parametrize('field,value',[('interrupted',0),('interrupted',1),('error','helper failed')])
def test_supplied_tool_metadata_contradictions_refuse(fixture,field,value):
    changed=deepcopy(fixture['manifest']);name='traces/settled/transcript.jsonl';data=rows(changed,name)
    result=next(x for x in data if x.get('type')=='user' and x['message']['content'][0]['tool_use_id']=='stage_receipt')
    result['tool_use_result'][field]=value;put_rows(changed,name,data)
    with pytest.raises(ValueError):verify(changed,fixture['expected'])


@pytest.mark.parametrize('field,value',[('deadline_seconds',True),('auxiliary_models',['historical-native-fixture-model']),
    ('limits',{'contextWindow':1000,'maxOutputTokens':True}),('model','--unregistered-option')])
def test_expected_runtime_is_the_closed_typed_runtime_contract(fixture,field,value):
    changed=deepcopy(fixture['manifest']);expected=deepcopy(fixture['expected'])
    expected['runtime'][field]=value;changed['binding']=deepcopy(expected)
    with pytest.raises(ValueError):verify(changed,expected)


@pytest.mark.parametrize('field,value',[('DISABLE_TELEMETRY','0'),('D4D_PROFILE','foreign'),('D4D_MANIFEST','/foreign')])
def test_expected_environment_cannot_relax_inherited_fixed_fields(fixture,field,value):
    changed=deepcopy(fixture['manifest']);expected=deepcopy(fixture['expected'])
    expected['permission_environment'][field]=value;changed['binding']=deepcopy(expected)
    with pytest.raises(ValueError):verify(changed,expected)


@pytest.mark.parametrize('module', ['native_shared_effects', 'native_shared_policy'])
def test_loaded_fixed_source_cannot_be_replaced_by_an_advertised_pin(fixture, module):
    changed=deepcopy(fixture['manifest']);expected=deepcopy(fixture['expected'])
    row=next(x for x in expected['production_sources'] if x['module']=='data_sheets_schema.'+module)
    row['sha256']='0'*64
    expected['probe_recipe']=p.recipe(expected);changed['binding']=deepcopy(expected)
    with pytest.raises(ValueError,match='loaded fixed source differs'):
        verify(changed,expected)


def test_recorder_mapping_pins_actual_module_execution_entrypoint(fixture):
    row=next(x for x in fixture['expected']['probe_recipe']['module_map'] if x['module']=='data_sheets_schema.cli')
    actual=Path(p.__file__).parent/'cli/__main__.py'
    assert row['production_sha256']==p._sha(actual.read_bytes())
    expected=deepcopy(fixture['expected'])
    production=next(x for x in expected['production_sources'] if x['module']=='data_sheets_schema.cli.__main__')
    production['module']='data_sheets_schema.cli'
    with pytest.raises(KeyError):p.recipe(expected)


def test_wrapper_encodings_preserve_members_and_exact_metadata_bound(fixture):
    raw=json.dumps(fixture['manifest'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
    assert permission_orchestration.verify_saved_probe(raw,expected=fixture['expected'])['passed'] is True
    with pytest.raises(ValueError,match='canonical JSON'):
        permission_orchestration.verify_saved_probe(json.dumps(fixture['manifest'],indent=2).encode(),expected=fixture['expected'])


def test_member_size_and_aggregate_bounds_precede_parsing_member_content(fixture):
    value=deepcopy(fixture['manifest']['members'])
    value['source.before']=member('x'*(p.MAX_MEMBER+1))
    with pytest.raises(ValueError,match='member size'):
        p._members(value)
    value=deepcopy(fixture['manifest']['members'])
    for name in ('source.before','source.after','traces/settled/transcript.jsonl','traces/settled/control.jsonl'):
        value[name]=member('x'*p.MAX_MEMBER)
    with pytest.raises(ValueError,match='decoded aggregate'):
        p._members(value)


def test_complete_verification_does_not_write_or_open_recorded_paths(fixture,monkeypatch):
    before=encoded(fixture['manifest']);expected_before=encoded(fixture['expected'])
    original_read=Path.read_bytes
    fixed=set(Path(x['path']) for x in fixture['expected']['production_sources'] if Path(x['path']).is_file())
    dependencies = authority.dependency_identity()
    base = dependencies['base']
    fixed.update(composition.ROOT / path for path in base['package_sources'])
    fixed.update(composition.ROOT / row['path'] for row in base['modules'].values())
    fixed.update(composition.ROOT / row['path'] for row in dependencies['additional_modules'].values())
    fixed.add(Path(base['python']))
    fixed = {path.absolute() for path in fixed}
    def read(path,*args,**kwargs):
        # The fixed v2 source roster uses both root-relative and absolute
        # spellings. Admit exactly those files, never arbitrary repo inputs.
        assert path.absolute() in fixed, 'manifest-supplied path opened'
        return original_read(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_bytes',read)
    monkeypatch.setattr(Path,'write_bytes',lambda *a,**k:pytest.fail('verifier wrote bytes'))
    monkeypatch.setattr(Path,'write_text',lambda *a,**k:pytest.fail('verifier wrote text'))
    assert verify(fixture['manifest'],fixture['expected'])['passed']
    assert encoded(fixture['manifest'])==before and encoded(fixture['expected'])==expected_before


def test_four_actual_prescribed_python_module_spellings_only_execute_no_io_stubs(fixture,tmp_path,monkeypatch):
    root=tmp_path/'stubs';root.mkdir()
    for name,text in p.stub_files().items():
        path=root/name.removeprefix('stubs/');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    before={str(path):p._sha(path.read_bytes()) for path in (fixture['root']/'inputs').rglob('*') if path.is_file()}
    assert before
    commands=fixture['expected']['commands'];python=fixture['expected']['policy']['python']
    exact={tuple(shlex.split(command)) for command in commands.values()}
    def allowed_only(argv,*args,**kwargs):
        assert tuple(argv) in exact and argv[0]==python and argv[1]=='-m'
        return _REAL_POPEN(argv,*args,**kwargs)
    monkeypatch.setattr(subprocess,'Popen',allowed_only)
    env={**fixture['expected']['permission_environment'],'PYTHONPATH':str(root),'PYTHONDONTWRITEBYTECODE':'1'}
    for role,command in commands.items():
        argv=shlex.split(command)
        result=subprocess.run(argv,env=env,cwd=fixture['expected']['policy']['readonly_lookups']['repository'],
            capture_output=True,check=True,text=True,timeout=20)
        assert json.loads(result.stdout)=={'d4d_shared_permission_stub':role,'argv':argv[3:]}
        assert result.stderr==''
    assert before=={str(path):p._sha(path.read_bytes()) for path in (fixture['root']/'inputs').rglob('*') if path.is_file()}


def test_recipe_source_capture_preserves_raw_newline_bytes(monkeypatch):
    original=Path.read_bytes
    raw=b'# exact CRLF recipe source\r\n'
    monkeypatch.setattr(Path,'read_bytes',lambda path:raw if path==Path(p.__file__) else original(path))
    assert p.recipe_sources()['recipe/projection.py'].encode()==raw


def test_saved_bash_replay_uses_same_fixed_native_classifier(fixture, monkeypatch):
    targets = {
        ('native_shared_policy', 'classify_bash'): ('command',),
        ('native_shared_policy', 'stage_overlay_governs'): ('tool_name', 'tool_input'),
        ('native_attribution_controller_v2', '_classify'): (),
    }
    with observe_consumer_calls(targets) as observed:
        assert verify(fixture['manifest'], fixture['expected'])['passed'] is True
    assert not any(key == ('native_attribution_controller_v2', '_classify') for key, _ in observed)
    calls = [values['command'] for key, values in observed
             if key == ('native_shared_policy', 'classify_bash')]
    routing = [(values['tool_name'], values['tool_input']) for key, values in observed
               if key == ('native_shared_policy', 'stage_overlay_governs')]
    assert {fixture['expected']['commands'][name] for name in ('draft', 'final_evidence', 'recorder')} <= set(calls)
    assert {tool for tool, _ in routing} == {'Bash', 'Read', 'Write'}
    assert {fixture['expected']['commands'][name] for name in ('stage', 'draft', 'final_evidence', 'recorder')} <= {
        payload['command'] for tool, payload in routing if tool == 'Bash'}
