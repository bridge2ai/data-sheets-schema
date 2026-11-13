"""Registered A3 subscription terms, 2026-11-08 (#4354).

Pure declaration checks, not launch authority. The runtime is already part of
the registration's exact bytes; these values cannot be supplied by a later
guard or owner statement. Explicit validity dates are required, never guessed.
"""
from datetime import datetime
import json
from pathlib import Path
import re

from .native_shared_runtime_values import _json, _closed, _text

TERM_VALUES = {'max_starting_weekly_utilization': 0.50,
               'max_starting_five_hour_utilization': 0.25,
               'max_age_seconds': 1200,
               'pre_reservation_margin_seconds': 90}
POLICY_KEYS = {*TERM_VALUES, 'capture_state_directory', 'valid_from', 'valid_until'}
N1_VALIDITY_SECONDS = 14 * 24 * 60 * 60


def timestamp(value, label):
    if (type(value) is not str or re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z', value) is None):
        raise ValueError(label + ' requires strict UTC ending Z')
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00').timestamp()
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError(label + ' requires a valid UTC timestamp') from exc


def validate_policy(policy):
    _closed(policy, POLICY_KEYS, 'registered admission policy')
    for key, wanted in TERM_VALUES.items():
        actual = policy[key]
        allowed = (int, float) if key.endswith('_utilization') else (int,)
        if type(actual) not in allowed or actual != wanted:
            raise ValueError('registered admission term differs from A3: ' + key)
    raw = policy['capture_state_directory']
    if type(raw) is not str or not raw or '\x00' in raw:
        raise ValueError('capture state directory requires an explicit physical path')
    path = Path(raw)
    if not path.is_absolute() or str(path) != raw or '..' in path.parts or path.resolve() != path:
        raise ValueError('capture state directory requires an exact physical absolute path')
    start = timestamp(policy['valid_from'], 'valid_from')
    end = timestamp(policy['valid_until'], 'valid_until')
    if end - start != N1_VALIDITY_SECONDS:
        raise ValueError('registered validity must span exactly fourteen days under N1.8')
    return json.loads(json.dumps(policy, allow_nan=False))


def validate_runtime_terms(runtime):
    """Registered D143 pair and N1.8 keep-awake; equality alone is insufficient."""
    from . import native_runtime_profiles as profiles
    if profiles.profile_name(runtime) == profiles.SYNTHETIC_PROFILE:
        profiles.require_synthetic_declarations(runtime)
        return
    if type(runtime) is not dict:
        raise ValueError('registration requires an explicit runtime')
    from .native_run_limits import require_registered_pair
    require_registered_pair(runtime)
    awake = runtime.get('keep_awake')
    _closed(awake, {'policy', 'host_platform', 'basis'}, 'registered keep-awake')
    _text(awake['basis'], 'registered keep-awake basis', 512)
    if (type(awake) is not dict or awake.get('policy') != 'macos_iokit_ims_v1'
            or awake.get('host_platform') != 'darwin'):
        raise ValueError('registered keep-awake must equal N1.8 macos_iokit_ims_v1 on darwin')


def registered_policy(runtime):
    if type(runtime) is not dict or type(runtime.get('limits_basis')) is not str:
        raise ValueError('registration requires its A3 admission policy')
    basis = _json(runtime['limits_basis'])
    if (type(basis) is not dict or basis.get('kind') != 'd4d_native_u4b_runtime_basis'
            or type(basis.get('version')) is not int or basis['version'] != 3):
        raise ValueError('registration requires A3 runtime basis v3')
    validate_runtime_terms(runtime)
    return validate_policy(basis.get('admission'))


def admission_terms(runtime):
    policy = registered_policy(runtime)
    return {key: policy[key] for key in TERM_VALUES}
