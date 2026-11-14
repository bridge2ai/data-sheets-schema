"""Input-only native stage capture and saved replay.

The reader accepts only S-owned roles and exact captured pins. Observation
references name actual complete stream prefixes, never future stream hashes.
Live callers and the saved replay use the same closed observation joins.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath
import re
import os
import shlex

from . import native_shared_contract as c
from . import native_shared_evidence as evidence
from . import native_shared_streams as live_streams
from . import native_shared_observations as observed
from . import native_shared_stage as stage
from . import native_shared_receipts as receipt_api

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
    'initialized': {'initialize_sent', 'initialize_ack', 'native_init', 'stream_files'},
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
        if role in ('phase1_full', 'phase1_core', 'phase1_receipt'):
            limit = min(limit, self.selection.bounds()['max_input_bytes'])
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
            if kind == 'request_admitted':
                cursor = c.StageCursor(**c.exact(payload['cursor'], {'ordinal', 'kind', 'target_id'},
                                                 'captured request cursor'))
                # These fixed-role outputs are published beside the first
                # worker/integration request, not in a stage_checked record.
                # The pure replay reconstructs and compares their exact bytes;
                # capture must retain them before that comparison can run.
                role = {'worker': 'packet', 'integration': 'typed_index'}.get(cursor.kind)
                if role is not None:
                    found = self.read(role, self.selection.role(role))
                    artifacts[found.pin.path] = found
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
    if kind == 'initialized':
        live_streams.identities(payload['stream_files'])
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
    if kind == 'initialized':
        anchors = live_streams.identities(doc['payload']['stream_files'])
        members = tuple(pool.member(dict(pool.stream_bindings)[
            evidence.stream_id(execution.execution.pin.sha256, role, doc[role + '_prefix']['path'])])
            for role in live_streams.ROLES)
        if anchors != live_streams.stream_files(members):
            raise ValueError('initialized stream files differ from captured physical identities')
    transcript = pool.prefix(doc['transcript_prefix'], execution_sha256=execution.execution.pin.sha256)
    control = pool.prefix(doc['control_prefix'], execution_sha256=execution.execution.pin.sha256)
    # Saved replay reads the captured outer-v2 wire without consulting live
    # files. Only activation/live capture perform execution admission.
    from .native_shared_controller import captured_execution_body
    execution_value = captured_execution_body(execution.execution.raw)
    if (transcript.path != str(Path(execution_value['attempt_directory']) / 'transcript.jsonl')
            or control.path != str(Path(execution_value['attempt_directory']) / 'control.jsonl')):
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


def _captured(role, path, raw):
    return c.CapturedArtifact(c.ArtifactPin(role, path, len(raw), c.sha(raw)), raw)


def _document(raw, label):
    return c.strict_json(raw, label, c.HARD_LIMITS['request_bytes'])


def _prefix(member, endpoint=None):
    item = member.captured
    end = len(item.raw) if endpoint is None else endpoint
    if type(end) is not int or not 0 <= end <= len(item.raw):
        raise ValueError('observed stream endpoint exceeds its captured bytes')
    raw = item.raw[:end]
    return c.EvidencePrefix(item.pin.role, item.pin.path, raw, len(raw), c.sha(raw), raw.count(b'\n'))


_THROUGH_CACHE = {}


def _through(prefix, line):
    if type(line) is not int or not 0 <= line <= prefix.lines:
        raise ValueError('observation line is outside the captured prefix')
    if line == prefix.lines:
        return prefix
    key = (prefix.sha256, prefix.stream, prefix.path, line)
    cached = _THROUGH_CACHE.get(key)
    if cached is not None and cached[0] is prefix.raw:
        return cached[1]
    pos = 0
    for _ in range(line):
        pos = prefix.raw.index(b'\n', pos) + 1
    raw = prefix.raw[:pos]
    result = c.EvidencePrefix(prefix.stream, prefix.path, raw, len(raw), c.sha(raw), line)
    if len(_THROUGH_CACHE) > 4096:
        _THROUGH_CACHE.clear()
    _THROUGH_CACHE[key] = (prefix.raw, result)
    return result


def _observation_paths(selection):
    """The fixed ordinal namespace, never an arbitrary path or latest selector."""
    root = Path(selection.role('observations_root'))
    if not root.exists():
        return ()
    if root.is_symlink() or str(root.resolve(strict=True)) != str(root) or not root.is_dir():
        raise ValueError('observation namespace is not the selected physical directory')
    names = []
    with os.scandir(root) as entries:
        for entry in entries:
            if len(names) >= c.HARD_LIMITS['observation_records']:
                raise ValueError('native observation count exceeds its complete bound')
            if re.fullmatch(r'[0-9]{6}\.json', entry.name) is None or not entry.is_file(follow_symlinks=False):
                raise ValueError('observation namespace contains an unsupported member')
            names.append(entry.name)
    names.sort()
    if names != [f'{index:06d}.json' for index in range(len(names))]:
        raise ValueError('native observation namespace has missing or foreign ordinals')
    return tuple(str(root / name) for name in names)






@dataclass
class _CapturedRun:
    selection: c.NativeSelectionCapture
    value: dict
    composition: dict
    spec: object
    reader: _Reader
    pool: evidence.CapturePool
    transcript: c.EvidencePrefix
    control: c.EvidencePrefix
    binding: c.ExecutionBinding
    history: c.RawHistory
    observations: tuple
    phase1: object
    _catalogs: object = field(default_factory=receipt_api._ReceiptCatalogContext,
                              init=False, compare=False, repr=False)
    _trace: object = field(default=None, init=False, compare=False, repr=False)
    _prefixes: dict = field(default_factory=dict, init=False, compare=False, repr=False)
    _chronology_cache: object = field(default=None, init=False, compare=False, repr=False)
    _callback_state_cache: dict = field(default_factory=dict, init=False, compare=False, repr=False)
    _prefix: object = field(default=None, init=False, compare=False, repr=False)

    def trace(self, transcript=None, control=None):
        if (transcript is None or transcript == self.transcript) and (control is None or control == self.control):
            if self._trace is None:
                # Only this immutable capture owns the parsed trace. The U3-B
                # context exposes pure catalog/derivation reuse, not admissions
                # or previously successful observation checks.
                self._trace = observed.Trace(self.transcript, self.control,
                    session_id=self.binding.session_id, policy=self.composition['policy'], runtime=self.value['runtime'])
            return self._trace
        return observed.Trace(transcript or self.transcript, control or self.control,
            session_id=self.binding.session_id, policy=self.composition['policy'], runtime=self.value['runtime'])

    def decision(self):
        return None if self.phase1 is None else stage._prepare_next(
            self.selection, self.binding, self.phase1, self.history, self._catalogs, _prefix=self._prefix)


def _binding_document(selection, value, composition, execution, started, observation_item, session):
    return {'kind': c.KINDS['binding'], 'version': 1,
        'selection_sha256': selection.registration.pin.sha256,
        'execution': c.pin_dict(execution.pin), 'started': c.pin_dict(started.pin),
        'init_observation': c.pin_dict(observation_item.pin), 'attempt_id': value['attempt_id'], 'session_id': session,
        'instruction_sha256': value['instruction_sha256'], 'permission_sha256': value['permission_probe_sha256'],
        'runtime_declaration_sha256': composition['runtime_sha256'],
        'registered_python': composition['python'], 'working_directory': value['working_directory']}


def _binding(selection, value, composition, reader, pool):
    execution = reader.read('execution_capture', selection.role('execution_capture'))
    started = reader.read('started_capture', selection.role('started_capture'))
    binding = reader.read('session_binding', selection.role('session_binding'))
    doc = _document(binding.raw, 'actual session binding')
    init = reader.pinned(doc['init_observation'])
    expected = _binding_document(selection, value, composition, execution, started, init, doc.get('session_id'))
    if binding.raw != c.canonical(expected):
        raise ValueError('session binding differs from its selected E/S/started authorities')
    runtime = _captured('runtime_declaration', composition['runtime_path'], composition['runtime_raw_json'].encode('utf-8'))
    result = c.ExecutionBinding(attempt_id=value['attempt_id'], binding_artifact=binding,
        execution=execution, init_observation=init, instruction_sha256=value['instruction_sha256'],
        permission_sha256=value['permission_probe_sha256'], registered_python=composition['python'],
        runtime_declaration=runtime, runtime_declaration_sha256=composition['runtime_sha256'],
        selection_sha256=selection.registration.pin.sha256, session_id=doc['session_id'], started=started,
        working_directory=value['working_directory'])
    observation_doc, transcript, control = observation(init, selection, result, pool)
    session, sent, ack, initialized = observed.initialization(transcript, control,
        policy=composition['policy'], runtime=value['runtime'])
    if (session != result.session_id or observation_doc['observation_type'] != 'initialized'
            or observation_doc['payload'] != {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack), 'native_init': asdict(initialized),
                'stream_files': live_streams.stream_files(tuple(pool.member(member_id)
                    for _, member_id in pool.stream_bindings))}):
        raise ValueError('session binding lacks exact actual initialization observations')
    return result


def _phase1(selection, execution, history, reader, *, _rows=None):
    rows = _rows if _rows is not None else stage._history(selection, execution, history)[0]
    full = [row['payload'] for row in rows if row['record_type'] == 'phase1_sealed']
    core = [row['payload'] for row in rows if row['record_type'] == 'core_sealed']
    if not full:
        if core:
            raise ValueError('core was sealed before full/original receipt')
        return None
    if len(full) != 1 or len(core) > 1:
        raise ValueError('native originals have duplicate seal records')
    one = full[0]
    first = reader.pinned(one['seal'])
    originals = (reader.pinned(one['full']), reader.pinned(one['original_receipt']))
    full_observation = reader.pinned(one['observation'])
    sealed = _document(first.raw, 'phase1 seal')
    if sealed != {'kind': 'd4d_native_shared_phase1_seal', 'version': 1,
            'selection_sha256': selection.registration.pin.sha256, 'execution_sha256': execution.execution.pin.sha256,
            'session_id': execution.session_id, 'full': one['full'], 'original_receipt': one['original_receipt'],
            'observation': one['observation']}:
        raise ValueError('phase1 seal differs from its exact original bytes and observation')
    values = {'core': None, 'core_seal': None, 'core_seal_observation': None}
    if core:
        two = core[0]
        values = {'core': reader.pinned(two['core']), 'core_seal': reader.pinned(two['seal']),
                  'core_seal_observation': reader.pinned(two['observation'])}
        if _document(values['core_seal'].raw, 'core seal') != {
                'kind': 'd4d_native_shared_core_seal', 'version': 1,
                'selection_sha256': selection.registration.pin.sha256, 'execution_sha256': execution.execution.pin.sha256,
                'session_id': execution.session_id, 'phase1_seal_sha256': first.pin.sha256,
                'core': two['core'], 'observation': two['observation']}:
            raise ValueError('core seal differs from its exact derived bytes and observation')
    return c.Phase1Capture(full=originals[0], original_receipt=originals[1], seal=first,
        full_seal_observation=full_observation, **values)


def _streams(value, *, transcript_bytes=None, control_bytes=None):
    members, prefixes = [], []
    for role, endpoint in (('transcript', transcript_bytes), ('control', control_bytes)):
        member = evidence.read_regular(str(Path(value['attempt_directory']) / (role + '.jsonl')),
            role, max_bytes=c.HARD_LIMITS['stream_bytes'])
        members.append(member)
        prefixes.append(_prefix(member, endpoint))
    return tuple(members), tuple(prefixes)


def _live_streams(value, *, stream_files, transcript_bytes=None, control_bytes=None):
    anchors = live_streams.identities(stream_files)
    members, prefixes = [], []
    for role, endpoint in (('transcript', transcript_bytes), ('control', control_bytes)):
        member = live_streams.read_live_stream(
            str(Path(value['attempt_directory']) / (role + '.jsonl')), role,
            max_bytes=c.HARD_LIMITS['stream_bytes'], identity=anchors[role])
        members.append(member)
        prefixes.append(live_streams.prefix(member, endpoint))
    return tuple(members), tuple(prefixes)


def _declared_stream_files(selection, reader):
    # This early declaration can only restrict an opened identity. _binding
    # subsequently verifies every E/S/init/prefix join before any effect.
    binding = _document(reader.read('session_binding', selection.role('session_binding')).raw,
                        'actual session binding')
    init = reader.pinned(binding['init_observation'])
    doc = c.strict_json(init.raw, 'initialized observation', c.HARD_LIMITS['metadata_record_bytes'])
    c.exact(doc, _OBSERVATION_KEYS, 'initialized observation')
    if doc['observation_type'] != 'initialized':
        raise ValueError('stream identity must come from the initialized observation')
    c.exact(doc['payload'], _OBSERVATION_PAYLOADS['initialized'], 'initialized payload')
    return live_streams.identities(doc['payload']['stream_files'])



def _pool(reader, streams):
    members = tuple(reader.members.values()) + tuple(streams)
    unique = {member.member_id: member for member in members}
    execution = reader.read('execution_capture', reader.selection.role('execution_capture'))
    return evidence.CapturePool(tuple(unique.values()), tuple((
        evidence.stream_id(execution.pin.sha256, member.captured.pin.role, member.captured.pin.path),
        member.member_id) for member in streams))



def _journal_prefix_digest(run, end):
    key = (run.selection.registration.pin.sha256, run.binding.execution.pin.sha256,
           run.binding.attempt_id, end, run.history.records[end - 1].pin)
    prefixes = getattr(run, '_prefixes', None)
    if prefixes is not None and key in prefixes:
        return prefixes[key]
    raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,
        execution_sha256=run.binding.execution.pin.sha256, attempt_id=run.binding.attempt_id,
        records=tuple(item.pin for item in run.history.records[:end]))
    pair = (c.sha(raw), raw)
    if prefixes is not None:
        prefixes[key] = (pair[0], None)
    return pair


def _history_prefix(run, digest):
    """Resolve an exact recorded predecessor; never substitute current history."""
    found = []
    for end in range(1, len(run.history.records) + 1):
        prefix_digest, raw = _journal_prefix_digest(run, end)
        if prefix_digest == digest:
            if raw is None:
                raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,
                    execution_sha256=run.binding.execution.pin.sha256, attempt_id=run.binding.attempt_id,
                    records=tuple(item.pin for item in run.history.records[:end]))
            found.append(replace(run.history, journal=_captured('journal', run.selection.role('journal'), raw),
                                 records=run.history.records[:end]))
    if len(found) != 1:
        raise ValueError('observation does not name one exact actual journal prefix')
    return found[0]


def _decision_at(run, digest):
    history = _history_prefix(run, digest)
    phase1 = _phase1(run.selection, run.binding, history, run.reader)
    if phase1 is None:
        raise ValueError('stage observation precedes actual phase1 seal')
    return stage._prepare_next(run.selection, run.binding, phase1, history, run._catalogs, _prefix=run._prefix)


def _require_completed_read_before_write(request, read):
    """Both native Write announcements must follow the actual delivered Read."""
    if (request.call.line <= read.result_event.line
            or request.callback.line <= read.result_event.line):
        raise ValueError('response Write precedes its complete current request Read')


def _bind_trace_cache(trace, settled_cache, base=None):
    if settled_cache is None or trace is None:
        return trace
    owner = base if base is not None else trace

    def request(identity, _trace=trace, _owner=owner):
        if identity not in _trace.calls or identity not in _trace.callbacks:
            return observed.Trace.request(_trace, identity)
        key = ('request', identity)
        if key not in settled_cache:
            settled_cache[key] = observed.Trace.request(_owner, identity)
        return settled_cache[key]

    def admitted(identity, _trace=trace, _owner=owner):
        if (identity not in _trace.calls or identity not in _trace.callbacks
                or identity not in _trace.decisions
                or _trace.decisions[identity][1]['classification'] != 'prescribed'):
            return observed.Trace.admitted(_trace, identity)
        key = ('admitted', identity)
        if key not in settled_cache:
            settled_cache[key] = observed.Trace.admitted(_owner, identity)
        return settled_cache[key]

    def settled(identity, _trace=trace, _owner=owner):
        if (identity not in _trace.calls or identity not in _trace.callbacks
                or identity not in _trace.decisions or identity not in _trace.results
                or _trace.decisions[identity][1]['classification'] != 'prescribed'
                or _trace.results[identity][0] <= _trace.callbacks[identity][0]):
            return observed.Trace.settled(_trace, identity)
        key = ('settled', identity)
        if key not in settled_cache:
            settled_cache[key] = observed.Trace.settled(_owner, identity)
        return settled_cache[key]

    trace.request = request
    trace.admitted = admitted
    trace.settled = settled
    return trace


def _prefix_trace(base, transcript, control, init_lines=None, settled_cache=None):
    """Project an already-verified Trace onto an exact earlier stream prefix."""
    if (base is None or transcript.stream != 'transcript' or control.stream != 'control'
            or not base.transcript.raw.startswith(transcript.raw)
            or not base.control.raw.startswith(control.raw)
            or init_lines is None or transcript.lines < init_lines[0] or control.lines < init_lines[1]):
        return None
    t_lines, c_lines = transcript.lines, control.lines
    for identity, (d_line, _) in base.decisions.items():
        if d_line <= c_lines and base.callbacks[identity][0] > t_lines:
            return None
    if transcript == base.transcript and control == base.control and settled_cache is None:
        return base
    sub = object.__new__(observed.Trace)
    sub.transcript, sub.control = transcript, control
    sub.session, sub.policy = base.session, base.policy
    sub.calls = {k: v for k, v in base.calls.items() if v[0] <= t_lines}
    sub.callbacks = {k: v for k, v in base.callbacks.items() if v[0] <= t_lines}
    sub.results = {k: v for k, v in base.results.items() if v[0] <= t_lines}
    sub.decisions = {k: v for k, v in base.decisions.items() if v[0] <= c_lines}
    sub.frames = {k: v for k, v in base.frames.items() if k <= t_lines}
    sub.terminal = base.terminal if (base.terminal is not None and base.terminal <= t_lines) else None
    return _bind_trace_cache(sub, settled_cache, base=base)


def _checked_observations(run):
    """Validate raw joins and current-request chronology, not saved success flags."""
    previous = {'transcript': 0, 'control': 0}
    seen_reads, seen_intents, seen_writes, seen_advances = {}, {}, set(), {}
    settled_advances = set()
    checked = []
    previous_decision = None
    base_trace = None
    base_attempted = False
    init_lines = None
    settled_cache = {}
    start = 0
    state = None if run._prefix is None else run._prefix.observation_checkpoint()
    if state is not None:
        start, prior, reads, intents, writes, advances, settled, init_lines = state
        previous = dict(prior)
        seen_reads, seen_intents = dict(reads), dict(intents)
        seen_writes, seen_advances = set(writes), dict(advances)
        settled_advances = set(settled)

    def decision_at(digest):
        # This invocation owns one immutable captured run. Reuse only the
        # immediately preceding successful reconstruction; every observation's
        # raw joins and causal checks below still run. Never reuse across loads.
        nonlocal previous_decision
        if previous_decision is not None and previous_decision[0] == digest:
            return previous_decision[1]
        previous_decision = None
        value = _decision_at(run, digest)
        if value.state != 'failed':
            previous_decision = (digest, value)
        return value

    def trace_at(transcript, control):
        nonlocal base_trace, base_attempted, settled_cache
        if not base_attempted and init_lines is not None:
            base_attempted = True
            try:
                base_trace = run.trace()
                _bind_trace_cache(base_trace, settled_cache)
            except ValueError:
                base_trace = None
        projected = _prefix_trace(base_trace, transcript, control, init_lines, settled_cache)
        if projected is not None:
            return projected
        return run.trace(transcript, control)

    for index, artifact in enumerate(run.observations):
        if index < start:
            continue
        doc, transcript, control = observation(artifact, run.selection, run.binding, run.pool)
        for prefix in (transcript, control):
            if prefix.bytes < previous[prefix.stream]:
                raise ValueError('durable observation prefixes move backwards')
            previous[prefix.stream] = prefix.bytes
        kind, payload = doc['observation_type'], doc['payload']
        if (index == 0) != (kind == 'initialized'):
            raise ValueError('durable observations lack one first actual initialization')
        if kind == 'initialized':
            trace = run.trace(transcript, control)
            init_lines = (transcript.lines, control.lines)
            if artifact != run.binding.init_observation:
                raise ValueError('initial observation differs from bound session')
        else:
            trace = trace_at(transcript, control)
        if kind == 'initialized':
            pass
        elif kind in ('request_read', 'response_written', 'advance_settled'):
            call = _call(payload['call'])
            actual = trace.settled(call.tool_use_id)
            if (actual.call != call or asdict(actual.result) != payload['result']
                    or asdict(actual.result_event) != payload['result_event']):
                raise ValueError('settled observation does not match actual raw tool events')
            if kind == 'request_read':
                request = run.reader.pinned(payload['request'])
                current = decision_at(payload['history_sha256'])
                if current.state != 'awaiting_response' or current.request != request:
                    raise ValueError('Read observation names a stale or unpublished request')
                observed.complete_request_read(trace, actual, request)
                if call.tool_use_id in seen_reads or request.pin.path in {row[1].pin.path for row in seen_reads.values()}:
                    raise ValueError('current request has duplicate delivered-read authority')
                seen_reads[call.tool_use_id] = (artifact, request, current, call)
            elif kind == 'response_written':
                intent = seen_intents.get(payload['intent_observation']['sha256'])
                if intent is None or c.pin_dict(intent[0].pin) != payload['intent_observation']:
                    raise ValueError('response result lacks the preceding exact Write intent')
                response = run.reader.pinned(payload['response'])
                intent_doc = intent[1]
                if (call.tool_use_id != intent_doc['tool_use_id'] or call.input_json.decode('utf-8') != intent_doc['input_json']
                        or payload['history_sha256'] != intent_doc['history_sha256']
                        or response.pin.path != intent_doc['response']['path'] or response.pin.path in seen_writes):
                    raise ValueError('response was replaced, retried or moved to another stage')
                observed.first_response_write(trace, actual, response, intent_input_json=call.input_json)
                seen_writes.add(response.pin.path)
            else:
                result = payload['advance_result']
                if call.tool_use_id not in seen_advances or call.tool_use_id in settled_advances:
                    raise ValueError('advance settlement lacks actual earlier selected admission')
                observed.helper_result(trace, actual, result)
                _check_advance_acknowledgement(run, actual, result,
                    before_history_sha256=seen_advances[call.tool_use_id])
                settled_advances.add(call.tool_use_id)
        elif kind == 'response_intent':
            current = decision_at(payload['history_sha256'])
            request = trace.request(payload['tool_use_id'])
            if (asdict(request.call) != payload['call'] or asdict(request.callback) != payload['callback']
                    or request.tool_name != 'Write' or request.input_json.decode('utf-8') != payload['input_json']
                    or current.state != 'awaiting_response' or current.request is None or current.response is None
                    or c.pin_dict(current.request.pin) != payload['request'] or asdict(current.response) != payload['response']):
                raise ValueError('Write intent differs from actual current request/callback')
            reads = [row for row in seen_reads.values() if c.pin_dict(row[0].pin) == payload['read_observation']]
            if len(reads) != 1 or reads[0][1] != current.request or current.response.path in {v[1]['response']['path'] for v in seen_intents.values()}:
                raise ValueError('Write intent reuses a stale Read or spent response destination')
            inputs = _document(request.input_json, 'Write intent')
            if (set(inputs) != {'file_path', 'content'} or inputs['file_path'] != current.response.path
                    or type(inputs['content']) is not str or not inputs['content']
                    or len(inputs['content'].encode('utf-8')) > current.response.max_bytes):
                raise ValueError('Write intent exceeds the exact response contract')
            read_call = reads[0][3]
            _require_completed_read_before_write(request, trace.settled(read_call.tool_use_id))
            seen_intents[artifact.pin.sha256] = (artifact, payload)
        elif kind == 'advance_admitted':
            call = _call(payload['call'])
            actual = trace.current_advance(call.tool_use_id, run.composition['policy']['native_shared_helpers']['advance'])
            if actual != call or call.tool_use_id in seen_advances:
                raise ValueError('advance admission repeats or differs from the actual pending callback')
            _history_prefix(run, payload['before_history_sha256'])
            seen_advances[call.tool_use_id] = payload['before_history_sha256']
        elif kind in ('phase1_sealed', 'core_sealed'):
            if type(payload['helper_calls']) is not list or not payload['helper_calls']:
                raise ValueError('seal lacks actual settled helper identities')
            for identity in payload['helper_calls']:
                trace.settled(identity)
            names = ('full', 'original_receipt') if kind == 'phase1_sealed' else ('core',)
            for name in names:
                run.reader.pinned(payload[name])
        else:
            raise ValueError('unsupported durable native observation')
        checked.append((artifact, doc, transcript, control))
    if run._prefix is not None:
        run._prefix.observation_state = (len(run.observations), previous,
            seen_reads, seen_intents, seen_writes, seen_advances, settled_advances, init_lines)
    return tuple(checked)





def _loaded(base, streams, prefixes, *, _catalogs=None, _prefix_owner=None):
    selection, reader, value, composition, spec = base
    transcript, control = prefixes
    observations = tuple(reader.read('observation', path) for path in _observation_paths(selection))
    pool = _pool(reader, streams)
    binding = _binding(selection, value, composition, reader, pool)
    history = reader.history(binding)
    # The complete closed observation catalog includes pre-grant intents that
    # intentionally cannot yet be referenced by response-consumed records.
    history = replace(history, observations=observations)
    phase1 = _phase1(selection, binding, history, reader)
    run = _CapturedRun(selection, value, composition, spec, reader, _pool(reader, streams),
                       transcript, control, binding, history, observations, phase1)
    if _catalogs is not None:
        run._catalogs = receipt_api._catalog_context(_catalogs)
    if _prefix_owner is not None:
        run._prefix = _prefix_owner.begin(run)
    _checked_observations(run)
    if run._prefix is not None:
        # Do not publish historical observation checkpoints before the current
        # stage suffix has also reconstructed successfully.
        current = run.decision()
        if current is None or current.state != 'failed':
            run._prefix.commit()
    return run






def _chronology(run):
    key = (tuple(item.pin for item in run.observations), tuple(item.pin for item in run.history.records))
    cached = getattr(run, '_chronology_cache', None)
    if cached is not None and cached[0] == key:
        return cached[1]
    catalog = {}
    advance_before, advance_after = {}, {}
    visible = {run.history.records[0].pin.sha256: 0}
    seal_observations = {}
    for item in run.observations:
        doc, transcript, _ = observation(item, run.selection, run.binding, run.pool)
        catalog[item.pin.sha256] = (doc, transcript.lines)
        payload = doc['payload']; kind = doc['observation_type']
        if kind == 'advance_admitted':
            advance_before[payload['call']['tool_use_id']] = payload['before_history_sha256']
        elif kind == 'advance_settled':
            identity = payload['call']['tool_use_id']
            advance_after[identity] = payload['advance_result']['after_history_sha256']
            for pin in payload['advance_result']['publications']:
                if pin['role'] == 'record':
                    if pin['sha256'] in visible:
                        raise ValueError('stage record has duplicate publication observations')
                    visible[pin['sha256']] = transcript.lines
        elif kind in ('phase1_sealed', 'core_sealed'):
            seal_observations[transcript.lines] = (kind, payload)
    for item in run.history.records:
        row = _document(item.raw, 'stage chronology'); payload = row['payload']
        role = {'session_bound': 'init_observation', 'phase1_sealed': 'observation',
                'core_sealed': 'observation', 'response_consumed': 'response_observation'}.get(row['record_type'])
        if role is not None:
            pin = payload[role]
            if pin['sha256'] not in catalog:
                raise ValueError('stage record lacks its actual observation visibility')
            visible[item.pin.sha256] = catalog[pin['sha256']][1]
    result = (catalog, advance_before, advance_after, visible, seal_observations)
    run._chronology_cache = (key, result)
    return result


def _require_initial_seal_identity(run, report, full, receipt):
    """Bind the checked helper result to the exact original bytes, live or saved."""
    from .native_shared_phase import initial_input_identity
    checks = [row for row in report['checks']
              if row['helper'] == 'phase1_receipts' and row['exit_code'] == 0]
    if not checks:
        raise ValueError('original seal lacks a successful initial receipt helper')
    trace = run.trace()
    actual = trace.settled(checks[-1]['tool_use_id'])
    block = evidence.event(trace.transcript, actual.result)
    value = _document(block['content'].encode('utf-8'), 'initial receipt helper result')
    observed.helper_result(trace, actual, value)
    identity = initial_input_identity(value.get('native_initial_inputs'))
    expected = {'selection_sha256': run.selection.registration.pin.sha256,
                'full_sha256': c.sha(full.raw), 'receipt_sha256': c.sha(receipt.raw)}
    if identity != expected:
        raise ValueError('original seal bytes differ from checked initial receipt inputs')


def phase_replay(run, *, complete=False):
    """Freshly run the actual phase machine over observed journal visibility."""
    from .native_shared_phase import PhaseState
    from .native_shared_render import commands
    paths = run.spec._agentic_artifact_paths
    phase = PhaseState(commands(run.spec), full_path=paths['full'], core_path=paths['core'],
        report_path=paths['report'], receipt_path=paths['receipt'], working_directory=run.binding.working_directory)
    catalog, advance_before, advance_after, visible, seal_observations = _chronology(run)
    actions = {}
    previous = None

    def decision_at(digest):
        # One immutable result for this captured run and this replay only.
        # Release the previous buffers on a transition; never retain failures.
        nonlocal previous
        if previous is not None and previous[0] == digest:
            return previous[1]
        previous = None
        value = _decision_at(run, digest)
        if value.state != 'failed':
            previous = (digest, value)
        return value

    cached_trace = getattr(run, '_trace', None)
    rows = (((line, None, frame) for line, frame in cached_trace.frames.items())
            if cached_trace is not None and cached_trace.transcript == run.transcript
            else observed.rows(run.transcript))
    for line, _, frame in rows:
        count = 0
        for item in run.history.records:
            if item.pin.sha256 not in visible or visible[item.pin.sha256] >= line:
                break
            count += 1
        digest = None
        if count >= 3:
            digest = _journal_prefix_digest(run, count)[0]
        blocks = frame.get('message', {}).get('content', [])
        for block in blocks if type(blocks) is list else ():
            if type(block) is not dict:
                continue
            identity = block.get('id') if block.get('type') == 'tool_use' else block.get('tool_use_id')
            if block.get('type') == 'tool_use' and identity in advance_before:
                digest = advance_before[identity]
            if block.get('type') == 'tool_result' and identity in advance_after:
                digest = advance_after[identity]
        decision = None if digest is None else decision_at(digest)
        emitted = phase.observe(frame, stage_decision=decision)
        if emitted:
            actions[line] = (emitted, phase.report())
        if line in seal_observations:
            kind, payload = seal_observations[line]
            needed = 'seal_phase1' if kind == 'phase1_sealed' else 'seal_core'
            if needed not in emitted:
                raise ValueError('sealed originals lack the actual settled phase boundary')
            expected = [row['tool_use_id'] for row in phase.report()['checks']
                        if row['helper'] in ({'chunk_check', 'source_scope', 'full_schema', 'full_terms', 'phase1_receipts'}
                                            if needed == 'seal_phase1' else {'derive_core', 'core_schema', 'pair'})]
            if payload['helper_calls'] != expected:
                raise ValueError('seal helper identities differ from actual phase observations')
            if kind == 'phase1_sealed':
                _require_initial_seal_identity(run, phase.report(),
                    run.reader.pinned(payload['full']), run.reader.pinned(payload['original_receipt']))
    if complete and set(visible) != {item.pin.sha256 for item in run.history.records}:
        raise ValueError('completed history has unpublished or unobserved stage records')
    return phase.report(complete=complete), actions



def current_effect_view(run, *, correction_window=False, exclude_pending=None):
    """Derive the restrictive overlay solely from captured state and events."""
    return _effect_view_from_decision(run, run.decision(),
        correction_window=correction_window, exclude_pending=exclude_pending)


def _effect_view_from_decision(run, decision, *, correction_window=False, exclude_pending=None):
    """Use a decision just derived by the fixed caller from this captured run.

    No result is retained across calls. The public wrapper always derives its
    own decision; the controller can pass the one it just checked for this
    event before granting an effect. All view and chronology checks stay here.
    """
    state = decision.state if decision is not None else 'request_ready'
    request = decision.request if decision is not None else None
    response = decision.response if decision is not None else None
    read = intent = None
    if decision is not None and state == 'awaiting_response':
        for item in run.observations:
            doc = _document(item.raw, 'stage observation'); payload = doc['payload']
            if payload.get('history_sha256') != run.history.journal.pin.sha256:
                continue
            if doc['observation_type'] == 'request_read' and payload['request'] == c.pin_dict(request.pin):
                read = item.pin.sha256
            elif doc['observation_type'] == 'response_intent' and payload['request'] == c.pin_dict(request.pin):
                intent = item.pin.sha256
        # A consumed response remains spent even after journal advancement.
        request_hash = c.strict_json(request.raw, max_bytes=run.selection.bounds()['max_request_bytes'])['request_sha256']
        for row in stage._history(run.selection, run.binding, run.history)[0]:
            if row['record_type'] == 'response_consumed' and row['payload']['request_sha256'] == request_hash:
                pin = row['payload']['response_observation']
                intent = pin['sha256']
    protected = list(run.selection.roles)
    protected += [c.RolePath('authority_' + str(index), path) for index, path in enumerate(
        run.composition['policy']['readonly_lookups']['inputs']) if path not in {role.path for role in protected}]
    if run.phase1 is not None:
        protected.append(c.RolePath('sealed_original_receipt_output', run.spec._agentic_artifact_paths['receipt']))
    trace = run.trace()
    pending = [identity for identity in trace.pending() if identity != exclude_pending
               and trace.calls[identity][2].get('input', {}).get('command') == run.composition['policy']['native_shared_helpers']['advance']]
    if len(pending) > 1:
        raise ValueError('overlapping selected advance effects')
    return c.NativeEffectView(correction_window=correction_window, cursor=None if decision is None else decision.cursor,
        execution_binding_sha256=run.binding.binding_artifact.pin.sha256, history_sha256=run.history.journal.pin.sha256,
        pending_advance_tool_use_id=pending[0] if pending else None, protected_roles=tuple(protected),
        protocol=c.NAME, request=None if request is None else request.pin,
        request_read_observation_sha256=read, response=response, response_intent_observation_sha256=intent,
        sealed=() if decision is None else decision.sealed, selection_sha256=run.selection.registration.pin.sha256,
        stage_command=run.composition['policy']['native_shared_helpers']['advance'], stage_root=run.selection.role('stage_root'),
        state=state, static_policy_sha256=run.composition['policy_sha256'], working_directory=run.binding.working_directory)






def _check_advance_acknowledgement(run, actual, result, *, before_history_sha256):
    """Reconstruct one acknowledgement from captured inputs in live and saved reads.

    Earlier saved acknowledgements name their own journal version, not the
    final run journal. No saved verdict or claimed publication list is reused.
    """
    c.exact(result, {'kind', 'version', 'selection_sha256', 'execution_sha256', 'attempt_id', 'session_id',
        'advance_tool_use_id', 'before_history_sha256', 'after_history_sha256', 'state', 'publications'}, 'advance acknowledgement')
    expected = {'kind': c.KINDS['advance_result'], 'version': 1,
        'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
        'attempt_id': run.binding.attempt_id, 'session_id': run.binding.session_id,
        'advance_tool_use_id': actual.call.tool_use_id, 'before_history_sha256': before_history_sha256}
    if any(type(result[key]) is not type(value) or result[key] != value for key, value in expected.items()):
        raise ValueError('advance acknowledgement identity differs from selected admission')
    before = _history_prefix(run, before_history_sha256)
    phase1 = _phase1(run.selection, run.binding, before, run.reader)
    replay = stage._Replay(run.selection, run.binding, phase1, before, _catalogs=run._catalogs, _prefix=run._prefix).run()
    if replay.pending is not None and replay.pending[-1] is not None:
        response, _ = replay.pending[-1]
        proposal = stage._check_response(run.selection, run.binding, phase1, before, replay.pending[2].raw,
            response.raw, run._catalogs, _prefix=run._prefix)
        publications = (*proposal.publications, *(c.HelperPublication('create_once', item, None) for item in proposal.records_to_append),
            c.HelperPublication('replace_journal_from_exact_predecessor', proposal.predicted_journal, before.journal.pin.sha256))
    else:
        publications = stage._prepare_next(run.selection, run.binding, phase1, before,
            run._catalogs, _prefix=run._prefix).publications
    expected_publications = [c.pin_dict(item.artifact.pin) for item in publications]
    if type(result['publications']) is not list or c.canonical(result['publications']) != c.canonical(expected_publications):
        raise ValueError('advance result does not describe every freshly derived actual effect')
    journals = [item.artifact for item in publications if item.artifact.pin.role == 'journal']
    if len(journals) > 1:
        raise ValueError('advance reconstruction has more than one resulting journal')
    after = journals[0] if journals else before.journal
    if result['after_history_sha256'] != after.pin.sha256:
        raise ValueError('advance acknowledgement differs from reconstructed resulting journal')
    after_history = _history_prefix(run, after.pin.sha256)
    # The observed journal is CapturedArtifact; the derived effect is
    # ProposedArtifact. Require exact pin and bytes, not carrier-class equality.
    if after_history.journal.pin != after.pin or after_history.journal.raw != after.raw:
        raise ValueError('advance acknowledgement journal bytes differ from captured history')
    if result['state'] != _decision_at(run, after.pin.sha256).state:
        raise ValueError('advance acknowledgement differs from reconstructed resulting state')
    for item in publications:
        actual_file = (after_history.journal if item.artifact.pin.role == 'journal' else
            run.reader.read(item.artifact.pin.role, item.artifact.pin.path, item.artifact.pin))
        if actual_file.raw != item.artifact.raw:
            raise ValueError('advance published bytes differ from fresh pure reconstruction')





from .native_shared_current import current_artifact


def _receipt_assessment(run, *, full_path, receipt_path):
    from . import native_shared_receipts as receipts
    from . import native_shared_selection as selection_api
    paths = run.spec._agentic_artifact_paths
    if (str(full_path) != paths['full'] or str(receipt_path) != paths['receipt']):
        raise ValueError('receipt caller paths differ from the exact execution-selected outputs')
    full = current_artifact(run, 'final_full', paths['full'])
    original = current_artifact(run, 'original_receipt_output', paths['receipt'])
    if run.phase1 is None:
        block = receipts.check_initial(run.selection, full_raw=full.raw, receipt_raw=original.raw)
        return block, full, original
    if original.raw != run.phase1.original_receipt.raw:
        raise ValueError('selected ordinary receipt changed from the exact sealed original')
    fresh_selection = selection_api.rebuild(run.selection.registration, run.selection.authority,
                                           run.selection.schemas, run.selection.receipt_policy)
    if fresh_selection != run.selection:
        raise ValueError('final receipt selection differs from independent reconstruction')
    # Final reconstruction must not reuse the live run's catalog context.
    if (stage.prepare_next is getattr(stage, '_DEFAULT_PREPARE_NEXT', None)
            and stage.check_assembly is getattr(stage, '_DEFAULT_CHECK_ASSEMBLY', None)
            and receipts.check_final is getattr(receipts, '_DEFAULT_CHECK_FINAL', None)):
        fresh_catalogs = receipts._catalog_context()
        decision = stage._prepare_next(fresh_selection, run.binding, run.phase1, run.history, fresh_catalogs)
        if decision.state != 'assembly_complete' or decision.completion is None:
            raise ValueError('final native receipts require the freshly checked complete stage history')
        completion = stage._check_assembly(fresh_selection, run.binding, run.phase1, run.history,
                                           decision.completion.assembly.raw, fresh_catalogs)
        assessed = completion.effective_receipt
        block = receipts._check_final(fresh_selection, run.binding, run.phase1, completion,
                                      final_full=full.raw, final_receipt=assessed.raw, _catalogs=fresh_catalogs)
    else:
        decision = stage.prepare_next(fresh_selection, run.binding, run.phase1, run.history)
        if decision.state != 'assembly_complete' or decision.completion is None:
            raise ValueError('final native receipts require the freshly checked complete stage history')
        completion = stage.check_assembly(fresh_selection, run.binding, run.phase1, run.history,
                                         decision.completion.assembly.raw)
        assessed = completion.effective_receipt
        block = receipts.check_final(fresh_selection, run.binding, run.phase1, completion,
                                    final_full=full.raw, final_receipt=assessed.raw)
    block['native_receipt_inputs'] = {'selected_original': c.pin_dict(original.pin),
        'sealed_original': c.pin_dict(run.phase1.original_receipt.pin), 'assessed_effective': c.pin_dict(assessed.pin),
        'final_full': c.pin_dict(full.pin), 'basis': 'Original caller-selected receipt preserved; reconstructed effective receipt assessed.'}
    return block, full, assessed



def _provenance_block(run):
    decision = run.decision()
    if decision is None or decision.state != 'assembly_complete' or decision.completion is None:
        raise ValueError('native provenance requires complete freshly reconstructed selected stages')
    completion = stage._check_assembly(run.selection, run.binding, run.phase1, run.history,
                                       decision.completion.assembly.raw, run._catalogs)
    artifact = run.reader.read('completion', run.selection.role('completion'))
    return {'protocol': c.NAME, 'selection_sha256': run.selection.registration.pin.sha256,
        'execution_sha256': run.binding.execution.pin.sha256, 'attempt_id': run.binding.attempt_id,
        'session_id': run.binding.session_id, 'assembly_sha256': completion.assembly.pin.sha256,
        'audit_sha256': completion.audit.pin.sha256, 'receipt_result_sha256': completion.receipt_result.pin.sha256,
        'stage_completion_sha256': artifact.pin.sha256, 'scientific_support': 'unverified evaluator declarations',
        'runtime_acceptance': 'pending independent saved readback'}








def at_callback(run, line):
    """Pure current authority at one real callback; no future observation credit."""
    catalog, _, _, visible, _ = _chronology(run)
    count = 0
    for item in run.history.records:
        if item.pin.sha256 not in visible or visible[item.pin.sha256] >= line:
            break
        count += 1
    if count < 2:
        raise ValueError('callback precedes actual session publication')
    observations = tuple(item for item in run.observations
        if catalog[item.pin.sha256][1] < line)
    state_key = (count, tuple(item.pin.sha256 for item in observations))
    cached_state = getattr(run, '_callback_state_cache', None)
    if cached_state is not None and state_key in cached_state:
        history, phase1 = cached_state[state_key]
    else:
        digest, _ = _journal_prefix_digest(run, count)
        history = replace(_history_prefix(run, digest), observations=observations)
        phase1 = _phase1(run.selection, run.binding, history, run.reader)
        if cached_state is not None:
            cached_state[state_key] = (history, phase1)
    transcript = _through(run.transcript, line)
    base_trace = None
    try:
        base_trace = run.trace()
    except ValueError:
        pass
    if base_trace is not None and 0 < line <= base_trace.transcript.lines:
        later = [d_line for identity, (d_line, _) in base_trace.decisions.items()
                 if base_trace.callbacks[identity][0] > line]
        control_lines = (min(later) - 1) if later else run.control.lines
    else:
        frames = {c.canonical(frame) for _, _, frame in observed.rows(transcript)}
        control_lines = 0
        for number, _, row in observed.rows(run.control):
            if row.get('kind') == 'decision' and c.canonical(row.get('request')) not in frames:
                break
            control_lines = number
    control = _through(run.control, control_lines)
    result = replace(run, history=history, observations=observations, transcript=transcript, control=control,
        phase1=phase1)
    result._catalogs = run._catalogs
    result._prefixes = run._prefixes
    result._chronology_cache = run._chronology_cache
    result._callback_state_cache = run._callback_state_cache
    if base_trace is not None and 0 < line <= base_trace.transcript.lines and 0 < control_lines <= base_trace.control.lines:
        result._trace = _prefix_trace(base_trace, transcript, control, (1, 1))
    return result
