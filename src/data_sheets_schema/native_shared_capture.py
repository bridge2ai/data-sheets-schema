"""Fixed native stage capture and publication boundary.

The reader accepts only S-owned roles and exact captured pins. Observation
references name actual complete stream prefixes, never future stream hashes.
Live callers and the saved replay use the same closed observation joins.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath
import re
import os
import shlex

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
    execution_value = c.strict_json(execution.execution.raw, 'captured execution', c.HARD_LIMITS['request_bytes'])
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


def _through(prefix, line):
    if type(line) is not int or not 0 <= line <= prefix.lines:
        raise ValueError('observation line is outside the captured prefix')
    raw = b''.join(part + b'\n' for part in prefix.raw.split(b'\n')[:line])
    return c.EvidencePrefix(prefix.stream, prefix.path, raw, len(raw), c.sha(raw), line)


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


def _create(selection, role, raw, *, ordinal=None):
    """Sole parent/helper create-once primitive for explicitly derived S roles."""
    from .native_attempt_supervisor import durable_new
    from .native_execution import _mkdir_durable
    if role == 'observation':
        paths = _observation_paths(selection)
        if ordinal is not None and ordinal != len(paths):
            raise ValueError('observation ordinal changed before publication')
        path = str(PurePosixPath(selection.role('observations_root')) / f'{len(paths):06d}.json')
    elif role == 'record':
        path = stage._dynamic(selection, role, ordinal)
    else:
        path = selection.role(role)
    limit = _Reader(selection).destination(role, path)
    if type(raw) is not bytes or not raw or len(raw) > limit:
        raise ValueError('selected publication exceeds its complete role bound')
    target = Path(path)
    root = Path(selection.role('stage_root'))
    if (root not in target.parents or target.resolve() != target or target.exists() or target.is_symlink()
            or not root.is_dir() or root.is_symlink() or root.resolve() != root):
        raise ValueError('native publication is not one new physical S-owned destination')
    _mkdir_durable(target.parent)
    durable_new(target, raw)
    item = evidence.read_regular(path, role, max_bytes=limit).captured
    if item.raw != raw:
        raise ValueError('published native artifact differs from its intended bytes')
    return item


def _append(selection, execution, history, kind, payload):
    """Parent record publication shares C's exact serializer and journal CAS."""
    from .native_shared_publication import _replace_journal
    records, journal = stage.append_records(selection, execution, history, ((kind, c.canonical(payload)),))
    for record in records:
        _create(selection, 'record', record.raw, ordinal=len(history.records))
    _replace_journal(Path(selection.role('journal')), history.journal, journal)


def activate(selection, execution_raw, started_raw):
    """Called only by the fixed lifetime immediately before its single dispatch.

    This writes no session declaration. The later session binding must come
    from actual initialized native/control streams.
    """
    from . import native_shared_registration as registration
    value = registration.verified(execution_raw)
    composition = _document(value['composition_raw_json'].encode('utf-8'), 'composition')
    if composition['selection_raw_json'].encode('utf-8') != selection.registration.raw:
        raise ValueError('activation E does not capture this exact selected S')
    started = _document(started_raw, 'started identity')
    if (started.get('state') != 'started' or started.get('attempt_id') != value['attempt_id']
            or started.get('registration_sha256') != c.sha(execution_raw)
            or started.get('composition_sha256') != value['composition_sha256']
            or type(started.get('dispatch_limit')) is not int or started['dispatch_limit'] != 1):
        raise ValueError('activation lacks its actual single-use started identity')
    attempt = Path(value['attempt_directory'])
    for name, expected in (('registration.json', execution_raw), ('started.json', started_raw)):
        if evidence.read_regular(str(attempt / name), 'attempt_identity', max_bytes=c.HARD_LIMITS['request_bytes']).captured.raw != expected:
            raise ValueError('activation differs from actual reserved attempt evidence')
    destinations = ('execution_capture', 'started_capture', 'journal')
    if any(Path(selection.role(role)).exists() or Path(selection.role(role)).is_symlink() for role in destinations):
        raise ValueError('native stage activation is spent and cannot be resumed')
    e = _create(selection, 'execution_capture', execution_raw)
    s = _create(selection, 'started_capture', started_raw)
    raw = stage.record_bytes(record_type='genesis', sequence=0, previous_record_sha256=None,
        selection_sha256=selection.registration.pin.sha256, execution_sha256=e.pin.sha256,
        attempt_id=value['attempt_id'], session_id=None,
        payload={'execution': c.pin_dict(e.pin), 'started': c.pin_dict(s.pin)})
    record = _create(selection, 'record', raw, ordinal=0)
    _create(selection, 'journal', stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
        execution_sha256=e.pin.sha256, attempt_id=value['attempt_id'], records=(record.pin,)))


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

    def trace(self, transcript=None, control=None):
        return observed.Trace(transcript or self.transcript, control or self.control,
            session_id=self.binding.session_id, policy=self.composition['policy'], runtime=self.value['runtime'])

    def decision(self):
        if self.phase1 is None:
            return None
        return stage.prepare_next(self.selection, self.binding, self.phase1, self.history)


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
            or observation_doc['payload'] != {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack), 'native_init': asdict(initialized)}):
        raise ValueError('session binding lacks exact actual initialization observations')
    return result


def _phase1(selection, execution, history, reader):
    rows, _ = stage._history(selection, execution, history)
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


def _base(selection_path):
    from . import native_shared_selection as selected
    from . import native_shared_registration as registration
    selection = selected.capture(selection_path)
    reader = _Reader(selection)
    e = reader.read('execution_capture', selection.role('execution_capture'))
    value = registration.verified(e.raw)
    composition, spec, doc, _ = registration._selection(value['composition_raw_json'].encode('utf-8'))
    if (doc['registration_path'] != selection_path or composition['selection_raw_json'].encode('utf-8') != selection.registration.raw
            or value['selection_sha256'] != selection.registration.pin.sha256):
        raise ValueError('actual E/C/S binding differs from the caller-selected registration')
    for filename, role in (('registration.json', 'execution_capture'), ('started.json', 'started_capture')):
        actual = evidence.read_regular(str(Path(value['attempt_directory']) / filename), role,
            max_bytes=c.HARD_LIMITS['request_bytes']).captured
        saved = reader.read(role, selection.role(role))
        if actual.raw != saved.raw:
            raise ValueError('stage binding differs from actual one-use attempt records')
    started = _document(reader.read('started_capture', selection.role('started_capture')).raw, 'started identity')
    if (started.get('state') != 'started' or started.get('attempt_id') != value['attempt_id']
            or started.get('registration_sha256') != e.pin.sha256
            or started.get('composition_sha256') != value['composition_sha256']
            or type(started.get('dispatch_limit')) is not int or started['dispatch_limit'] != 1):
        raise ValueError('selected stage does not have its actual one-use started identity')
    return selection, reader, value, composition, spec


def _pool(reader, streams):
    members = tuple(reader.members.values()) + tuple(streams)
    unique = {member.member_id: member for member in members}
    execution = reader.read('execution_capture', reader.selection.role('execution_capture'))
    return evidence.CapturePool(tuple(unique.values()), tuple((
        evidence.stream_id(execution.pin.sha256, member.captured.pin.role, member.captured.pin.path),
        member.member_id) for member in streams))


def initialize(selection_path, *, transcript_bytes, control_bytes):
    """Bind the actual parent-observed initialization, never owner summary flags."""
    selection, reader, value, composition, _ = _base(selection_path)
    streams, (transcript, control) = _streams(value, transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    session, sent, ack, init = observed.initialization(transcript, control,
        policy=composition['policy'], runtime=value['runtime'])
    if Path(selection.role('session_binding')).exists() or _observation_paths(selection):
        raise ValueError('native initialization binding is spent or repeated')
    execution = reader.read('execution_capture', selection.role('execution_capture'))
    started = reader.read('started_capture', selection.role('started_capture'))
    item = _create(selection, 'observation', observation_bytes('initialized', selection, execution.pin.sha256,
        value['attempt_id'], session, transcript, control,
        {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack), 'native_init': asdict(init)}))
    _create(selection, 'session_binding', c.canonical(_binding_document(selection, value, composition,
        execution, started, item, session)))
    reader = _Reader(selection)
    binding = _binding(selection, value, composition, reader, _pool(reader, streams))
    history = reader.history(binding)
    if len(history.records) != 1:
        raise ValueError('native session binding requires the sole prior genesis')
    _append(selection, binding, history, 'session_bound',
        {'binding': c.pin_dict(binding.binding_artifact.pin), 'init_observation': c.pin_dict(item.pin)})


def _history_prefix(run, digest):
    """Resolve an exact recorded predecessor; never substitute current history."""
    found = []
    for end in range(1, len(run.history.records) + 1):
        raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,
            execution_sha256=run.binding.execution.pin.sha256, attempt_id=run.binding.attempt_id,
            records=tuple(item.pin for item in run.history.records[:end]))
        if c.sha(raw) == digest:
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
    return stage.prepare_next(run.selection, run.binding, phase1, history)


def _checked_observations(run):
    """Validate raw joins and current-request chronology, not saved success flags."""
    previous = {'transcript': 0, 'control': 0}
    seen_reads, seen_intents, seen_writes, seen_advances = {}, {}, set(), set()
    checked = []
    for index, artifact in enumerate(run.observations):
        doc, transcript, control = observation(artifact, run.selection, run.binding, run.pool)
        for prefix in (transcript, control):
            if prefix.bytes < previous[prefix.stream]:
                raise ValueError('durable observation prefixes move backwards')
            previous[prefix.stream] = prefix.bytes
        kind, payload = doc['observation_type'], doc['payload']
        if (index == 0) != (kind == 'initialized'):
            raise ValueError('durable observations lack one first actual initialization')
        trace = run.trace(transcript, control)
        if kind == 'initialized':
            if artifact != run.binding.init_observation:
                raise ValueError('initial observation differs from bound session')
        elif kind in ('request_read', 'response_written', 'advance_settled'):
            call = _call(payload['call'])
            actual = trace.settled(call.tool_use_id)
            if (actual.call != call or asdict(actual.result) != payload['result']
                    or asdict(actual.result_event) != payload['result_event']):
                raise ValueError('settled observation does not match actual raw tool events')
            if kind == 'request_read':
                request = run.reader.pinned(payload['request'])
                current = _decision_at(run, payload['history_sha256'])
                if current.state != 'awaiting_response' or current.request != request:
                    raise ValueError('Read observation names a stale or unpublished request')
                observed.complete_request_read(trace, actual, request)
                if call.tool_use_id in seen_reads or request.pin.path in {row[1].pin.path for row in seen_reads.values()}:
                    raise ValueError('current request has duplicate delivered-read authority')
                seen_reads[call.tool_use_id] = (artifact, request, current)
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
                if result.get('advance_tool_use_id') != call.tool_use_id or call.tool_use_id not in seen_advances:
                    raise ValueError('advance settlement lacks actual earlier selected admission')
                observed.helper_result(trace, actual, result)
                _history_prefix(run, result['before_history_sha256'])
                after = _decision_at(run, result['after_history_sha256'])
                if after.state != result['state']:
                    raise ValueError('advance settlement differs from actual post-publication state')
                for pin in result['publications']:
                    if pin.get('role') == 'journal':
                        actual = _history_prefix(run, pin['sha256']).journal
                        if c.pin_dict(actual.pin) != pin:
                            raise ValueError('advance acknowledgement names another journal version')
                    else:
                        run.reader.pinned(pin)
        elif kind == 'response_intent':
            current = _decision_at(run, payload['history_sha256'])
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
            if request.call.line <= _call(c.strict_json(reads[0][0].raw)['payload']['call']).call.line:
                raise ValueError('response Write precedes its complete current request Read')
            seen_intents[artifact.pin.sha256] = (artifact, payload)
        elif kind == 'advance_admitted':
            call = _call(payload['call'])
            actual = trace.current_advance(call.tool_use_id, run.composition['policy']['native_shared_helpers']['advance'])
            if actual != call or call.tool_use_id in seen_advances:
                raise ValueError('advance admission repeats or differs from the actual pending callback')
            _history_prefix(run, payload['before_history_sha256'])
            seen_advances.add(call.tool_use_id)
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
    return tuple(checked)


def _load(selection_path, *, transcript_bytes=None, control_bytes=None):
    selection, reader, value, composition, spec = _base(selection_path)
    streams, (transcript, control) = _streams(value, transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    for path in _observation_paths(selection):
        reader.read('observation', path)
    pool = _pool(reader, streams)
    binding = _binding(selection, value, composition, reader, pool)
    history = reader.history(binding)
    observations = tuple(reader.read('observation', path) for path in _observation_paths(selection))
    # The complete closed observation catalog includes pre-grant intents that
    # intentionally cannot yet be referenced by response-consumed records.
    history = replace(history, observations=observations)
    phase1 = _phase1(selection, binding, history, reader)
    run = _CapturedRun(selection, value, composition, spec, reader, _pool(reader, streams),
                       transcript, control, binding, history, observations, phase1)
    _checked_observations(run)
    return run


def _persist_observation(run, kind, payload):
    return _create(run.selection, 'observation', observation_bytes(kind, run.selection,
        run.binding.execution.pin.sha256, run.binding.attempt_id, run.binding.session_id,
        run.transcript, run.control, payload), ordinal=len(run.observations))


def capture_stage(selection_registration_path):
    """Capture the sole pending, actually admitted fixed advance invocation."""
    run = _load(str(selection_registration_path))
    if run.phase1 is None:
        raise ValueError('advance precedes actual sealed originals')
    trace = run.trace()
    pending = trace.pending()
    if len(pending) != 1:
        raise ValueError('stage helper requires one actual pending call')
    command = run.composition['policy']['native_shared_helpers']['advance']
    call = trace.current_advance(pending[0], command)
    # A helper cannot use bytes prefetched after its own actual callback.
    transcript = _through(run.transcript, call.callback.line)
    control = _through(run.control, call.admission.line)
    candidates = [item for item in run.observations if c.strict_json(item.raw)['observation_type'] == 'advance_admitted'
                  and c.strict_json(item.raw)['payload']['call']['tool_use_id'] == call.tool_use_id]
    if not candidates:
        if sum(c.strict_json(item.raw)['observation_type'] == 'advance_admitted' for item in run.observations) >= c.HARD_LIMITS['advance_invocations']:
            raise ValueError('stage helper invocation count exceeds its complete bound')
        admission = _persist_observation(replace(run, transcript=transcript, control=control), 'advance_admitted',
            {'call': call_document(call), 'before_history_sha256': run.history.journal.pin.sha256})
    elif len(candidates) == 1:
        admission = candidates[0]
        doc, actual_transcript, actual_control = observation(admission, run.selection, run.binding, run.pool)
        if (actual_transcript != transcript or actual_control != control
                or doc['payload'] != {'call': call_document(call), 'before_history_sha256': run.history.journal.pin.sha256}):
            raise ValueError('spent advance admission cannot publish against a different journal')
    else:
        raise ValueError('duplicate advance admission identity')
    return c.StageInvocationCapture(selection=run.selection, execution=run.binding, phase1=run.phase1,
        history=run.history, current_advance=c.CurrentAdvance(admission_observation=admission,
            argv=tuple(shlex.split(command)), call=call, command=command, control_prefix=control,
            predecessor_history_sha256=run.history.journal.pin.sha256, transcript_prefix=transcript,
            working_directory=run.binding.working_directory))


def publish_stage(invocation, proposal):
    """Recheck the same current invocation, then perform only derived effects."""
    from .native_shared_publication import publish_derived
    if type(invocation) is not c.StageInvocationCapture:
        raise ValueError('publication requires the actual selected captured invocation')
    fresh = capture_stage(invocation.selection.registration.pin.path)
    # A newly persisted admission is an external observation, not part of the
    # journal predecessor; include it consistently in the freshly read history.
    old = replace(invocation, history=replace(invocation.history,
        observations=fresh.history.observations))
    if old != fresh:
        raise ValueError('selected capture changed before stage publication')
    result, _ = publish_derived(fresh, proposal)
    return result
