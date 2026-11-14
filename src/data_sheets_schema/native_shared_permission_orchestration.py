"""Source loading for D's saved-permission consumer, with C's real interfaces.

Only orchestration obtains A's loader and C's live projection. Ordinary entry
points enter the same verified consumer module set as A's execution verifier.
"""
from contextlib import contextmanager
from pathlib import Path

from . import native_execution_authority_v2 as authority
from . import native_shared_controls_orchestration as control_loading
from . import native_shared_permission_protocol_orchestration as protocol_loading
from . import native_shared_registration as registration


# Compatibility name for callers; implementation and per-call mutation checks
# belong to C's six-function interface, not a second D loader.
loaded_protocol = protocol_loading.loaded_protocol
_validate_protocol_source = protocol_loading._validate_source
_validate_protocol_interface = protocol_loading._validate_interface


@contextmanager
def loaded_permission_inputs(dependencies=None):
    """Yield the genuine classifier and freshly checked source manifest."""
    dependencies = authority.dependency_identity() if dependencies is None else dependencies
    sources = registration.controller_sources()
    with control_loading.loaded_controls(dependencies) as controls:
        yield controls, sources


def verify_saved_probe(raw_manifest: bytes, *, expected: dict) -> dict:
    from .native_u4b_runtime import is_prepared_runtime
    from .native_u4b_probe_sequence import _refuse_bound_failure
    from .native_subscription_guard import strict_json
    if is_prepared_runtime(expected.get('runtime')):
        basis = strict_json(expected['runtime']['limits_basis'])
        _refuse_bound_failure(Path(basis['observation_probe']['path']).parent.parent)
    dependencies = authority.dependency_identity()
    with loaded_permission_inputs(dependencies) as (controls, sources), \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_permissions',
                package_sources=dependencies['base']['package_sources']) as consumer:
        return consumer.verify_saved_probe(raw_manifest, expected=expected,
            controls=controls, controller_sources=sources)


def probe_argv(expected, probe_policy):
    dependencies = authority.dependency_identity()
    with authority.loaded_verified_package_module('data_sheets_schema.native_shared_permissions',
            package_sources=dependencies['base']['package_sources']) as consumer:
        return consumer.probe_argv(expected, probe_policy)
