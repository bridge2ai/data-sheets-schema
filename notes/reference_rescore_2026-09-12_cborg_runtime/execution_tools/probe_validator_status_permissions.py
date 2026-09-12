from pathlib import Path
import json,os,sys,subprocess,tempfile,threading,shutil
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import reference_rescore_cborg as c
state={}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers.get('content-length','0'))))
  if 'count_tokens' in self.path:
   payload=json.dumps({'input_tokens':10}).encode(); self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
  state['requests']+=1
  for m in body.get('messages',[]):
   if not isinstance(m.get('content'),list):continue
   for b in m['content']:
    if b.get('type')=='tool_result' :state['result']={k:b.get(k) for k in ('is_error','content')}
  state.setdefault('request_shapes',[]).append({'path':self.path,'tools':[t.get('name') for t in body.get('tools',[])],'stream':body.get('stream'),'max_tokens':body.get('max_tokens')})
  first=any(t.get('name')=='Bash' for t in body.get('tools',[])) and not state.get('injected')
  if first:state['injected']=True
  message={'id':'msg_probe_'+str(state['requests']),'type':'message','role':'assistant','model':'claude-opus-5','content':[],'stop_reason':None,'stop_sequence':None,'usage':{'input_tokens':10,'output_tokens':0,'cache_creation_input_tokens':0,'cache_read_input_tokens':0}}
  events=[('message_start',{'type':'message_start','message':message})]
  block={'type':'tool_use','id':'toolu_probe_1','name':'Bash','input':{}} if first else {'type':'text','text':''}
  delta={'type':'input_json_delta','partial_json':json.dumps({'command':state['command'],'description':'Synthetic offline permission probe'})} if first else {'type':'text_delta','text':'Offline permission probe complete.'}
  events += [('content_block_start',{'type':'content_block_start','index':0,'content_block':block}),('content_block_delta',{'type':'content_block_delta','index':0,'delta':delta}),('content_block_stop',{'type':'content_block_stop','index':0}),('message_delta',{'type':'message_delta','delta':{'stop_reason':'tool_use' if first else 'end_turn','stop_sequence':None},'usage':{'output_tokens':20}}),('message_stop',{'type':'message_stop'})]
  payload=''.join('event: '+kind+'\ndata: '+json.dumps(event)+'\n\n' for kind,event in events).encode()
  self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
canonical='poetry run python scripts/validate_evaluation_schema.py --file output_evaluation.json --rubric rubric20-semantic'
rules=['Bash(echo "EXIT=$?")','Bash(echo "exit=$?")']
cases=[('canonical',canonical,False),('old_compound',canonical+'; echo "EXIT=$?"',False),('status_exact',canonical+'; echo "EXIT=$?"',True),('status_lowercase',canonical+'; echo "exit=$?"',True),('unrelated_environment','echo "$CBORG_API_KEY"',True),('extra_mutation',canonical+'; echo "EXIT=$?"; touch forbidden',True)]
results=[]
try:
 for name,command,extended in cases:
  state.clear();state.update(requests=0,command=command)
  with tempfile.TemporaryDirectory(prefix='d4d-status-offline-') as temp:
   cwd=Path(temp);(cwd/'scripts').mkdir();(cwd/'scripts/validate_evaluation_schema.py').write_text("print('VALID output_evaluation.json: rubric20-semantic')\n")
   for file in ('pyproject.toml','poetry.lock'):shutil.copyfile(ROOT/file,cwd/file)
   env=c.cborg_environment({**os.environ,'CBORG_API_KEY':'offline-probe-key'})
   env.update(ANTHROPIC_BASE_URL=f'http://127.0.0.1:{server.server_port}',CLAUDE_CONFIG_DIR=str(cwd/'config'),DISABLE_AUTOUPDATER='1')
   args=['/private/tmp/d4d-cborg-pinned-bin/claude','--print','--safe-mode','--restricted','--no-session-persistence','--model','claude-opus-5[1m]','--max-budget-usd','5','--output-format','stream-json','--verbose','--permission-mode','dontAsk','--tools','Bash','--allowedTools','Bash(poetry run python scripts/validate_evaluation_schema.py:*)',*(rules if extended else []),'--system-prompt','Synthetic offline tool-permission probe; no evaluation task or real record.']
   done=subprocess.run(args,input='Run the synthetic permission probe.',text=True,env=env,cwd=cwd,capture_output=True,timeout=45)
   events=[]
   for line in done.stdout.splitlines():
    try:events.append(json.loads(line))
    except ValueError:pass
   tool_results=[block for event in events if isinstance(event.get('message'),dict) and isinstance(event['message'].get('content'),list) for block in event['message']['content'] if isinstance(block,dict) and block.get('type')=='tool_result']
   if tool_results:state['result']={k:tool_results[-1].get(k) for k in ('is_error','content')}
   # Full synthetic traces stay in private scratch; only scoped results are published.
   Path('/private/tmp/d4d-status-probe-'+name+'.jsonl').write_text(done.stdout)
   row={'case':name,'extended':extended,'exit_code':done.returncode,'local_requests':state['requests'],'request_shapes':state.get('request_shapes'),'tool_result':state.get('result'),'forbidden_file_exists':(cwd/'forbidden').exists(),'provider_calls':0}
   expected=name in {'canonical','status_exact','status_lowercase'}
   assert row['tool_result'] is not None and (row['tool_result']['is_error'] is False)==expected,name
   assert not row['forbidden_file_exists'],name
   print(json.dumps(row),flush=True);results.append(row)
finally:server.shutdown();server.server_close()
Path('/private/tmp/d4d-cborg-status-permission-probe.json').write_text(json.dumps({'probe':'Scripted local SSE endpoint, synthetic credentials and validator, no real records or provider calls. Headers and full request context were not recorded.','cases':results},indent=2)+'\n')
