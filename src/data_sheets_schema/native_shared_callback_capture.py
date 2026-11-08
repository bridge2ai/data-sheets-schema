"""Captured callback inputs; fresh reconstruction without a source loader.

Admission supplies the fixed, already source-verified reconstruction entry.
Neither an earlier replay verdict nor a mutable RunSpec is worker authority.
"""
from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True, slots=True)
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

    def reconstruct(self):
        self.check_sources()
        arguments = c.strict_json(self.rebuild_arguments_json)
        value = self.rebuild(preparation_raw=self.preparation_raw,
            classifier_projection=self.controls, **arguments)
        if c.canonical(value) != self.execution_json:
            raise ValueError('callback execution changed after admission')
        self.check_sources()
        return value

    def base(self, selection_path):
        """Rebuild E every time through the captured fixed consumer, then read S.

        Main-thread admission already validated A's preparation envelope.
        Its complete source/input pins are checked again around reconstruction.
        D's consumer still independently reconstructs the entire E body; no
        submitted derived body or cached verdict is passed to that consumer.
        """
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
        self.check_sources()
        return current, reader, value, composition, self.spec
