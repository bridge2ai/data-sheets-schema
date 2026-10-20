"""Fixed native stage capture and publication boundary.

The reader accepts only S-owned roles and exact captured pins. Observation
references name actual complete stream prefixes, never future stream hashes.
Live callers and the saved replay use the same closed observation joins.
"""
from __future__ import annotations

from contextlib import contextmanager
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
_OWNER_LIMIT = 16_384
# Canonical JSON of the released manifest whose raw SHA is d1f13def58c0… .
# This fixes the entire declared roster without consulting today's files.
_OWNER_CONTROLLER_DECLARATION_SHA = 'c75e1e2cf9939f6b8f9bb82b3b76e5886acd89aecf183fee1ae9795f5f9a3f59'


def _selected_owner_execution(value):
    """Recognize the reserved saved-only branch, including malformed attempts."""
    dependencies = value.get('dependencies') if type(value) is dict else None
    return type(dependencies) is dict and (
        'stream_snapshot_profile' in dependencies or dependencies.get('version') == 2)


def _require_owner_association(context, selection, execution_raw, started_raw=None):
    """Borrow only the exact active reader and its immutable captured joins."""
    from . import native_stream_coordination_v1 as coordination
    if type(context) is not coordination._OwnerReaderContext:
        raise ValueError('selected live capture requires its exact owner reader context')
    context.require_current()
    association = context._association
    if (type(execution_raw) is not bytes or association.selection != selection
            or association.execution_raw != execution_raw
            or (started_raw is not None and association.started_raw != started_raw)):
        raise ValueError('selected live capture differs from its reader association')
    return association


def _publication_guard(selection, owner_context):
    if owner_context is not None:
        from . import native_stream_coordination_v1 as coordination
        if type(owner_context) is not coordination._OwnerReaderContext:
            raise ValueError('selected publication requires its exact owner reader context')
        _require_owner_association(owner_context, selection,
                                  owner_context._association.execution_raw)


@contextmanager
def _helper_owner_scope(selection_registration_path):
    """Independently join the actual owner; retain one scope through helper writes.

    Bootstrap claims grant no command permission. capture_stage must still
    prove its actual pending fixed advance and complete current phase history.
    """
    from . import native_shared_selection as selections
    from . import native_shared_registration as registration
    selection = selections.capture(str(selection_registration_path))
    reader = _Reader(selection)
    execution = reader.read('execution_capture', selection.role('execution_capture'))
    value = registration._execution_value(execution.raw)
    profile = registration._execution_profile(value)
    if profile is None:
        yield None
        return

    import threading
    from . import native_clock_domain_v1 as clocks
    from . import native_execution_authority as authority
    from . import native_owner_profile_v1 as profiles
    from . import native_stream_coordination_v1 as coordination
    from .native_owner_runner_v1 import validate_owner_record_v2
    if (profiles._ACTIVE.get() is not None or coordination.current_reader_budget() is not None
            or coordination._SCOPE.get() is not None or coordination._OWNER_READER.get() is not None):
        raise ValueError('independent helper cannot borrow or nest another owner scope')
    started = reader.read('started_capture', selection.role('started_capture'))
    attempt = Path(c.canonical_path(value.get('attempt_directory'), 'helper attempt'))
    owner_member = evidence.read_regular(str(attempt / 'stream-owner.json'), 'owner', max_bytes=_OWNER_LIMIT)
    owner = validate_owner_record_v2(c.strict_json(owner_member.captured.raw, 'helper owner', _OWNER_LIMIT))
    if (owner['execution_sha256'] != execution.pin.sha256 or owner['started_sha256'] != started.pin.sha256
            or c.canonical(owner['coordination_profile']) != c.canonical(profile)):
        raise ValueError('helper owner differs from its captured execution, started or source profile')
    # A local event is not a shared parent Event. The reader also checks the
    # durable owner-stop marker on every admission and SH contention poll.
    with clocks.capture_domain() as lease:
        lease.require_current(owner['clock_domain'])
        budget = coordination.ReaderBudget(owner['deadline_ns'], (threading.Event(),),
                                            clock_domain=owner['clock_domain'])
        with coordination.reader_budget(budget, clock_lease=lease):
            budget.remaining()
            with authority.loaded_dependencies(value['dependencies']) as controls:
                budget.remaining()
                registration._verified_in_scope(execution.raw)
                for filename, expected in (('registration.json', execution.raw), ('started.json', started.raw)):
                    budget.remaining()
                    actual = evidence.read_regular(str(attempt / filename), 'attempt_identity',
                                                   max_bytes=c.HARD_LIMITS['request_bytes'])
                    if actual.captured.raw != expected:
                        raise ValueError('helper capture differs from the actual one-use attempt')
                # Binding reconstructs S and exact E/C/started joins, proves
                # named committed sources and rechecks this same deadline.
                context = profiles.bind_reader_context(profile, controls, selection=selection,
                    execution_raw=execution.raw, started_raw=started.raw,
                    owner_raw=owner_member.captured.raw, budget=budget)
                with context:
                    if context._owner_metadata != owner_member.metadata_json:
                        raise ValueError('helper owner identity changed during bootstrap')
                    yield context
                budget.remaining()


def _saved_member(pool, role, path):
    if type(pool) is not evidence.CapturePool:
        raise ValueError('owner initialization requires an exact immutable captured pool')
    found = [member for member in pool.members
             if member.captured.pin.role == role and member.captured.pin.path == path]
    if len(found) != 1:
        raise ValueError('saved pool lacks one exact artifact role/path: ' + role)
    return found[0]


def _saved_selection_carriers(pool, value):
    """Extract the complete current-pool carriers without granting validity."""
    from . import native_shared_selection as selection_api
    if type(value) is not dict or type(value.get('composition_raw_json')) is not str:
        raise ValueError('saved owner execution lacks bounded captured composition text')
    composition = c.strict_json(value['composition_raw_json'].encode('utf-8'),
                               'captured C', c.HARD_LIMITS['request_bytes'])
    if type(composition) is not dict or type(composition.get('selection_raw_json')) is not str:
        raise ValueError('saved owner composition lacks captured selection text')
    raw = composition['selection_raw_json'].encode('utf-8')
    doc = c.parse_selection(raw)
    registration = _saved_member(pool, 'selection', doc['registration_path']).captured
    if registration.raw != raw:
        raise ValueError('saved selection differs from the execution declaration')
    artifacts = {role: _saved_member(pool, role, pin['path']).captured
                 for role, pin in selection_api._declarations(doc)}
    schemas = selection_api._declared_schemas(doc, artifacts)
    authority = tuple(a for role, a in artifacts.items()
                      if role != 'receipt_policy' and not role.startswith(('full_schema:', 'core_schema:')))
    return registration, authority, schemas, artifacts['receipt_policy']


def _saved_selection(pool, value):
    """Uncached saved-entry oracle over complete current-pool carriers."""
    from . import native_shared_selection as selection_api
    return selection_api.rebuild(*_saved_selection_carriers(pool, value))


def _saved_owner_execution(selection, pool, execution):
    """Pure captured E/C/S association; neither public verification nor loading."""
    if type(execution) is not c.CapturedArtifact:
        raise ValueError('saved owner association requires exact immutable execution bytes')
    value = c.strict_json(execution.raw, 'owner captured E', c.HARD_LIMITS['request_bytes'])
    if (type(value) is not dict or value.get('kind') != c.KINDS['execution']
            or type(value.get('version')) is not int or value['version'] != 1
            or type(value.get('composition_raw_json')) is not str):
        raise ValueError('owner initialization requires the exact shared execution kind/version')
    from . import native_shared_selection as selection_api
    # Repeated owner joins may reuse only exact-byte schema derivation
    # metadata. Every carrier, declaration, bound and non-schema authority is
    # freshly checked; the independent saved-entry oracle remains uncached.
    rebuilt = selection_api._rebuild(*_saved_selection_carriers(pool, value), use_schema_cache=True)
    if rebuilt != selection:
        raise ValueError('owner selection differs from its complete captured reconstruction')
    member = _saved_member(pool, 'execution_capture', rebuilt.role('execution_capture'))
    if member.captured != execution:
        raise ValueError('owner execution differs from its unique captured pool member')
    composition_raw = value['composition_raw_json'].encode('utf-8')
    composition = c.strict_json(composition_raw, 'owner captured C', c.HARD_LIMITS['request_bytes'])
    if (type(composition) is not dict
            or composition.get('kind') != 'd4d_native_shared_callback_composition'
            or type(composition.get('version')) is not int or composition['version'] != 1
            or c.sha(composition_raw) != value.get('composition_sha256')
            or composition.get('selection_raw_json') != rebuilt.registration.raw.decode('utf-8')
            or composition.get('selection_sha256') != rebuilt.registration.pin.sha256
            or value.get('selection_sha256') != rebuilt.registration.pin.sha256):
        raise ValueError('owner captured E/C/S raw identities disagree')
    if type(composition.get('runtime_raw_json')) is not str:
        raise ValueError('owner captured composition lacks exact runtime text')
    runtime_raw = composition['runtime_raw_json'].encode('utf-8')
    runtime = c.strict_json(runtime_raw, 'owner captured runtime', c.HARD_LIMITS['request_bytes'])
    if (type(runtime) is not dict
            or c.sha(runtime_raw) != composition.get('runtime_sha256')
            or value.get('runtime_declaration_sha256') != composition.get('runtime_sha256')
            or c.canonical(value.get('runtime')) != c.canonical(runtime)):
        raise ValueError('owner captured E/C runtime bytes, hashes or typed values disagree')
    dependencies = c.exact(value.get('dependencies'),
        {'version', 'base', 'additional_modules', 'stream_snapshot_profile'}, 'owner dependencies')
    if type(dependencies['version']) is not int or dependencies['version'] != 2:
        raise ValueError('owner initialization requires selected dependency version 2')
    if type(dependencies['base']) is not dict or type(dependencies['additional_modules']) is not dict:
        raise ValueError('owner captured dependency declarations are malformed')
    if ('stream_snapshot_profile' in composition and c.canonical(composition['stream_snapshot_profile'])
            != c.canonical(dependencies['stream_snapshot_profile'])):
        raise ValueError('captured composition profile differs from its execution')
    c.canonical_path(value.get('attempt_directory'), 'owner attempt')
    if (type(value.get('attempt_id')) is not str or not value['attempt_id']
            or PurePosixPath(value['attempt_directory']).name != value['attempt_id']
            or value.get('working_directory') != composition.get('working_directory')):
        raise ValueError('owner execution attempt/composition association differs')
    return value, composition


def _owner_document(artifact):
    from .native_owner_runner_v1 import validate_owner_record_v2
    if (type(artifact) is not c.CapturedArtifact or artifact.pin.role != 'owner'
            or PurePosixPath(artifact.pin.path).name != 'stream-owner.json'
            or artifact.pin.bytes > _OWNER_LIMIT):
        raise ValueError('initialized owner differs from its fixed bounded artifact role')
    return validate_owner_record_v2(c.strict_json(artifact.raw, 'captured owner', _OWNER_LIMIT))


def _saved_owner(selection, pool, execution, started, owner_artifact):
    value, composition = _saved_owner_execution(selection, pool, execution)
    if (type(started) is not c.CapturedArtifact
            or _saved_member(pool, 'started_capture', selection.role('started_capture')).captured != started):
        raise ValueError('owner started identity differs from the captured member')
    consumed = c.strict_json(started.raw, 'owner started identity', c.HARD_LIMITS['metadata_record_bytes'])
    if (type(consumed) is not dict or consumed.get('kind') != 'd4d_native_shared_attempt'
            or type(consumed.get('version')) is not int or consumed['version'] != 1
            or consumed.get('state') != 'started' or type(consumed.get('dispatch_limit')) is not int
            or consumed['dispatch_limit'] != 1 or consumed.get('attempt_id') != value['attempt_id']
            or consumed.get('registration_sha256') != execution.pin.sha256
            or consumed.get('composition_sha256') != value['composition_sha256']):
        raise ValueError('owner initialization lacks exact consumed E/C/started identity')
    owner = _owner_document(owner_artifact)
    path = str(PurePosixPath(value['attempt_directory']) / 'stream-owner.json')
    if (owner_artifact.pin.path != path
            or _saved_member(pool, 'owner', path).captured != owner_artifact
            or owner['execution_sha256'] != execution.pin.sha256
            or owner['started_sha256'] != started.pin.sha256):
        raise ValueError('owner differs from its exact attempt/execution/started pins')
    dependencies = value['dependencies']
    profile = owner['coordination_profile']
    if c.canonical(profile) != c.canonical(dependencies['stream_snapshot_profile']):
        raise ValueError('owner profile differs from captured execution dependencies')
    base = dependencies['base']
    package = base.get('package_sources')
    manifest = composition.get('controller_sources')
    if (type(package) is not dict or type(base.get('modules')) is not dict
            or type(manifest) is not dict or type(manifest.get('modules')) is not dict
            or c.sha(c.canonical(manifest)) != _OWNER_CONTROLLER_DECLARATION_SHA
            or composition.get('controller_sources_sha256') != profile['base_controller_sources_sha256']
            or any(package.get(pin['path']) != pin['sha256'] for pin in profile['implementations'].values())
            or any(c.canonical(base['modules'].get(name)) != c.canonical(pin)
                   for name, pin in manifest['modules'].items())):
        raise ValueError('owner source profile differs from captured controller/package declarations')
    runtime = value.get('runtime')
    if (type(runtime) is not dict or type(runtime.get('deadline_seconds')) is not int
            or runtime['deadline_seconds'] <= 0
            or owner['duration_ns'] != runtime['deadline_seconds'] * 1_000_000_000):
        raise ValueError('owner original duration differs from captured execution')
    for role in live_streams.ROLES:
        if owner[role]['path'] != str(PurePosixPath(value['attempt_directory']) / (role + '.jsonl')):
            raise ValueError('owner stream is outside its exact captured attempt')
    return owner


def _pin(value):
    c.exact(value, {'role', 'path', 'bytes', 'sha256'}, 'captured artifact pin')
    return c.ArtifactPin(**value)


class _Reader:
    """One bounded capture transaction; no directory discovery or read fallback."""
    def __init__(self, selection, *, pool=None, execution=None, owner_context=None):
        if type(selection) is not c.NativeSelectionCapture:
            raise ValueError('capture requires the exact immutable selection')
        if pool is not None and type(pool) is not evidence.CapturePool:
            raise ValueError('saved reader requires the exact immutable pool')
        self.selection, self.pool = selection, pool
        self.owner_context = owner_context
        self._owner_execution = None
        if owner_context is not None:
            if pool is not None or execution is not None:
                raise ValueError('live owner reader cannot also use a saved pool')
            association = _require_owner_association(owner_context, selection,
                owner_context._association.execution_raw)
            self._owner_execution = _captured('execution_capture',
                selection.role('execution_capture'), association.execution_raw)
        if execution is not None:
            _saved_owner_execution(selection, pool, execution)
            self._owner_execution = execution
        self.members = {}
        self.total = 0
        if owner_context is not None:
            # The saved observation resolver must have the complete actual S
            # closure, including metadata, rather than invented pool members.
            artifacts = (selection.registration, *selection.authority,
                *(item for closure in selection.schemas for item in closure.sources),
                selection.receipt_policy)
            for artifact in artifacts:
                _publication_guard(selection, owner_context)
                member = evidence.read_regular(artifact.pin.path, artifact.pin.role,
                    max_bytes=max(1, artifact.pin.bytes))
                if member.captured != artifact:
                    raise ValueError('live owner selection authority changed')
                self._remember(member)
            self.read('owner', association.owner_path)

    def _remember(self, member):
        key = (member.captured.pin.role, member.captured.pin.path)
        if key not in self.members:
            self.total += member.captured.pin.bytes
            if (self.total > self.selection.bounds()['max_evidence_bytes']
                    or len(self.members) >= c.HARD_LIMITS['captured_members']):
                raise ValueError('complete stage capture exceeds its total bound')
            self.members[key] = member

    def destination(self, role, path):
        c.canonical_path(path, 'selected stage artifact')
        if role == 'owner':
            if self.owner_context is not None:
                association = _require_owner_association(self.owner_context, self.selection,
                    self._owner_execution.raw)
                if path != association.owner_path:
                    raise ValueError('owner artifact is outside its exact live execution role')
                return _OWNER_LIMIT
            if self.pool is None or self._owner_execution is None:
                raise ValueError('owner role is available only through exact saved execution association')
            value, _ = _saved_owner_execution(self.selection, self.pool, self._owner_execution)
            if path != str(PurePosixPath(value['attempt_directory']) / 'stream-owner.json'):
                raise ValueError('owner artifact is outside its exact captured execution role')
            return _OWNER_LIMIT
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
        _publication_guard(self.selection, self.owner_context)
        limit = self.destination(role, path)
        if expected is not None and (type(expected) is not c.ArtifactPin or expected.role != role
                                    or expected.path != path or expected.bytes > limit):
            raise ValueError('selected pin differs from its bounded artifact role')
        key = (role, path)
        if key in self.members:
            member = self.members[key]
        elif self.pool is None:
            member = evidence.read_regular(path, role, max_bytes=limit)
        elif role == 'owner':
            member = _saved_member(self.pool, role, path)
        else:
            candidates = [m for m in self.pool.members if m.captured.pin.role == role and m.captured.pin.path == path
                          and (expected is None or m.captured.pin == expected)]
            if len(candidates) != 1:
                raise ValueError('saved capture lacks one exact artifact version')
            member = candidates[0]
        if member.captured.pin.bytes > limit or (expected is not None and member.captured.pin != expected):
            raise ValueError('captured artifact differs from its exact pin or bound')
        if role == 'owner' and self.owner_context is not None:
            if (member.captured.raw != self.owner_context._association.owner_raw
                    or member.metadata_json != self.owner_context._owner_metadata):
                raise ValueError('captured live owner differs from its admitted bytes or identity')
        self._remember(member)
        _publication_guard(self.selection, self.owner_context)
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
                      transcript, control, payload, *, owner=None):
    if kind not in _OBSERVATION_PAYLOADS:
        raise ValueError('unknown native shared observation type')
    c.exact(payload, _OBSERVATION_PAYLOADS[kind], 'observation payload')
    if kind == 'initialized':
        live_streams.identities(payload['stream_files'])
    if owner is not None:
        if kind != 'initialized':
            raise ValueError('owner pins are supported only by initialized observations')
        owner_value = _owner_document(owner)
        if owner_value['execution_sha256'] != execution_sha256:
            raise ValueError('initialized owner belongs to another execution')
        payload = {**payload, 'owner': c.pin_dict(owner.pin)}
    raw = c.canonical({'kind': c.KINDS['observation'], 'version': 1 if owner is None else 2, 'observation_type': kind,
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
    doc = c.strict_json(artifact.raw, 'native observation', c.HARD_LIMITS['metadata_record_bytes'])
    c.exact(doc, _OBSERVATION_KEYS, 'native observation')
    kind = doc['observation_type']
    if (doc['kind'] != c.KINDS['observation'] or type(doc['version']) is not int or doc['version'] not in (1, 2)
            or kind not in _OBSERVATION_PAYLOADS or doc['selection_sha256'] != execution.selection_sha256
            or doc['selection_sha256'] != selection.registration.pin.sha256
            or doc['execution_sha256'] != execution.execution.pin.sha256
            or doc['attempt_id'] != execution.attempt_id or doc['session_id'] != execution.session_id):
        raise ValueError('native observation belongs to another exact execution/session')
    execution_value = c.strict_json(execution.execution.raw, 'captured execution', c.HARD_LIMITS['request_bytes'])
    selected = _selected_owner_execution(execution_value)
    if doc['version'] == 2:
        if kind != 'initialized' or not selected:
            raise ValueError('initialized v2 requires the selected saved owner association')
        reader = _Reader(selection, pool=pool, execution=execution.execution)
        expected_streams = {evidence.stream_id(execution.execution.pin.sha256, role,
            str(PurePosixPath(execution_value['attempt_directory']) / (role + '.jsonl')))
            for role in live_streams.ROLES}
        if set(dict(pool.stream_bindings)) != expected_streams:
            raise ValueError('owner initialization lacks its two exact captured stream bindings')
        keys = _OBSERVATION_PAYLOADS['initialized'] | {'owner'}
    else:
        if selected and kind == 'initialized':
            raise ValueError('selected owner initialization cannot use v1 observations')
        if selected:
            # Later v1 records do not repeat the owner pin. Their immutable
            # binding must resolve the same actual initialized-v2 observation.
            init = _saved_member(pool, 'observation', execution.init_observation.pin.path).captured
            if init != execution.init_observation:
                raise ValueError('later selected observation has another initialization')
            header = c.strict_json(init.raw, 'selected initialization', c.HARD_LIMITS['metadata_record_bytes'])
            if (type(header) is not dict or header.get('kind') != c.KINDS['observation']
                    or type(header.get('version')) is not int or header['version'] != 2
                    or header.get('observation_type') != 'initialized'):
                raise ValueError('later selected observation requires an initialized-v2 binding')
            initial, _, _ = observation(init, selection, execution, pool)
            if initial['version'] != 2 or initial['observation_type'] != 'initialized':
                raise ValueError('later selected observation lacks initialized owner binding')
            _, composition = _saved_owner_execution(selection, pool, execution.execution)
            if 'stream_snapshot_profile' not in composition:
                raise ValueError('historical private composition supports initialization-only evidence')
            reader = _Reader(selection, pool=pool, execution=execution.execution)
        else:
            reader = _Reader(selection)
        keys = _OBSERVATION_PAYLOADS[kind]
    reader.destination('observation', artifact.pin.path)
    c.exact(doc['payload'], keys, 'native observation payload')
    if kind == 'initialized':
        anchors = live_streams.identities(doc['payload']['stream_files'])
        members = tuple(pool.member(dict(pool.stream_bindings)[
            evidence.stream_id(execution.execution.pin.sha256, role, doc[role + '_prefix']['path'])])
            for role in live_streams.ROLES)
        if anchors != live_streams.stream_files(members):
            raise ValueError('initialized stream files differ from captured physical identities')
        if doc['version'] == 2:
            owner_artifact = reader.pinned(doc['payload']['owner'])
            owner_value = _saved_owner(selection, pool, execution.execution, execution.started, owner_artifact)
            if c.canonical(anchors) != c.canonical({role: {key: owner_value[role][key]
                    for key in ('device', 'inode')} for role in live_streams.ROLES}):
                raise ValueError('initialized stream files differ from captured owner identities')
    transcript = pool.prefix(doc['transcript_prefix'], execution_sha256=execution.execution.pin.sha256)
    control = pool.prefix(doc['control_prefix'], execution_sha256=execution.execution.pin.sha256)
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


def _create(selection, role, raw, *, ordinal=None, owner_context=None):
    """Sole parent/helper create-once primitive for explicitly derived S roles."""
    from .native_attempt_supervisor import durable_new
    from .native_execution import _mkdir_durable
    _publication_guard(selection, owner_context)
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
    _publication_guard(selection, owner_context)
    _mkdir_durable(target.parent)
    _publication_guard(selection, owner_context)
    durable_new(target, raw)
    item = evidence.read_regular(path, role, max_bytes=limit).captured
    if item.raw != raw:
        raise ValueError('published native artifact differs from its intended bytes')
    _publication_guard(selection, owner_context)
    return item


def _append(selection, execution, history, kind, payload, *, owner_context=None):
    """Parent record publication shares C's exact serializer and journal CAS."""
    from .native_shared_publication import _replace_journal
    if _selected_owner_execution(c.strict_json(execution.execution.raw)):
        _require_owner_association(owner_context, selection,
            execution.execution.raw, execution.started.raw)
    records, journal = stage.append_records(selection, execution, history, ((kind, c.canonical(payload)),))
    for record in records:
        _create(selection, 'record', record.raw, ordinal=len(history.records), owner_context=owner_context)
    _publication_guard(selection, owner_context)
    if owner_context is None:
        _replace_journal(Path(selection.role('journal')), history.journal, journal)
    else:
        _replace_journal(Path(selection.role('journal')), history.journal, journal, owner_context=owner_context)
    _publication_guard(selection, owner_context)


def activate(selection, execution_raw, started_raw, *, owner_context=None):
    """Called only by the fixed lifetime immediately before its single dispatch.

    This writes no session declaration. The later session binding must come
    from actual initialized native/control streams.
    """
    from . import native_shared_registration as registration
    if owner_context is None:
        value = registration.verified(execution_raw)
    else:
        _require_owner_association(owner_context, selection, execution_raw, started_raw)
        value = registration._verified_in_scope(execution_raw)
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
    e = _create(selection, 'execution_capture', execution_raw, owner_context=owner_context)
    s = _create(selection, 'started_capture', started_raw, owner_context=owner_context)
    raw = stage.record_bytes(record_type='genesis', sequence=0, previous_record_sha256=None,
        selection_sha256=selection.registration.pin.sha256, execution_sha256=e.pin.sha256,
        attempt_id=value['attempt_id'], session_id=None,
        payload={'execution': c.pin_dict(e.pin), 'started': c.pin_dict(s.pin)})
    record = _create(selection, 'record', raw, ordinal=0, owner_context=owner_context)
    _create(selection, 'journal', stage.journal_bytes(selection_sha256=selection.registration.pin.sha256,
        execution_sha256=e.pin.sha256, attempt_id=value['attempt_id'], records=(record.pin,)),
        owner_context=owner_context)


def _extend_trace(prev, transcript, control, runtime):
    if (prev is None or transcript.stream != 'transcript' or control.stream != 'control'
            or transcript.bytes < prev.transcript.bytes or control.bytes < prev.control.bytes
            or not transcript.raw.startswith(prev.transcript.raw)
            or not control.raw.startswith(prev.control.raw)):
        return None
    if transcript == prev.transcript and control == prev.control:
        return prev
    t_tail = transcript.raw[prev.transcript.bytes:]
    c_tail = control.raw[prev.control.bytes:]
    native_tail = []
    if t_tail:
        for offset_line, part in enumerate(t_tail.split(b'\n')[:-1], prev.transcript.lines + 1):
            raw = part + b'\n'
            if not raw.endswith(b'\n') or not raw.strip():
                return None
            value = c.strict_json(raw, 'native observed row', 16 * 1024 * 1024)
            if type(value) is not dict or value.get('type') == 'control_response' or (
                    value.get('type') == 'system' and value.get('subtype') == 'init'):
                return None
            native_tail.append((offset_line, raw, value))
    parent_tail = []
    if c_tail:
        for offset_line, part in enumerate(c_tail.split(b'\n')[:-1], prev.control.lines + 1):
            raw = part + b'\n'
            if not raw.endswith(b'\n') or not raw.strip():
                return None
            value = c.strict_json(raw, 'native observed row', 16 * 1024 * 1024)
            if type(value) is not dict or value.get('kind') in ('initialize_sent', 'initialize_ack'):
                return None
            parent_tail.append((offset_line, raw, value))
    sub = object.__new__(observed.Trace)
    sub.transcript, sub.control = transcript, control
    sub.session, sub.policy = prev.session, prev.policy
    sub.calls = dict(prev.calls)
    sub.callbacks = dict(prev.callbacks)
    sub.results = dict(prev.results)
    sub.decisions = dict(prev.decisions)
    sub.frames = dict(prev.frames)
    sub.terminal = prev.terminal
    sub._req_cache = dict(getattr(prev, '_req_cache', {}))
    sub._adm_cache = dict(getattr(prev, '_adm_cache', {}))
    sub._set_cache = dict(getattr(prev, '_set_cache', {}))
    callback_ids = {v.get('request_id') for _, v in sub.callbacks.values()}
    policy = sub.policy
    session_id = sub.session
    for number, raw, value in native_tail:
        sub.frames[number] = value
        kind = value.get('type')
        if value.get('parent_tool_use_id') is not None:
            return None
        if kind in ('assistant', 'user', 'result'):
            message = value.get('message')
            if value.get('model', runtime['model']) != runtime['model'] or (
                    type(message) is dict and message.get('model', runtime['model']) != runtime['model']):
                return None
        if sub.terminal is not None or kind == 'control_cancel_request':
            return None
        if kind == 'result':
            if value.get('session_id') != session_id or value.get('parent_tool_use_id') is not None:
                return None
            sub.terminal = number
        if kind in ('assistant', 'user'):
            message = value.get('message')
            if (value.get('session_id') != session_id or value.get('parent_tool_use_id') is not None
                    or type(message) is not dict or message.get('role', kind) != kind):
                return None
            content = message.get('content')
            if type(content) is not list:
                return None
            for offset, item in enumerate(content):
                if type(item) is not dict:
                    return None
                identity = item.get('id') if item.get('type') == 'tool_use' else item.get('tool_use_id')
                if item.get('type') == 'tool_use':
                    if (kind != 'assistant' or type(identity) is not str or not identity or identity in sub.calls
                            or item.get('name') not in ('Read', 'Write', 'Bash') or type(item.get('input')) is not dict):
                        return None
                    sub.calls[identity] = (number, offset, item)
                elif item.get('type') == 'tool_result':
                    if (kind != 'user' or identity not in sub.calls or identity in sub.results
                            or sub.calls[identity][0] >= number):
                        return None
                    sub.results[identity] = (number, offset, item)
        if kind == 'control_request':
            request = value.get('request')
            data = request.get('input') if type(request) is dict else None
            if type(data) is not dict:
                return None
            identity = data.get('tool_use_id')
            callback = value.get('request_id')
            if (identity not in sub.calls or identity in sub.callbacks or identity in sub.results
                    or type(callback) is not str or not callback or callback in callback_ids
                    or request.get('subtype') != 'hook_callback'
                    or request.get('callback_id') != policy['pretool_control']['callback_id']
                    or request.get('tool_use_id') not in (None, identity)
                    or data.get('hook_event_name') != policy['pretool_control']['event']
                    or data.get('cwd') != policy['readonly_lookups']['repository']
                    or data.get('session_id', session_id) != session_id):
                return None
            call = sub.calls[identity]
            if (call[0] >= number or data.get('tool_name') != call[2]['name']
                    or not observed._same(data.get('tool_input'), call[2]['input'])):
                return None
            sub.callbacks[identity] = (number, value)
            callback_ids.add(callback)
    for number, raw, value in parent_tail:
        if value.get('kind') != 'decision':
            continue
        request = value.get('request')
        data = request.get('request', {}).get('input', {}) if type(request) is dict else {}
        identity = data.get('tool_use_id')
        if (identity not in sub.callbacks or identity in sub.decisions
                or not observed._same(request, sub.callbacks[identity][1])
                or value.get('classification') not in ('prescribed', 'not_prescribed')
                or type(value.get('basis')) is not str):
            return None
        classification, basis = value['classification'], value['basis']
        output = {} if classification == 'prescribed' else {'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
            'permissionDecisionReason': 'Outside the registered tool policy: ' + basis}}
        expected = {'type': 'control_response', 'response': {'subtype': 'success',
            'request_id': request['request_id'], 'response': output}}
        if not observed._same(value.get('response'), expected):
            return None
        sub.decisions[identity] = (number, value)
    return sub


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
    _owner_context: object = field(default=None, compare=False, repr=False)

    def __post_init__(self):
        self._prefixes = self._catalogs._prefixes

    def trace(self, transcript=None, control=None):
        if (transcript is None or transcript == self.transcript) and (control is None or control == self.control):
            if self._trace is None:
                token = receipt_api.catalog_reuse.runtime_token()
                meta_key = None if (token is None or self._catalogs is None) else (
                    token, self.binding.session_id,
                    c.canonical(self.composition['policy']), c.canonical(self.value['runtime']),
                )
                last = getattr(self._catalogs, '_last_trace', None) if meta_key is not None else None
                extended = (_extend_trace(last[1], self.transcript, self.control, self.value['runtime'])
                            if last is not None and last[0] == meta_key else None)
                if extended is not None:
                    self._trace = extended
                else:
                    self._trace = observed.Trace(self.transcript, self.control,
                        session_id=self.binding.session_id, policy=self.composition['policy'], runtime=self.value['runtime'])
                if meta_key is not None and receipt_api.catalog_reuse.runtime_token() is token:
                    self._catalogs._last_trace = (meta_key, self._trace)
            return self._trace
        return observed.Trace(transcript or self.transcript, control or self.control,
            session_id=self.binding.session_id, policy=self.composition['policy'], runtime=self.value['runtime'])

    def decision(self):
        return None if self.phase1 is None else stage._prepare_next(
            self.selection, self.binding, self.phase1, self.history, self._catalogs)


def _require_captured_run(run):
    if type(run) is not _CapturedRun:
        raise ValueError('effect/assessment requires a captured run, not initialization-only evidence')


def _require_run_effect(run):
    _require_captured_run(run)
    value = c.strict_json(run.binding.execution.raw, 'captured execution', c.HARD_LIMITS['request_bytes'])
    if _selected_owner_execution(value):
        association = _require_owner_association(run._owner_context, run.selection,
            run.binding.execution.raw, run.binding.started.raw)
        if (type(run.pool) is not evidence.CapturePool
                or sum(member.captured.pin.bytes for member in run.pool.members)
                   > association.selection.bounds()['max_evidence_bytes']):
            raise ValueError('selected live pool exceeds its complete evidence byte bound')
        if (type(run.reader) is not _Reader or run.reader.pool is not None
                or run.reader.owner_context is not run._owner_context
                or run.reader.selection != run.selection
                or run.reader._owner_execution != run.binding.execution):
            raise ValueError('selected effect requires its actual live owner reader')
        if (c.canonical(run.value) != c.canonical(value)
                or c.canonical(run.composition) != c.canonical(c.strict_json(
                    value['composition_raw_json'].encode('utf-8')))):
            raise ValueError('selected live run changed its execution or composition')
        owner = _saved_member(run.pool, 'owner', association.owner_path)
        if (owner.captured.raw != association.owner_raw
                or owner.metadata_json != run._owner_context._owner_metadata):
            raise ValueError('selected effect owner differs from its admitted bytes or identity')
        # Reconstruct solely from this immutable pool: assigning a live context
        # to a saved/altered run cannot substitute its binding or prefix roles.
        saved = _Reader(run.selection, pool=run.pool, execution=run.binding.execution)
        if _binding(run.selection, value, run.composition, saved, run.pool) != run.binding:
            raise ValueError('selected effect binding differs from its captured initialization')
        for role, prefix in (('transcript', run.transcript), ('control', run.control)):
            if (prefix.stream != role or run.pool.prefix(evidence.prefix_reference(prefix,
                    execution_sha256=run.binding.execution.pin.sha256),
                    execution_sha256=run.binding.execution.pin.sha256) != prefix):
                raise ValueError('selected effect prefix differs from its exact captured stream')
        _require_owner_association(run._owner_context, run.selection,
            run.binding.execution.raw, run.binding.started.raw)
    elif run._owner_context is not None or _selected_owner_execution(run.value):
        raise ValueError('selected live run contradicts its captured execution')


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
    expected_payload = {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack), 'native_init': asdict(initialized),
        'stream_files': live_streams.stream_files(tuple(pool.member(member_id) for _, member_id in pool.stream_bindings))}
    if observation_doc['version'] == 2:
        expected_payload['owner'] = observation_doc['payload']['owner']
    if (session != result.session_id or observation_doc['observation_type'] != 'initialized'
            or c.canonical(observation_doc['payload']) != c.canonical(expected_payload)):
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


def _live_streams(value, *, stream_files, transcript_bytes=None, control_bytes=None, owner_context=None):
    if _selected_owner_execution(value):
        if owner_context is None:
            raise ValueError('selected live streams require their exact owner context')
        association = _require_owner_association(owner_context, owner_context._association.selection,
            owner_context._association.execution_raw)
        if c.canonical(value) != c.canonical(c.strict_json(association.execution_raw)):
            raise ValueError('live streams differ from their owner execution')
    elif owner_context is not None:
        raise ValueError('default live streams cannot borrow selected owner authority')
    anchors = live_streams.identities(stream_files)
    members, prefixes = [], []
    for role, endpoint in (('transcript', transcript_bytes), ('control', control_bytes)):
        kwargs = {} if owner_context is None else {'coordination': owner_context}
        member = live_streams.read_live_stream(
            str(Path(value['attempt_directory']) / (role + '.jsonl')), role,
            max_bytes=(c.HARD_LIMITS['stream_bytes'] if owner_context is None
                       else owner_context._association.max_bytes), identity=anchors[role], **kwargs)
        members.append(member)
        prefixes.append(live_streams.prefix(member, endpoint))
    return tuple(members), tuple(prefixes)


def _declared_stream_files(selection, reader):
    # This early declaration can only restrict an opened identity. _binding
    # subsequently verifies every E/S/init/prefix join before any effect.
    if reader.owner_context is not None:
        association = _require_owner_association(reader.owner_context, selection,
            reader._owner_execution.raw)
        return {role: {'device': device, 'inode': inode}
                for role, _, device, inode in association.streams}
    binding = _document(reader.read('session_binding', selection.role('session_binding')).raw,
                        'actual session binding')
    init = reader.pinned(binding['init_observation'])
    doc = c.strict_json(init.raw, 'initialized observation', c.HARD_LIMITS['metadata_record_bytes'])
    c.exact(doc, _OBSERVATION_KEYS, 'initialized observation')
    if doc['observation_type'] != 'initialized':
        raise ValueError('stream identity must come from the initialized observation')
    if type(doc['version']) is int and doc['version'] == 2:
        if reader.pool is None or reader._owner_execution is None:
            raise ValueError('initialized v2 stream declarations require a saved owner reader')
        value, composition = _saved_owner_execution(selection, reader.pool, reader._owner_execution)
        _binding(selection, value, composition, reader, reader.pool)
        return live_streams.identities(doc['payload']['stream_files'])
    c.exact(doc['payload'], _OBSERVATION_PAYLOADS['initialized'], 'initialized payload')
    return live_streams.identities(doc['payload']['stream_files'])


def _base(selection_path, *, _catalogs=None, owner_context=None):
    from copy import deepcopy
    import sys
    from . import native_shared_selection as selected
    from . import native_shared_registration as registration
    from . import native_execution_authority as authority
    if owner_context is not None:
        association = _require_owner_association(owner_context, owner_context._association.selection,
            owner_context._association.execution_raw)
        if selection_path != association.selection.registration.pin.path:
            raise ValueError('live selection path differs from the owner reader')
    selection = selected.capture(selection_path)
    reader = _Reader(selection, owner_context=owner_context)
    e = reader.read('execution_capture', selection.role('execution_capture'))
    ctx = (_catalogs if owner_context is None and
           type(_catalogs) is receipt_api._ReceiptCatalogContext else None)
    token = receipt_api.catalog_reuse.runtime_token() if ctx is not None else None
    base_key = None if token is None else (
        token, selection_path, selection.registration.raw, e.raw,
        registration.verified, registration.registration, registration._selection, authority.dependency_identity,
    )
    hit = False
    if base_key is not None and base_key in ctx._base:
        saved_inputs, cached_val, cached_comp, cached_spec, cached_doc = ctx._base[base_key]
        try:
            current_inputs = (
                registration._read(cached_val['composition'], 'composition', c.HARD_LIMITS['request_bytes']),
                registration._read(cached_val['system_path'], 'system', c.HARD_LIMITS['input_bytes']),
                registration._read(cached_val['permission_probe'], 'saved permission', c.HARD_LIMITS['permission_wire_bytes']),
                registration._read(cached_comp['runtime_path'], 'runtime_declaration', c.HARD_LIMITS['input_bytes']),
                registration._read(cached_comp['instruction_path'], 'instruction', c.HARD_LIMITS['request_bytes']),
                str(Path.cwd().resolve()), sys.executable, sys.version,
            )
            if current_inputs == saved_inputs:
                value, composition, spec, doc = deepcopy(cached_val), deepcopy(cached_comp), cached_spec, deepcopy(cached_doc)
                registration._paths(value, composition, fresh=False)
                hit = True
        except Exception:
            hit = False
    if not hit and owner_context is None:
        value = registration.verified(e.raw)
        composition, spec, doc, _ = registration._selection(value['composition_raw_json'].encode('utf-8'))
        if base_key is not None and receipt_api.catalog_reuse.runtime_token() is token:
            saved_inputs = (
                registration._read(value['composition'], 'composition', c.HARD_LIMITS['request_bytes']),
                registration._read(value['system_path'], 'system', c.HARD_LIMITS['input_bytes']),
                registration._read(value['permission_probe'], 'saved permission', c.HARD_LIMITS['permission_wire_bytes']),
                registration._read(composition['runtime_path'], 'runtime_declaration', c.HARD_LIMITS['input_bytes']),
                registration._read(composition['instruction_path'], 'instruction', c.HARD_LIMITS['request_bytes']),
                str(Path.cwd().resolve()), sys.executable, sys.version,
            )
            ctx._base[base_key] = (saved_inputs, deepcopy(value), deepcopy(composition), spec, deepcopy(doc))
    if owner_context is not None:
        _require_owner_association(owner_context, selection, e.raw)
        value = registration._verified_in_scope(e.raw)
        composition, spec, doc, _ = registration._selection_in_scope(value['composition_raw_json'].encode('utf-8'))
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
    if owner_context is not None:
        _require_owner_association(owner_context, selection, e.raw,
            reader.read('started_capture', selection.role('started_capture')).raw)
    return selection, reader, value, composition, spec


def _pool(reader, streams):
    if reader.owner_context is not None:
        reader.read('execution_capture', reader.selection.role('execution_capture'))
        reader.read('started_capture', reader.selection.role('started_capture'))
    members = tuple(reader.members.values()) + tuple(streams)
    unique = {member.member_id: member for member in members}
    if (reader.owner_context is not None
            and sum(member.captured.pin.bytes for member in unique.values())
                > reader.selection.bounds()['max_evidence_bytes']):
        raise ValueError('selected live pool exceeds its complete evidence byte bound')
    execution = reader.read('execution_capture', reader.selection.role('execution_capture'))
    return evidence.CapturePool(tuple(unique.values()), tuple((
        evidence.stream_id(execution.pin.sha256, member.captured.pin.role, member.captured.pin.path),
        member.member_id) for member in streams))


def initialize(selection_path, *, transcript_bytes, control_bytes, stream_files, observed_prefixes, owner_context=None):
    """Bind the actual parent-observed initialization, never owner summary flags."""
    selection, reader, value, composition, _ = _base(selection_path, owner_context=owner_context)
    streams, (transcript, control) = _live_streams(value, stream_files=stream_files,
        transcript_bytes=transcript_bytes, control_bytes=control_bytes, owner_context=owner_context)
    c.exact(observed_prefixes, {'transcript', 'control'}, 'parent observed prefixes')
    if observed_prefixes != {'transcript': transcript, 'control': control}:
        raise ValueError('initialization differs from the exact parent-observed prefixes')
    session, sent, ack, init = observed.initialization(transcript, control,
        policy=composition['policy'], runtime=value['runtime'])
    if Path(selection.role('session_binding')).exists() or _observation_paths(selection):
        raise ValueError('native initialization binding is spent or repeated')
    execution = reader.read('execution_capture', selection.role('execution_capture'))
    started = reader.read('started_capture', selection.role('started_capture'))
    owner = None if owner_context is None else reader.read('owner', owner_context._association.owner_path)
    if owner_context is not None:
        _pool(reader, streams)  # Bound both streams plus captured sources before any init publication.
    item = _create(selection, 'observation', observation_bytes('initialized', selection, execution.pin.sha256,
        value['attempt_id'], session, transcript, control,
        {'initialize_sent': asdict(sent), 'initialize_ack': asdict(ack), 'native_init': asdict(init),
         'stream_files': live_streams.stream_files(streams)}, owner=owner), owner_context=owner_context)
    _create(selection, 'session_binding', c.canonical(_binding_document(selection, value, composition,
        execution, started, item, session)), owner_context=owner_context)
    reader = _Reader(selection, owner_context=owner_context)
    binding = _binding(selection, value, composition, reader, _pool(reader, streams))
    history = reader.history(binding)
    if len(history.records) != 1:
        raise ValueError('native session binding requires the sole prior genesis')
    _append(selection, binding, history, 'session_bound',
        {'binding': c.pin_dict(binding.binding_artifact.pin), 'init_observation': c.pin_dict(item.pin)},
        owner_context=owner_context)


def _journal_prefix_digest(run, end):
    pins = tuple(item.pin for item in run.history.records[:end])
    key = (run.selection.registration.pin.sha256, run.binding.execution.pin.sha256,
           run.binding.attempt_id, pins)
    prefixes = getattr(run, '_prefixes', None)
    if prefixes is not None and key in prefixes:
        return prefixes[key]
    raw = stage.journal_bytes(selection_sha256=run.selection.registration.pin.sha256,
        execution_sha256=run.binding.execution.pin.sha256, attempt_id=run.binding.attempt_id,
        records=pins)
    pair = (c.sha(raw), raw)
    if prefixes is not None:
        prefixes[key] = pair
    return pair


def _history_prefix(run, digest):
    """Resolve an exact recorded predecessor; never substitute current history."""
    found = []
    for end in range(1, len(run.history.records) + 1):
        prefix_digest, raw = _journal_prefix_digest(run, end)
        if prefix_digest == digest:
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
    seen_reads, seen_intents, seen_writes, seen_advances = {}, {}, set(), set()
    checked = []
    previous_decision = None
    base_trace = None
    base_attempted = False
    init_lines = None
    settled_cache = {}
    token = receipt_api.catalog_reuse.runtime_token()
    ctx = getattr(run, '_catalogs', None) if token is not None else None
    verified_obs = getattr(ctx, '_verified_obs', None) if ctx is not None else None

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
                if ctx is not None and hasattr(ctx, '_settled'):
                    meta = (token, base_trace.session, c.canonical(base_trace.policy))
                    saved = ctx._settled
                    if (saved is not None and saved[0] == meta
                            and base_trace.transcript.raw.startswith(saved[1])
                            and base_trace.control.raw.startswith(saved[2])):
                        settled_cache = saved[3]
                    ctx._settled = (meta, base_trace.transcript.raw, base_trace.control.raw, settled_cache)
                _bind_trace_cache(base_trace, settled_cache)
            except ValueError:
                base_trace = None
        projected = _prefix_trace(base_trace, transcript, control, init_lines, settled_cache)
        if projected is not None:
            return projected
        return run.trace(transcript, control)

    for index, artifact in enumerate(run.observations):
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
                obs_key = None if verified_obs is None else (
                    'request_read', token, artifact.pin.sha256, request.pin.sha256, actual,
                )
                obs_val = None if obs_key is None else (artifact.raw, request.raw)
                if obs_key is None or verified_obs.get(obs_key) != obs_val:
                    observed.complete_request_read(trace, actual, request)
                    if obs_key is not None and receipt_api.catalog_reuse.runtime_token() is token:
                        verified_obs[obs_key] = obs_val
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
                obs_key = None if verified_obs is None else (
                    'response_written', token, artifact.pin.sha256, response.pin.sha256, actual,
                )
                obs_val = None if obs_key is None else (artifact.raw, response.raw, call.input_json)
                if obs_key is None or verified_obs.get(obs_key) != obs_val:
                    observed.first_response_write(trace, actual, response, intent_input_json=call.input_json)
                    if obs_key is not None and receipt_api.catalog_reuse.runtime_token() is token:
                        verified_obs[obs_key] = obs_val
                seen_writes.add(response.pin.path)
            else:
                result = payload['advance_result']
                if result.get('advance_tool_use_id') != call.tool_use_id or call.tool_use_id not in seen_advances:
                    raise ValueError('advance settlement lacks actual earlier selected admission')
                obs_key = None if verified_obs is None else (
                    'advance_settled', token, artifact.pin.sha256, actual,
                )
                obs_val = None if obs_key is None else (artifact.raw, result)
                if obs_key is None or verified_obs.get(obs_key) != obs_val:
                    observed.helper_result(trace, actual, result)
                    if obs_key is not None and receipt_api.catalog_reuse.runtime_token() is token:
                        verified_obs[obs_key] = obs_val
                _history_prefix(run, result['before_history_sha256'])
                after = decision_at(result['after_history_sha256'])
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
            obs_key = None if verified_obs is None else (
                'response_intent', token, artifact.pin.sha256, current.response.path, current.response.max_bytes,
            )
            obs_val = None if obs_key is None else (artifact.raw, request.input_json)
            if obs_key is None or verified_obs.get(obs_key) != obs_val:
                inputs = _document(request.input_json, 'Write intent')
                if (set(inputs) != {'file_path', 'content'} or inputs['file_path'] != current.response.path
                        or type(inputs['content']) is not str or not inputs['content']
                        or len(inputs['content'].encode('utf-8')) > current.response.max_bytes):
                    raise ValueError('Write intent exceeds the exact response contract')
                if obs_key is not None and receipt_api.catalog_reuse.runtime_token() is token:
                    verified_obs[obs_key] = obs_val
            read_call = reads[0][3]
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


_LAST_VERIFIED_CATALOGS = None


def _load(selection_path, *, transcript_bytes=None, control_bytes=None, _catalogs=None):
    """Strict complete-file route for final and recorded consumers."""
    base = _base(selection_path, _catalogs=_catalogs)
    streams, prefixes = _streams(base[2], transcript_bytes=transcript_bytes, control_bytes=control_bytes)
    return _loaded(base, streams, prefixes, _catalogs=_catalogs)


def _load_live(selection_path, *, transcript_bytes=None, control_bytes=None, stream_files=None,
               _catalogs=None, owner_context=None):
    """Fresh live authority, optionally with owner-reused pure catalog storage."""
    base = _base(selection_path, _catalogs=_catalogs, owner_context=owner_context)
    anchors = _declared_stream_files(base[0], base[1])
    if stream_files is not None and live_streams.identities(stream_files) != anchors:
        raise ValueError('observed stream identities differ from initialized authority')
    streams, prefixes = _live_streams(base[2], stream_files=anchors,
        transcript_bytes=transcript_bytes, control_bytes=control_bytes, owner_context=owner_context)
    return _loaded(base, streams, prefixes, _catalogs=_catalogs)


def _loaded(base, streams, prefixes, *, _catalogs=None):
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
                       transcript, control, binding, history, observations, phase1,
                       _owner_context=reader.owner_context)
    if _catalogs is not None:
        run._catalogs = receipt_api._catalog_context(_catalogs)
        run._prefixes = run._catalogs._prefixes
    _checked_observations(run)
    if reader.owner_context is not None:
        _require_run_effect(run)
    return run


def _persist_observation(run, kind, payload):
    _require_run_effect(run)
    return _create(run.selection, 'observation', observation_bytes(kind, run.selection,
        run.binding.execution.pin.sha256, run.binding.attempt_id, run.binding.session_id,
        run.transcript, run.control, payload), ordinal=len(run.observations), owner_context=run._owner_context)


def capture_stage(selection_registration_path, *, _catalogs=None, owner_context=None):
    """Capture the sole pending, actually admitted fixed advance invocation."""
    run = _load_live(str(selection_registration_path), _catalogs=_catalogs,
                     owner_context=owner_context)
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
    obs_docs = [(item, c.strict_json(item.raw)) for item in run.observations]
    candidates = [item for item, doc in obs_docs if doc['observation_type'] == 'advance_admitted'
                  and doc['payload']['call']['tool_use_id'] == call.tool_use_id]
    if not candidates:
        if sum(doc['observation_type'] == 'advance_admitted' for _, doc in obs_docs) >= c.HARD_LIMITS['advance_invocations']:
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


def _stage_owner_selected(invocation):
    """Recognize reserved E/C declarations without changing pure v1 fixtures."""
    if type(invocation) is not c.StageInvocationCapture:
        raise ValueError('publication requires the actual selected captured invocation')
    value = c.strict_json(invocation.execution.execution.raw, 'stage execution', c.HARD_LIMITS['request_bytes'])
    reserved = _selected_owner_execution(value)
    if type(value) is dict:
        reserved = reserved or 'stream_snapshot_profile' in value
        raw = value.get('composition_raw_json')
        if type(raw) is str:
            composition = c.strict_json(raw.encode('utf-8'), 'stage composition', c.HARD_LIMITS['request_bytes'])
            reserved = reserved or (type(composition) is dict and 'stream_snapshot_profile' in composition)
    if reserved:
        from . import native_shared_registration as registration
        if registration._execution_profile(registration._execution_value(invocation.execution.execution.raw)) is None:
            raise ValueError('stage invocation has an incomplete selected owner profile')
    return reserved


def _fresh_stage_invocation(invocation, owner_context, *, _catalogs=None):
    """Actual current invocation check shared by capture and selected writer."""
    if type(invocation) is not c.StageInvocationCapture:
        raise ValueError('publication requires the actual selected captured invocation')
    if _stage_owner_selected(invocation):
        _require_owner_association(owner_context, invocation.selection,
            invocation.execution.execution.raw, invocation.execution.started.raw)
    elif owner_context is not None:
        raise ValueError('default stage invocation cannot use a selected owner context')
    fresh = capture_stage(invocation.selection.registration.pin.path,
                          owner_context=owner_context, _catalogs=_catalogs)
    # A newly persisted admission is an external observation, not part of the
    # journal predecessor; include it consistently in the freshly read history.
    old = replace(invocation, history=replace(invocation.history,
        observations=fresh.history.observations))
    if old != fresh:
        raise ValueError('selected capture changed before stage publication')
    return fresh


def publish_stage(invocation, proposal, *, owner_context=None, _catalogs=None):
    """Recheck the same current invocation, then perform only derived effects."""
    from .native_shared_publication import publish_derived
    if _stage_owner_selected(invocation):
        # The actual selected publisher performs the one fresh check, even
        # when called directly rather than through this convenience wrapper.
        result, _ = publish_derived(invocation, proposal, owner_context=owner_context,
                                    _catalogs=_catalogs)
    else:
        fresh = _fresh_stage_invocation(invocation, owner_context, _catalogs=_catalogs)
        result, _ = publish_derived(fresh, proposal, _catalogs=_catalogs)
    return result


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
    if complete and set(visible) != {item.pin.sha256 for item in run.history.records}:
        raise ValueError('completed history has unpublished or unobserved stage records')
    return phase.report(complete=complete), actions


def seal_originals(run, kind):
    """Parent-only observation effect after genuine settled helper results."""
    _require_run_effect(run)
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
        _create(run.selection, role, captured[source].raw, owner_context=run._owner_context)
    sealed = {source: _captured(role, run.selection.role(role), captured[source].raw) for source, role in inputs}
    calls = [row['tool_use_id'] for row in report['checks'] if row['helper'] in helpers]
    if kind == 'seal_phase1':
        payload = {'full': c.pin_dict(sealed['full'].pin), 'original_receipt': c.pin_dict(sealed['receipt'].pin), 'helper_calls': calls}
        obs = _persist_observation(run, 'phase1_sealed', payload)
        body = {'kind': 'd4d_native_shared_phase1_seal', 'version': 1,
            'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
            'session_id': run.binding.session_id, 'full': payload['full'], 'original_receipt': payload['original_receipt'],
            'observation': c.pin_dict(obs.pin)}
        seal = _create(run.selection, 'phase1_seal', c.canonical(body), owner_context=run._owner_context)
        record_payload = {'seal': c.pin_dict(seal.pin), 'full': payload['full'],
            'original_receipt': payload['original_receipt'], 'observation': c.pin_dict(obs.pin)}
        _append(run.selection, run.binding, run.history, 'phase1_sealed', record_payload,
                owner_context=run._owner_context)
    else:
        payload = {'core': c.pin_dict(sealed['core'].pin), 'helper_calls': calls}
        obs = _persist_observation(run, 'core_sealed', payload)
        body = {'kind': 'd4d_native_shared_core_seal', 'version': 1,
            'selection_sha256': run.selection.registration.pin.sha256, 'execution_sha256': run.binding.execution.pin.sha256,
            'session_id': run.binding.session_id, 'phase1_seal_sha256': run.phase1.seal.pin.sha256,
            'core': payload['core'], 'observation': c.pin_dict(obs.pin)}
        seal = _create(run.selection, 'core_seal', c.canonical(body), owner_context=run._owner_context)
        _append(run.selection, run.binding, run.history, 'core_sealed',
            {'seal': c.pin_dict(seal.pin), 'core': payload['core'], 'observation': c.pin_dict(obs.pin)},
            owner_context=run._owner_context)
    # A mutating host cannot make a result certify different bytes between
    # actual helper settlement and the original-copy publication.
    for source, role in inputs:
        if evidence.read_regular(paths[source], role, max_bytes=c.HARD_LIMITS['original_full_bytes']).captured != captured[source]:
            raise ValueError('original output changed during its exact observed seal')
    _require_run_effect(run)


def current_effect_view(run, *, correction_window=False, exclude_pending=None):
    """Derive the restrictive overlay solely from captured state and events."""
    _require_captured_run(run)
    return _effect_view_from_decision(run, run.decision(),
        correction_window=correction_window, exclude_pending=exclude_pending)


def _effect_view_from_decision(run, decision, *, correction_window=False, exclude_pending=None):
    """Use a decision just derived by the fixed caller from this captured run.

    No result is retained across calls. The public wrapper always derives its
    own decision; the controller can pass the one it just checked for this
    event before granting an effect. All view and chronology checks stay here.
    """
    _require_captured_run(run)
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


def observe_request_read(run, identity):
    _require_run_effect(run)
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
    _require_run_effect(run)
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
    _require_run_effect(run)
    current = run.decision(); trace = run.trace(); actual = trace.settled(identity)
    if current is None or current.state != 'awaiting_response' or current.response is None:
        raise ValueError('response settlement has no current selected destination')
    matches = [(item, doc['payload']) for item, doc in (
        (item, _document(item.raw, 'response intent')) for item in run.observations
    ) if doc['observation_type'] == 'response_intent' and doc['payload']['tool_use_id'] == identity]
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
        'read_observation': payload['read_observation'], 'response_observation': c.pin_dict(obs.pin)},
        **({} if run._owner_context is None else {'owner_context': run._owner_context}))


def observe_advance_settled(run, identity):
    _require_run_effect(run)
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


def _refuse_implicit_owner_context(owner_context):
    """Missing explicit context cannot fall through from a selected scope.

    This detects refusal only. It never borrows an ambient context or grants
    permission to an otherwise ordinary recorded/default caller.
    """
    if owner_context is None:
        from . import native_owner_profile_v1 as profiles
        from . import native_stream_coordination_v1 as coordination
        if profiles._ACTIVE.get() is not None or coordination._OWNER_READER.get() is not None:
            raise ValueError('selected helper requires its explicit owner context')


def _helper_live_run(selection_registration_path, owner_context):
    _refuse_implicit_owner_context(owner_context)
    if owner_context is None:
        return _load_live(str(selection_registration_path))
    from . import native_stream_coordination_v1 as coordination
    if type(owner_context) is not coordination._OwnerReaderContext:
        raise ValueError('selected helper requires its exact owner reader context')
    association = _require_owner_association(owner_context, owner_context._association.selection,
                                             owner_context._association.execution_raw)
    if str(selection_registration_path) != association.selection.registration.pin.path:
        raise ValueError('selected helper registration differs from its owner context')
    run = _load_live(str(selection_registration_path), owner_context=owner_context)
    _require_run_effect(run)
    return run


def _pending_receipt_or_recorder(run, roles):
    """A fixed internal role set restricts an actual, sole pending admission."""
    _require_run_effect(run)
    trace = run.trace()
    pending = trace.pending()
    if len(pending) != 1 or trace.terminal is not None:
        raise ValueError('selected helper requires one pending nonterminal call')
    call = trace.admitted(pending[0])
    inputs = c.strict_json(call.input_json, 'selected helper input', c.HARD_LIMITS['request_bytes'])
    if type(inputs) is not dict:
        raise ValueError('selected helper input must be a closed tool object')
    matches = [role for role in roles
               if inputs.get('command') == run.composition['policy']['native_shared_helpers'][role]]
    if call.tool_name != 'Bash' or len(matches) != 1:
        raise ValueError('selected helper differs from its actual fixed admitted purpose')
    phase, _ = phase_replay(run)
    if not phase['passed']:
        raise ValueError('selected helper current phase history did not pass')
    return matches[0]


def _receipt_paths(run):
    paths = run.spec._agentic_artifact_paths
    return {'full': Path(paths['full']), 'receipt': Path(paths['receipt']),
            'provenance': Path(run.composition['policy']['post_final_recorder']['destination']),
            'core_dir': Path(paths['core']).parent}


def _require_cli_process(command):
    """Check the actual Python CLI invocation, not a caller-provided argv.

    This is trusted local process consistency, not OS authentication or a
    defense against arbitrary Python mutation of interpreter/module state.
    """
    import sys
    from importlib.machinery import ModuleSpec
    from types import ModuleType
    from . import native_execution_authority as authority
    words = shlex.split(command)
    original = getattr(sys, 'orig_argv', None)
    if (len(words) < 4 or words[1:3] != ['-m', 'data_sheets_schema.cli']
            or type(original) is not list or any(type(word) is not str for word in original)
            or original != words):
        raise ValueError('selected helper process differs from its exact registered argv')
    main = sys.modules.get('__main__')
    spec = getattr(main, '__spec__', None)
    if (type(main) is not ModuleType or main.__name__ != '__main__'
            or type(spec) is not ModuleSpec or spec.name != 'data_sheets_schema.cli.__main__'
            or getattr(main, '__package__', None) != 'data_sheets_schema.cli'
            or type(sys.argv) is not list or not sys.argv):
        raise ValueError('selected helper requires the actual fixed CLI module entry')
    expected = authority.ROOT / 'src/data_sheets_schema/cli/__main__.py'
    for origin in (getattr(main, '__file__', None), spec.origin, sys.argv[0]):
        if type(origin) is not str or not origin or Path(origin).resolve() != expected.resolve():
            raise ValueError('selected helper CLI module has a foreign physical origin')


def require_receipt_invocation(selection_registration_path, *, owner_context):
    """Fixed read-only receipt helper; caller options may only restrict it."""
    if owner_context is None:
        _refuse_implicit_owner_context(owner_context)
        raise ValueError('selected receipt invocation requires its owner context')
    run = _helper_live_run(selection_registration_path, owner_context)
    _pending_receipt_or_recorder(run, ('phase1_receipts',))
    _require_cli_process(run.composition['policy']['native_shared_helpers']['phase1_receipts'])
    doc = run.selection.document()
    result = {'selection_path': run.selection.registration.pin.path,
        'method': run.spec.method, 'label': run.spec.label, 'project': run.spec.project,
        'bundle': doc['inputs']['bundle']['path'],
        'chunk_manifest': doc['inputs']['chunk_manifest']['path'],
        'manifest': str(run.spec.manifest),
        'command': run.composition['policy']['native_shared_helpers']['phase1_receipts'],
        'paths': _receipt_paths(run)}
    _require_run_effect(run)
    return result


def selected_receipt_paths(selection_registration_path, *, owner_context=None):
    """Explicit live S reaches only the paths captured in its already active E."""
    _refuse_implicit_owner_context(owner_context)
    if owner_context is not None:
        return require_receipt_invocation(selection_registration_path,
                                          owner_context=owner_context)['paths']
    _, _, _, composition, spec = _base(str(selection_registration_path))
    paths = spec._agentic_artifact_paths
    return {'full': Path(paths['full']), 'receipt': Path(paths['receipt']),
            'provenance': Path(composition['policy']['post_final_recorder']['destination']),
            'core_dir': Path(paths['core']).parent}


from .native_shared_current import current_artifact


def _receipt_assessment(run, *, full_path, receipt_path):
    _require_captured_run(run)
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
        fresh_catalogs = getattr(run, '_catalogs', None) or receipts._catalog_context()
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


def live_receipt_block(selection_registration_path, *, full_path, receipt_path,
                       owner_context=None, snapshot_spec=None, snapshot_record=None):
    global _LAST_VERIFIED_CATALOGS
    run = _helper_live_run(selection_registration_path, owner_context)
    if owner_context is None:
        phase_replay(run)
    else:
        _pending_receipt_or_recorder(run, ('phase1_receipts', 'recorder'))
    if snapshot_record is not None:
        _record_matches_run(run, snapshot_spec, snapshot_record)
    elif snapshot_spec is not None and c.canonical(snapshot_spec.render_spec()) != c.canonical(run.composition['render_spec']):
        raise ValueError('caller spec differs from the explicit native execution')
    block = _receipt_assessment(run, full_path=full_path, receipt_path=receipt_path)[0]
    if owner_context is not None:
        _require_run_effect(run)
    elif getattr(run, '_catalogs', None) is not None:
        _LAST_VERIFIED_CATALOGS = (str(selection_registration_path), run._catalogs)
    return block


def _provenance_block(run):
    _require_captured_run(run)
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


def _current_provenance_block(run):
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


def live_provenance_block(selection_registration_path, *, owner_context=None):
    global _LAST_VERIFIED_CATALOGS
    run = _helper_live_run(selection_registration_path, owner_context)
    if owner_context is not None:
        _pending_receipt_or_recorder(run, ('recorder',))
    block = _current_provenance_block(run)
    if owner_context is not None:
        _require_run_effect(run)
    elif getattr(run, '_catalogs', None) is not None:
        _LAST_VERIFIED_CATALOGS = (str(selection_registration_path), run._catalogs)
    return block


_RECORDER_PARAMETERS = frozenset(('project', 'method', 'label', 'input_bundle', 'prompts',
    'prompt_text', 'condition', 'arm', 'runtime', 'provider', 'bundle_for_spec',
    'reasoning_effort', 'phase_specs', 'phases_skipped', 'manifest', 'chunk_manifest',
    'receipt_expected', 'stated_profile', 'render_spec_json', 'prompt_text_env'))
_RECORDER_FLAGS = {'--project': 'project', '--method': 'method', '--label': 'label',
    '--input-bundle': 'input_bundle', '--prompt': 'prompts', '--manifest': 'manifest',
    '--profile': 'stated_profile', '--chunk-manifest': 'chunk_manifest',
    '--reasoning-effort': 'reasoning_effort', '--render-spec-json': 'render_spec_json',
    '--prompt-text-env': 'prompt_text_env'}


def _recorder_parameters(run, spec, parameters):
    c.exact(parameters, {'values', 'sources', 'instruction_path'}, 'selected recorder parameters')
    values = c.exact(parameters['values'], _RECORDER_PARAMETERS, 'selected recorder callback values')
    sources = c.exact(parameters['sources'], _RECORDER_PARAMETERS, 'selected recorder parameter sources')
    words = shlex.split(run.composition['policy']['native_shared_helpers']['recorder'])
    if words[:5] != [run.composition['policy']['python'], '-m', 'data_sheets_schema.cli', 'provenance', 'record']:
        raise ValueError('selected recorder command has an unsupported fixed prefix')
    expected = {name: None for name in _RECORDER_PARAMETERS}
    expected.update(arm='baseline', receipt_expected=False, prompts=(), phase_specs=(), phases_skipped=())
    supplied = set()
    if len(words[5:]) % 2:
        raise ValueError('selected recorder command has an incomplete fixed argument')
    for flag, value in zip(words[5::2], words[6::2]):
        name = _RECORDER_FLAGS.get(flag)
        if name is None or (name in supplied and name != 'prompts'):
            raise ValueError('selected recorder command has an unsupported or duplicate fixed argument')
        supplied.add(name)
        expected[name] = expected[name] + (value,) if name == 'prompts' else value
    if supplied != set(_RECORDER_FLAGS.values()):
        raise ValueError('selected recorder command lacks its complete fixed arguments')
    for name in _RECORDER_PARAMETERS:
        if (type(values[name]) is not type(expected[name]) or values[name] != expected[name]
                or (name in ('prompts', 'phase_specs', 'phases_skipped')
                    and any(type(value) is not str for value in values[name]))
                or type(sources[name]) is not str
                or sources[name] != ('COMMANDLINE' if name in supplied else 'DEFAULT')):
            raise ValueError('selected recorder callback differs from its registered argument: ' + name)
    if (spec is None or c.canonical(spec.render_spec()) != c.canonical(run.composition['render_spec'])
            or type(parameters['instruction_path']) is not str
            or c.canonical_path(parameters['instruction_path'], 'selected recorder instruction')
               != run.composition['instruction_path']):
        raise ValueError('selected recorder differs from its used instruction or rendering')


def require_recorder_invocation(selection_registration_path, *, owner_context, spec, parameters):
    if owner_context is None:
        _refuse_implicit_owner_context(owner_context)
        raise ValueError('selected recorder invocation requires its owner context')
    run = _helper_live_run(selection_registration_path, owner_context)
    _pending_receipt_or_recorder(run, ('recorder',))
    _require_cli_process(run.composition['policy']['native_shared_helpers']['recorder'])
    _recorder_parameters(run, spec, parameters)
    _current_provenance_block(run)
    _require_run_effect(run)


def require_recorder_write(path, *, owner_context=None, record):
    """Fixed recorder destination guard; never acquire a writer-owned scope.

    Checks surround known Python writer boundaries, not arbitrary host writes
    or a guarantee that a later syscall cannot race with external changes.
    """
    _refuse_implicit_owner_context(owner_context)
    if owner_context is None:
        return
    from . import native_stream_coordination_v1 as coordination
    if type(owner_context) is not coordination._OwnerReaderContext:
        raise ValueError('selected recorder write requires its exact owner context')
    run = _helper_live_run(owner_context._association.selection.registration.pin.path, owner_context)
    _pending_receipt_or_recorder(run, ('recorder',))
    _current_provenance_block(run)
    _record_matches_run(run, None, record)
    destination = c.canonical_path(str(path), 'selected recorder destination')
    expected = run.composition['policy']['post_final_recorder']['destination']
    if type(expected) is not str or not expected:
        raise ValueError('selected recorder policy destination requires nonempty text')
    if not expected.startswith('/'):
        working_directory = c.canonical_path(run.binding.working_directory,
                                             'selected recorder working directory')
        # Preserve the registered spelling for validation, including aliases
        # that Path joining or resolving would silently normalize away.
        expected = working_directory.rstrip('/') + '/' + expected
    expected = c.canonical_path(expected, 'selected recorder policy destination')
    target = Path(destination)
    if destination != expected or target.is_symlink() or str(target.resolve()) != destination:
        raise ValueError('selected recorder write differs from its exact physical destination')
    _require_run_effect(run)


def _recorded_run(spec, record):
    global _LAST_VERIFIED_CATALOGS
    from .native_shared_render import validate_metadata
    if type(record) is not dict:
        raise ValueError('native recorded reader requires one explicit provenance mapping')
    try:
        render_spec = record['prompts']['request']['spec']
        document = validate_metadata(render_spec)
    except (KeyError, TypeError) as exc:
        raise ValueError('native record lacks its complete selected render authority') from exc
    reg_path = str(document['registration_path'])
    saved_catalogs = (_LAST_VERIFIED_CATALOGS[1]
                      if _LAST_VERIFIED_CATALOGS is not None and _LAST_VERIFIED_CATALOGS[0] == reg_path
                      else None)
    run = _load(document['registration_path'], _catalogs=saved_catalogs)
    _record_matches_run(run, spec, record)
    if getattr(run, '_catalogs', None) is not None:
        _LAST_VERIFIED_CATALOGS = (reg_path, run._catalogs)
    return run


def _record_matches_run(run, spec, record):
    """Join an optional record to this exact run, without selecting another route."""
    _require_captured_run(run)
    from .native_shared_render import validate_metadata
    if type(record) is not dict:
        raise ValueError('native recorded reader requires one explicit provenance mapping')
    try:
        render_spec = record['prompts']['request']['spec']
        document = validate_metadata(render_spec)
    except (KeyError, TypeError) as exc:
        raise ValueError('native record lacks its complete selected render authority') from exc
    if document['registration_path'] != run.selection.registration.pin.path:
        raise ValueError('native record belongs to another selected registration')
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
    _, _, _, _, _, bases, _, _ = receipts._inputs(run.selection, run.phase1, _catalogs=run._catalogs)
    return rc.claim_receipts(_mapping(effective.raw, 'native effective receipt'),
        _mapping(full.raw, 'native final full'), _mapping(run.phase1.full.raw, 'native original full'),
        identifier_bases=bases)


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
