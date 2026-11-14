"""Retained A/C integration requirement exposed by actual D verification.

This is a real preparation and genuine C scope, not a reconstructed authority
stand-in. Keep the positive requirement unmarked while its A-owned fix awaits
review; it is independent of the later protected U1 admission hook.
"""
from tests.test_native_shared_controller import bound, declaration, synthetic_declaration, native_spec
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from data_sheets_schema import native_execution_registration_v2 as admission
from data_sheets_schema import native_shared_controls_orchestration as controls


def test_real_preparation_reconstructs_inside_the_required_classifier_scope(bound):
    source, preparation, raw, instruction = bound
    with controls.loaded_controls(preparation['registration']['dependencies']):
        assert admission.verify_preparer(raw, job_id=source['kwargs']['job_id']) == preparation['registration']
