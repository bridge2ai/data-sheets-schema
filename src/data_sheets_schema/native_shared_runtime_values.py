"""Neutral native runtime values and offline validation, U3-D round 8.

Parity extraction, 2026-11-07, from native_execution_registration.py at
e97831616f56f2741bdf9fa9d55c74afab3c6c46 (unchanged on D 9687dea189).
The JSON helpers preserve native_attribution_registration.py at that same
commit: pretty UTF-8 serialization, sorted keys, a terminal newline, and
duplicate/nonfinite JSON refusal. Neither frozen module is imported here.

Fingerprinting reads an explicitly supplied regular file; it never invokes
the file, discovers an executable, or probes credentials or a provider.
Validation is data validation, not execution admission.
"""
from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
import re
import stat


ROUTE = 'claude_code_direct_stream_json_v1'
RUNTIME_KEYS = {'route', 'executable', 'model', 'auxiliary_models', 'effort', 'limits',
    'limits_basis', 'provider', 'auth', 'environment', 'deadline_seconds', 'budget_guard_usd', 'keep_awake'}
BASE_ENV_KEYS = {'PATH', 'HOME', 'USER', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM',
                'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_CODE_DISABLE_1M_CONTEXT'}
ENV_REQUIRED = {'PATH', 'HOME', 'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_CODE_DISABLE_1M_CONTEXT'}
V2_BASE_ENV_KEYS = BASE_ENV_KEYS | {'PYSTOW_HOME'}
V2_ENV_REQUIRED = ENV_REQUIRED | {'PYSTOW_HOME'}
POLICY_ENV = {'DISABLE_NON_ESSENTIAL_MODEL_CALLS': '1',
              'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
              'DISABLE_TELEMETRY': '1', 'CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS': '1',
              'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1'}
FLAGS = ['--print', '--safe-mode', '--restricted', '--strict-mcp-config',
         '--disable-slash-commands', '--no-session-persistence', '--prompt-suggestions', 'false',
         '--output-format', 'stream-json', '--verbose',
         '--permission-mode', 'dontAsk', '--tools', 'Read,Write,Bash']


def _json(raw):
    """The frozen attribution parser's duplicate/nonfinite refusal semantics."""
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f'duplicate JSON key: {key}')
            out[key] = value
        return out
    def invalid(value):
        raise ValueError(f'nonfinite JSON number: {value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _encoded(value):
    """Exact frozen attribution bytes; do not substitute compact canonical JSON."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


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


def validate_runtime(value, *, helper_cache=False):
    """Apply the frozen runtime refusals and return its exact JSON-roundtrip copy."""
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
    allowed = V2_BASE_ENV_KEYS if helper_cache else BASE_ENV_KEYS
    required = V2_ENV_REQUIRED if helper_cache else ENV_REQUIRED
    if type(env) is not dict or set(env) - allowed or not required <= set(env):
        raise ValueError('environment must explicitly supply required base names and no credential, redirect or override names')
    for key, item in env.items():
        if type(item) is not str or len(item) > 16384 or any(c in item for c in ('\x00', '\r', '\n')):
            raise ValueError('environment values must be bounded literal single-line strings')
        if key != 'CLAUDE_SECURESTORAGE_CONFIG_DIR' and not item.strip():
            raise ValueError('only the explicitly selected secure-storage config value may be empty')
    if not Path(env['HOME']).is_absolute() or any(not Path(p).is_absolute() for p in env['PATH'].split(os.pathsep)):
        raise ValueError('HOME and every PATH component must be explicit absolute paths')
    if helper_cache:
        from .native_helper_cache import declared_path
        declared_path(env)
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
    return _json(_encoded(value))


def validate_runtime_v2(value):
    """Dispatch explicitly declared v2 software tests without changing v1 validation."""
    from . import native_runtime_profiles as profiles
    if profiles.profile_name(value) == profiles.SYNTHETIC_PROFILE:
        return profiles.require_synthetic(value)
    return validate_runtime(value, helper_cache=True)
