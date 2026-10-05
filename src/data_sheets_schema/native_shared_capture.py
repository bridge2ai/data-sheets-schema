"""Fixed native stage capture and publication boundary.

The reader accepts only S-owned roles and exact captured pins. Observation
references name actual complete stream prefixes, never future stream hashes.
Live callers and the saved replay use the same closed observation joins.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path, PurePosixPath
import re

from . import native_shared_contract as c
from . import native_shared_evidence as evidence
from . import native_shared_observations as observed
from . import native_shared_stage as stage

_DYNAMIC = {'record': ('journal_records_root', 'json', 'history_records', 0),
            'request': ('requests_root', 'json', 'submissions', 1),
            'response': ('responses_root', 'bin', 'submissions', 1),
            'observation': ('observations_root', 'json', 'observation_records', 0)}
_LIMITS = {'execution_capture': 'request_bytes', 'started_capture': 'metadata_record_bytes',
    'session_binding': 'metadata_record_bytes', 'phase1_full': 'original_full_bytes',
    'phase1_receipt': 'original_full_bytes', 'phase1_core': 'original_full_bytes',
    'phase1_seal': 'metadata_record_bytes', 'core_seal': 'metadata_record_bytes',
    'record': 'metadata_record_bytes', 'observation': 'metadata_record_bytes',
    'request': 'request_bytes', 'response': 'generic_response_bytes',
    'journal': 'journal_bytes', 'packet': 'packet_bytes', 'typed_index': 'assembly_bytes',
    'typed_assembly': 'assembly_bytes', 'audit': 'assembly_bytes', 'completion': 'metadata_record_bytes',
    'effective_receipt': 'generic_response_bytes', 'receipt_result': 'request_bytes', 'receipt_carry': 'request_bytes'}
_OBSERVATION_KEYS = {'kind', 'version', 'observation_type', 'selection_sha256', 'execution_sha256',
    'attempt_id', 'session_id', 'transcript_prefix', 'control_prefix', 'payload'}
_OBSERVATION_PAYLOADS = {
    'initialized': {'initialize_sent', 'initialize_ack', 'native_init'},
    'advance_admitted': {'call', 'before_history_sha256'},
    'request_read': {'call', 'result', 'result_event', 'request', 'history_sha256'},
    'response_intent': {'request', 'response', 'call', 'callback', 'tool_use_id', 'input_json', 'history_sha256', 'read_observation'},
    'response_written': {'call', 'result', 'result_event', 'response', 'intent_observation', 'history_sha256'},
    'phase1_sealed': {'full', 'original_receipt', 'helper_calls'},
    'core_sealed': {'core', 'helper_calls'},
    'advance_settled': {'call', 'result', 'result_event', 'advance_result'},
}


def _pin(value):
    c.exact(value, {'role', 'path', 'bytes', 'sha256'}, 'captured artifact pin')
    return c.ArtifactPin(**value)


class _Reader:
    """One bounded capture transaction; no directory discovery or read fallback."""
    def __init__(self, selection, *, pool=None):
        if type(selection) is not c.NativeSelectionCapture:
            raise ValueError('capture requires the exact immutable selection')
        if pool is not None and type(pool) is not evidence.CapturePool:
            raise ValueError('saved reader requires the exact immutable pool')
        self.selection, self.pool = selection, pool
        self.members = {}
        self.total = 0

    def destination(self, role, path):
        c.canonical_path(path, 'selected stage artifact')
        if role in _DYNAMIC:
            root, suffix, ceiling, first = _DYNAMIC[role]
            p = PurePosixPath(path)
            if p.parent != PurePosixPath(self.selection.role(root)) or re.fullmatch(r'[0-9]{6}\.' + suffix, p.name) is None:
                raise ValueError('dynamic artifact is outside its exact selected role')
            number = int(p.stem)
            maximum = c.HARD_LIMITS[ceiling]
            if role in ('request', 'response'):
                maximum = min(maximum, self.selection.bounds()['max_submissions']) + 1
            elif role == 'record':
                maximum = min(maximum, self.selection.bounds()['max_history_records'])
            if not first <= number < maximum:
                raise ValueError('dynamic artifact ordinal exceeds its complete bound')
        elif role not in _LIMITS or path != self.selection.role(role):
            raise ValueError('artifact is not an exact selected captured role')
        limit = c.HARD_LIMITS[_LIMITS[role]]
        if role == 'request': limit = min(limit, self.selection.bounds()['max_request_bytes'])
        if role == 'response': limit = min(limit, self.selection.bounds()['max_response_bytes'])
        return limit

    def read(self, role, path, expected=None):
        limit = self.destination(role, path)
        if expected is not None and (type(expected) is not c.ArtifactPin or expected.role != role
                                    or expected.path != path or expected.bytes > limit):
            raise ValueError('selected pin differs from its bounded artifact role')
        key = (role, path)
        if key in self.members:
            member = self.members[key]
        elif self.pool is None:
            member = evidence.read_regular(path, role, max_bytes=limit)
        else:
            candidates = [m for m in self.pool.members if m.captured.pin.role == role and m.captured.pin.path == path
                          and (expected is None or m.captured.pin == expected)]
            if len(candidates) != 1:
                raise ValueError('saved capture lacks one exact artifact version')
            member = candidates[0]
        if member.captured.pin.bytes > limit or (expected is not None and member.captured.pin != expected):
            raise ValueError('captured artifact differs from its exact pin or bound')
        if key not in self.members:
            self.total += member.captured.pin.bytes
            if (self.total > self.selection.bounds()['max_evidence_bytes']
                    or len(self.members) >= c.HARD_LIMITS['captured_members']):
                raise ValueError('complete stage capture exceeds its total bound')
            self.members[key] = member
        return member.captured

    def pinned(self, value):
        pin = _pin(value)
        return self.read(pin.role, pin.path, pin)

    def history(self, execution):
        """Read only pins reached by the exact numbered journal and records."""
        journal = self.read('journal', self.selection.role('journal'))
        doc = c.strict_json(journal.raw, 'captured journal', c.HARD_LIMITS['journal_bytes'])
        c.exact(doc, stage.JOURNAL_KEYS, 'captured journal')
        rows = doc['records']
        if type(rows) is not list or len(rows) > self.selection.bounds()['max_history_records']:
            raise ValueError('captured journal record list exceeds its bound')
        records = []
        artifacts, observations = {}, {}
        for number, pin in enumerate(rows):
            expected_path = str(PurePosixPath(self.selection.role('journal_records_root')) / f'{number:06d}.json')
            actual = _pin(pin)
            if actual.role != 'record' or actual.path != expected_path:
                raise ValueError('journal does not name the complete ordered selected records')
            item = self.pinned(pin)
            record = c.strict_json(item.raw, 'captured record', c.HARD_LIMITS['metadata_record_bytes'])
            c.exact(record, stage.RECORD_KEYS, 'captured record')
            kind = record['record_type']
            if kind not in stage.PAYLOAD_KEYS:
                raise ValueError('captured record has an unknown type')
            payload = c.exact(record['payload'], stage.PAYLOAD_KEYS[kind], 'captured record payload')
            records.append(item)
            # Only fields the pure stage consumes as file pins are followed;
            # derived response bytes and scientific payloads are not paths.
            for name in ('execution', 'started', 'binding', 'init_observation', 'seal', 'full', 'original_receipt',
                         'core', 'observation', 'request', 'response', 'read_observation', 'response_observation',
                         'assembly', 'audit', 'completion'):
                value = payload.get(name)
                if type(value) is dict and set(value) == {'role', 'path', 'bytes', 'sha256'}:
                    found = self.pinned(value)
                    target = observations if found.pin.role == 'observation' else artifacts
                    if found.pin.path in target and target[found.pin.path] != found:
                        raise ValueError('history substitutes an already consumed artifact')
                    target[found.pin.path] = found
            if 'outputs' in payload:
                if type(payload['outputs']) is not list or len(payload['outputs']) > len(stage.OUTPUT_ROLES):
                    raise ValueError('stage output pin list exceeds its closed roles')
                for pin in payload['outputs']:
                    found = self.pinned(pin)
                    if found.pin.role not in stage.OUTPUT_ROLES:
                        raise ValueError('stage output has a foreign role')
                    artifacts[found.pin.path] = found
        result = c.RawHistory(journal=journal, records=tuple(records),
                              artifacts=tuple(artifacts.values()), observations=tuple(observations.values()))
        stage._history(self.selection, execution, result)
        return result


def observation_bytes(kind, selection, execution_sha256, attempt_id, session_id,
                      transcript, control, payload):
    if kind not in _OBSERVATION_PAYLOADS:
        raise ValueError('unknown native shared observation type')
    c.exact(payload, _OBSERVATION_PAYLOADS[kind], 'observation payload')
    raw = c.canonical({'kind': c.KINDS['observation'], 'version': 1, 'observation_type': kind,
        'selection_sha256': selection.registration.pin.sha256, 'execution_sha256': execution_sha256,
        'attempt_id': attempt_id, 'session_id': session_id,
        'transcript_prefix': evidence.prefix_reference(transcript, execution_sha256=execution_sha256),
        'control_prefix': evidence.prefix_reference(control, execution_sha256=execution_sha256), 'payload': payload})
    if len(raw) > c.HARD_LIMITS['metadata_record_bytes']:
        raise ValueError('native observation exceeds its complete byte bound')
    return raw


def observation(artifact, selection, execution, pool):
    """Resolve a closed durable observation through its actual captured prefixes."""
    if artifact.pin.role != 'observation':
        raise ValueError('not a captured native observation')
    _Reader(selection).destination('observation', artifact.pin.path)
    doc = c.strict_json(artifact.raw, 'native observation', c.HARD_LIMITS['metadata_record_bytes'])
    c.exact(doc, _OBSERVATION_KEYS, 'native observation')
    kind = doc['observation_type']
    if (doc['kind'] != c.KINDS['observation'] or type(doc['version']) is not int or doc['version'] != 1
            or kind not in _OBSERVATION_PAYLOADS or doc['selection_sha256'] != execution.selection_sha256
            or doc['selection_sha256'] != selection.registration.pin.sha256
            or doc['execution_sha256'] != execution.execution.pin.sha256
            or doc['attempt_id'] != execution.attempt_id or doc['session_id'] != execution.session_id):
        raise ValueError('native observation belongs to another exact execution/session')
    c.exact(doc['payload'], _OBSERVATION_PAYLOADS[kind], 'native observation payload')
    transcript = pool.prefix(doc['transcript_prefix'], execution_sha256=execution.execution.pin.sha256)
    control = pool.prefix(doc['control_prefix'], execution_sha256=execution.execution.pin.sha256)
    if (transcript.path != str(Path(c.strict_json(execution.execution.raw)['attempt_directory']) / 'transcript.jsonl')
            or control.path != str(Path(c.strict_json(execution.execution.raw)['attempt_directory']) / 'control.jsonl')):
        raise ValueError('native observation streams are outside their exact registered attempt')
    return doc, transcript, control


def _call(value):
    c.exact(value, {'admission', 'call', 'callback', 'input_json', 'session_id', 'tool_name', 'tool_use_id'}, 'observed call')
    def ref(row):
        c.exact(row, {'stream', 'line', 'block', 'raw_line_sha256', 'value_sha256'}, 'event reference')
        return c.EventRef(**row)
    if type(value['input_json']) is not str:
        raise ValueError('observed call must retain raw JSON text')
    return c.ObservedCall(admission=ref(value['admission']), call=ref(value['call']), callback=ref(value['callback']),
        input_json=value['input_json'].encode('utf-8'), session_id=value['session_id'],
        tool_name=value['tool_name'], tool_use_id=value['tool_use_id'])


def call_document(call):
    if type(call) is not c.ObservedCall:
        raise ValueError('serialization requires a complete actually admitted call')
    result = asdict(call)
    result['input_json'] = call.input_json.decode('utf-8')
    return result
