"""A pinned SDK control callback for the isolated native CLI (#2055).

Ordinary settings hooks are disabled by safe mode. The SDK control channel
remains available. It checks Bash input without rewriting commands or
overriding the runtime's own permissions. No SDK package is needed: retain
the original CLI JSONL and implement only initialization and this callback.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import selectors
import threading
import time

from budgeted_cborg import BudgetStop


CONTRACT = {'version': 1, 'event': 'PreToolUse', 'matcher': 'Bash',
            'callback_id': 'd4d_command_policy_v1', 'initialize_timeout_seconds': 30,
            'callback_timeout_seconds': 2, 'runtime_callback_timeout_seconds': 3}
INIT_ID = 'd4d_initialize_v1'
MAX_FRAME_BYTES = 16 * 1024 * 1024


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def initialize_frame():
    return {'type': 'control_request', 'request_id': INIT_ID, 'request': {
        'subtype': 'initialize', 'hooks': {CONTRACT['event']: [{
            'matcher': CONTRACT['matcher'], 'hookCallbackIds': [CONTRACT['callback_id']],
            'timeout': CONTRACT['runtime_callback_timeout_seconds']}]}}}


def hook_output(classification, basis):
    # A prescribed command still goes through the runtime permission check.
    return {} if classification == 'prescribed' else {'hookSpecificOutput': {
        'hookEventName': CONTRACT['event'], 'permissionDecision': 'deny',
        'permissionDecisionReason': 'Outside the registered command policy: ' + basis}}


class NativeControl:
    def __init__(self, policy, classify):
        if policy.get('pretool_control') != CONTRACT:
            raise BudgetStop('missing or changed native control contract')
        self.policy, self.classify = policy, classify
        self.selector = selectors.DefaultSelector()
        self.buffer, self.outgoing = b'', b''
        self.initialized = self.terminal = self.stdout_closed = False
        self.calls, self.pending, self.decided = {}, {}, set()
        self.decided_tools = set()
        self.replies = queue.Queue()
        self.started = time.monotonic()

    def start(self, process, transcript, evidence, instruction):
        self.process, self.transcript, self.evidence = process, transcript, evidence
        self.instruction = instruction
        self.started = time.monotonic()
        os.set_blocking(process.stdout.fileno(), False)
        os.set_blocking(process.stdin.fileno(), False)
        self.selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        self.record({'kind': 'initialize_sent', 'policy_sha256': digest(self.policy),
                     'frame': initialize_frame()})
        self.send(initialize_frame())

    def record(self, value):
        value = {'at': datetime.now(timezone.utc).isoformat(), **value}
        self.evidence.write(json.dumps(value) + '\n')
        self.evidence.flush()

    def send(self, value):
        self.outgoing += (json.dumps(value) + '\n').encode()
        try:
            self.selector.get_key(self.process.stdin)
        except KeyError:
            self.selector.register(self.process.stdin, selectors.EVENT_WRITE, 'stdin')

    def handle(self, event):
        if not isinstance(event, dict):
            raise BudgetStop('native control received a non-object event')
        kind = event.get('type')
        if kind == 'control_response':
            response = event.get('response', {})
            if (self.initialized or not isinstance(response, dict) or
                response.get('request_id') != INIT_ID or response.get('subtype') != 'success'):
                raise BudgetStop('native control initialization was refused or ambiguous')
            self.initialized = True
            self.record({'kind': 'initialize_ack', 'frame': event})
            self.send({'type': 'user', 'session_id': '', 'parent_tool_use_id': None,
                       'message': {'role': 'user', 'content': self.instruction}})
        elif kind == 'control_request':
            self.callback(event)
        elif kind == 'control_cancel_request':
            raise BudgetStop('native control callback was cancelled or timed out')
        elif kind == 'result':
            if not self.initialized or self.terminal or self.pending:
                raise BudgetStop('native result arrived with ambiguous or pending controls')
            self.terminal = True
        message = event.get('message')
        if isinstance(message, dict) and isinstance(message.get('content'), list):
            for block in message['content']:
                if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                    identity = block.get('id')
                    if not isinstance(identity, str) or not identity or identity in self.calls:
                        raise BudgetStop('native Bash call has a missing or duplicate identity')
                    payload = block.get('input')
                    if not isinstance(payload, dict):
                        raise BudgetStop('native Bash call has malformed input')
                    self.calls[identity] = payload.get('command')

    def callback(self, frame):
        request = frame.get('request')
        request_id = frame.get('request_id')
        if not self.initialized or self.terminal or not isinstance(request, dict):
            raise BudgetStop('native callback is outside the initialized run')
        data = request.get('input')
        if (not isinstance(request_id, str) or not request_id or request_id == INIT_ID or
            request_id in self.pending or request_id in self.decided or
            request.get('subtype') != 'hook_callback' or
            request.get('callback_id') != CONTRACT['callback_id'] or
            not isinstance(data, dict) or data.get('hook_event_name') != CONTRACT['event'] or
            data.get('tool_name') != 'Bash' or not isinstance(data.get('tool_input'), dict)):
            raise BudgetStop('native callback is malformed or unregistered')
        identity = data.get('tool_use_id')
        command = data['tool_input'].get('command')
        if (not isinstance(command, str) or
            not isinstance(identity, str) or identity not in self.calls or
            self.calls[identity] != command or
            request.get('tool_use_id') not in (None, identity) or identity in self.decided_tools or
            data.get('cwd') != self.policy['readonly_lookups']['repository']):
            raise BudgetStop('native callback does not match an observed Bash call')
        if identity in {item[1]['request']['input']['tool_use_id'] for item in self.pending.values()}:
            raise BudgetStop('duplicate native callback for one tool call')
        self.pending[request_id] = (time.monotonic(), frame)

        def evaluate():
            try:
                value = self.classify(command, self.policy['python'], set(), self.policy)
            except BaseException as error:
                value = error
            self.replies.put((request_id, value))
        # The classifier only reads paths/syntax. A stalled filesystem lookup
        # must not stop the parent from enforcing deadlines and terminating.
        threading.Thread(target=evaluate, daemon=True).start()

    def service(self):
        now = time.monotonic()
        if not self.initialized and now - self.started >= CONTRACT['initialize_timeout_seconds']:
            raise BudgetStop('native control initialization timed out before the prompt')
        if any(now - started >= CONTRACT['callback_timeout_seconds'] for started, _ in self.pending.values()):
            raise BudgetStop('native command classification timed out before execution')
        while True:
            try:
                request_id, value = self.replies.get_nowait()
            except queue.Empty:
                break
            if isinstance(value, BaseException):
                raise BudgetStop('native command classification failed before execution') from value
            if (not isinstance(value, tuple) or len(value) != 2 or
                value[0] not in ('prescribed', 'not_prescribed') or not isinstance(value[1], str)):
                raise BudgetStop('native command classification returned a malformed decision')
            _, request = self.pending.pop(request_id)
            classification, basis = value
            response = {'type': 'control_response', 'response': {'subtype': 'success',
                        'request_id': request_id, 'response': hook_output(classification, basis)}}
            self.record({'kind': 'decision', 'request': request, 'response': response,
                         'classification': classification, 'basis': basis})
            self.decided.add(request_id)
            self.decided_tools.add(request['request']['input']['tool_use_id'])
            self.send(response)
        for key, _ in self.selector.select(.05):
            if key.data == 'stdin':
                try:
                    count = os.write(key.fd, self.outgoing)
                except BlockingIOError:
                    continue
                self.outgoing = self.outgoing[count:]
                if not self.outgoing:
                    self.selector.unregister(key.fileobj)
            else:
                try:
                    raw = os.read(key.fd, 65536)
                except BlockingIOError:
                    continue
                if not raw:
                    self.selector.unregister(key.fileobj)
                    self.stdout_closed = True
                    if self.buffer.strip():
                        raise BudgetStop('native transcript ends inside a JSON frame')
                    continue
                self.transcript.write(raw); self.transcript.flush()
                self.buffer += raw
                while b'\n' in self.buffer:
                    line, self.buffer = self.buffer.split(b'\n', 1)
                    if len(line) > MAX_FRAME_BYTES:
                        raise BudgetStop('native control frame exceeds its size limit')
                    if line.strip():
                        try:
                            event = json.loads(line)
                        except (ValueError, UnicodeError) as error:
                            raise BudgetStop('native control received malformed JSON') from error
                        self.handle(event)
                if len(self.buffer) > MAX_FRAME_BYTES:
                    raise BudgetStop('native control frame exceeds its size limit')
        if self.terminal and not self.outgoing and not self.process.stdin.closed:
            self.process.stdin.close()

    def finish(self):
        if not self.initialized or not self.terminal or self.pending or self.decided_tools != set(self.calls):
            raise BudgetStop('native control session ended without complete evidence')

    def close(self):
        self.selector.close()
        process = getattr(self, 'process', None)
        if process:
            for stream in (process.stdin, process.stdout):
                if stream and not stream.closed:
                    stream.close()

    def retain_pipe_tail(self, path):
        """After child termination, preserve bytes the parser had not consumed.

        Do not dispatch callbacks during shutdown. Already buffered bytes
        were written before parsing and must not be duplicated here.
        """
        process = getattr(self, 'process', None)
        if process and process.stdout and not process.stdout.closed:
            with Path(path).open('ab') as stream:
                while True:
                    try:
                        raw = os.read(process.stdout.fileno(), 65536)
                    except BlockingIOError:
                        break
                    if not raw:
                        break
                    stream.write(raw)


def check_control_history(events, path, policy, classify):
    """Reconcile parent decisions against the unchanged native transcript."""
    problems = []
    try:
        with Path(path).open() as stream:
            records = [json.loads(line) for line in stream if line.strip()]
        if any(r.get('kind') not in ('initialize_sent', 'initialize_ack', 'decision') for r in records):
            problems.append('native control evidence contains an unrecognized record')
        sent = [r for r in records if r.get('kind') == 'initialize_sent']
        ack = [r for r in records if r.get('kind') == 'initialize_ack']
        if len(sent) != 1 or sent[0].get('frame') != initialize_frame() or sent[0].get('policy_sha256') != digest(policy):
            problems.append('native control initialization does not bind this policy')
        if (len(ack) != 1 or ack[0].get('frame') not in events or
            ack[0]['frame'].get('response', {}).get('subtype') != 'success' or
            ack[0]['frame'].get('response', {}).get('request_id') != INIT_ID):
            problems.append('native control has no unique successful initialization evidence')
        calls, results, callbacks = {}, {}, {}
        for line, event in enumerate(events, 1):
            if event.get('type') == 'control_request':
                callbacks.setdefault(event.get('request_id'), []).append((line, event))
            message = event.get('message')
            if not isinstance(message, dict) or not isinstance(message.get('content'), list):
                continue
            for block in message['content']:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                    calls.setdefault(block.get('id'), []).append((line, block))
                elif block.get('type') == 'tool_result':
                    results.setdefault(block.get('tool_use_id'), []).append((line, block))
        seen_ids, seen_requests = [], []
        for record in (r for r in records if r.get('kind') == 'decision'):
            frame = record['request']; request = frame['request']; data = request['input']
            identity = data['tool_use_id']; request_id = frame['request_id']
            seen_ids.append(identity); seen_requests.append(request_id)
            observed_calls, observed_callbacks = calls.get(identity, []), callbacks.get(request_id, [])
            observed_results = results.get(identity, [])
            if len(observed_calls) != 1 or len(observed_callbacks) != 1 or len(observed_results) != 1:
                problems.append('native control decision lacks unique call, callback and result evidence')
                continue
            call_line, call = observed_calls[0]; callback_line, callback = observed_callbacks[0]
            result_line, result = observed_results[0]
            command = call['input']['command']
            classification, basis = classify(command, policy['python'], set(), policy)
            expected = {'type': 'control_response', 'response': {'subtype': 'success',
                        'request_id': request_id, 'response': hook_output(classification, basis)}}
            if (callback != frame or not call_line < callback_line < result_line or
                request.get('subtype') != 'hook_callback' or request.get('callback_id') != CONTRACT['callback_id'] or
                data.get('hook_event_name') != CONTRACT['event'] or data.get('tool_name') != 'Bash' or
                data.get('cwd') != policy['readonly_lookups']['repository'] or
                data['tool_input'].get('command') != command or record.get('classification') != classification or
                record.get('basis') != basis or record.get('response') != expected):
                problems.append('native control decision disagrees with its observed command or registered policy')
            if classification != 'prescribed' and result.get('is_error') is not True:
                problems.append('native denied command has a successful tool result')
        if Counter(seen_ids) != Counter({identity: 1 for identity in calls}):
            problems.append('native Bash calls lack exactly one control decision each')
        if Counter(seen_requests) != Counter({identity: 1 for identity in callbacks}):
            problems.append('native callbacks lack exactly one control response each')
        return {'checked': True, 'bash_calls': len(calls), 'decisions': len(seen_ids), 'problems': problems}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as error:
        return {'checked': False, 'problems': [f'native control evidence is missing or malformed ({type(error).__name__})']}
