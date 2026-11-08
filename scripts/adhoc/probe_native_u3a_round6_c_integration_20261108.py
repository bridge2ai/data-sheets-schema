"""R9-3 genuine final-C loader test; copied into an offline snapshot, 2026-11-08.

Inputs: final C sources plus the exact A6 registration source. Outputs: pytest
assertions/properties. Never runs a native executable; fixture permits only Git.
"""
import sys

from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_contract as contract
from data_sheets_schema import native_shared_controls_orchestration as loading
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_selection import declaration


def test_real_c_verified_loader_preparer_capture_identity(inputs, record_property):
    authority = registration.authority
    dependencies = authority.dependency_identity()
    authority.require_committed(dependencies)
    with loading.loaded_controls(dependencies) as projection:
        with authority.loaded_verified_package_module(
                'data_sheets_schema.native_shared_evidence',
                package_sources=dependencies['base']['package_sources']) as evidence:
            current = sys.modules['data_sheets_schema.native_shared_contract']
            assert current.CapturedArtifact is not contract.CapturedArtifact
            stale = registration.read_regular(str(inputs['runtime_path']), 'runtime_declaration',
                max_bytes=contract.HARD_LIMITS['input_bytes']).captured
            assert type(stale) is not current.CapturedArtifact
            fresh = evidence.read_regular(str(inputs['runtime_path']), 'runtime_declaration',
                max_bytes=contract.HARD_LIMITS['input_bytes']).captured
            assert type(fresh) is current.CapturedArtifact
            envelope = registration.prepare(inputs['selection'], inputs['runtime_path'], **inputs['kwargs'])
            body = registration.verify_preparer(contract.canonical(envelope), job_id=inputs['kwargs']['job_id'])
            assert body == envelope['registration']
            assert '# Model: synthetic-native-model' in body['instruction']
            sys.modules['data_sheets_schema.native_shared_controls'].require_controls(projection)
            record_property('real_c_loader', loading.__file__)
            record_property('stale_capture_class_refused', True)
            record_property('verified_capture_exact_class', True)
            record_property('verify_preparer_prepare_instruction', True)
