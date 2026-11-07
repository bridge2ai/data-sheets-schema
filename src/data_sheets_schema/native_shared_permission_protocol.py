"""Pure permission frames for C/D's input-only consumer, 2026-11-07.

Successful values preserve native_control.py e53f9627e629f06f40046460dbe43bb7a62c26d3f28bedf41408531bc5374a36
and native_command_policy.py 99db1879752ea73fea0002ea5a3a2d8333365b4e3843abdab3e1a1f0008709cc.
Unknown control contracts raise ValueError with the historical refusal text;
the historical BudgetStop class remains outside this pure interface. These
functions grant no permission or execution authority and perform no I/O.
"""
from copy import deepcopy as _deepcopy
import hashlib as _hashlib
import json as _json


_CONTRACT = {'version': 2, 'event': 'PreToolUse', 'matcher': 'Bash|Read|Write',
             'callback_id': 'd4d_tool_policy_v2', 'initialize_timeout_seconds': 30,
             'callback_timeout_seconds': 2, 'runtime_callback_timeout_seconds': 3}
_HISTORY_CONTRACT = {'version': 3, 'event': 'PreToolUse', 'matcher': 'Bash|Read|Write',
                     'callback_id': 'd4d_tool_policy_v3', 'initialize_timeout_seconds': 30,
                     'callback_timeout_seconds': 2, 'observer_timeout_seconds': 120,
                     'runtime_callback_timeout_seconds': 125}
_INIT_ID = 'd4d_initialize_v1'


def history_contract():
    """Return a fresh complete history contract, never shared mutable state."""
    return _deepcopy(_HISTORY_CONTRACT)


def initialization_id():
    return _INIT_ID


def policy_digest(value):
    """Preserve sorted, ASCII-escaped, compact historical JSON exactly."""
    return _hashlib.sha256(_json.dumps(
        value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def initialize_frame(pretool_control):
    """Build the selected known contract's frame; None keeps the old default."""
    if pretool_control is None:
        contract = _CONTRACT
    else:
        try:
            known = type(pretool_control) is dict and any(
                policy_digest(pretool_control) == policy_digest(item)
                for item in (_CONTRACT, _HISTORY_CONTRACT))
        except (TypeError, ValueError, OverflowError):
            known = False
        if not known:
            raise ValueError('missing or changed native control contract')
        contract = _deepcopy(pretool_control)
    return {'type': 'control_request', 'request_id': _INIT_ID, 'request': {
        'subtype': 'initialize', 'hooks': {contract['event']: [{
            'matcher': contract['matcher'], 'hookCallbackIds': [contract['callback_id']],
            'timeout': contract['runtime_callback_timeout_seconds']}]}}}


def hook_output(classification, basis):
    return {} if classification == 'prescribed' else {'hookSpecificOutput': {
        'hookEventName': _CONTRACT['event'], 'permissionDecision': 'deny',
        'permissionDecisionReason': 'Outside the registered tool policy: ' + basis}}


def permission_arguments(policy):
    """Keep rule order and compact inline JSON; create no settings file."""
    return ['--input-format', 'stream-json', '--settings', _json.dumps(
        {'permissions': {'allow': policy['allowed_tools']}}, separators=(',', ':'))]
