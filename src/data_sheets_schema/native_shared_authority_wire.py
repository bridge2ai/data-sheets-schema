"""Pure v3 registration vocabulary over frozen controller authority v2.

These declarations parse closed saved shapes only. They neither verify current
sources nor grant execution. Historical v2 parsing is an explicit read-only API;
the current parser never falls back to it. The A/v1 modules remain unmodified.
"""
AUTHORITY_VERSION = 2
VERSION = 3
CONTROLLER_SOURCES_SHA256 = '8436623f0852a4f98c8061006e0fd160952f529b75607fc8171f2dc4658ae1fe'
PREPARATION_KIND = 'd4d_native_shared_preparation_v3'
EXECUTION_KIND = 'd4d_native_shared_execution_registration_v3'
HISTORICAL_PREPARATION_KIND = 'd4d_native_shared_preparation_v2'
HISTORICAL_EXECUTION_KIND = 'd4d_native_shared_execution_registration_v2'
PREPARATION_SCOPE = 'offline_inputs_only_not_permission_or_launch_authority'
EXECUTION_SCOPE = 'requires_exact_independent_review_ci_permission_and_owner_launch_evidence'
EXECUTION_GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution',
    'saved_attribution', 'phase_history', 'tool_history', 'schema', 'pair',
    'receipts', 'evidence', 'observation', 'accounting', 'runtime_authority', 'keep_awake')
PREPARATION_KEYS = frozenset(('kind', 'schema_version', 'execution', 'job_id',
    'working_directory', 'dependencies', 'selection', 'runtime', 'run_date',
    'max_draft_checks', 'render_spec', 'input_identity', 'instruction',
    'instruction_sha256', 'outputs', 'pinned_files', 'environment_manifest'))
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


def require_envelope(value):
    """Current registration v3 over unchanged frozen controller authority v2."""
    if (type(value) is not dict
            or set(value) != {'authority_version', 'controller_sources_sha256', 'registration'}
            or type(value['authority_version']) is not int
            or value['authority_version'] != AUTHORITY_VERSION
            or value['controller_sources_sha256'] != CONTROLLER_SOURCES_SHA256
            or type(value['registration']) is not dict
            or type(value['registration'].get('schema_version')) is not int
            or value['registration']['schema_version'] != VERSION
            or value['registration'].get('kind') not in {PREPARATION_KIND, EXECUTION_KIND}):
        raise ValueError('current registration requires v3 body under v2 controller authority')
    return value['registration']


def envelope(body):
    value = {'authority_version': AUTHORITY_VERSION,
             'controller_sources_sha256': CONTROLLER_SOURCES_SHA256, 'registration': body}
    require_envelope(value)
    return value


def historical_body(value):
    """Read the closed historical v2 shape only; never current admission."""
    if (type(value) is not dict
            or set(value) != {'authority_version', 'controller_sources_sha256', 'registration'}
            or type(value['authority_version']) is not int or value['authority_version'] != 2
            or value['controller_sources_sha256'] != CONTROLLER_SOURCES_SHA256
            or type(value['registration']) is not dict):
        raise ValueError('not historical v2 authority evidence')
    body = value['registration']
    if type(body.get('schema_version')) is not int or body['schema_version'] != 2:
        raise ValueError('not a historical v2 registration body')
    if body.get('kind') == HISTORICAL_PREPARATION_KIND:
        if set(body) != PREPARATION_KEYS - {'environment_manifest'} or body['execution'] != PREPARATION_SCOPE:
            raise ValueError('historical preparation shape mismatch')
    elif body.get('kind') == HISTORICAL_EXECUTION_KIND:
        if (set(body) not in (EXECUTION_KEYS, EXECUTION_KEYS | {'receipt_origin_reporting'})
                or body['execution'] != EXECUTION_SCOPE
                or body['execution_gates'] != list(EXECUTION_GATES)):
            raise ValueError('historical execution shape mismatch')
    else:
        raise ValueError('unknown historical registration kind')
    return body
