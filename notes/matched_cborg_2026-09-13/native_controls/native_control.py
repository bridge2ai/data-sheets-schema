"""A pinned SDK control callback for the isolated native CLI (#2055).

Ordinary settings hooks are disabled by safe mode. The SDK control channel
remains available. It checks tool inputs without rewriting commands or
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
from native_file_policy import FileAccess


TOOLS = frozenset({'Bash', 'Read', 'Write'})
CONTRACT = {'version': 2, 'event': 'PreToolUse', 'matcher': 'Bash|Read|Write',
            'callback_id': 'd4d_tool_policy_v2', 'initialize_timeout_seconds': 30,
            'callback_timeout_seconds': 2, 'runtime_callback_timeout_seconds': 3}
INIT_ID = 'd4d_initialize_v1'
MAX_FRAME_BYTES = 16 * 1024 * 1024
BLANK_FRAME_TYPE = 'd4d_blank_native_frame'


def load_native_events(path):
    """Retain physical JSONL positions without repairing malformed evidence.

    Blank lines receive explicit review markers, not invented native events;
    control history remains uncheckable when one is present (#2075). Invalid
    UTF-8, malformed/non-object JSON, oversized frames and an unterminated
    nonblank frame are rejected. Only LF separates physical records; Unicode
    separators inside valid JSON strings are not split (#2043).
    """
    events = []
    with Path(path).open(encoding='utf-8', newline='\n') as stream:
        for number, line in enumerate(stream, 1):
            if len(line.removesuffix('\n').encode('utf-8')) > MAX_FRAME_BYTES:
                raise ValueError(f'native transcript frame {number} exceeds its size limit')
            if not line.strip():
                events.append({'type': BLANK_FRAME_TYPE, 'physical_line': number})
                continue
            if not line.endswith('\n'):
                raise ValueError(f'native transcript frame {number} is unterminated')
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError(f'native transcript frame {number} is not an object')
            events.append(event)
    return events


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
        'permissionDecisionReason': 'Outside the registered tool policy: ' + basis}}


def input_validation_rejection(call_event, call, result_event, call_line, result_line, session):
    """Recognize the evidenced, unexecuted Read numeric-string rejection.

    This is native runtime evidence, not a permission decision. Both the
    typed envelope and its error-only wrapper must match the original input.
    Other failures (including range errors and other invalid types) remain
    unexplained without a callback. The caller must also enforce unique IDs,
    initialization/order, and the absence of any callback for this call.
    No file is resolved, opened or granted by this recognizer. Frame hashes
    use canonical JSON via digest(); original transcript bytes remain intact.
    """
    if not all(isinstance(value, dict) for value in (call_event, call, result_event)):
        return None
    call_message = call_event.get('message')
    if (call_event.get('type') != 'assistant' or not isinstance(call_message, dict) or
        call_message.get('role') != 'assistant' or
        call.get('type') != 'tool_use' or call.get('name') != 'Read' or
        not isinstance(call.get('id'), str) or not call['id'] or
        not call_line < result_line):
        return None
    call_session = call_event.get('session_id')
    if (not isinstance(call_session, str) or not call_session or
        not isinstance(session, str) or not session or call_session != session or
        result_event.get('session_id') != call_session or result_event.get('type') != 'user' or
        call_event.get('parent_tool_use_id') is not None or
        result_event.get('parent_tool_use_id') is not None or
        set(result_event) - {'type', 'message', 'parent_tool_use_id', 'session_id',
                             'uuid', 'timestamp', 'tool_use_result'}):
        return None
    message = result_event.get('message')
    if (not isinstance(message, dict) or set(message) != {'role', 'content'} or
        message['role'] != 'user' or not isinstance(message['content'], list) or
        len(message['content']) != 1):
        return None
    result = message['content'][0]
    if (not isinstance(result, dict) or
        set(result) != {'type', 'tool_use_id', 'is_error', 'content'} or
        result['type'] != 'tool_result' or result['tool_use_id'] != call.get('id') or
        result['is_error'] is not True):
        return None
    payload = call.get('input')
    if (not isinstance(payload, dict) or
        set(payload) - {'file_path', 'offset', 'limit', 'pages'} or
        not isinstance(payload.get('file_path'), str) or not payload['file_path'] or
        ('pages' in payload and not isinstance(payload['pages'], str))):
        return None
    # The captured native schema gives offset/limit the same numeric type.
    # Limit changes the minimum only. Cover strings, the observed wrong type,
    # without guessing other native error-rendering or coercion behavior.
    bad = [field for field in ('offset', 'limit') if isinstance(payload.get(field), str)]
    if len(bad) != 1:
        return None
    field = bad[0]
    for other in ('offset', 'limit'):
        if other == field or other not in payload:
            continue
        value = payload[other]
        if (type(value) not in (int, float) or not 0 <= value <= 9007199254740991 or
            value != int(value) or (other == 'limit' and value == 0)):
            return None
    metadata = result_event.get('tool_use_result')
    prefix = 'InputValidationError: '
    if not isinstance(metadata, str) or not metadata.startswith(prefix):
        return None

    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate validation field')
            value[key] = item
        return value

    try:
        errors = json.loads(metadata[len(prefix):], object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        return None
    expected = [{'expected': 'number', 'code': 'invalid_type', 'path': [field],
                 'message': 'Invalid input'}]
    wrapper = ('<tool_use_error>InputValidationError: Read failed due to the following issue:\n'
               f'The parameter `{field}` type is expected as `number` but provided as '
               '`unknown`</tool_use_error>')
    if errors != expected or result['content'] != wrapper:
        return None
    return {'kind': 'input_rejected_before_callback', 'tool_use_id': call['id'],
            'tool': 'Read', 'field': field, 'input_type': 'string',
            'session_id': call_session,
            'call_line': call_line, 'result_line': result_line,
            'call_sha256': digest(call_event), 'result_sha256': digest(result_event)}


class NativeControl:
    def __init__(self, policy, classify, config_root=None, event_observer=None):
        if policy.get('pretool_control') != CONTRACT:
            raise BudgetStop('missing or changed native control contract')
        self.policy, self.classify = policy, classify
        self.event_observer = event_observer
        self.files = FileAccess(policy, config_root)
        self.classifications = {}
        self.selector = selectors.DefaultSelector()
        self.buffer, self.outgoing = b'', b''
        self.initialized = self.terminal = self.stdout_closed = False
        self.calls, self.pending, self.decided = {}, {}, set()
        self.decided_tools = set()
        self.call_frames, self.results, self.input_rejections = {}, {}, {}
        self.call_sessions = {}
        self.event_line = self.transcript_line = 0
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

    def handle(self, event, *, line_number=None):
        if not isinstance(event, dict):
            raise BudgetStop('native control received a non-object event')
        self.event_line = self.event_line + 1 if line_number is None else line_number
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
                if isinstance(block, dict) and block.get('type') in ('tool_use', 'tool_result'):
                    if not self.initialized or self.terminal:
                        raise BudgetStop('native tool event is outside the initialized run')
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    if block.get('name') not in TOOLS:
                        raise BudgetStop('native call uses an unregistered tool')
                    identity = block.get('id')
                    if not isinstance(identity, str) or not identity or identity in self.calls:
                        raise BudgetStop('native tool call has a missing or duplicate identity')
                    payload = block.get('input')
                    if not isinstance(payload, dict):
                        raise BudgetStop('native tool call has malformed input')
                    self.calls[identity] = block
                    self.call_frames[identity] = (self.event_line, event)
                    self.call_sessions[identity] = self.files.session
                elif isinstance(block, dict) and block.get('type') == 'tool_result':
                    identity = block.get('tool_use_id')
                    if not isinstance(identity, str) or identity not in self.calls or identity in self.results:
                        raise BudgetStop('native tool result lacks a unique preceding call')
                    self.results[identity] = (self.event_line, event)
                    pending_tools = {item[1]['request']['input']['tool_use_id'] for item in self.pending.values()}
                    if identity not in self.decided_tools and identity not in pending_tools:
                        call_line, call_event = self.call_frames[identity]
                        rejection = input_validation_rejection(call_event, self.calls[identity],
                                                               event, call_line, self.event_line,
                                                               self.call_sessions[identity])
                        if rejection is not None:
                            self.input_rejections[identity] = rejection
                            self.record(rejection)
        observed = self.files.observe(event, self.calls, self.classifications)
        if observed is not None:
            self.record(observed)
        if self.event_observer is not None:
            # The phase reviewer sees the retained native event before a
            # following tool callback can authorize execution (#2067).
            self.event_observer(event)

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
            data.get('tool_name') not in TOOLS or not isinstance(data.get('tool_input'), dict)):
            raise BudgetStop('native callback is malformed or unregistered')
        identity = data.get('tool_use_id')
        payload, tool = data['tool_input'], data['tool_name']
        if (not isinstance(identity, str) or identity not in self.calls or
            self.calls[identity]['name'] != tool or
            (tool == 'Bash' and self.calls[identity]['input'] != payload) or
            request.get('tool_use_id') not in (None, identity) or identity in self.decided_tools or
            data.get('cwd') != self.policy['readonly_lookups']['repository']):
            raise BudgetStop('native callback does not match an observed tool call')
        if identity in {item[1]['request']['input']['tool_use_id'] for item in self.pending.values()}:
            raise BudgetStop('duplicate native callback for one tool call')
        if identity in self.results:
            raise BudgetStop('native callback arrived after its tool result')
        self.pending[request_id] = (time.monotonic(), frame)

        def evaluate():
            try:
                if tool != 'Bash' and not self.files.matches(tool, self.calls[identity]['input'], payload):
                    raise BudgetStop('native callback does not match an observed tool call')
                if tool == 'Bash':
                    command = payload.get('command')
                    if not isinstance(command, str):
                        raise ValueError('Bash command is not text')
                    value = self.classify(command, self.policy['python'], set(), self.policy)
                else:
                    value = self.files.classify(tool, payload)
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
            if isinstance(value, BudgetStop):
                raise value
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
            self.classifications[request['request']['input']['tool_use_id']] = classification
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
                    self.transcript_line += 1
                    if len(line) > MAX_FRAME_BYTES:
                        raise BudgetStop('native control frame exceeds its size limit')
                    if line.strip():
                        try:
                            event = json.loads(line)
                        except (ValueError, UnicodeError) as error:
                            raise BudgetStop('native control received malformed JSON') from error
                        self.handle(event, line_number=self.transcript_line)
                if len(self.buffer) > MAX_FRAME_BYTES:
                    raise BudgetStop('native control frame exceeds its size limit')
        if self.terminal and not self.outgoing and not self.process.stdin.closed:
            self.process.stdin.close()

    def finish(self):
        for identity, recorded in self.input_rejections.items():
            call_line, call_event = self.call_frames[identity]
            result_line, result_event = self.results[identity]
            if (identity in self.decided_tools or
                input_validation_rejection(call_event, self.calls[identity], result_event,
                                           call_line, result_line, self.call_sessions[identity]) != recorded):
                raise BudgetStop('native input rejection has contradictory execution evidence')
        if (not self.initialized or not self.terminal or self.pending or
            self.decided_tools | set(self.input_rejections) != set(self.calls) or
            set(self.results) != set(self.calls)):
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


def check_control_history(events, path, policy, classify, config_root=None):
    """Reconcile every tool with parent decisions in native event order."""
    problems = []
    try:
        blank_lines = [line for line, event in enumerate(events, 1)
                       if event.get('type') == BLANK_FRAME_TYPE]
        if blank_lines:
            problems.append('native transcript has blank physical frames; history is uncheckable')
        with Path(path).open() as stream:
            records = [json.loads(line) for line in stream if line.strip()]
        if any(r.get('kind') not in ('initialize_sent', 'initialize_ack', 'decision', 'persisted_output',
                                    'input_rejected_before_callback') for r in records):
            problems.append('native control evidence contains an unrecognized record')
        sent = [r for r in records if r.get('kind') == 'initialize_sent']
        ack = [r for r in records if r.get('kind') == 'initialize_ack']
        if len(sent) != 1 or sent[0].get('frame') != initialize_frame() or sent[0].get('policy_sha256') != digest(policy):
            problems.append('native control initialization does not bind this policy')
        if (len(ack) != 1 or ack[0].get('frame') not in events or
            ack[0]['frame'].get('response', {}).get('subtype') != 'success' or
            ack[0]['frame'].get('response', {}).get('request_id') != INIT_ID):
            problems.append('native control has no unique successful initialization evidence')
        decisions = {}
        for record in (r for r in records if r['kind'] == 'decision'):
            decisions.setdefault(record['request']['request_id'], []).append(record)
        files = FileAccess(policy, config_root)
        calls, results, callbacks, classifications = {}, {}, {}, {}
        call_events, result_events, call_sessions = {}, {}, {}
        observed_files, input_rejections = [], []
        ack_lines = [line for line, event in enumerate(events, 1)
                     if len(ack) == 1 and event == ack[0].get('frame')]
        terminal_lines = [line for line, event in enumerate(events, 1) if event.get('type') == 'result']
        for line, event in enumerate(events, 1):
            message = event.get('message')
            if isinstance(message, dict) and isinstance(message.get('content'), list):
                for block in message['content']:
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'tool_use':
                        if block.get('name') not in TOOLS:
                            problems.append('native transcript uses an unregistered tool')
                        identity = block.get('id')
                        if not isinstance(identity, str) or not identity or identity in calls:
                            problems.append('native tool call lacks a unique identity')
                        calls[identity] = (line, block)
                        call_events[identity] = event
                        call_sessions[identity] = files.session
                    elif block.get('type') == 'tool_result':
                        results.setdefault(block.get('tool_use_id'), []).append((line, block))
                        result_events[line] = event
            if event.get('type') == 'control_request':
                request = event['request']; data = request['input']
                identity = data['tool_use_id']; request_id = event['request_id']
                callbacks.setdefault(identity, []).append((line, request_id))
                matches = decisions.get(request_id, [])
                if identity not in calls or len(matches) != 1:
                    problems.append('native callback lacks one preceding call and parent decision')
                    continue
                call_line, call = calls[identity]
                tool, payload = call['name'], call['input']
                if tool == 'Bash':
                    classification, basis = classify(payload['command'], policy['python'], set(), policy)
                elif tool in ('Read', 'Write'):
                    classification, basis = files.classify(tool, payload)
                else:
                    raise ValueError('unregistered tool')
                classifications[identity] = classification
                record = matches[0]
                expected = {'type': 'control_response', 'response': {'subtype': 'success',
                            'request_id': request_id, 'response': hook_output(classification, basis)}}
                if (record['request'] != event or not call_line < line or
                    request.get('subtype') != 'hook_callback' or request.get('callback_id') != CONTRACT['callback_id'] or
                    data.get('hook_event_name') != CONTRACT['event'] or data.get('tool_name') != tool or
                    data.get('cwd') != policy['readonly_lookups']['repository'] or
                    not files.matches(tool, payload, data.get('tool_input', {})) or request.get('tool_use_id') not in (None, identity) or
                    record.get('classification') != classification or record.get('basis') != basis or
                    record.get('response') != expected):
                    problems.append('native control decision disagrees with its observed tool or registered policy')
            observed = files.observe(event, {key: value[1] for key, value in calls.items()}, classifications)
            if observed is not None:
                observed_files.append(observed)
        for identity, (call_line, call) in calls.items():
            matches, replies = callbacks.get(identity, []), results.get(identity, [])
            if (not matches and len(replies) == 1 and len(ack_lines) == 1 and
                ack_lines[0] < call_line < replies[0][0] and
                not any(line <= replies[0][0] for line in terminal_lines)):
                rejection = input_validation_rejection(call_events[identity], call,
                    result_events[replies[0][0]], call_line, replies[0][0], call_sessions[identity])
                if rejection is not None:
                    input_rejections.append(rejection)
                    continue
            if (len(matches) != 1 or len(replies) != 1 or
                not call_line < matches[0][0] < replies[0][0]):
                problems.append('native tool call lacks unique subsequent callback and result evidence')
            elif classifications.get(identity) != 'prescribed' and replies[0][1].get('is_error') is not True:
                problems.append('native denied tool has a successful result')
        if set(results) - set(calls):
            problems.append('native tool result has no observed call')
        if Counter(rid for values in callbacks.values() for _, rid in values) != Counter({rid: 1 for rid in decisions}):
            problems.append('native callbacks lack exactly one control response each')
        recorded_files = [{k: v for k, v in r.items() if k != 'at'} for r in records if r['kind'] == 'persisted_output']
        if recorded_files != observed_files:
            problems.append('native persisted-output evidence differs from its observed origin or current bytes')
        input_rejections.sort(key=lambda value: value['result_line'])
        recorded_rejections = [{k: v for k, v in r.items() if k != 'at'} for r in records
                               if r['kind'] == 'input_rejected_before_callback']
        if recorded_rejections != input_rejections:
            problems.append('native input-rejection evidence differs from its unique observed call and result')
        return {'checked': not blank_lines, 'bash_calls': sum(call['name'] == 'Bash' for _, call in calls.values()),
                'file_calls': sum(call['name'] in ('Read', 'Write') for _, call in calls.values()),
                'decisions': sum(map(len, decisions.values())),
                'input_rejections': input_rejections,
                'persisted_output_paths': list(files.persisted), 'problems': problems}
    except BudgetStop as error:
        # These messages originate in the local file policy, not provider errors.
        return {'checked': False, 'problems': [f'native control evidence failed file policy: {error}']}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as error:
        return {'checked': False, 'problems': [f'native control evidence is missing or malformed ({type(error).__name__})']}
