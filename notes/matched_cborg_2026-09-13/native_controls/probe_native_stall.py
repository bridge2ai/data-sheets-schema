"""Real pinned CLI against a scripted upstream that stalls; no provider is contacted (#2150).

The scripted upstream answers one paid request with HTTP 524 and lets another
time out before any response header, then behaves normally. Under a stall
policy the proxy counts each stalled request at its whole reservation and
answers the child with a retryable status. The probe establishes whether the
real native executable retries and completes its session, which offline unit
tests cannot show. Every price and count here is synthetic.
"""
from pathlib import Path
import json, os, sys, tempfile
from types import SimpleNamespace
import httpx

from budgeted_cborg import Ledger, STALL_DEBIT_BASIS
from native_proxy import NativeProxy
from run_native_canary import execute_child, verified_executable, sha

PYTHON = sys.executable
CLI = str(Path(os.environ.get('D4D_PROBE_CLI', Path.home() / '.local/share/claude/versions/2.1.272')).resolve(strict=True))
overlay = {'claude_executable': CLI, 'pinned_files': {CLI: sha(CLI)}}
PRICES = {"input": 0.000005, "output": 0.000025, "cache_read": 0.0000005, "cache_write": 0.00000625}
root = Path(tempfile.mkdtemp(prefix='d4d-native-stall-')).resolve()
work = root / 'work'; work.mkdir()
(work / 'input.txt').write_text('Synthetic offline stall probe. No dataset facts.\n')
(work / 'probe.py').write_text('print("OFFLINE_HELPER_OK")\n')
calls, faults = [], []


def respond(req):
    body = json.loads(req.content); calls.append(body)
    tooled = [v for v in calls if v.get('tools')]
    # A stall repeats the same conversation, so count distinct conversations.
    n = len({json.dumps(v['messages'], sort_keys=True) for v in tooled})
    if body.get('tools'):
        key = json.dumps(body['messages'], sort_keys=True)
        if n == 2 and ('http524', key) not in faults:
            faults.append(('http524', key))
            return httpx.Response(524, content=b'<html>synthetic origin timeout</html>')
        if n == 3 and ('timeout', key) not in faults:
            faults.append(('timeout', key))
            raise httpx.ReadTimeout('synthetic pre-header stall', request=req)
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
                    stall_policy={'count_attempts': 3, 'max_stall_debits': 4}, count_pause=lambda seconds: None)
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
value = {'root': str(root), 'executable': overlay, 'exit_code': code, 'proxy_failure': proxy.failure,
         'scripted_upstream_calls': len(calls), 'scripted_faults': [kind for kind, _ in faults],
         'count_tries': counts['tries'], 'count_retries': proxy.messages.count_retries,
         'stalls_survived': proxy.stalls_survived,
         'ledger_rows': len(rows), 'unsettled_rows': sum(row['status'] != 'settled' for row in rows),
         'stall_debit_rows': sum(row.get('settlement_basis') == STALL_DEBIT_BASIS for row in rows),
         'output_created': (work / 'output.txt').exists(),
         'terminal_result': ({k: terminal[-1].get(k) for k in ('is_error', 'terminal_reason', 'stop_reason', 'num_turns')}
                             if terminal else None),
         'unfinished_handlers': proxy.unfinished_handlers, 'real_provider_requests': 0}
(root / 'result.json').write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps(value, indent=2))
