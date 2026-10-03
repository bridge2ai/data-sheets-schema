"""Fabricated evidence for verifier software tests, NEVER real native permission.

All observation claims below are invented test inputs. Only the three ordinary
Python no-I/O stubs execute; no native/auth/provider executable is called.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

from data_sheets_schema import native_execution_permissions as permission
from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attribution_registration as draft
from tests.test_native_attempt_supervisor import make_case


def member(text):
    return {'text': text, 'sha256': draft._sha(text.encode())}


def change_member(value, name, text):
    value['members'][name] = member(text)


def jsonlines(rows):
    return ''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows)


@pytest.fixture(scope='module')
def fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp('fabricated-permission-data')
    case = make_case(root/'selected')
    selected = draft._json(Path(case['value']['composition']).read_bytes())
    commands = draft._commands(case['spec'])
    runtime = {'route':'claude_code_direct_stream_json_v1',
        'executable':{'path':'/fictional/claude','sha256':'a'*64,'version':'fictional test version', 'init_version':'test-only'},
        'model':'synthetic-test-model','effort':'synthetic-test-effort','budget_guard_usd':1}
    expected = {'runtime':runtime, 'policy':selected['policy'],
        'commands':{'draft':next(c for c,k in commands.items() if k=='draft'),
                    'final_evidence':next(c for c,k in commands.items() if k=='final_evidence'),
                    'recorder':selected['policy']['post_final_recorder']['command']},
        'source':{'path':str(case['spec'].bundle),'sha256':draft._sha(case['spec'].bundle.read_bytes())},
        'permission_environment':{'PATH':str(Path(sys.executable).parent)+os.pathsep+'/usr/bin:/bin',
            'PYTHONDONTWRITEBYTECODE':'1','LANG':'en_US.UTF-8',
            'CLAUDE_CONFIG_DIR':str(root/'future-config'), 'PYTHONPATH':str(composition.ROOT/'src'),
            'D4D_LAUNCH_INSTRUCTION':selected['instruction_path']},
        'controller_sources':selected['controller_sources'],
        'instruction_sha256':selected['instruction_sha256'],'system_sha256':'b'*64}
    return {'root':root, **fabricated_manifest(expected, root/'separate-probe', case['spec'].bundle.read_bytes())}


def fabricated_manifest(expected, neutral, source_raw):
    """Test-only forged observation; never serialize/use as real launch authority."""
    runtime = expected['runtime']
    neutral = Path(neutral); neutral.mkdir()
    config, stubs = str(neutral/'config'), str(neutral/'stubs')
    provider = 'http://127.0.0.1:12345'
    source = source_raw.decode('utf-8')
    provider_source = '# Fabricated test provider evidence; this file is never executed.\n'
    launch = {'cwd':expected['policy']['readonly_lookups']['repository'], 'argv':permission.probe_argv(expected),
        'environment':{**expected['permission_environment'],'CLAUDE_CONFIG_DIR':config,'PYTHONPATH':stubs,
                       'ANTHROPIC_BASE_URL':provider,'ANTHROPIC_API_KEY':'d4d-local-permission-probe-token'},
        'config_root':config,'stub_root':stubs,'provider_url':provider,
        'provider_source_sha256':draft._sha(provider_source.encode()),'exit_code':0,
        'shutdown':{'control_initialized':True,'control_shutdown_complete':True,'unfinished_control_workers':0},
        'executable':runtime['executable']}
    controls = composition.load_controls(); native = controls['native_control']
    cases = permission.probe_cases(expected)
    classifications = permission._authority(expected, controls)
    ack = {'type':'control_response','response':{'subtype':'success','request_id':native.INIT_ID}}
    session = 'dc2de951-0f4c-4fd3-9e69-4e66285533a1'
    events = [ack, {'type':'system','subtype':'init','model':runtime['model'],
        'claude_code_version':runtime['executable']['init_version'],'apiKeySource':'ANTHROPIC_API_KEY',
        'tools':['Read','Write','Bash'],'cwd':launch['cwd'],'session_id':session}]
    records = [{'kind':'initialize_sent','policy_sha256':native.digest(expected['policy']),
                'frame':native.initialize_frame(expected['policy']['pretool_control'])},
               {'kind':'initialize_ack','frame':ack}]
    for case_row in cases:
        identity = case_row['id']; kind, reason = classifications[identity]
        block = {'type':'tool_use','id':identity,'name':case_row['tool'],'input':case_row['input']}
        call = {'type':'assistant','session_id':session,'message':{'id':identity,'content':[block]}}
        callback = {'type':'control_request','request_id':'callback-'+identity,'request':{'subtype':'hook_callback',
            'callback_id':expected['policy']['pretool_control']['callback_id'],'input':{'hook_event_name':'PreToolUse',
            'tool_name':case_row['tool'],'tool_use_id':identity,'cwd':launch['cwd'],'tool_input':case_row['input']}}}
        if case_row['allow'] and case_row['tool']=='Bash':
            content = json.dumps({'d4d_permission_stub':identity,'argv':shlex.split(case_row['input']['command'])[3:]})
            metadata = {'exitCode':0,'stdout':content}
        elif case_row['allow']:
            content, metadata = source, {}
        else:
            content, metadata = 'Outside the registered tool policy: '+reason, {}
        result = {'type':'user','session_id':session,'tool_use_result':metadata,
            'message':{'content':[{'type':'tool_result','tool_use_id':identity,'is_error':not case_row['allow'],'content':content}]}}
        events += [call,callback,result]
        records.append({'kind':'decision','request':callback,'classification':kind,'basis':reason,
            'response':{'type':'control_response','response':{'subtype':'success','request_id':'callback-'+identity,
                        'response':native.hook_output(kind,reason)}}})
    events.append({'type':'result','is_error':False,'terminal_reason':'completed','stop_reason':'end_turn',
                   'permission_denials':[{'tool_use_id':r['id']} for r in cases if not r['allow']]})
    files = {'policy.json':json.dumps(expected['policy']), 'cases.json':json.dumps(cases), 'launch.json':json.dumps(launch),
        'config.json':'{}','source.before':source,'source.after':source,'version.txt':runtime['executable']['version']+'\n',
        'transcript.jsonl':jsonlines(events),'control.jsonl':jsonlines(records),'provider.py':provider_source,
        **permission.stub_files()}
    value = {'kind':permission.KIND,'version':1,'origin':permission.ORIGIN,'binding':expected,
             'members':{name:member(text) for name,text in files.items()}}
    return {'expected':expected,'manifest':value,'events':events,'records':records,'launch':launch}


def test_complete_fabricated_record_is_checked_without_claiming_authentication(fixture):
    raw = draft._encoded(fixture['manifest'])
    result = permission.verify_saved_probe(raw, expected=fixture['expected'])
    assert result['checked'] is result['passed'] is True
    assert len(result['cases']) == 7
    assert result['manifest_sha256'] == draft._sha(raw)
    assert 'observation authenticity' in result['unassessed']
    assert 'current authentication' in result['unassessed']
    assert 'helper execution was stubbed' in result['basis']


def test_actual_three_selected_commands_run_only_fixed_stubs(fixture):
    """Usability proof: keep exact selected absolute arguments/cwd, no native CLI."""
    launch, expected = fixture['launch'], fixture['expected']
    stubs = Path(launch['stub_root']); stubs.mkdir()
    for name, text in permission.stub_files().items():
        target = stubs/name; target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
    before = {str(p):draft._sha(p.read_bytes()) for p in fixture['root'].rglob('*') if p.is_file()}
    for role, command in expected['commands'].items():
        process = subprocess.run(shlex.split(command),cwd=launch['cwd'],env=launch['environment'],
                                 capture_output=True,text=True,timeout=20)
        assert process.returncode == 0, process.stderr
        assert json.loads(process.stdout) == {'d4d_permission_stub':role,'argv':shlex.split(command)[3:]}
    after = {str(p):draft._sha(p.read_bytes()) for p in fixture['root'].rglob('*') if p.is_file()}
    assert after == before
    assert not list((fixture['root']/'selected/corpus').glob('data/**/EXAMPLE_d4d*'))


@pytest.mark.parametrize('change', ['summary','mock','origin_missing','version_bool','missing_member','member_hash',
    'changed_source','changed_policy','case_drop','case_duplicate','case_order','case_extra','stub_changed',
    'callback_drop','result_drop','result_duplicate','post_terminal','cancel','init_version','init_model','init_cwd',
    'control_policy','control_decision','control_drop','control_callback','terminal_error','terminal_missing',
    'all_denied','denial_omitted','exit_bool','exit_float','stdout_typed','missing_exit','pending','extra_tool',
    'binary','env_override','provider_remote','config_populated','argv_weakened','shutdown','process_exit',
    'authority_drift','closure_drift','unterminated','blank_line','denied_stdout','init_permission'])
def test_required_authority_and_raw_evidence_cannot_be_replaced_by_summary(fixture, change):
    value=deepcopy(fixture['manifest']); expected=deepcopy(fixture['expected'])
    events=deepcopy(fixture['events']); records=deepcopy(fixture['records']); launch=deepcopy(fixture['launch'])
    if change=='summary':value={'passed':True}
    elif change=='mock':value['origin']='ordinary_python_fake_cli'
    elif change=='origin_missing':del value['origin']
    elif change=='version_bool':value['version']=True
    elif change=='missing_member':del value['members']['control.jsonl']
    elif change=='member_hash':value['members']['source.before']['sha256']='f'*64
    elif change=='changed_source':change_member(value,'source.after','modified source')
    elif change=='changed_policy':change_member(value,'policy.json','{}')
    elif change.startswith('case_'):
        rows=permission.probe_cases(expected)
        if change=='case_drop':rows.pop()
        elif change=='case_duplicate':rows[-1]=rows[0]
        elif change=='case_order':rows.reverse()
        else:rows.append(deepcopy(rows[0]))
        change_member(value,'cases.json',json.dumps(rows))
    elif change=='stub_changed':change_member(value,'data_sheets_schema/cli.py','print("fake")\n')
    elif change=='callback_drop':events.pop(3)
    elif change=='result_drop':events.pop(4)
    elif change=='result_duplicate':events.insert(5,deepcopy(events[4]))
    elif change=='post_terminal':events.append(deepcopy(events[2]))
    elif change=='cancel':events[3]['type']='control_cancel_request'
    elif change=='init_version':events[1]['claude_code_version']='stale'
    elif change=='init_model':events[1]['model']='foreign'
    elif change=='init_cwd':events[1]['cwd']='/wrong'
    elif change=='init_permission':events[1]['permissionMode']='bypassPermissions'
    elif change=='control_policy':records[0]['policy_sha256']='f'*64
    elif change=='control_decision':records[2]['response']['response']['response']={'allow':True}
    elif change=='control_drop':records.pop()
    elif change=='control_callback':records[2]['request']['request_id']='different'
    elif change=='terminal_error':events[-1]['is_error']=True
    elif change=='terminal_missing':events.pop()
    elif change=='all_denied':
        for e in events:
            if e.get('type')=='user':e['message']['content'][0]['is_error']=True
    elif change=='denial_omitted':events[-1]['permission_denials'].pop()
    elif change=='exit_bool':events[4]['tool_use_result']['exit_code']=False
    elif change=='exit_float':events[4]['tool_use_result']['exit_code']=0.0
    elif change=='stdout_typed':
        events[4]['tool_use_result']['stdout']='{"d4d_permission_stub":true,"argv":[]}'
    elif change=='denied_stdout':events[16]['tool_use_result']['stdout']='{"d4d_permission_stub":"executed"}'
    elif change=='missing_exit':del events[4]['tool_use_result']['exitCode']
    elif change=='pending':events[4]['tool_use_result']['backgroundTaskId']='pending'
    elif change=='extra_tool':events[2]['message']['content'].append(deepcopy(events[2]['message']['content'][0]))
    elif change=='binary':launch['executable']['sha256']='f'*64
    elif change=='env_override':launch['environment']['LD_PRELOAD']='/foreign.so'
    elif change=='provider_remote':launch['provider_url']='https://remote.invalid'
    elif change=='config_populated':change_member(value,'config.json','{"permissions":{"allow":["Bash"]}}')
    elif change=='argv_weakened':launch['argv'].remove('--restricted')
    elif change=='shutdown':launch['shutdown']['unfinished_control_workers']=True
    elif change=='process_exit':launch['exit_code']=False
    elif change=='authority_drift':expected['runtime']['effort']='changed'
    elif change=='closure_drift':expected['controller_sources']['version']=False
    if change not in {'summary','missing_member'}:
        change_member(value,'transcript.jsonl',jsonlines(events))
        change_member(value,'control.jsonl',jsonlines(records))
        change_member(value,'launch.json',json.dumps(launch))
    if change=='unterminated':change_member(value,'transcript.jsonl',jsonlines(events).rstrip('\n'))
    if change=='blank_line':change_member(value,'transcript.jsonl',jsonlines(events)+'\n')
    with pytest.raises(ValueError):permission.verify_saved_probe(draft._encoded(value),expected=expected)


def test_path_rewrite_and_nonmodule_helpers_are_explicitly_unsupported(fixture):
    for role in permission.MODULES:
        expected=deepcopy(fixture['expected']); expected['commands'][role]='/absolute/helper.py --run'
        with pytest.raises(ValueError):permission.verify_saved_probe(draft._encoded(fixture['manifest']),expected=expected)


def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(fixture):
    for raw in (b'{"kind":1,"kind":2}',b'{"value":NaN}',b'{"value":Infinity}'):
        with pytest.raises(ValueError):permission.verify_saved_probe(raw,expected=fixture['expected'])
