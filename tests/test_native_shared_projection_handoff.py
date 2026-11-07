"""Executable C4 requirement: a genuine projection survives A's source boundary.

No stand-in, alternate class test, source cache exemption or xfail hides the
current loader-lifetime gap. A loader ruling is required if this gate fails.
"""
from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_controls as controls
from data_sheets_schema import native_shared_controls_orchestration as orchestration
from tests.test_native_execution_authority_v2 import isolated_modules


def test_genuine_projection_handoff_to_fresh_source_consumer(isolated_modules):
    identity = authority.dependency_identity()
    pins = identity['base']['package_sources']
    relative = 'src/data_sheets_schema/native_shared_controls.py'
    path = authority.ROOT / relative
    digest = pins[relative]
    raw = authority._verified_source_bytes(path, digest)
    with orchestration.loaded_controls(identity) as projected:
        assert controls.require_controls(projected) is projected
        with authority.verified_source_module(
                'data_sheets_schema.native_shared_controls', path=path,
                raw=raw, sha256=digest, package_sources=pins) as consumer:
            assert consumer.require_controls(projected) is projected
