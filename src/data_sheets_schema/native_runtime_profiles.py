"""Closed v2 runtime profiles; synthetic peers never authorize native execution.

The software-test profile is a separately declared capability over one exact
ordinary Python peer. It is not a way to shorten production limits or borrow a
subscription identity. Legacy v1 validation does not import this dispatcher.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys

PRODUCTION_PROFILE = 'production'
SYNTHETIC_PROFILE = 'synthetic-software-test'
SYNTHETIC_REQUESTED = 'synthetic-native-model'
SYNTHETIC_RETURNED = 'synthetic-native-returned-model'
SYNTHETIC_PROVIDER = 'scripted-local'
SYNTHETIC_DEADLINE_SECONDS = 900
SYNTHETIC_BUDGET = '1.0'
SYNTHETIC_PEER_SHA256 = 'eea1f457b940ced66fe8a2c7e2bbb030d20d902fc04824baa74eba7a86ae510d'
_KINDS = {'d4d_native_u4b_runtime_basis', 'd4d_native_u4b_provisional_runtime_basis'}
_AUTH = {'loggedIn': False, 'authMethod': SYNTHETIC_PROFILE,
         'apiProvider': SYNTHETIC_PROVIDER, 'subscriptionType': SYNTHETIC_PROFILE,
         'expected_api_key_source': 'none'}


def profile_name(runtime):
    """Select only an explicit closed profile; reserved test labels cannot fall back."""
    from . import native_shared_runtime_values as values
    if type(runtime) is not dict:
        raise ValueError('runtime profile requires an object')
    raw = runtime.get('limits_basis')
    basis = None
    if type(raw) is str and raw.lstrip().startswith('{'):
        basis = values._json(raw)
        if type(basis) is not dict:
            raise ValueError('runtime basis must be an object')
    profile = basis.get('profile', PRODUCTION_PROFILE) if basis else PRODUCTION_PROFILE
    if type(profile) is not str or profile not in (PRODUCTION_PROFILE, SYNTHETIC_PROFILE):
        raise ValueError('unknown runtime profile')
    if profile == SYNTHETIC_PROFILE:
        if type(basis.get('kind')) is not str or basis['kind'] not in _KINDS:
            raise ValueError('synthetic profile requires a closed U4b basis')
        return profile
    auth = runtime.get('auth')
    reserved = {SYNTHETIC_PROFILE, SYNTHETIC_PROVIDER, SYNTHETIC_REQUESTED, SYNTHETIC_RETURNED}
    markers = [runtime.get('model'), runtime.get('provider')]
    if type(auth) is dict:
        markers.extend(auth.values())
    if any(type(x) is str and x in reserved for x in markers):
        raise ValueError('synthetic runtime markers require the explicit synthetic profile')
    return PRODUCTION_PROFILE


def require_production(runtime):
    """Reject software-test declarations at every real producer/actuation entry."""
    if profile_name(runtime) != PRODUCTION_PROFILE:
        raise ValueError('real native entry refuses the synthetic software-test profile')
    return runtime


def require_synthetic_declarations(runtime):
    """Pure closed wire checks, suitable for permission and saved-evidence readers."""
    from . import native_shared_runtime_values as v
    if profile_name(runtime) != SYNTHETIC_PROFILE:
        raise ValueError('synthetic entry requires its explicit software-test profile')
    v._closed(runtime, v.RUNTIME_KEYS, 'synthetic runtime')
    if (runtime['route'] != v.ROUTE or runtime['model'] != SYNTHETIC_REQUESTED
            or runtime['auxiliary_models'] != [] or runtime['effort'] != 'high'
            or runtime['provider'] != SYNTHETIC_PROVIDER or runtime['auth'] != _AUTH
            or type(runtime['auth'].get('loggedIn')) is not bool
            or type(runtime['deadline_seconds']) is not int
            or runtime['deadline_seconds'] != SYNTHETIC_DEADLINE_SECONDS
            or runtime['budget_guard_usd'] != SYNTHETIC_BUDGET):
        raise ValueError('synthetic runtime differs from the closed test model/account/provider/limits')
    v._text(runtime['limits_basis'], 'limits_basis')
    basis = v._json(runtime['limits_basis'])
    provisional = basis['kind'] == 'd4d_native_u4b_provisional_runtime_basis'
    basis_keys = {'kind', 'version', 'profile', 'model_aliases'}
    if not provisional:
        basis_keys |= {'probe', 'request', 'observed', 'thinking', 'durable_copy',
                       'observation_probe', 'admission'}
    v._closed(basis, basis_keys, 'synthetic runtime basis')
    if (type(basis['version']) is not int or basis['version'] != (1 if provisional else 3)
            or basis['model_aliases'] != {'requested': SYNTHETIC_REQUESTED,
                                          'returned': SYNTHETIC_RETURNED}):
        raise ValueError('synthetic basis requires its exact versioned model pair')
    v._closed(runtime['limits'], {'contextWindow', 'maxOutputTokens'}, 'synthetic limits')
    if (any(type(x) is not int or x <= 0 for x in runtime['limits'].values())
            or runtime['limits']['maxOutputTokens'] > runtime['limits']['contextWindow']):
        raise ValueError('synthetic limits require positive counts with output within context')
    binary = runtime['executable']
    v._closed(binary, {'path', 'sha256', 'version', 'init_version'}, 'synthetic executable')
    v._sha_text(binary['sha256'], 'synthetic executable SHA256')
    if (binary['version'] != 'SYNTHETIC PYTHON SOFTWARE TEST'
            or binary['init_version'] != 'synthetic-python-1'):
        raise ValueError('synthetic executable requires explicit software-test labels')
    v._text(binary['path'], 'synthetic executable path')
    env = runtime['environment']
    if type(env) is not dict or set(env) - v.BASE_ENV_KEYS or not v.ENV_REQUIRED <= set(env):
        raise ValueError('synthetic environment has missing or forbidden names')
    for key, value in env.items():
        if (type(value) is not str or len(value) > 16384
                or any(c in value for c in ('\0', '\r', '\n'))
                or (key != 'CLAUDE_SECURESTORAGE_CONFIG_DIR' and not value.strip())):
            raise ValueError('synthetic environment requires bounded literal strings')
    if (env['CLAUDE_SECURESTORAGE_CONFIG_DIR'] != ''
            or env['CLAUDE_CODE_DISABLE_1M_CONTEXT'] != '0'
            or not Path(env['HOME']).is_absolute()
            or any(not Path(x).is_absolute() for x in env['PATH'].split(os.pathsep))):
        raise ValueError('synthetic environment must select isolated home/storage and explicit context')
    awake = runtime['keep_awake']
    v._closed(awake, {'policy', 'host_platform', 'basis'}, 'synthetic keep-awake')
    if awake['policy'] != 'not_applicable' or awake['host_platform'] != sys.platform:
        raise ValueError('synthetic runtime never selects production keep-awake')
    v._text(awake['basis'], 'synthetic keep-awake basis')
    return runtime


def require_synthetic(runtime):
    """Recheck exact peer bytes and isolated HOME; never inspect or invoke an account."""
    from . import native_shared_runtime_values as v
    require_synthetic_declarations(runtime)
    binary = Path(runtime['executable']['path'])
    if (not binary.is_absolute() or binary.resolve(strict=True) != binary
            or binary.stat().st_nlink != 1):
        raise ValueError('synthetic peer must be a physical single-link durable executable')
    fd = os.open(binary, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111
                or before.st_nlink != 1 or before.st_size > 1048576):
            raise ValueError('synthetic peer must be a bounded regular executable')
        raw = stream.read(1048577)
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    if any(getattr(before, k) != getattr(after, k) or
           getattr(after, k) != getattr(binary.stat(), k) for k in fields):
        raise ValueError('synthetic peer changed during validation')
    # The exact interpreter must suppress the peer directory before any import.
    # A sibling json.py/package must never execute before this runtime guard.
    shebang = ('#!' + sys.executable + ' -P\n').encode()
    if (not raw.startswith(shebang)
            or hashlib.sha256(raw[len(shebang):]).hexdigest() != SYNTHETIC_PEER_SHA256
            or hashlib.sha256(raw).hexdigest() != runtime['executable']['sha256']):
        raise ValueError('synthetic entry refuses any executable except the exact Python test peer')
    home = Path(runtime['environment']['HOME'])
    if (home != binary.parent / 'synthetic-home' or home.resolve(strict=True) != home
            or not home.is_dir()):
        raise ValueError('synthetic HOME must be the physical isolated sibling synthetic-home')
    # Empty HOME is intentional: no account configuration, keychain selectors,
    # shell startup files or credential files may be inherited by the peer.
    if any(home.iterdir()):
        raise ValueError('synthetic HOME must contain no account or configuration artifacts')
    return v._json(v._encoded(runtime))
