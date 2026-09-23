"""Pinned native CLI, synthetic HTTP200 partial-tool timeout, no provider (#2304).
Every price/count is synthetic; verifies retry preserves conversation and causes
exactly one Read/Write/Bash action. All retained transcripts are invented fixtures.
"""
from pathlib import Path
import hashlib, json, os, subprocess, sys, tempfile
from types import SimpleNamespace
import httpx

from budgeted_cborg import Ledger, STALL_DEBIT_BASIS
from native_proxy import NativeProxy
from run_native_canary import execute_child, verified_executable, sha

PYTHON = sys.executable
CLI = str(Path(os.environ.get('D4D_PROBE_CLI', Path.home() / '.local/share/claude/versions/2.1.272')).resolve(strict=True))
CLI_SHA = '195e24e8e1f9bf46f1eaee72d434a33e18f9f5796f29a6348a00d16c5f8aee75'
overlay = {'claude_executable': CLI, 'pinned_files': {CLI: CLI_SHA}}
PRICES = {"input": 0.000005, "output": 0.000025, "cache_read": 0.0000005, "cache_write": 0.00000625}
root = Path(tempfile.mkdtemp(prefix='d4d-native-buffered-stall-')).resolve()
work = root / 'work'; work.mkdir()
(work / 'input.txt').write_text('Synthetic offline stall probe. No dataset facts.\n')
(work / 'probe.py').write_text('from pathlib import Path\np=Path("executions.txt")\np.write_text((p.read_text() if p.exists() else "")+"once\\n")\nprint("OFFLINE_HELPER_OK")\n')
calls, faults = [], []


def respond(req):
    body = json.loads(req.content); calls.append(body)
    tooled = [v for v in calls if v.get('tools')]
    # A stall repeats the same conversation, so count distinct conversations.
    n = len({json.dumps(v['messages'], sort_keys=True) for v in tooled})
    key = json.dumps(body['messages'], sort_keys=True)
    if not body.get('tools'):
        block = {'type': 'text', 'text': 'Offline stall probe'}
    elif n == 1:
        block = {'type': 'tool_use', 'id': 'offline_read', 'name': 'Read', 'input': {'file_path': str(work / 'input.txt')}}
    elif n == 2:
        block = {'type': 'tool_use', 'id': 'offline_write', 'name': 'Write',
                 'input': {'file_path': str(work / 'output.txt'), 'content': 'OFFLINE_WRITE_OK\n'}}
    elif n == 3:
        block = {'type': 'tool_use', 'id': 'offline_bash', 'name': 'Bash',
                 'input': {'command': f'{PYTHON} probe.py', 'description': 'Run the offline synthetic helper'}}
    else:
        block = {'type': 'text', 'text': 'OFFLINE_COMPLETE'}
    start = dict(block)
    start['input' if block['type'] == 'tool_use' else 'text'] = {} if block['type'] == 'tool_use' else ''
    delta = ({'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])} if block['type'] == 'tool_use'
             else {'type': 'text_delta', 'text': block['text']})
    values = [{'type': 'message_start', 'message': {'id': f'offline_{len(calls)}', 'type': 'message', 'role': 'assistant',
               'model': body['model'], 'content': [], 'stop_reason': None, 'stop_sequence': None,
               'usage': {'input_tokens': 100, 'output_tokens': 0}}},
              {'type': 'content_block_start', 'index': 0, 'content_block': start},
              {'type': 'content_block_delta', 'index': 0, 'delta': delta},
              {'type': 'content_block_stop', 'index': 0},
              {'type': 'message_delta', 'delta': {'stop_reason': 'tool_use' if block['type'] == 'tool_use' else 'end_turn',
               'stop_sequence': None}, 'usage': {'output_tokens': 12}},
              {'type': 'message_stop'}]
    raw = ''.join(f"event: {v['type']}\ndata: {json.dumps(v)}\n\n" for v in values).encode()
    if body.get('tools') and n == 2 and key not in faults:
        faults.append(key)
        partial = raw.split(b'event: message_delta')[0]
        class Cut(httpx.SyncByteStream):
            def __iter__(self):
                yield partial
                raise httpx.ReadTimeout('synthetic partial-tool response', request=req)
        return httpx.Response(200, stream=Cut(), headers={'content-type':'text/event-stream'})
    return httpx.Response(200, content=raw, headers={'content-type': 'text/event-stream'})


counts = {'tries': 0}
def count_tokens(**kw):
    counts['tries'] += 1
    if counts['tries'] == 2:                      # one free counting failure as well
        import anthropic
        raise anthropic.APITimeoutError(request=httpx.Request('POST', 'https://offline.invalid/count'))
    return SimpleNamespace(input_tokens=100)


sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=count_tokens))
ledger = Ledger(root / 'ledger.json', manifest_sha256='offline-stall-probe')
proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt='offline', evidence=root / 'requests', model='claude-opus-5',
                    prices=PRICES, verify=lambda: None, provider_key='offline-fake-provider-key',
                    base_url='https://api.cborg.lbl.gov', upstream=httpx.Client(transport=httpx.MockTransport(respond)),
                    stall_policy={'count_attempts': 3, 'max_stall_debits': 4}, count_pause=lambda seconds: None,
                    response_buffer={'kind':'complete_response_v1','max_bytes':16777216,'total_seconds':1200})
env = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM'}}
config = root / 'config'; config.mkdir()
env.update(CLAUDE_CONFIG_DIR=str(config), DISABLE_NON_ESSENTIAL_MODEL_CALLS='1', DISABLE_TELEMETRY='1',
           CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS='1', ANTHROPIC_API_KEY=proxy.token)
with proxy.running() as url:
    env['ANTHROPIC_BASE_URL'] = url
    args = [CLI, '--print', '--safe-mode', '--restricted', '--strict-mcp-config', '--no-session-persistence',
            '--model', 'claude-opus-5', '--name', 'd4d-offline-stall', '--disable-slash-commands',
            '--max-budget-usd', '5', '--prompt-suggestions', 'false', '--output-format', 'stream-json', '--verbose',
            '--permission-mode', 'dontAsk', '--tools', 'Read,Write,Bash', '--allowedTools', 'Read', 'Write',
            f'Bash({PYTHON} probe.py)', '--system-prompt',
            'Synthetic offline stall probe. Read input.txt, write output.txt, run the provided probe.py and finish. '
            'Do not access other files or networks.']
    instruction = root / 'instruction.txt'; instruction.write_text('Perform the synthetic offline stall probe.')
    code = execute_child(args, proxy=proxy, instruction=instruction, attempt=root, cwd=work, env=env,
                         deadline_seconds=180, verify_launch=lambda: verified_executable(overlay))
rows = json.loads(ledger.path.read_bytes())['requests']
terminal = [json.loads(line) for line in (root / 'transcript.jsonl').read_text().splitlines()
            if line.strip().startswith('{') and '"type":"result"' in line.replace(' ', '')]
records=[json.loads(line) for line in (root/'transcript.jsonl').read_text().splitlines() if line.strip().startswith('{')]
tool_counts={name:0 for name in ('Read','Write','Bash')}
for event in records:
    for block in event.get('message',{}).get('content',[]):
        if block.get('type')=='tool_use' and block.get('name') in tool_counts:
            tool_counts[block['name']]+=1
assert code==0 and proxy.failure is None and len(faults)==1
repeated=[body for body in calls if body.get('tools') and json.dumps(body['messages'],sort_keys=True)==faults[0]]
assert len(repeated)==2 and repeated[0]==repeated[1]
request_digest=hashlib.sha256((json.dumps(repeated[0],sort_keys=True,ensure_ascii=False)+'\n').encode()).hexdigest()
repeated_rows=[row for row in rows if row['request_sha256']==request_digest]
assert len(repeated_rows)==2 and repeated_rows[0].get('settlement_basis')==STALL_DEBIT_BASIS
assert repeated_rows[1].get('settlement_basis') is None
assert tool_counts=={'Read':1,'Write':1,'Bash':1}, tool_counts
assert (work/'executions.txt').read_text()=='once\n'
assert sum(row.get('settlement_basis')==STALL_DEBIT_BASIS for row in rows)==1
assert all(row['status']=='settled' for row in rows)
debit = next(row for row in rows if row.get('settlement_basis')==STALL_DEBIT_BASIS)
assert debit['cost_usd']==debit['reserved_usd'] and debit['provider_charge_confirmed'] is False
value = {'kind':'synthetic_native_buffered_retry_probe_v1', 'native_executable_sha256': CLI_SHA,
         'repository_commit':subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[3]),'rev-parse','HEAD'],text=True).strip(),
         'source_sha256':{'probe':sha(__file__),
                         'proxy':sha(sys.modules[NativeProxy.__module__].__file__),
                         'native_controller':sha(sys.modules[execute_child.__module__].__file__)},
         'exit_code': code, 'proxy_failure': proxy.failure,
         'scripted_upstream_calls': len(calls), 'scripted_partial_response_faults': len(faults),
         'same_conversation_retry_requests':len(repeated), 'repeated_request_digests_match':True,
         'count_tries': counts['tries'], 'count_retries': proxy.messages.count_retries,
         'stalls_survived': proxy.stalls_survived,
         'ledger_rows': len(rows), 'unsettled_rows': sum(row['status'] != 'settled' for row in rows),
         'stall_debit_rows': sum(row.get('settlement_basis') == STALL_DEBIT_BASIS for row in rows),
         'synthetic_stall_reservation_usd':debit['reserved_usd'], 'synthetic_stall_debit_usd':debit['cost_usd'],
         'output_created': (work / 'output.txt').exists(), 'tool_action_counts':tool_counts,
         'provider_calls':0, 'scope':'synthetic native client retry only; absolute transport deadline is tested separately',
         'terminal_result': ({k: terminal[-1].get(k) for k in ('is_error', 'terminal_reason', 'stop_reason', 'num_turns')}
                             if terminal else None),
         'unfinished_handlers': proxy.unfinished_handlers, 'real_provider_requests': 0}
(root / 'result.json').write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps(value, indent=2))
