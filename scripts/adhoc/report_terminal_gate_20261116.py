"""Diagnose terminal fixture failure for the Claude lead, 2026-11-16.

Inputs: retained lane artifacts. Output: JSON evidence summary on stdout.
Serves terminal-gate assignment; no provider, native, or artifact mutation.
"""
import hashlib
import json
from pathlib import Path
import sys

lane = Path(sys.argv[1])
attempt = next((lane / 'native-case').glob('*/native26/native-attempt'))
events = [json.loads(line) for line in (attempt / 'transcript.jsonl').read_text().splitlines()]
log = (lane / 'logs/native-public-native-public-correction.log').read_text()
start = json.loads((attempt / 'host-clock-start.json').read_text())
end = json.loads((attempt / 'host-clock-end.json').read_text())
calls = []
results = []
for event in events:
    for block in event.get('message', {}).get('content', []):
        if block.get('type') == 'tool_use':
            calls.append({'id': block.get('id'), 'name': block.get('name'), 'input': block.get('input')})
        if block.get('type') == 'tool_result':
            results.append({'id': block.get('tool_use_id'), 'result': event.get('tool_use_result'),
                            'is_error': block.get('is_error')})
limits = []
def scan(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            if 'deadline' in key:
                limits.append({'path': path + '/' + key, 'value': child})
            scan(child, path + '/' + key)
    elif isinstance(value, list):
        for child in value:
            scan(child, path)
scan(json.loads((attempt / 'registration.json').read_text()))
print(json.dumps({'terminal': [e for e in events if e.get('type') == 'result'],
    'child_exit_log': [line.strip() for line in log.splitlines() if 'child_exit_code' in line],
    'attempt_elapsed_seconds': (end['monotonic_ns'] - start['monotonic_ns']) / 1e9,
    'deadlines': limits, 'last_calls': calls[-6:], 'last_results': results[-6:],
    'stderr_tail': (attempt / 'stderr.txt').read_text().splitlines()[-1:],
    'files': {name: hashlib.sha256((attempt / name).read_bytes()).hexdigest()
              for name in ('transcript.jsonl', 'stderr.txt', 'registration.json')}}, indent=2))
