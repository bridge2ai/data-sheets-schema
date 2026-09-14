"""Real CLI with scripted fake responses; no external provider is contacted."""
from pathlib import Path
import hashlib, json, os, subprocess, tempfile
from types import SimpleNamespace
import httpx

from budgeted_cborg import Ledger
from native_proxy import NativeProxy

PYTHON='/Users/marcin/Library/Caches/pypoetry/virtualenvs/data-sheets-schema-KeX3bMFJ-py3.13/bin/python'
CLI='/Users/marcin/.local/bin/claude'
PRICES={"input":0.000005,"output":0.000025,"cache_read":0.0000005,"cache_write":0.00000625}
root=Path(tempfile.mkdtemp(prefix='d4d-native-offline-')).resolve()
work=root/'work';work.mkdir()
(work/'input.txt').write_text('Synthetic offline capability probe. No dataset facts.\n')
(work/'probe.py').write_text('print("OFFLINE_HELPER_OK")\n')
calls=[]
def respond(req):
    body=json.loads(req.content);calls.append(body)
    n=sum(bool(v.get('tools')) for v in calls)
    if not body.get('tools'):
        block={'type':'text','text':'Offline capability probe'}
    elif n==1:
        block={'type':'tool_use','id':'offline_read','name':'Read','input':{'file_path':str(work/'input.txt')}}
    elif n==2:
        block={'type':'tool_use','id':'offline_write','name':'Write','input':{'file_path':str(work/'output.txt'),'content':'OFFLINE_WRITE_OK\n'}}
    elif n==3:
        block={'type':'tool_use','id':'offline_bash','name':'Bash','input':{'command':f'{PYTHON} probe.py','description':'Run the offline synthetic helper'}}
    else:
        block={'type':'text','text':'OFFLINE_COMPLETE'}
    start=dict(block)
    start['input' if block['type']=='tool_use' else 'text']={} if block['type']=='tool_use' else ''
    delta={'type':'input_json_delta','partial_json':json.dumps(block['input'])} if block['type']=='tool_use' else {'type':'text_delta','text':block['text']}
    values=[{'type':'message_start','message':{'id':f'offline_{n}','type':'message','role':'assistant','model':body['model'],'content':[],'stop_reason':None,'stop_sequence':None,'usage':{'input_tokens':100,'output_tokens':0}}},
       {'type':'content_block_start','index':0,'content_block':start},
       {'type':'content_block_delta','index':0,'delta':delta},
       {'type':'content_block_stop','index':0},
       {'type':'message_delta','delta':{'stop_reason':'tool_use' if block['type']=='tool_use' else 'end_turn','stop_sequence':None},'usage':{'output_tokens':12}},
       {'type':'message_stop'}]
    raw=''.join(f"event: {v['type']}\ndata: {json.dumps(v)}\n\n" for v in values).encode()
    return httpx.Response(200,content=raw,headers={'content-type':'text/event-stream'})
sdk=SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw:SimpleNamespace(input_tokens=100)))
ledger=Ledger(root/'ledger.json',manifest_sha256='offline-cli-probe')
proxy=NativeProxy(sdk=sdk,ledger=ledger,attempt='offline',evidence=root/'requests',model='claude-opus-5',prices=PRICES,verify=lambda:None,provider_key='offline-fake-provider-key',base_url='https://api.cborg.lbl.gov',upstream=httpx.Client(transport=httpx.MockTransport(respond)))
env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','SHELL','TMPDIR','LANG','LC_ALL','TERM'}}
config=root/'config';config.mkdir()
env.update(CLAUDE_CONFIG_DIR=str(config),DISABLE_NON_ESSENTIAL_MODEL_CALLS='1',DISABLE_TELEMETRY='1',CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS='1',ANTHROPIC_API_KEY=proxy.token)
with proxy.running() as url:
    env['ANTHROPIC_BASE_URL']=url
    args=[CLI,'--print','--safe-mode','--restricted','--strict-mcp-config','--no-session-persistence','--model','claude-opus-5','--name','d4d-offline-capability','--disable-slash-commands','--max-budget-usd','5','--prompt-suggestions','false','--output-format','stream-json','--verbose','--permission-mode','dontAsk','--tools','Read,Write,Bash','--allowedTools','Read','Write',f'Bash({PYTHON} probe.py)','--system-prompt','Synthetic offline capability probe. Read input.txt, write output.txt, run the provided probe.py and finish. Do not access other files or networks.']
    with (root/'transcript.jsonl').open('w') as out,(root/'stderr.txt').open('w') as err:
        proc=subprocess.run(args,input='Perform the synthetic offline capability probe.',text=True,cwd=work,env=env,stdout=out,stderr=err,timeout=60)
value={'root':str(root),'exit_code':proc.returncode,'scripted_requests':len(calls),'proxy_failure':proxy.failure,'output_created':(work/'output.txt').exists(),'real_provider_requests':0}
(root/'result.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value,indent=2))
