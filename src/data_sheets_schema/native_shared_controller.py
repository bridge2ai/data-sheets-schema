"""Input-only composition and captured-wire checks for native shared generation.

Current file/source verification and callbacks live in controller_orchestration.
This consumer receives explicit verified captures and a live C-minted classifier
projection. Saved wire parsing alone grants no callback or execution authority.
"""
from __future__ import annotations

from . import native_shared_contract as c
from . import native_shared_authority_wire as wire
from . import native_shared_policy as policy
from . import native_shared_controls as pure_controls

KIND = 'd4d_native_shared_callback_composition'
VERSION = 1
AUTHORITY_VERSION = 2
EXECUTION = 'offline_composition_only_requires_separate_native_execution_registration'
_COMPOSITION_KEYS = frozenset(('kind', 'version', 'authority_version', 'execution',
    'preparation_raw_json', 'preparation_sha256', 'dependencies', 'selection_raw_json',
    'selection_sha256', 'runtime_path', 'runtime_raw_json', 'runtime_sha256',
    'max_draft_checks', 'render_spec', 'instruction_path', 'instruction_sha256',
    'controller_sources', 'controller_sources_sha256', 'policy', 'policy_sha256',
    'working_directory', 'python', 'python_version'))


def _file_pin(artifact):
    return {'path': artifact.pin.path, 'bytes': artifact.pin.bytes, 'sha256': artifact.pin.sha256}


def _captured_wire(raw):
    value = c.strict_json(raw, 'captured v2 authority envelope', c.HARD_LIMITS['request_bytes'])
    c.exact(value, {'authority_version', 'controller_sources_sha256', 'registration'},
            'captured v2 authority envelope')
    body = value['registration']
    if (type(value['authority_version']) is not int or value['authority_version'] != AUTHORITY_VERSION
            or value['controller_sources_sha256'] != wire.CONTROLLER_SOURCES_SHA256
            or type(body) is not dict or type(body.get('schema_version')) is not int
            or body['schema_version'] != AUTHORITY_VERSION):
        raise ValueError('captured record is not the exact v2 authority wire')
    return body


def captured_execution_body(raw):
    """Closed captured E only; never source verification or admission."""
    body = _captured_wire(raw)
    wire.closed_execution(body)
    return body


def captured_preparation_body(raw):
    """Pure preparation wire parser; current verification belongs to orchestration."""
    body = _captured_wire(raw)
    c.exact(body, wire.PREPARATION_KEYS, 'captured shared v2 preparation')
    if body['kind'] != wire.PREPARATION_KIND or body['execution'] != wire.PREPARATION_SCOPE:
        raise ValueError('captured record is not the shared v2 preparation wire')
    return body


def captured_composition(raw):
    value = c.strict_json(raw, 'native shared composition', c.HARD_LIMITS['request_bytes'])
    c.exact(value, _COMPOSITION_KEYS, 'native shared composition')
    if (value['kind'] != KIND or type(value['version']) is not int or value['version'] != VERSION
            or type(value['authority_version']) is not int or value['authority_version'] != AUTHORITY_VERSION
            or value['execution'] != EXECUTION):
        raise ValueError('not a v2-authority native shared callback composition')
    return value


def compose(preparation_raw, *, prepared, spec, current, runtime, instruction,
            controller_sources, command_argv, repository, output_directories,
            python, python_version, classifier_projection):
    """Derive C only from the orchestrator's explicit verified input captures.

    RunSpec boundary: validated-caller

    RunSpec precondition: orchestration rederived this spec from current U3-A
    preparation, checked the selected instruction and runtime, and computed the
    renderer's command argv before entering this input-only consumer.
    """
    controls = pure_controls.require_controls(classifier_projection)
    if captured_preparation_body(preparation_raw) != prepared:
        raise ValueError('composition preparation differs from the verified capture')
    if (_file_pin(current.registration) != prepared['selection']
            or _file_pin(runtime) != prepared['runtime']
            or instruction.raw != prepared['instruction'].encode('utf-8')
            or instruction.pin.sha256 != prepared['instruction_sha256']
            or spec._native_shared_generation_capture is not current
            or spec._native_shared_runtime_capture is not runtime):
        raise ValueError('composition inputs differ from the verified captures')
    selected_policy = policy.command_policy(spec, instruction.pin.path,
        command_argv=command_argv, repository=repository, output_directories=output_directories,
        classifier_projection=controls)
    value = {'kind': KIND, 'version': VERSION, 'authority_version': AUTHORITY_VERSION,
        'execution': EXECUTION, 'preparation_raw_json': preparation_raw.decode('utf-8'),
        'preparation_sha256': c.sha(preparation_raw), 'dependencies': prepared['dependencies'],
        'selection_raw_json': current.registration.raw.decode('utf-8'),
        'selection_sha256': current.registration.pin.sha256,
        'runtime_path': runtime.pin.path, 'runtime_raw_json': runtime.raw.decode('utf-8'),
        'runtime_sha256': runtime.pin.sha256, 'max_draft_checks': prepared['max_draft_checks'],
        'render_spec': prepared['render_spec'], 'instruction_path': instruction.pin.path,
        'instruction_sha256': instruction.pin.sha256,
        'controller_sources': controller_sources,
        'controller_sources_sha256': wire.CONTROLLER_SOURCES_SHA256,
        'policy': selected_policy, 'policy_sha256': c.sha(c.canonical(selected_policy)),
        'working_directory': repository, 'python': python, 'python_version': python_version}
    pure_controls.require_controls(controls)
    raw = c.canonical(value)
    if len(raw) > c.HARD_LIMITS['request_bytes']:
        raise ValueError('native shared composition exceeds its complete byte bound')
    return c.strict_json(raw, 'constructed native shared composition', c.HARD_LIMITS['request_bytes'])


def reconstruct_composition(raw, *, prepared, spec, current, runtime, instruction,
                            controller_sources, command_argv, repository, output_directories,
                            python, python_version, classifier_projection):
    """Compare the complete submitted C with explicit independently verified inputs.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies the unchanged validated spec and independently verified preparation, selection and runtime; compose compares the complete captured composition without live reconstruction.
    """
    pure_controls.require_controls(classifier_projection)
    value = captured_composition(raw)
    expected = compose(value['preparation_raw_json'].encode('utf-8'), prepared=prepared,
        spec=spec, current=current, runtime=runtime, instruction=instruction,
        controller_sources=controller_sources, command_argv=command_argv,
        repository=repository, output_directories=output_directories, python=python,
        python_version=python_version, classifier_projection=classifier_projection)
    if c.canonical(value) != c.canonical(expected):
        raise ValueError('native shared composition identity changed')
    return value, spec, current


def verified_composition(raw, *, prepared, spec, current, runtime, instruction,
                         controller_sources, command_argv, repository, output_directories,
                         python, python_version, classifier_projection):
    """    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies the unchanged validated spec and independently verified reconstruction inputs; reconstruct_composition compares the complete composition.
    """
    return reconstruct_composition(raw, prepared=prepared, spec=spec, current=current,
        runtime=runtime, instruction=instruction, controller_sources=controller_sources,
        command_argv=command_argv, repository=repository, output_directories=output_directories,
        python=python, python_version=python_version, classifier_projection=classifier_projection)[0]


def capture_phase(run, *, complete):
    from .native_shared_capture import phase_replay
    return phase_replay(run, complete=complete)
