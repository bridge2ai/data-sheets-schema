"""Captured callback inputs; fresh reconstruction without a source loader.

Admission supplies the fixed, already source-verified reconstruction entry.
Neither an earlier replay verdict nor a mutable RunSpec is worker authority.
"""
from dataclasses import dataclass
from pathlib import Path
from weakref import WeakKeyDictionary, ref

from . import native_shared_contract as c
from . import native_shared_capture as captured
from . import native_shared_evidence as evidence
from . import native_shared_selection as selection


_SPEC_FIELDS = (
    'native_shared_generation_version', 'native_shared_generation_registration',
    'condition', 'render_version', 'runtime', 'method', 'out_dir', 'prompt_text_env',
    'native_source_attribution_version', 'shared_generation_version', 'api_playbook_version',
    'receipt_completion_version', 'removal_repair_version', 'bounded_carry_version',
    'native_source_attribution_max_checks', 'receipt_completion_registration',
    'shared_generation_registration', 'provider', 'reasoning_effort', 'profile',
    'profile_basis', 'chunk_manifest', 'manifest', 'manifest_used', 'project', 'arm',
    'label', 'bundle', '_agentic_artifact_paths', '_agentic_toolchain',
)


@dataclass(frozen=True, slots=True)
class FrozenSpec:
    fields_json: bytes
    rendered_json: bytes

    @classmethod
    def capture(cls, spec):
        """        RunSpec boundary: validated-caller

        RunSpec precondition: Admission caller supplies the unchanged validated RunSpec from freshly verified preparation; this captures fields and render_spec without granting authority.
        """
        fields = {name: getattr(spec, name) for name in _SPEC_FIELDS}
        fields = {name: str(value) if isinstance(value, Path) else value
                  for name, value in fields.items()}
        fields['_replay_only'] = True
        return cls(c.canonical(fields), c.canonical(spec.render_spec()))

    def __getattr__(self, name):
        values = c.strict_json(self.fields_json)
        if name not in values:
            raise AttributeError(name)
        return values[name]

    def render_spec(self):
        return c.strict_json(self.rendered_json, max_bytes=c.HARD_LIMITS['request_bytes'])


_ADMISSIONS = WeakKeyDictionary()
_PREFIX_OWNERS = WeakKeyDictionary()
_ADMISSION_MEMBERS = ('registration_raw', 'execution_json', 'composition_json',
    'preparation_raw', 'rebuild_arguments_json', 'selection', 'spec', 'rebuild',
    'controls', 'check_sources')


def require_admission(value):
    if type(value) is not Admission or value not in _ADMISSIONS:
        raise ValueError('callback capture was not minted by the active admission loader')
    if (type(value.selection) is not c.NativeSelectionCapture or type(value.spec) is not FrozenSpec
            or any(getattr(value, name) is not original
                   for name, original in _ADMISSIONS[value])):
        raise ValueError('captured callback admission reference changed')
    return value


class _PrefixOwner:
    """One admission's bounded semantic checkpoints and irreversible byte anchors."""
    def __init__(self, guard, admission=None):
        self.guard = guard
        self.admission = None if admission is None else ref(admission)
        self.closed = False
        self.records = ()
        self.observations = ()
        self.streams = ()
        self.artifacts = {}
        self.semantic = {}
        self.observation_state = None
        self.epoch = 0

    def check_active(self):
        if self.closed:
            raise ValueError('callback prefix admission has closed')
        if self.admission is not None:
            require_admission(self.admission())

    def close(self):
        self.closed = True
        self.guard.disabled = True
        self.semantic.clear()
        self.observation_state = None

    def begin(self, run):
        self.check_active()
        epoch = self.epoch
        records = tuple(item.pin for item in run.history.records)
        observations = tuple(item.pin for item in run.observations)
        if (records[:len(self.records)] != self.records
                or observations[:len(self.observations)] != self.observations):
            raise ValueError('callback history replaced its verified prefix')
        for role, length, digest in self.streams:
            raw = getattr(run, role).raw
            if len(raw) < length or c.sha(raw[:length]) != digest:
                raise ValueError('callback stream replaced its verified prefix')
        for pin in self.artifacts.values():
            run.reader.read(pin.role, pin.path, pin)
        reusable = self.guard.reusable()
        if not reusable:
            self.semantic.clear()
            self.observation_state = None
        return _PrefixTransaction(self, run, reusable, epoch=epoch)


class _PrefixTransaction:
    """Uncommitted suffix; exceptions cannot publish partial semantic state."""
    def __init__(self, owner, run, reusable, *, epoch=None):
        self.owner, self.run, self.reusable = owner, run, reusable
        self.epoch = owner.epoch if epoch is None else epoch
        self.pending = {}
        self.observation_state = owner.observation_state if reusable else None

    def check_reuse(self):
        self.owner.check_active()
        if not self.reusable:
            return False
        if not self.owner.guard.reusable():
            self.owner.semantic.clear()
            self.owner.observation_state = None
            self.pending.clear()
            raise ValueError('validator changed during callback semantic reuse')
        return True

    def observation_checkpoint(self):
        return self.observation_state if self.check_reuse() else None

    def get(self, key):
        if not self.check_reuse():
            return None
        return self.pending.get(key, self.owner.semantic.get(key))

    def put(self, key, value):
        self.owner.check_active()
        if self.reusable:
            self.pending[key] = value

    def commit(self):
        run, owner = self.run, self.owner
        owner.check_active()
        if owner.epoch != self.epoch:
            raise ValueError('overlapping callback cannot replace a newer verified prefix')
        if self.reusable and not owner.guard.reusable():
            owner.semantic.clear()
            owner.observation_state = None
            raise ValueError('validator changed during callback verification')
        owner.records = tuple(item.pin for item in run.history.records)
        owner.observations = tuple(item.pin for item in run.observations)
        owner.streams = tuple((role, len(getattr(run, role).raw), c.sha(getattr(run, role).raw))
                              for role in ('transcript', 'control'))
        for member in run.reader.members.values():
            pin = member.captured.pin
            if pin.role != 'journal':
                owner.artifacts[(pin.role, pin.path)] = pin
        if self.reusable:
            owner.semantic.update(self.pending)
            owner.observation_state = self.observation_state
        owner.epoch += 1


def prefix_owner(admission):
    require_admission(admission)
    return _PREFIX_OWNERS.get(admission)


def _check_admitted_sources(admission):
    try:
        admission.check_sources()
    except (ValueError, OSError):
        owner = _PREFIX_OWNERS.get(admission)
        if owner is not None:
            owner.guard.disabled = True
            owner.semantic.clear()
            owner.observation_state = None
        raise


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False)
class Admission:
    registration_raw: bytes
    execution_json: bytes
    composition_json: bytes
    preparation_raw: bytes
    rebuild_arguments_json: bytes
    selection: object
    spec: FrozenSpec
    rebuild: object
    controls: object
    check_sources: object

    def check_active(self):
        require_admission(self)

    def reconstruct(self):
        require_admission(self)
        _check_admitted_sources(self)
        arguments = c.strict_json(self.rebuild_arguments_json)
        value = self.rebuild(preparation_raw=self.preparation_raw,
            classifier_projection=self.controls, **arguments)
        if c.canonical(value) != self.execution_json:
            raise ValueError('callback execution changed after admission')
        _check_admitted_sources(self)
        require_admission(self)
        return value

    def base(self, selection_path):
        """Rebuild E every time through the captured fixed consumer, then read S.

        Main-thread admission already validated A's preparation envelope.
        Its complete source/input pins are checked again around reconstruction.
        D's consumer still independently reconstructs the entire E body; no
        submitted derived body or cached verdict is passed to that consumer.
        """
        require_admission(self)
        if selection_path != self.selection.registration.pin.path:
            raise ValueError('callback selection differs from its admitted capture')
        value = self.reconstruct()
        current = selection.capture(selection_path)
        if current != self.selection:
            raise ValueError('callback selection changed after admission')
        reader = captured._Reader(current)
        composition = c.strict_json(self.composition_json, max_bytes=c.HARD_LIMITS['request_bytes'])
        for filename, role in (('registration.json', 'execution_capture'), ('started.json', 'started_capture')):
            actual = evidence.read_regular(str(Path(value['attempt_directory']) / filename), role,
                max_bytes=c.HARD_LIMITS['request_bytes']).captured
            saved = reader.read(role, current.role(role))
            if actual.raw != saved.raw:
                raise ValueError('stage binding differs from actual one-use attempt records')
        execution = reader.read('execution_capture', current.role('execution_capture'))
        if execution.raw != self.registration_raw:
            raise ValueError('callback execution capture differs from admission')
        started = c.strict_json(reader.read('started_capture', current.role('started_capture')).raw)
        if (started.get('state') != 'started' or started.get('attempt_id') != value['attempt_id']
                or started.get('registration_sha256') != execution.pin.sha256
                or started.get('composition_sha256') != value['composition_sha256']
                or type(started.get('dispatch_limit')) is not int or started['dispatch_limit'] != 1):
            raise ValueError('selected stage does not have its actual one-use started identity')
        _check_admitted_sources(self)
        return current, reader, value, composition, self.spec
