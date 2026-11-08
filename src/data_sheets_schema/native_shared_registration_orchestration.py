"""D proposal and verification orchestration, outside A's consumer graph.

Only this layer obtains fresh verifier identities and a live C projection.
No authority is placed in serialized preparation or hidden process state.
"""
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
    """Produce a closed v2 proposal; never reserve an attempt or grant admission."""
    body = _require_runtime_observation(_registration_body(composition_path, system_path, **kwargs))
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
    """Explicit v2 outer-envelope verifier; no historical fallback."""
    dependencies = authority.dependency_identity()
    with control_loading.loaded_controls(dependencies) as controls:
        value = execution_v2.verified(raw, classifier_projection=controls)
    return _require_runtime_observation(value)


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
