"""#6094: supplemental controller timestamps, never an admission document.

Helper endpoints are response delivery and result intake, not subprocess CPU
time. Event boundaries describe what this controller received from the CLI.
"""
import hashlib
import json
import os
from pathlib import Path
import time

from .native_elapsed import elapsed_ns
from .native_host_power import observation_error


class Timing:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.fd = None
        self.rows = 0
        self.decisions = {}
        self.responses = []
        self.calls = {}
        try:
            self.fd = os.open(self.directory / 'host-controller-timing.jsonl',
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except Exception as exc:
            observation_error(self.directory, 'controller-timing', exc)

    def record(self, boundary, **fields):
        if self.fd is None:
            return
        try:
            if self.rows >= 100_000:
                raise ValueError('controller timing record bound exceeded')
            raw = json.dumps({'boundary': boundary, 'wall_ns': time.time_ns(),
                'monotonic_ns': time.monotonic_ns(), 'elapsed_ns': elapsed_ns(),
                **fields}, sort_keys=True, separators=(',', ':')).encode() + b'\n'
            if len(raw) > 4096 or os.write(self.fd, raw) != len(raw):
                raise OSError('incomplete controller timing write')
            self.rows += 1
        except Exception as exc:
            self.close()
            observation_error(self.directory, 'controller-timing', exc)

    def safely(self, method, *args):
        """A malformed diagnostic input or unavailable disk cannot stop work."""
        if self.fd is None:
            return
        try:
            getattr(self, method)(*args)
        except Exception as exc:
            self.close()
            observation_error(self.directory, 'controller-timing', exc)

    def event(self, event, line):
        kind = event.get('type')
        message = event.get('message', {})
        if kind in ('assistant', 'user', 'result'):
            self.record('turn_boundary', event_type=kind, transcript_line=line,
                basis='controller intake of complete CLI frame',
                message_id=str(message.get('id', ''))[:256])
        if kind == 'stream_event' and isinstance(event.get('event'), dict):
            phase = event['event'].get('type')
            if phase in ('message_start', 'message_stop'):
                self.record('turn_boundary', event_type=phase, transcript_line=line,
                    basis='controller intake of CLI partial-message boundary')
        for block in message.get('content', []) if isinstance(message, dict) else []:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use':
                identity = str(block.get('id', ''))[:256]
                self.calls[identity] = str(block.get('name', ''))[:64]
                self.record('helper_requested', tool_use_id=identity,
                    tool_name=self.calls[identity], transcript_line=line)
            elif block.get('type') == 'tool_result':
                identity = str(block.get('tool_use_id', ''))[:256]
                self.record('helper_end', tool_use_id=identity, tool_name=self.calls.get(identity),
                    transcript_line=line, is_error=block.get('is_error'),
                    basis='controller intake of tool result; includes transport and scheduling')
                self.calls.pop(identity, None)

    def decision(self, value):
        if value.get('kind') != 'decision':
            return
        frame = value['request']
        data = frame['request']['input']
        command = data.get('tool_input', {}).get('command', '')
        self.decisions[frame['request_id']] = {
            'tool_use_id': str(data['tool_use_id'])[:256], 'tool_name': str(data['tool_name'])[:64],
            'classification': value['classification'],
            'command_sha256': hashlib.sha256(command.encode()).hexdigest()}

    def queued(self, frame, pending_bytes):
        if frame.get('type') == 'control_response':
            detail = self.decisions.pop(frame.get('response', {}).get('request_id'), None)
            if detail is not None:
                self.responses.append([pending_bytes, detail])

    def written(self, count):
        pending = []
        for remaining, detail in self.responses:
            remaining -= count
            if remaining <= 0:
                self.record('helper_start' if detail['classification'] == 'prescribed' else 'helper_denied',
                    **detail, basis='controller finished writing callback response; runtime may still refuse')
            else:
                pending.append([remaining, detail])
        self.responses = pending

    def close(self):
        descriptor, self.fd = self.fd, None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                observation_error(self.directory, 'controller-timing-close', exc)
