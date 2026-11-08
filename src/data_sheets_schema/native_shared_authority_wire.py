"""Pure v2 captured-wire vocabulary, parity with U3-A round four.

These declarations parse closed saved shapes only. They neither verify current
sources nor grant execution. The original A/v1 modules remain unmodified.
"""
VERSION = 2
CONTROLLER_SOURCES_SHA256 = '58d9be00007719d2bc1247c7524256a60522d3d7bfedf39409341973c88c0a6c'
PREPARATION_KIND = 'd4d_native_shared_preparation_v2'
EXECUTION_KIND = 'd4d_native_shared_execution_registration_v2'
PREPARATION_SCOPE = 'offline_inputs_only_not_permission_or_launch_authority'
EXECUTION_SCOPE = 'requires_exact_independent_review_ci_permission_and_owner_launch_evidence'
EXECUTION_GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution',
    'saved_attribution', 'phase_history', 'tool_history', 'schema', 'pair',
    'receipts', 'evidence', 'observation', 'accounting', 'runtime_authority', 'keep_awake')
PREPARATION_KEYS = frozenset(('kind', 'schema_version', 'execution', 'job_id',
    'working_directory', 'dependencies', 'selection', 'runtime', 'run_date',
    'max_draft_checks', 'render_spec', 'input_identity', 'instruction',
    'instruction_sha256', 'outputs', 'pinned_files'))
EXECUTION_KEYS = frozenset(('kind', 'schema_version', 'execution', 'attempt_id',
    'composition', 'system_path', 'permission_probe', 'attempt_directory',
    'evidence_directory', 'job_id', 'preparation_raw_json', 'preparation_sha256',
    'execution_gates', 'runtime', 'max_draft_checks', 'selection_sha256',
    'runtime_declaration_sha256', 'working_directory', 'dependencies',
    'composition_raw_json', 'composition_sha256', 'system_sha256',
    'effective_system', 'effective_system_sha256', 'instruction_sha256',
    'permission_probe_sha256', 'permission_expected_sha256',
    'permission_observations', 'argv', 'environment', 'selection', 'scope'))


def closed_execution(body):
    """Exact A shape/kind/gate checks; optional origin content is checked later."""
    if type(body) is not dict or set(body) not in (
            EXECUTION_KEYS, EXECUTION_KEYS | {'receipt_origin_reporting'}):
        raise ValueError('v2 execution body keys mismatch')
    if (body['kind'] != EXECUTION_KIND or type(body['schema_version']) is not int
            or body['schema_version'] != VERSION or body['execution'] != EXECUTION_SCOPE):
        raise ValueError('not the closed v2 shared execution route')
    if body['execution_gates'] != list(EXECUTION_GATES):
        raise ValueError('v2 execution gate obligations mismatch')
