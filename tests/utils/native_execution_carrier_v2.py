"""Closed-shape synthetic carriers for pure U3-C replay tests, never admission.

Each caller supplies the genuine captures needed for its specific computation.
The remaining values are explicitly synthetic and cannot satisfy reconstruction,
permission, source, review, CI or runtime admission. Keep this roster literal so
an interface change requires an intentional fixture migration.
"""
from data_sheets_schema import native_execution_registration_v2 as registration


def execution_body(**captures):
    body = {
        'kind': registration.EXECUTION_KIND, 'schema_version': 2,
        'execution': registration.EXECUTION_SCOPE,
        'execution_gates': list(registration.EXECUTION_GATES),
        'attempt_id': 'synthetic-captured-attempt',
        'composition': '/synthetic/composition.json',
        'system_path': '/synthetic/system.md',
        'permission_probe': '/synthetic/permission.json',
        'attempt_directory': '/synthetic/attempt',
        'evidence_directory': '/synthetic/evidence',
        'job_id': 'synthetic-captured-job',
        'preparation_raw_json': '{}', 'preparation_sha256': '0' * 64,
        'runtime': {}, 'max_draft_checks': 1,
        'selection_sha256': '0' * 64, 'runtime_declaration_sha256': '0' * 64,
        'working_directory': '/synthetic', 'dependencies': {},
        'composition_raw_json': '{}', 'composition_sha256': '0' * 64,
        'system_sha256': '0' * 64, 'effective_system': '',
        'effective_system_sha256': '0' * 64, 'instruction_sha256': '0' * 64,
        'permission_probe_sha256': '0' * 64,
        'permission_expected_sha256': '0' * 64, 'permission_observations': {},
        'argv': [], 'environment': {}, 'selection': {}, 'scope': {},
    }
    assert set(body) == registration.EXECUTION_KEYS
    assert set(captures) <= set(body)
    body.update(captures)
    return body
