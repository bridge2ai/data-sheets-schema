"""Fixed native stage capture and publication boundary.

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
    _catalogs: object = field(default_factory=receipt_api._ReceiptCatalogContext,
                              init=False, compare=False, repr=False)

    def trace(self, transcript=None, control=None):
        return observed.Trace(transcript or self.transcript, control or self.control,
            session_id=self.binding.session_id, policy=self.composition['policy'], runtime=self.value['runtime'])

    def decision(self):
        if self.phase1 is None:
            return None
        return stage._prepare_next(self.selection, self.binding, self.phase1, self.history, self._catalogs)


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


def initialize(selection_path, *, transcript_bytes, control_bytes, stream_files, observed_prefixes):
    """Bind the actual parent-observed initialization, never owner summary flags."""
    selection, reader, value, composition, _ = _base(selection_path)
    streams, (transcript, control) = _live_streams(value, stream_files=stream_files, transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    c.exact(observed_prefixes, {'transcript', 'control'}, 'parent observed prefixes')
    if observed_prefixes != {'transcript': transcript, 'control': control}:
        raise ValueError('initialization differs from the exact parent-observed prefixes')
    session, sent, ack, init = observed.initialization(transcript, control,
        policy=composition['policy'], runtime=value['runtime'])
    if Path(selection.role('session_binding')).exists() or _observation_paths(selection):
        raise ValueError('native initialization binding is spent or repeated')
    execution = reader.read('execution_capture', selection.role('execution_capture'))
    started = reader.read('started_capture', selection.role('started_capture'))
    item = _create(selection, 'observation', observation_bytes('initialized', selection, execution.pin.sha256,
        value['attempt_id'], session, transcript, control,
        {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack), 'native_init': asdict(init), 'stream_files': live_streams.stream_files(streams)}))
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
    return stage._prepare_next(run.selection, run.binding, phase1, history, run._catalogs)


def _require_completed_read_before_write(request, read):
    """Both native Write announcements must follow the actual delivered Read."""
    if (request.call.line <= read.result_event.line
            or request.callback.line <= read.result_event.line):
        raise ValueError('response Write precedes its complete current request Read')


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
            read_call = _call(c.strict_json(reads[0][0].raw)['payload']['call'])
            _require_completed_read_before_write(request, trace.settled(read_call.tool_use_id))
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
    """Strict complete-file route for final and recorded consumers."""
    base = _base(selection_path)
    streams, prefixes = _streams(base[2], transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    return _loaded(base, streams, prefixes)


def _load_live(selection_path, *, transcript_bytes=None, control_bytes=None, stream_files=None):
    """Fixed live route; a new authority/catalog transaction at every call."""
    base = _base(selection_path)
    anchors = _declared_stream_files(base[0], base[1])
    if stream_files is not None and live_streams.identities(stream_files) != anchors:
        raise ValueError('observed stream identities differ from initialized authority')
    streams, prefixes = _live_streams(base[2], stream_files=anchors,
        transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    return _loaded(base, streams, prefixes)


def _loaded(base, streams, prefixes):
    selection, reader, value, composition, spec = base
    transcript, control = prefixes
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
    run = _load_live(str(selection_registration_path))
    if run.phase1 is None:
        raise ValueError('advance precedes actual sealed originals')
    phase, _ = phase_replay(run)
    if not phase['passed']:
        raise ValueError('advance current phase history did not pass')
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


def _chronology(run):
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
    return catalog, advance_before, advance_after, visible, seal_observations


def phase_replay(run, *, complete=False):
    """Freshly run the actual phase machine over observed journal visibility."""
    from .native_shared_phase import PhaseState
    from .native_shared_render import commands
    paths = run.spec._agentic_artifact_paths
    phase = PhaseState(commands(run.spec), full_path=paths['full'], core_path=paths['core'],
        report_path=paths['report'], receipt_path=paths['receipt'], working_directory=run.binding.working_directory)
    catalog, advance_before, advance_after, visible, seal_observations = _chronology(run)
    actions = {}
    for line, _, frame in observed.rows(run.transcript):
        count = 0
        for item in run.history.records:
            if item.pin.sha256 not in visible or visible[item.pin.sha256] >= line:
                break
            count += 1
        decision = None
        if count >= 3:
            raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,
                execution_sha256=run.binding.execution.pin.sha256, attempt_id=run.binding.attempt_id,
                records=tuple(item.pin for item in run.history.records[:count]))
            decision = _decision_at(run, c.sha(raw))
        blocks = frame.get('message', {}).get('content', [])
        for block in blocks if type(blocks) is list else ():
            if type(block) is not dict:
                continue
            identity = block.get('id') if block.get('type') == 'tool_use' else block.get('tool_use_id')
            if block.get('type') == 'tool_use' and identity in advance_before:
                decision = _decision_at(run, advance_before[identity])
            if block.get('type') == 'tool_result' and identity in advance_after:
                decision = _decision_at(run, advance_after[identity])
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
    if complete and set(visible) != {item.pin.sha256 for item in run.history.records}:
        raise ValueError('completed history has unpublished or unobserved stage records')
    return phase.report(complete=complete), actions


def seal_originals(run, kind):
    """Parent-only observation effect after genuine settled helper results."""
    if kind not in ('seal_phase1', 'seal_core'):
        raise ValueError('unknown native seal action')
    report, actions = phase_replay(run)
    if kind not in actions.get(run.transcript.lines, ((), None))[0]:
        raise ValueError('seal does not follow this exact observed helper boundary')
    paths = run.spec._agentic_artifact_paths
    if kind == 'seal_phase1':
        if run.phase1 is not None:
            raise ValueError('original full/receipt seal is spent')
        inputs = [('full', 'phase1_full'), ('receipt', 'phase1_receipt')]
        helpers = {'chunk_check', 'source_scope', 'full_schema', 'full_terms', 'phase1_receipts'}
    else:
        if run.phase1 is None or run.phase1.core is not None:
            raise ValueError('original core seal is absent, premature or spent')
        decision = run.decision()
        if decision.state != 'await_core':
            raise ValueError('genuine original core is not at the current receipt boundary')
        inputs = [('core', 'phase1_core')]
        helpers = {'derive_core', 'core_schema', 'pair'}
    captured = {source: evidence.read_regular(paths[source], role,
        max_bytes=min(c.HARD_LIMITS['original_full_bytes'], run.selection.bounds()['max_input_bytes'])).captured for source, role in inputs}
    for source, role in inputs:
        _create(run.selection, role, captured[source].raw)
    sealed = {source: _captured(role, run.selection.role(role), captured[source].raw) for source, role in inputs}
    calls = [row['tool_use_id'] for row in report['checks'] if row['helper'] in helpers]
    if kind == 'seal_phase1':
        payload = {'full': c.pin_dict(sealed['full'].pin), 'original_receipt': c.pin_dict(sealed['receipt'].pin), 'helper_calls': calls}
        obs = _persist_observation(run, 'phase1_sealed', payload)
        body = {'kind': 'd4d_native_shared_phase1_seal', 'version': 1,
            'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
            'session_id': run.binding.session_id, 'full': payload['full'], 'original_receipt': payload['original_receipt'],
            'observation': c.pin_dict(obs.pin)}
        seal = _create(run.selection, 'phase1_seal', c.canonical(body))
        record_payload = {'seal': c.pin_dict(seal.pin), 'full': payload['full'],
            'original_receipt': payload['original_receipt'], 'observation': c.pin_dict(obs.pin)}
        _append(run.selection, run.binding, run.history, 'phase1_sealed', record_payload)
    else:
        payload = {'core': c.pin_dict(sealed['core'].pin), 'helper_calls': calls}
        obs = _persist_observation(run, 'core_sealed', payload)
        body = {'kind': 'd4d_native_shared_core_seal', 'version': 1,
            'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
            'session_id': run.binding.session_id, 'phase1_seal_sha256': run.phase1.seal.pin.sha256,
            'core': payload['core'], 'observation': c.pin_dict(obs.pin)}
        seal = _create(run.selection, 'core_seal', c.canonical(body))
        _append(run.selection, run.binding, run.history, 'core_sealed',
            {'seal': c.pin_dict(seal.pin), 'core': payload['core'], 'observation': c.pin_dict(obs.pin)})
    # A mutating host cannot make a result certify different bytes between
    # actual helper settlement and the original-copy publication.
    for source, role in inputs:
        if evidence.read_regular(paths[source], role, max_bytes=c.HARD_LIMITS['original_full_bytes']).captured != captured[source]:
            raise ValueError('original output changed during its exact observed seal')


def current_effect_view(run, *, correction_window=False, exclude_pending=None):
    """Derive the restrictive overlay solely from captured state and events."""
    decision = run.decision()
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
    pending = [identity for identity in run.trace().pending() if identity != exclude_pending
               and run.trace().calls[identity][2].get('input', {}).get('command') == run.composition['policy']['native_shared_helpers']['advance']]
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


def observe_request_read(run, identity):
    current = run.decision()
    if current is None or current.state != 'awaiting_response' or current.request is None:
        raise ValueError('request delivery has no current admitted outer request')
    trace = run.trace(); actual = trace.settled(identity)
    observed.complete_request_read(trace, actual, current.request)
    # An additional correct Read grants no new response identity. Retain the
    # first complete current Read rather than inventing independent deliveries.
    for item in run.observations:
        prior = _document(item.raw, 'current read observation')
        if (prior['observation_type'] == 'request_read'
                and prior['payload']['history_sha256'] == run.history.journal.pin.sha256
                and prior['payload']['request'] == c.pin_dict(current.request.pin)):
            return
    _persist_observation(run, 'request_read', {'call': call_document(actual.call),
        'result': asdict(actual.result), 'result_event': asdict(actual.result_event),
        'request': c.pin_dict(current.request.pin), 'history_sha256': run.history.journal.pin.sha256})


def observe_response_intent(run, identity):
    from .native_shared_effects import classify_effect
    trace = run.trace(); request = trace.request(identity)
    inputs = _document(request.input_json, 'response Write')
    view = current_effect_view(run, exclude_pending=identity)
    if classify_effect(view, tool_name=request.tool_name, tool_input=inputs)[0] != 'prescribed':
        raise ValueError('current response Write is not permitted by actual captured effects')
    path = Path(view.response.path)
    if path.exists() or path.is_symlink():
        raise ValueError('first response destination already exists; no overwrite or retry')
    matches = [item for item in run.observations if item.pin.sha256 == view.request_read_observation_sha256]
    if len(matches) != 1:
        raise ValueError('response Write lacks one durable whole request observation')
    read_call = _call(_document(matches[0].raw, 'request Read observation')['payload']['call'])
    _require_completed_read_before_write(request, trace.settled(read_call.tool_use_id))
    _persist_observation(run, 'response_intent', {'request': c.pin_dict(view.request), 'response': asdict(view.response),
        'call': asdict(request.call), 'callback': asdict(request.callback), 'tool_use_id': identity,
        'input_json': request.input_json.decode('utf-8'), 'history_sha256': run.history.journal.pin.sha256,
        'read_observation': c.pin_dict(matches[0].pin)})


def observe_response_written(run, identity):
    current = run.decision(); trace = run.trace(); actual = trace.settled(identity)
    if current is None or current.state != 'awaiting_response' or current.response is None:
        raise ValueError('response settlement has no current selected destination')
    matches = [(item, _document(item.raw, 'response intent')['payload']) for item in run.observations
        if _document(item.raw, 'response intent')['observation_type'] == 'response_intent'
        and _document(item.raw, 'response intent')['payload']['tool_use_id'] == identity]
    if len(matches) != 1:
        raise ValueError('response settlement lacks one preceding exact pre-grant intent')
    intent, payload = matches[0]
    response = run.reader.read('response', current.response.path)
    observed.first_response_write(trace, actual, response, intent_input_json=payload['input_json'].encode('utf-8'))
    obs = _persist_observation(run, 'response_written', {'call': call_document(actual.call),
        'result': asdict(actual.result), 'result_event': asdict(actual.result_event), 'response': c.pin_dict(response.pin),
        'intent_observation': c.pin_dict(intent.pin), 'history_sha256': run.history.journal.pin.sha256})
    request_hash = c.strict_json(current.request.raw, max_bytes=run.selection.bounds()['max_request_bytes'])['request_sha256']
    _append(run.selection, run.binding, run.history, 'response_consumed', {'cursor': asdict(current.cursor),
        'request_sha256': request_hash, 'response': c.pin_dict(response.pin),
        'read_observation': payload['read_observation'], 'response_observation': c.pin_dict(obs.pin)})


def observe_advance_settled(run, identity):
    trace = run.trace(); actual = trace.settled(identity)
    frame = evidence.event(run.transcript, actual.result_event)
    result = _document(frame.get('tool_use_result', {}).get('stdout', '').encode('utf-8'), 'advance stdout')
    observed.helper_result(trace, actual, result)
    c.exact(result, {'kind', 'version', 'selection_sha256', 'execution_sha256', 'attempt_id', 'session_id',
        'advance_tool_use_id', 'before_history_sha256', 'after_history_sha256', 'state', 'publications'}, 'advance acknowledgement')
    expected = {'kind': c.KINDS['advance_result'], 'version': 1,
        'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
        'attempt_id': run.binding.attempt_id, 'session_id': run.binding.session_id, 'advance_tool_use_id': identity,
        'after_history_sha256': run.history.journal.pin.sha256, 'state': run.decision().state}
    if any(type(result[key]) is not type(value) or result[key] != value for key, value in expected.items()):
        raise ValueError('advance result differs from actual current selected publication')
    before = _history_prefix(run, result['before_history_sha256'])
    phase1 = _phase1(run.selection, run.binding, before, run.reader)
    replay = stage._Replay(run.selection, run.binding, phase1, before, _catalogs=run._catalogs).run()
    if replay.pending is not None and replay.pending[-1] is not None:
        response, _ = replay.pending[-1]
        proposal = stage._check_response(run.selection, run.binding, phase1, before, replay.pending[2].raw, response.raw, run._catalogs)
        publications = (*proposal.publications, *(c.HelperPublication('create_once', item, None) for item in proposal.records_to_append),
            c.HelperPublication('replace_journal_from_exact_predecessor', proposal.predicted_journal, before.journal.pin.sha256))
    else:
        publications = stage._prepare_next(run.selection, run.binding, phase1, before, run._catalogs).publications
    if result['publications'] != [c.pin_dict(item.artifact.pin) for item in publications]:
        raise ValueError('advance result does not describe every freshly derived actual effect')
    for item in publications:
        actual_file = run.reader.read(item.artifact.pin.role, item.artifact.pin.path, item.artifact.pin)
        if actual_file.raw != item.artifact.raw:
            raise ValueError('advance published bytes differ from fresh pure reconstruction')
    _persist_observation(run, 'advance_settled', {'call': call_document(actual.call),
        'result': asdict(actual.result), 'result_event': asdict(actual.result_event), 'advance_result': result})


def selected_receipt_paths(selection_registration_path):
    """Explicit live S reaches only the paths captured in its already active E."""
    _, _, _, composition, spec = _base(str(selection_registration_path))
    paths = spec._agentic_artifact_paths
    return {'full': Path(paths['full']), 'receipt': Path(paths['receipt']),
            'provenance': Path(composition['policy']['post_final_recorder']['destination']),
            'core_dir': Path(paths['core']).parent}


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


def live_receipt_block(selection_registration_path, *, full_path, receipt_path):
    run = _load_live(str(selection_registration_path))
    phase_replay(run)
    return _receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)[0]


def _provenance_block(run):
    decision = run.decision()
    if decision is None or decision.state != 'assembly_complete' or decision.completion is None:
        raise ValueError('native provenance requires complete freshly reconstructed selected stages')
    completion = stage.check_assembly(run.selection, run.binding, run.phase1, run.history, decision.completion.assembly.raw)
    artifact = run.reader.read('completion', run.selection.role('completion'))
    return {'protocol': c.NAME, 'selection_sha256': run.selection.registration.pin.sha256,
        'execution_sha256': run.binding.execution.pin.sha256, 'attempt_id': run.binding.attempt_id,
        'session_id': run.binding.session_id, 'assembly_sha256': completion.assembly.pin.sha256,
        'audit_sha256': completion.audit.pin.sha256, 'receipt_result_sha256': completion.receipt_result.pin.sha256,
        'stage_completion_sha256': artifact.pin.sha256, 'scientific_support': 'unverified evaluator declarations',
        'runtime_acceptance': 'pending independent saved readback'}


def live_provenance_block(selection_registration_path):
    run = _load_live(str(selection_registration_path))
    phase, _ = phase_replay(run)
    required = {'draft', 'final_evidence', 'final_source_inventory', 'phase1_receipts', 'final_scope',
                'derive_final_core', 'core_schema', 'pair', 'full_schema', 'full_terms', 'audit_evidence'}
    if not required <= set(phase['current_checks']) or not phase['passed']:
        raise ValueError('recorder precedes actual current final helper obligations')
    from .native_shared_gates import current_evidence
    checked = current_evidence(run)
    if checked.get('checked') is not True or checked.get('findings') != []:
        raise ValueError('recorder current captured evidence did not pass')
    paths = run.spec._agentic_artifact_paths
    block, _, _ = _receipt_assessment(run, full_path=paths['full'], receipt_path=paths['receipt'])
    from .canary import receipt_floors
    if any(receipt_floors(block).values()):
        raise ValueError('recorder current selected receipt floors did not pass')
    return _provenance_block(run)


def _recorded_run(spec, record):
    from .native_shared_render import validate_metadata
    if type(record) is not dict:
        raise ValueError('native recorded reader requires one explicit provenance mapping')
    try:
        render_spec = record['prompts']['request']['spec']
        document = validate_metadata(render_spec)
    except (KeyError, TypeError) as exc:
        raise ValueError('native record lacks its complete selected render authority') from exc
    run = _load(document['registration_path'])
    if c.canonical(render_spec) != c.canonical(run.composition['render_spec']):
        raise ValueError('native record rendering differs from its observed execution composition')
    if spec is not None and c.canonical(spec.render_spec()) != c.canonical(render_spec):
        raise ValueError('caller spec differs from the explicit native record')
    if c.canonical(record.get('native_shared_generation')) != c.canonical(_provenance_block(run)):
        raise ValueError('native record stage/session identity differs from actual reconstructed evidence')
    phase, _ = phase_replay(run)
    if not phase['passed']:
        raise ValueError('native recorded stage chronology did not pass')
    return run


def recorded_receipt_block(spec, *, record, full_path, receipt_path):
    run = _recorded_run(spec, record)
    return _receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)[0]


def recorded_receipt_claims(spec, *, record, full_path, receipt_path, expected_block):
    """Claim sidecar from the same captured effective bytes as the checked block."""
    from . import native_shared_receipts as receipts
    from . import receipts as rc
    from .audit_omissions import _mapping
    run = _recorded_run(spec, record)
    block, full, effective = _receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)
    if (block.get('native_receipt_stage') != 'final' or block.get('final_stage_complete') is not True
            or c.canonical(expected_block) != c.canonical(block)):
        raise ValueError('claim sidecar expected block differs from the same freshly captured final receipt assessment')
    _, _, _, _, _, bases, _, _ = receipts._inputs(run.selection, run.phase1)
    return rc.claim_receipts(_mapping(effective.raw, 'native effective receipt'),
        _mapping(full.raw, 'native final full'), _mapping(run.phase1.full.raw, 'native original full'),
        identifier_bases=bases)


def at_callback(run, line):
    """Pure current authority at one real callback; no future observation credit."""
    _, _, _, visible, _ = _chronology(run)
    count = 0
    for item in run.history.records:
        if item.pin.sha256 not in visible or visible[item.pin.sha256] >= line:
            break
        count += 1
    if count < 2:
        raise ValueError('callback precedes actual session publication')
    raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,
        execution_sha256=run.binding.execution.pin.sha256, attempt_id=run.binding.attempt_id,
        records=tuple(item.pin for item in run.history.records[:count]))
    history = _history_prefix(run, c.sha(raw))
    observations = tuple(item for item in run.observations
        if observation(item, run.selection, run.binding, run.pool)[1].lines < line)
    history = replace(history, observations=observations)
    transcript = _through(run.transcript, line)
    frames = {c.canonical(frame) for _, _, frame in observed.rows(transcript)}
    control_lines = 0
    for number, _, row in observed.rows(run.control):
        if row.get('kind') == 'decision' and c.canonical(row.get('request')) not in frames:
            break
        control_lines = number
    control = _through(run.control, control_lines)
    return replace(run, history=history, observations=observations, transcript=transcript, control=control,
        phase1=_phase1(run.selection, run.binding, history, run.reader))
