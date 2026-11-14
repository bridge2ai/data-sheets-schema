"""D proposal and verification orchestration, outside A's consumer graph.

Only this layer obtains fresh verifier identities and a live C projection.
No authority is placed in serialized preparation or hidden process state.
"""

from . import native_pre_dispatch_timing as pre_timing
from . import native_execution_authority_v2 as authority
from . import native_execution_registration_v2 as execution_v2
from . import native_shared_contract as c
from . import native_shared_controller_orchestration as composition
from . import native_shared_controller as captured_composition
from . import native_shared_controls_orchestration as control_loading
from . import native_shared_registration as consumer
from . import native_shared_permission_orchestration as permission_inputs
from .native_shared_registration import (
    AUTHORITY_VERSION, KIND, VERSION, EXECUTION, environment, command,
    permission_expectation, execution_paths_v2, _paths,
)


def _require_integrated_gate_implementation():
    """Keep the engine-contract check outside the input-only consumer graph."""
    try:
        from .native_shared_execution_orchestration import _engine_bindings
        contract, _ = _engine_bindings()
        contract.require_fixed()
        consumer._require_integrated_gate_implementation()
    except (ImportError, AttributeError) as exc:
        raise ValueError('native shared execution gate implementation is incomplete') from exc


def _registration_body(composition_path, system_path, **kwargs):
    consumer.validate_arguments(composition_path, system_path, **kwargs)
    _require_integrated_gate_implementation()
    raw = consumer._read(composition_path, 'composition', c.HARD_LIMITS['request_bytes'])
    selected, _, _ = composition.reconstruct_composition(raw)
    preparation_raw = selected['preparation_raw_json'].encode('utf-8')
    job_id = captured_composition.captured_preparation_body(preparation_raw)['job_id']
    prepared = execution_v2.verify_preparer(preparation_raw, job_id=job_id)
    dependencies = authority.dependency_identity()
    if prepared['dependencies'] != dependencies or selected['dependencies'] != dependencies:
        raise ValueError('execution preparation differs from current v2 authority')
    with permission_inputs.loaded_permission_inputs(dependencies) as (controls, controller_sources), \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_registration',
                package_sources=dependencies['base']['package_sources']) as verified_consumer:
        value = verified_consumer._registration_body(composition_path, system_path,
            preparation_raw=preparation_raw, controls=controls,
            controller_sources=controller_sources, **kwargs)
    if (authority.dependency_identity() != dependencies
            or execution_v2.verify_preparer(preparation_raw, job_id=job_id) != prepared):
        raise ValueError('execution authority changed during capture')
    return value


def registration(composition_path, system_path, **kwargs):
    """Produce a closed v2 proposal; never reserve an attempt or grant admission.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit composition/system paths; _registration_body verifies preparation and composition before creating an execution proposal.
    """
    from .native_runtime_profiles import require_production
    body = _registration_body(composition_path, system_path, **kwargs)
    require_production(body['runtime'])
    return _observed_envelope(body)


def synthetic_registration(composition_path, system_path, **kwargs):
    """Prepare an explicitly synthetic proposal; never real launch authority.

    The same captured preparation, permission and observation consumers run.
    The separate entry additionally requires the fixed ordinary-Python peer.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies explicit composition and system paths; _registration_body reconstructs guarded preparation and composition before creating the proposal, and require_synthetic restricts it to the fixed software-test peer.
    """
    from .native_runtime_profiles import require_synthetic
    body = _registration_body(composition_path, system_path, **kwargs)
    require_synthetic(body['runtime'])
    return _observed_envelope(body)


def _observed_envelope(body):
    body = _require_runtime_observation(body)
    with authority.loaded_dependencies(body['dependencies']) as controls:
        value = controls['prepare_registration_v2'].envelope(body)
        controls['prepare_registration_v2'].require_envelope(value)
    if len(c.canonical(value)) > c.HARD_LIMITS['request_bytes']:
        raise ValueError('v2 shared execution exceeds its wire bound')
    return value

def verified_v2_body(body_raw, *, preparation_raw):
    """Compare a proposal with fresh reconstruction; not A's consumer entry.

    A calls the separate input-only rebuild_v2_body and owns the outer body
    comparison. This retained helper does not bypass A's source/import guard.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies bounded body/preparation bytes; _registration_body reconstructs guarded preparation and compares the complete body.
    """
    value = c.strict_json(body_raw, 'native shared v2 execution body', c.HARD_LIMITS['request_bytes'])
    if (type(value) is not dict or value.get('kind') != KIND
            or type(value.get('schema_version')) is not int or value['schema_version'] != VERSION
            or value.get('execution') != EXECUTION
            or value.get('execution_gates') != list(consumer.GATES)):
        raise ValueError('not the selected native shared v2 execution registration')
    if (type(preparation_raw) is not bytes
            or value.get('preparation_raw_json') != preparation_raw.decode('utf-8')
            or value.get('preparation_sha256') != c.sha(preparation_raw)):
        raise ValueError('v2 consumer preparation binding differs')
    origin_version = 0
    if 'receipt_origin_reporting' in value:
        from .native_receipt_origin import version
        origin_version = version(value)
    try:
        expected = _registration_body(
            composition_path=value['composition'], system_path=value['system_path'],
            permission_probe_path=value['permission_probe'],
            attempt_id=value['attempt_id'], attempt_directory=value['attempt_directory'],
            evidence_directory=value['evidence_directory'], max_draft_checks=value['max_draft_checks'],
            receipt_origin_version=origin_version)
    except (KeyError, TypeError) as exc:
        raise ValueError('incomplete native shared execution registration') from exc
    if c.canonical(value) != c.canonical(expected):
        raise ValueError('execution registration differs from its selected authorities')
    return _require_runtime_observation(value)

def verified(raw):
    """Explicit v2 outer-envelope verifier; no historical fallback.

    RunSpec boundary: validated-caller

    RunSpec precondition: Caller supplies outer execution bytes; execution_v2.verified freshly rederives guarded preparation under verified controls.
    """
    with pre_timing.step('registration.verified'):
        dependencies = authority.dependency_identity()
        with control_loading.loaded_controls(dependencies) as controls:
            value = execution_v2.verified(raw, classifier_projection=controls)
        result = _require_runtime_observation(value)
        pre_timing.bind(result)
        return result


def _recheck_verified(raw, value):
    """Recheck live source, preparation/composition pins and runtime for a verified body."""
    from pathlib import Path
    import sys
    from .native_shared_runtime_values import validate_runtime_v2 as validate_runtime
    _require_integrated_gate_implementation()
    envelope = c.strict_json(raw, 'v2 authority envelope', execution_v2.MAX_WIRE_BYTES)
    if (type(envelope) is not dict
            or set(envelope) != {'authority_version', 'controller_sources_sha256', 'registration'}
            or type(envelope['authority_version']) is not int or envelope['authority_version'] != VERSION
            or type(envelope['controller_sources_sha256']) is not str
            or envelope['controller_sources_sha256'] != authority.neutral.composition.SOURCES_SHA256
            or type(envelope['registration']) is not dict
            or type(envelope['registration'].get('schema_version')) is not int
            or envelope['registration']['schema_version'] != VERSION
            or c.canonical(envelope) != raw):
        raise ValueError('v2 launch requires an exact v2 authority envelope')
    body = envelope['registration']
    execution_v2._closed_execution(body)
    if type(value) is not dict or c.canonical(value) != c.canonical(body):
        raise ValueError('v2 execution body differs from initial verification')
    dependencies = authority.dependency_identity()
    if body['dependencies'] != dependencies:
        raise ValueError('v2 dependency identity mismatch')
    authority.require_committed(dependencies)
    controller_manifest = consumer.controller_sources()
    cwd = str(Path.cwd().resolve())
    if Path(cwd) != authority.ROOT or body['working_directory'] != cwd:
        raise ValueError('v2 execution working_directory mismatch')
    try:
        origin_version = 0
        if 'receipt_origin_reporting' in body:
            declaration = body['receipt_origin_reporting']
            if type(declaration) is not dict or type(declaration.get('version')) is not int or declaration['version'] != 1:
                raise ValueError('v2 receipt origin declaration version mismatch')
            origin_version = 1
        paths = consumer.validate_arguments(body['composition'], body['system_path'],
            permission_probe_path=body['permission_probe'], attempt_id=body['attempt_id'],
            attempt_directory=body['attempt_directory'], evidence_directory=body['evidence_directory'],
            max_draft_checks=body['max_draft_checks'], receipt_origin_version=origin_version)
        if any(body[key] != expected_path for key, expected_path in paths.items()):
            raise ValueError('v2 execution path binding mismatch')
        preparation_raw = body['preparation_raw_json'].encode('utf-8')
        if body['preparation_sha256'] != c.sha(preparation_raw):
            raise ValueError('v2 preparation digest mismatch')
        preparation = captured_composition.captured_preparation_body(preparation_raw)
        execution_v2._job_id(preparation['job_id'])
        if (preparation['job_id'] != body['job_id']
                or preparation['dependencies'] != dependencies
                or preparation['working_directory'] != cwd):
            raise ValueError('v2 preparation binding mismatch')
        captured_selection = execution_v2.selection.capture(preparation['selection']['path'])
        selection_capture = captured_selection.registration
        runtime_capture = execution_v2._read(preparation['runtime']['path'], 'runtime_declaration',
                                             c.HARD_LIMITS['input_bytes'])
        if (execution_v2._file_pin(selection_capture) != preparation['selection']
                or execution_v2._file_pin(runtime_capture) != preparation['runtime']):
            raise ValueError('v2 prepared selection or runtime changed before execution binding')
        runtime = validate_runtime(c.strict_json(runtime_capture.raw, 'runtime declaration'))
        executable_path = runtime['executable']['path']
        if (type(preparation['pinned_files']) is not dict
                or preparation['pinned_files'].get(executable_path) != runtime['executable']['sha256']):
            raise ValueError('v2 prepared executable pin mismatch')
        for pinned_path, expected_sha256 in preparation['pinned_files'].items():
            if pinned_path == executable_path:
                continue
            captured_pin = execution_v2._read(pinned_path, 'pinned preparation input',
                                              c.HARD_LIMITS['input_bytes'])
            if captured_pin.pin.sha256 != expected_sha256:
                raise ValueError('v2 pinned preparation input changed: ' + str(pinned_path))
        expected_body = {'runtime': runtime,
            'runtime_declaration_sha256': preparation['runtime']['sha256'],
            'selection_sha256': preparation['selection']['sha256'],
            'max_draft_checks': preparation['max_draft_checks'],
            'instruction_sha256': preparation['instruction_sha256'],
            'working_directory': preparation['working_directory']}
        for key, wanted in expected_body.items():
            if c.canonical(body[key]) != c.canonical(wanted):
                raise ValueError('v2 execution ' + key + ' mismatch')
        composition_file = execution_v2._read(body['composition'], 'composition',
                                              c.HARD_LIMITS['request_bytes'])
        composition_raw = body['composition_raw_json'].encode('utf-8')
        if (composition_file.raw != composition_raw
                or composition_file.pin.sha256 != body['composition_sha256']
                or c.sha(composition_raw) != body['composition_sha256']):
            raise ValueError('v2 composition digest mismatch')
        selected = captured_composition.captured_composition(composition_raw)
        if (selected['preparation_raw_json'].encode('utf-8') != preparation_raw
                or selected['preparation_sha256'] != body['preparation_sha256']
                or selected['dependencies'] != dependencies
                or selected['selection_raw_json'].encode('utf-8') != selection_capture.raw
                or selected['runtime_path'] != runtime_capture.pin.path
                or selected['runtime_raw_json'].encode('utf-8') != runtime_capture.raw
                or selected['max_draft_checks'] != body['max_draft_checks']
                or selected['working_directory'] != cwd
                or selected['python'] != sys.executable
                or selected['python_version'] != sys.version
                or c.canonical(selected['controller_sources']) != c.canonical(controller_manifest)):
            raise ValueError('v2 composition binding mismatch')
        expected_composition = {'render_spec': preparation['render_spec'],
            'instruction_sha256': preparation['instruction_sha256'],
            'selection_sha256': preparation['selection']['sha256'],
            'runtime_sha256': preparation['runtime']['sha256']}
        for key, wanted in expected_composition.items():
            if c.canonical(selected[key]) != c.canonical(wanted):
                raise ValueError('v2 composition ' + key + ' mismatch')
        instruction_file = execution_v2._read(selected['instruction_path'], 'instruction',
                                              c.HARD_LIMITS['request_bytes'])
        if (instruction_file.raw != preparation['instruction'].encode('utf-8')
                or instruction_file.pin.sha256 != preparation['instruction_sha256']
                or instruction_file.pin.sha256 != body['instruction_sha256']):
            raise ValueError('v2 instruction digest mismatch')
        system_file = execution_v2._read(body['system_path'], 'system',
                                         c.HARD_LIMITS['input_bytes'])
        if (not system_file.raw.decode('utf-8').strip()
                or system_file.pin.sha256 != body['system_sha256']):
            raise ValueError('v2 system digest mismatch')
        probe_file = execution_v2._read(body['permission_probe'], 'saved permission',
                                        c.HARD_LIMITS['permission_wire_bytes'])
        if probe_file.pin.sha256 != body['permission_probe_sha256']:
            raise ValueError('v2 permission probe digest mismatch')
    except (KeyError, TypeError, AttributeError, UnicodeDecodeError) as exc:
        raise ValueError('incomplete v2 shared execution binding') from exc
    execution_paths_v2(body, fresh=False, extra_protected=())
    if authority.dependency_identity() != dependencies:
        raise ValueError('v2 execution authority changed during verification')
    return _require_runtime_observation(
        c.strict_json(c.canonical(body), 'verified v2 execution', execution_v2.MAX_WIRE_BYTES))


def _require_runtime_observation(value):
    """Require U4b's observed registration fields at the host-reading boundary.

    The fixed input-only reconstruction graph remains unchanged. Historical
    other-model runtime profiles retain their own validators. The current
    model identity independently requires U4b evidence, so removing its basis
    discriminator cannot downgrade a proposal or readback to historical rules.
    """
    from .native_u4b_runtime import MODEL, is_prepared_runtime, validate_prepared_runtime
    runtime = value['runtime']
    if ((type(runtime) is dict and runtime.get('model') == MODEL)
            or is_prepared_runtime(runtime)):
        validate_prepared_runtime(runtime)
        from .native_u4b_probe_sequence import validate_bound_probe
        if type(value.get('permission_probe')) is not str:
            raise ValueError('A3 registration requires its bound permission probe')
        c._hash(value.get('permission_probe_sha256'), 'registered permission probe sha256')
        bound = validate_bound_probe(runtime, value['permission_probe'])
        pin = bound.get('permission') if type(bound) is dict else None
        if (type(bound) is not dict or bound.get('checked') is not True or bound.get('passed') is not True
                or type(pin) is not dict or set(pin) != {'path', 'sha256', 'bytes'}
                or type(pin.get('bytes')) is not int
                or not 0 < pin['bytes'] <= c.HARD_LIMITS['permission_wire_bytes']
                or pin.get('path') != value['permission_probe']
                or pin.get('sha256') != value['permission_probe_sha256']):
            raise ValueError('bound permission result differs from the registered path and bytes')
    return value
