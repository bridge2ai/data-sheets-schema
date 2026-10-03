"""Ordinary Python TEST executable, never a native CLI or permission probe.

Invoked only by offline tests, using fabricated external authority. Genuine
helpers run over synthetic public text and all control callbacks are real.
"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_attempt_supervisor as neutral
from data_sheets_schema.api_runner import RunSpec


def main():
    attempt = Path(os.environ['CLAUDE_CONFIG_DIR']).parent
    value = draft._json((attempt/'registration.json').read_bytes())
    assert sys.argv[1:] == value['argv'][1:], 'actual dispatch argv differs from registration'
    assert all(os.environ.get(k) == v for k,v in value['environment'].items()), 'actual child environment differs'
    assert not any(k in os.environ for k in ('ANTHROPIC_API_KEY','ANTHROPIC_BASE_URL','CBORG_API_KEY')), 'provider credential/redirect leaked'
    selected = draft._json(value['composition_raw_json'])
    parent = draft._json(selected['registration_raw_json'])
    root = Path(selected['instruction_path']).parent
    fixture = neutral._fixture((root/'fixture.json').read_bytes())
    mode = (root/'test-mode.txt').read_text()
    spec = RunSpec.from_render_spec(parent['render_spec'], project=parent['project'],
                                   method=parent['method'], label=parent['label'])
    steps = neutral.recipe_steps(spec, selected['policy'], fixture)
    if mode != 'no_correction':
        position = next(i for i,s in enumerate(steps) if s['tool']=='Bash'
                        and draft.command_kind(s['input']['command'],spec)=='draft')
        bad = fixture['report'].replace('"attributed_to": ["neutral.txt"]',
                                         '"attributed_to": ["project_documentation"]', 1)
        if bad == fixture['report']:
            raise AssertionError('test correction mutation did not alter the selected source')
        steps[position-1]['input']['content'] = bad
        repair = {'tool':'Write','input':{'file_path':str(spec._agentic_artifact_paths['report']),'content':fixture['report']}}
        if mode == 'protected_correction':
            repair['input']['file_path'] = str(spec._agentic_artifact_paths['full'])
        steps[position+1:position+1] = [repair,steps[position].copy()]
    runtime=value['runtime'];session='43340000-0000-4000-8000-000000000001'
    def send(event):
        print(json.dumps(event,allow_nan=False),flush=True)
    init=draft._json(sys.stdin.readline())
    callback=init['request']['hooks']['PreToolUse'][0]['hookCallbackIds'][0]
    send({'type':'control_response','response':{'subtype':'success','request_id':init['request_id']}})
    draft._json(sys.stdin.readline())
    send({'type':'system','subtype':'init','model':runtime['model'],'apiKeySource':'none',
          'claude_code_version':runtime['executable']['init_version'],
          'tools':['Read','Write','Bash'],'session_id':session,'cwd':os.getcwd()})
    for number,step in enumerate(steps):
        identity='native-test-'+str(number);tool=step['tool'];inputs=step['input']
        send({'type':'assistant','session_id':session,'message':{'content':[
            {'type':'tool_use','id':identity,'name':tool,'input':inputs}]}})
        request_id='callback-'+identity
        send({'type':'control_request','request_id':request_id,'request':{'subtype':'hook_callback',
            'callback_id':callback,'input':{'hook_event_name':'PreToolUse','tool_name':tool,
            'tool_use_id':identity,'cwd':os.getcwd(),'tool_input':inputs,'effort':runtime['effort']}}})
        line=sys.stdin.readline()
        if not line:return 7
        response=draft._json(line).get('response',{})
        if response.get('request_id')!=request_id or response.get('response')!={}:return 8
        if tool=='Write':
            Path(inputs['file_path']).write_text(inputs['content'])
            code,text=0,'{}'
        elif tool=='Read':code,text=0,Path(inputs['file_path']).read_text()
        else:
            proc=subprocess.run(shlex.split(inputs['command']),capture_output=True,text=True,timeout=150)
            code,text=proc.returncode,proc.stdout
            if proc.stderr:print(proc.stderr,file=sys.stderr,flush=True)
        metadata={'exitCode':code,'stdout':text}
        if mode=='contradictory_exit' and tool=='Bash' and draft.command_kind(inputs['command'],spec)=='draft':
            metadata['exit_code']=not bool(code)
        send({'type':'user','session_id':session,'tool_use_result':metadata,'message':{'content':[
            {'type':'tool_result','tool_use_id':identity,'is_error':code!=0,'content':text}]}})
        if code and not (tool=='Bash' and draft.command_kind(inputs['command'],spec)=='draft' and code==1):
            return code
    usage={'input_tokens':10,'output_tokens':2,'cache_read_input_tokens':0,'cache_creation_input_tokens':0}
    own={'inputTokens':10,'outputTokens':2,'cacheReadInputTokens':0,'cacheCreationInputTokens':0,**runtime['limits']}
    if mode=='unknown_usage':usage['input_tokens']=None
    send({'type':'result','session_id':session,'is_error':False,'terminal_reason':'completed','stop_reason':'end_turn',
          'usage':usage,'modelUsage':{runtime['model']:own},'total_cost_usd':0,'permission_denials':[]})
    return 0


if __name__=='__main__':raise SystemExit(main())
