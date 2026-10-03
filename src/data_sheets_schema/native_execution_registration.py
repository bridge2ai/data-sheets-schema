"""Explicit offline registration for a separately authorized native attempt.

No executable discovery, version/auth probe, provider call or child launch is
performed here. Every runtime choice comes from the caller. Existing offline
registrations and historical launcher kind guards remain unchanged.
"""
from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
import re
import stat
import sys

from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema import native_execution_authority as authority
from data_sheets_schema.native_attempt_supervisor import _file

KIND = 'd4d_native_attribution_execution_registration'
VERSION = 1
ROUTE = 'claude_code_direct_stream_json_v1'
EXECUTION = 'requires_exact_independent_review_ci_permission_and_owner_launch_evidence'
RUNTIME_KEYS = {'route', 'executable', 'model', 'auxiliary_models', 'effort', 'limits',
    'limits_basis', 'provider', 'auth', 'environment', 'deadline_seconds', 'budget_guard_usd', 'keep_awake'}
BASE_ENV_KEYS = {'PATH', 'HOME', 'USER', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM',
                'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_CODE_DISABLE_1M_CONTEXT'}
ENV_REQUIRED = {'PATH', 'HOME', 'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_CODE_DISABLE_1M_CONTEXT'}
POLICY_ENV = {'DISABLE_NON_ESSENTIAL_MODEL_CALLS': '1',
              'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
              'DISABLE_TELEMETRY': '1', 'CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS': '1',
              'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'}
FLAGS = ['--print', '--safe-mode', '--restricted', '--strict-mcp-config',
         '--disable-slash-commands', '--no-session-persistence', '--prompt-suggestions', 'false',
         '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose',
         '--permission-mode', 'dontAsk', '--tools', 'Read,Write,Bash']


def _text(value, name, limit=4096):
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(c in value for c in ('\x00', '\r', '\n'))):
        raise ValueError(f'{name} must be explicit bounded nonblank single-line text')
    return value


def _closed(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f'{name} must contain exactly: {", ".join(sorted(keys))}')


def _sha_text(value, name):
    if not isinstance(value, str) or re.fullmatch(r'[a-f0-9]{64}', value) is None:
        raise ValueError(f'{name} must be an exact lowercase SHA256')


def executable_identity(path):
    """Bounded streaming fingerprint, without invoking the supplied executable."""
    import hashlib
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError('runtime executable must be an absolute resolved path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111
                or before.st_size > 1024 * 1024 * 1024):
            raise ValueError('runtime executable must be a bounded executable regular file')
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, k) != getattr(after, k) for k in fields) or any(
            getattr(after, k) != getattr(path.stat(), k) for k in fields):
        raise ValueError('runtime executable changed during fingerprinting')
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': after.st_size}


def validate_runtime(value):
    _closed(value, RUNTIME_KEYS, 'runtime declaration')
    if value['route'] != ROUTE:
        raise ValueError('only the explicitly selected direct stream-JSON route is supported')
    binary = value['executable']
    _closed(binary, {'path', 'sha256', 'version', 'init_version'}, 'executable declaration')
    for key in ('path', 'version', 'init_version'):
        _text(binary[key], 'executable.' + key)
    _sha_text(binary['sha256'], 'executable.sha256')
    if executable_identity(binary['path'])['sha256'] != binary['sha256']:
        raise ValueError('runtime executable differs from the supplied SHA256')
    for key in ('model', 'effort'):
        if not isinstance(value[key], str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:+/@\[\]-]{0,255}', value[key]) is None:
            raise ValueError(f'{key} must be an explicit literal identifier, never a CLI option')
    auxiliary = value['auxiliary_models']
    if (type(auxiliary) is not list or len(auxiliary) > 32
            or any(not isinstance(x, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:+/@\[\]-]{0,255}', x) is None for x in auxiliary)
            or len(set(auxiliary)) != len(auxiliary) or value['model'] in auxiliary):
        raise ValueError('auxiliary models must be explicit distinct literal identifiers excluding the primary')
    _closed(value['limits'], {'contextWindow', 'maxOutputTokens'}, 'expected runtime limits')
    if (any(type(x) is not int or x <= 0 for x in value['limits'].values())
            or value['limits']['maxOutputTokens'] > value['limits']['contextWindow']):
        raise ValueError('expected limits must be positive integer counts with output no larger than context')
    _text(value['limits_basis'], 'limits_basis')
    _text(value['provider'], 'provider')
    auth = value['auth']
    _closed(auth, {'loggedIn', 'authMethod', 'apiProvider', 'subscriptionType', 'expected_api_key_source'}, 'auth expectations')
    if (auth['loggedIn'] is not True or auth['authMethod'] != 'claude.ai'
            or auth['apiProvider'] != 'firstParty' or auth['expected_api_key_source'] != 'none'):
        raise ValueError('this direct adapter requires an explicitly selected first-party subscription login, not provider keys')
    _text(auth['subscriptionType'], 'auth.subscriptionType')
    env = value['environment']
    if type(env) is not dict or set(env) - BASE_ENV_KEYS or not ENV_REQUIRED <= set(env):
        raise ValueError('environment must explicitly supply required base names and no credential, redirect or override names')
    for key, item in env.items():
        if type(item) is not str or len(item) > 16384 or any(c in item for c in ('\x00', '\r', '\n')):
            raise ValueError('environment values must be bounded literal single-line strings')
        if key != 'CLAUDE_SECURESTORAGE_CONFIG_DIR' and not item.strip():
            raise ValueError('only the explicitly selected secure-storage config value may be empty')
    if not Path(env['HOME']).is_absolute() or any(not Path(p).is_absolute() for p in env['PATH'].split(os.pathsep)):
        raise ValueError('HOME and every PATH component must be explicit absolute paths')
    if env['CLAUDE_CODE_DISABLE_1M_CONTEXT'] not in ('0', '1'):
        raise ValueError('the context-mode environment selection must be explicit 0 or 1')
    if env['CLAUDE_SECURESTORAGE_CONFIG_DIR'] and not Path(env['CLAUDE_SECURESTORAGE_CONFIG_DIR']).is_absolute():
        raise ValueError('a nonempty secure-storage config selection must be an absolute path')
    if type(value['deadline_seconds']) is not int or not 0 < value['deadline_seconds'] <= 86400:
        raise ValueError('deadline_seconds must be an explicit positive integer no larger than one day')
    budget = value['budget_guard_usd']
    if (not isinstance(budget, str) or len(budget) > 32 or re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', budget) is None
            or Decimal(budget) <= 0):
        raise ValueError('budget_guard_usd must be an explicit finite positive decimal string')
    awake = value['keep_awake']
    _closed(awake, {'policy', 'host_platform', 'basis'}, 'keep-awake selection')
    if awake['policy'] not in ('macos_iokit_ims_v1', 'not_applicable'):
        raise ValueError('unsupported keep-awake policy')
    _text(awake['host_platform'], 'keep_awake.host_platform')
    _text(awake['basis'], 'keep_awake.basis')
    if awake['policy'] == 'macos_iokit_ims_v1' and awake['host_platform'] != 'darwin':
        raise ValueError('the selected IOKit policy requires a declared macOS host')
    return draft._json(draft._encoded(value))


def environment(runtime, selected, spec, config_directory):
    """No inherited environment, secrets or historical live configuration."""
    return {**runtime['environment'], **POLICY_ENV,
            'CLAUDE_CONFIG_DIR': str(config_directory),
            'PYTHONPATH': str(authority.ROOT / 'src'), 'VIRTUAL_ENV': sys.prefix,
            'D4D_LAUNCH_INSTRUCTION': selected['instruction_path'],
            'D4D_MANIFEST': str(spec.manifest), 'D4D_PROFILE': spec.profile}


def command(runtime, selected, effective_system, attempt_id, controls):
    return [runtime['executable']['path'], *FLAGS, '--effort', runtime['effort'],
            '--model', runtime['model'], '--name', attempt_id,
            '--max-budget-usd', runtime['budget_guard_usd'],
            *controls['native_command_policy'].permission_arguments(selected['policy']),
            '--system-prompt', effective_system]


def _selection(composition_path, runtime):
    raw = _file(composition_path, 'composition')
    selected = composition.verified_composition(raw)
    spec, registration = draft.verified(selected['registration_raw_json'].encode())
    from data_sheets_schema.agentic_runtime import toolchain
    if draft._encoded(spec._agentic_toolchain) != draft._encoded(toolchain()):
        raise ValueError('native execution requires the exact pinned local helper toolchain')
    if (spec.runtime != 'Claude Code (direct)' or spec.method != 'claudecode_direct'
            or spec.out_dir is not None or spec.manifest is None
            or not isinstance(spec.profile, str) or not spec.profile.strip()
            or spec.reasoning_effort != runtime['effort'] or spec.provider != runtime['provider']
            or spec.prompt_text_env is not True):
        raise ValueError('complete direct spec, explicit manifest/profile/effort/provider and prompt-text environment are required')
    if registration['code_commit'] != authority.neutral.head():
        raise ValueError('offline registration source identity differs from the actual local Git head')
    return raw, selected, spec, registration


def permission_expectation(runtime, selected, spec, effective_system, config_directory):
    """Authority comes from the selected composition, never the saved probe."""
    commands = draft._commands(spec)
    expected_commands = {}
    for kind in ('draft', 'final_evidence'):
        matches = [text for text, role in commands.items() if role == kind]
        if len(matches) != 1:
            raise ValueError(f'the selected composition must name one exact {kind} command')
        expected_commands[kind] = matches[0]
    expected_commands['recorder'] = selected['policy']['post_final_recorder']['command']
    return {'runtime': runtime, 'policy': selected['policy'], 'commands': expected_commands,
            'source': {'path': str(spec.bundle), 'sha256': draft._sha(Path(spec.bundle).read_bytes())},
            'permission_environment': environment(runtime, selected, spec, config_directory),
            'controller_sources': selected['controller_sources'],
            'instruction_sha256': selected['instruction_sha256'],
            'system_sha256': draft._sha(effective_system.encode('utf-8'))}


def _paths(value, selected, *, fresh, extra_protected=()):
    """Return disjoint canonical reservations without writing or consuming one."""
    _, reg = draft.verified(selected['registration_raw_json'].encode())
    outputs = sorted({Path(p).absolute() for p in selected['policy']['readonly_lookups']['output_directories']})
    reserved = [Path(value[k]) for k in ('attempt_directory', 'evidence_directory')] + outputs
    protected = [Path(value[k]).resolve() for k in ('composition', 'system_path', 'permission_probe')]
    protected += [Path(selected['instruction_path']).resolve(), Path(value['runtime']['executable']['path'])]
    protected += [Path(pin['path']).resolve() for pin in reg['inputs'].values()]
    protected += [Path(pin['path']).resolve() for pin in selected['metadata_inputs'].values()]
    protected += [authority.ROOT / p for p in ('src', 'notes', 'scripts', 'tests', 'project', '.git', '.github', '.claude')]
    protected += [Path(p).resolve() for p in extra_protected]
    for path in reserved:
        if not path.is_absolute() or path != path.resolve() or path.is_symlink():
            raise ValueError('reserved paths must be canonical absolute paths without symlink components')
        if fresh and (path.exists() or path.is_symlink()):
            raise ValueError('attempt, evidence and output directories must be new; a spent identity cannot resume')
        if any(path == p or path in p.parents or p in path.parents for p in protected):
            raise ValueError('reserved directory overlaps an immutable authority/input or protected source')
    for index, path in enumerate(reserved):
        if any(path == p or path in p.parents or p in path.parents for p in reserved[index + 1:]):
            raise ValueError('attempt, evidence and output directories must be disjoint')
    for path in reserved[:2]:
        if not path.parent.is_dir():
            raise ValueError('attempt and evidence parents must already exist before reservation')
    return reserved


def registration(composition_path, system_path, *, permission_probe_path, attempt_id,
                 attempt_directory, evidence_directory, runtime):
    """Capture an offline proposal, not permission to invoke any native command."""
    if not isinstance(attempt_id, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', attempt_id) is None:
        raise ValueError('attempt_id must be an explicit safe single path component')
    runtime = validate_runtime(runtime)
    paths = {key: str(Path(path).absolute()) for key, path in {
        'composition': composition_path, 'system_path': system_path,
        'permission_probe': permission_probe_path,
        'attempt_directory': attempt_directory, 'evidence_directory': evidence_directory}.items()}
    if Path(paths['attempt_directory']).name != attempt_id:
        raise ValueError('attempt directory basename must equal its one-use identity')
    composition_raw, selected, spec, original = _selection(paths['composition'], runtime)
    system_raw = _file(paths['system_path'], 'system instructions')
    system_text = system_raw.decode('utf-8')
    if not system_text.strip():
        raise ValueError('system instructions must be explicit nonblank UTF-8 bytes')
    dependencies = authority.dependency_identity()
    with authority.loaded_dependencies(dependencies) as controls:
        effective_system = system_text + controls['native_command_policy'].command_guidance(selected['policy'])
        argv = command(runtime, selected, effective_system, attempt_id, controls)
    config = Path(paths['attempt_directory']) / 'cli_config'
    expected = permission_expectation(runtime, selected, spec, effective_system, config)
    probe_raw = _file(paths['permission_probe'], 'saved permission observations')
    from data_sheets_schema.native_execution_permissions import verify_saved_probe
    permission = verify_saved_probe(probe_raw, expected=expected)
    if permission.get('checked') is not True or permission.get('passed') is not True:
        raise ValueError('saved permission observations are not complete and passing')
    value = {'kind': KIND, 'version': VERSION, 'execution': EXECUTION,
        'attempt_id': attempt_id, **paths, 'runtime': runtime,
        'working_directory': str(Path.cwd().resolve()), 'dependencies': dependencies,
        'composition_raw_json': composition_raw.decode('utf-8'),
        'composition_sha256': draft._sha(composition_raw),
        'system_sha256': draft._sha(system_raw), 'effective_system': effective_system,
        'effective_system_sha256': draft._sha(effective_system.encode('utf-8')),
        'instruction_sha256': selected['instruction_sha256'],
        'permission_probe_sha256': draft._sha(probe_raw),
        'permission_expected_sha256': draft._sha(draft._encoded(expected)),
        'permission_observations': permission,
        'argv': argv, 'environment': environment(runtime, selected, spec, config),
        'selection': {'project': spec.project, 'method': spec.method, 'label': spec.label,
                      'render_spec': original['render_spec']},
        'scope': 'Offline proposal only. Separate exact review, CI, permission observations and owner launch evidence are required; no scientific acceptance or provider billing assertion.'}
    _paths(value, selected, fresh=False)
    # These resources are read by reconstructed selection, so capture drift is
    # a refusal rather than an unnoticed mixed registration.
    if (_file(paths['composition'], 'composition') != composition_raw
            or _file(paths['system_path'], 'system instructions') != system_raw
            or _file(paths['permission_probe'], 'saved permission observations') != probe_raw
            or draft._encoded(authority.dependency_identity()) != draft._encoded(dependencies)):
        raise ValueError('native registration authority changed during preparation')
    return value


def verified(raw):
    if type(raw) is not bytes or len(raw) > 8 * 1024 * 1024:
        raise ValueError('native execution registration must be bounded exact bytes')
    value = draft._json(raw)
    if (type(value) is not dict or value.get('kind') != KIND or type(value.get('version')) is not int
            or value['version'] != VERSION or value.get('execution') != EXECUTION):
        raise ValueError('not a supported explicit native execution registration')
    try:
        expected = registration(value['composition'], value['system_path'],
            permission_probe_path=value['permission_probe'], attempt_id=value['attempt_id'],
            attempt_directory=value['attempt_directory'], evidence_directory=value['evidence_directory'],
            runtime=value['runtime'])
    except (KeyError, TypeError) as exc:
        raise ValueError('incomplete native execution registration') from exc
    if draft._encoded(value) != draft._encoded(expected):
        raise ValueError('native execution registration differs from its exact source, permission, runtime or selection authority')
    return value


def write_registration(destination, **kwargs):
    value = registration(**kwargs)
    raw = draft._encoded(value)
    verified(raw)
    destination = Path(destination).absolute()
    if destination != destination.resolve() or destination.is_symlink():
        raise ValueError('registration destination must have no symlink components')
    selected = composition.verified_composition(value['composition_raw_json'].encode())
    reservations = _paths(value, selected, fresh=False)
    if any(destination == p or p in destination.parents or destination in p.parents for p in reservations):
        raise ValueError('registration destination overlaps a one-use reservation')
    if any(destination.resolve().is_relative_to(authority.ROOT / directory)
           for directory in ('src', 'notes', 'scripts', 'tests', 'project', '.git', '.github', '.claude')):
        raise ValueError('registration cannot modify source or historical controls')
    with destination.open('xb') as stream:
        stream.write(raw)
    return {'path': str(destination), 'sha256': draft._sha(raw), 'execution': EXECUTION}
