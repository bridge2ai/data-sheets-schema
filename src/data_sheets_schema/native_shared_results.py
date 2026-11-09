"""Bounded captured reconstruction without verifier/bootstrap or frozen v1 imports.

Host capture, replay orchestration and publication live in the explicitly named
native_shared_results_orchestration module. Nothing here imports that layer.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from . import native_shared_contract as c
from . import native_shared_capture as capture_api
from . import native_shared_evidence as evidence
from . import native_shared_selection as selection_api

POOL_NAME = 'native-shared-capture.json'
REPORT_KIND = 'native_shared_saved_reconstruction'

class Snapshot:
    """Old engine's fixed snapshot surface, backed by bounded immutable members."""
    def __init__(self, root, members=()):
        self.root = Path(root)
        self.raw, self.roles, self.metadata = {}, {}, {}
        self.aliases, self.alias_metadata = {}, {}
        self.members = {}
        self.sealed = False
        for member in members:
            self.add(member)

    def add(self, member):
        if self.sealed:
            raise ValueError('cannot extend a sealed native snapshot')
        item = member.captured
        path = item.pin.path
        metadata = c.strict_json(member.metadata_json)
        metadata.pop('symlink')
        if path in self.raw and (self.raw[path] != item.raw or self.metadata[path] != metadata):
            raise ValueError('current capture contains contradictory versions of one physical path')
        self.raw[path], self.metadata[path] = item.raw, metadata
        self.roles.setdefault(path, set()).add(item.pin.role)
        self.aliases[path], self.alias_metadata[path] = path, {'symlink': False}
        self.members[member.member_id] = member
        if (len(self.members) > c.HARD_LIMITS['captured_members'] or
                sum(len(raw) for raw in self.raw.values()) > c.HARD_LIMITS['evidence_raw_total_bytes']):
            raise ValueError('complete native snapshot exceeds its bounded collection')

    def path(self, value):
        path = Path(value)
        key = str(path if path.is_absolute() else self.root / path)
        if key not in self.aliases:
            raise ValueError('saved consumer requested an uncaptured path identity')
        return Path(self.aliases[key])

    def read(self, value, role):
        key = str(self.path(value))
        if key not in self.raw:
            raise ValueError('saved consumer requested uncaptured bytes')
        return self.raw[key]

    def identity(self):
        return {path: {'sha256': c.sha(raw), 'bytes': len(raw), 'roles': sorted(self.roles[path])}
                for path, raw in sorted(self.raw.items())}

    def verify_unchanged(self):
        for member in self.members.values():
            pin = member.captured.pin
            current = evidence.read_regular(pin.path, pin.role, max_bytes=max(1, pin.bytes))
            if current != member:
                raise ValueError('native captured bytes or opened file identity changed before publication')


def _member(pool, role, path):
    found = [m for m in pool.members if m.captured.pin.role == role and m.captured.pin.path == str(path)]
    if len(found) != 1:
        raise ValueError('saved pool lacks exactly one ' + role + ' at its selected path')
    return found[0]


def _captured_selection(pool, value):
    composition = c.strict_json(value['composition_raw_json'].encode(), 'captured C', c.HARD_LIMITS['request_bytes'])
    raw = composition['selection_raw_json'].encode('utf-8')
    doc = c.parse_selection(raw)
    registration = _member(pool, 'selection', doc['registration_path']).captured
    if registration.raw != raw:
        raise ValueError('saved selection differs from the execution declaration')
    artifacts = {role: _member(pool, role, pin['path']).captured
                 for role, pin in selection_api._declarations(doc)}
    schemas = selection_api._declared_schemas(doc, artifacts)
    authority = tuple(a for role, a in artifacts.items()
        if role != 'receipt_policy' and not role.startswith(('full_schema:', 'core_schema:')))
    return selection_api.rebuild(registration, authority, schemas, artifacts['receipt_policy'])


def rebuild(pool, value, *, _catalogs=None):
    """Reconstruct the captured run; this function performs no filesystem reads.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies bounded captured pool and execution value; RunSpec.from_render_spec validates the captured spec before replay, with no filesystem reads or live admission.
    """
    from .api_runner import RunSpec
    selected = _captured_selection(pool, value)
    if sum(member.captured.pin.bytes for member in pool.members) > selected.bounds()['max_evidence_bytes']:
        raise ValueError('complete capture exceeds the selected evidence bound')
    reader = capture_api._Reader(selected, pool=pool)
    composition = c.strict_json(value['composition_raw_json'].encode(), 'captured composition', c.HARD_LIMITS['request_bytes'])
    if (composition['selection_raw_json'].encode() != selected.registration.raw
            or c.sha(value['composition_raw_json'].encode()) != value['composition_sha256']):
        raise ValueError('saved E/C/S raw identities disagree')
    run = selected.document()['run']
    spec = RunSpec.from_render_spec(composition['render_spec'], project=run['project'], method=run['method'], label=run['label'])
    spec._native_shared_generation_capture = selected
    streams = tuple(_member(pool, role, Path(value['attempt_directory']) / (role + '.jsonl'))
                    for role in ('transcript', 'control'))
    transcript, control = (capture_api._prefix(member, None) for member in streams)
    binding = capture_api._binding(selected, value, composition, reader, pool)
    from .native_shared_controller import captured_execution_body
    if c.canonical(captured_execution_body(binding.execution.raw)) != c.canonical(value):
        raise ValueError('saved binding differs from the exact supplied execution')
    started = c.strict_json(binding.started.raw, 'saved started identity', c.HARD_LIMITS['metadata_record_bytes'])
    if (started.get('state') != 'started' or started.get('attempt_id') != value['attempt_id']
            or started.get('registration_sha256') != binding.execution.pin.sha256
            or started.get('composition_sha256') != value['composition_sha256']
            or type(started.get('dispatch_limit')) is not int or started['dispatch_limit'] != 1):
        raise ValueError('saved binding lacks its exact one-use consumed identity')
    observations = sorted((m.captured for m in pool.members if m.captured.pin.role == 'observation'),
                          key=lambda item: item.pin.path)
    if len(observations) > c.HARD_LIMITS['observation_records']:
        raise ValueError('saved observation collection exceeds its bound')
    for number, item in enumerate(observations):
        expected = str(Path(selected.role('observations_root')) / f'{number:06d}.json')
        if item.pin.path != expected:
            raise ValueError('saved observation collection is not the complete ordered selected catalog')
        reader.read('observation', item.pin.path, item.pin)
    history = replace(reader.history(binding), observations=tuple(observations))
    phase1 = capture_api._phase1(selected, binding, history, reader)
    result = capture_api._CapturedRun(selected, value, composition, spec, reader, pool,
        transcript, control, binding, history, tuple(observations), phase1)
    if _catalogs is not None:
        from .native_shared_receipts import _catalog_context
        result._catalogs = _catalog_context(_catalogs)
    capture_api._checked_observations(result)
    return result


def validate_file_basis(value, result, *, retain_paths=()):
    """Native-only bound before the common reader's historical file loop."""
    files = result['captured_files']
    if len(files) > c.HARD_LIMITS['captured_members']:
        raise ValueError('saved native file catalog exceeds its bounded count')
    total = 0
    retained = {}
    for path, pin in files.items():
        c.canonical_path(path, 'saved native file')
        c.exact(pin, {'bytes', 'sha256', 'roles'}, 'saved native file identity')
        size = pin['bytes']
        if (type(size) is not int or not 0 <= size <= c.HARD_LIMITS['stream_bytes']
                or type(pin['roles']) is not list or not pin['roles']
                or any(type(role) is not str or not role for role in pin['roles'])
                or sorted(set(pin['roles'])) != pin['roles']):
            raise ValueError('saved native file identity has untyped or oversized bytes/roles')
        total += size
        if total > c.HARD_LIMITS['evidence_raw_total_bytes']:
            raise ValueError('saved native file basis exceeds its aggregate byte bound')
        actual = evidence.read_regular(path, 'saved_file', max_bytes=max(1, size)).captured
        if actual.pin.bytes != size or actual.pin.sha256 != pin['sha256']:
            raise ValueError('saved evidence differs from its bounded captured basis')
        if path in retain_paths:
            retained[path] = actual.raw
    if retain_paths:
        return retained


def _read_pool(path, limit):
    # This role's wire ceiling exceeds an individual native stream ceiling.
    # The opened read remains bounded and metadata-stable before JSON decoding.
    import os
    import stat
    c.canonical_path(path, 'saved pool path')
    target = Path(path)
    before = target.lstat()
    if (target.resolve(strict=True) != target or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1 or before.st_size > limit):
        raise ValueError('saved pool is not its bounded regular physical file')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        chunks, remaining = [], limit + 1
        while remaining:
            part = os.read(descriptor, min(65536, remaining))
            if not part: break
            chunks.append(part); remaining -= len(part)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = lambda x: (x.st_dev, x.st_ino, x.st_mode, x.st_nlink, x.st_size, x.st_mtime_ns)
    if (len(raw) != before.st_size or len(raw) > limit or
            any(identity(x) != identity(before) for x in (opened, after, target.lstat()))):
        raise ValueError('saved pool changed or exceeded its bound during opened capture')
    return raw
