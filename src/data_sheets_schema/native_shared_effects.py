"""Pure stage-effect classification shared by callback and saved probe replay.

This is a restrictive stage overlay, not a replacement for the pinned command
classifier or FileAccess. The caller must use governs_stage_effect before
classification; a stage approval still requires the real file-access policy.
No function here resolves paths, reads files, or proves observed tool delivery.
"""
from __future__ import annotations

from pathlib import PurePosixPath
import shlex

from data_sheets_schema.native_shared_contract import (
    NAME, ROLE_RELATIVE_PATHS, NativeEffectView, canonical_path,
)

MODULE = 'data_sheets_schema.native_shared_stage'
_FILES = frozenset(('Read', 'Write', 'Edit', 'MultiEdit'))
_WRITES = frozenset(('Write', 'Edit', 'MultiEdit'))


def _within(path, root):
    target, parent = PurePosixPath(path), PurePosixPath(root)
    return target == parent or parent in target.parents


def _view(view):
    if type(view) is not NativeEffectView or view.protocol != NAME:
        raise ValueError('stage effects require the exact frozen native view')
    # Recheck carrier shape at the trust boundary; even Python-side mutation of
    # a frozen object must not turn a malformed view into inherited admission.
    view.__post_init__()
    roles = {row.role: row.path for row in view.protected_roles}
    if len(roles) != len(view.protected_roles):
        raise ValueError('stage effect protected roles are ambiguous')
    if roles.get('stage_root') != view.stage_root or 'selection' not in roles:
        raise ValueError('stage effect view lacks its selected protected roots')
    root = PurePosixPath(view.stage_root)
    if root == PurePosixPath('/') or _within(roles['selection'], view.stage_root):
        raise ValueError('selection must be outside mutable stage effects')
    for role, relative in ROLE_RELATIVE_PATHS.items():
        if roles.get(role) != str(root / relative):
            raise ValueError('stage effect roles differ from the fixed recipe')
    try:
        argv = shlex.split(view.stage_command)
    except ValueError as exc:
        raise ValueError('stage effect command is not literal') from exc
    if (len(argv) != 6 or argv[1:5] != ['-m', MODULE, 'advance', '--registration']
            or argv[5] != roles['selection'] or view.stage_command != shlex.join(argv)):
        raise ValueError('stage effect command differs from fixed selected advance')
    canonical_path(argv[0], 'registered Python')
    if view.state == 'awaiting_response':
        if view.cursor is None or view.request is None or view.response is None:
            raise ValueError('current effects require observed request and exact response')
        ordinal = view.cursor.ordinal
        if (view.request.path != str(root/'requests'/f'{ordinal:06d}.json')
                or view.response.path != str(root/'responses'/f'{ordinal:06d}.bin')):
            raise ValueError('current effect paths differ from their selected cursor')
    elif view.request_read_observation_sha256 is not None or view.response_intent_observation_sha256 is not None:
        raise ValueError('nonresponse effects must not reuse request or response observations')
    if view.pending_advance_tool_use_id is not None and not view.pending_advance_tool_use_id.strip():
        raise ValueError('pending advance requires an explicit tool identity')
    paths = [pin.path for pin in view.sealed]
    if len(paths) != len(set(paths)):
        raise ValueError('sealed effects contain duplicate path identities')
    for path in paths:
        if _within(path, str(root/'requests')) or _within(path, str(root/'responses')):
            raise ValueError('request/response files cannot gain sealed-read authority')
    return roles


def _input(tool_name, tool_input):
    if type(tool_name) is not str or not tool_name or type(tool_input) is not dict:
        raise ValueError('stage routing requires explicit typed tool input')
    if tool_name in _FILES:
        # Never normalize an alias or let a malformed path fall through to a
        # broader inherited directory grant. Actual aliases are checked by I/O
        # capture and the live observer, separately from lexical identity.
        return canonical_path(tool_input.get('file_path'), 'tool file path')
    if tool_name == 'Bash':
        command = tool_input.get('command')
        if type(command) is not str or not command or '\x00' in command:
            raise ValueError('stage routing requires an explicit Bash command')
    return None


def governs_stage_effect(view, *, tool_name, tool_input):
    """Whether this restrictive overlay owns the effect; malformed input raises.

    Ordinary source Reads and nonstage helpers retain their frozen classifiers.
    Writes to captured immutable authorities are always owned and refused here.
    """
    roles = _view(view)
    path = _input(tool_name, tool_input)
    if tool_name in _FILES:
        return (_within(path, view.stage_root)
                or tool_name in _WRITES and (path in roles.values()
                    or path in {pin.path for pin in view.sealed}))
    if tool_name == 'Bash':
        command = tool_input['command']
        # The exact helper owns its S path outside stage_root; altered module
        # spellings or shell paths inside stage_root cannot fall through.
        return command == view.stage_command or MODULE in command or view.stage_root in command
    return False


def classify_effect(view, *, tool_name, tool_input):
    """Return a strict (classification, basis) for the stage overlay only."""
    if not governs_stage_effect(view, tool_name=tool_name, tool_input=tool_input):
        return 'not_prescribed', 'outside stage overlay; inherited classifier remains required'
    if view.state == 'failed':
        return 'not_prescribed', 'selected stage failure is terminal'
    if view.pending_advance_tool_use_id is not None:
        return 'not_prescribed', 'current advance has not settled'
    if tool_name == 'Bash':
        if view.correction_window:
            return 'not_prescribed', 'report-only correction cannot advance selected stages'
        allowed = {'command', 'description', 'timeout', 'run_in_background'}
        if (set(tool_input) - allowed or tool_input['command'] != view.stage_command
                or 'description' in tool_input and type(tool_input['description']) is not str
                or 'timeout' in tool_input and (type(tool_input['timeout']) is not int or tool_input['timeout'] <= 0)
                or 'run_in_background' in tool_input and tool_input['run_in_background'] is not False):
            return 'not_prescribed', 'stage helper requires exact foreground selected invocation'
        return 'prescribed', 'exact fixed selected stage helper; transition remains independently checked'
    path = tool_input['file_path']
    if tool_name == 'Read':
        if set(tool_input) != {'file_path'}:
            return 'not_prescribed', 'stage delivery requires one whole Read, not a range or variant'
        if view.state == 'awaiting_response' and path == view.request.path:
            return 'prescribed', 'current immutable request Read; complete settled delivery remains required'
        if path in {pin.path for pin in view.sealed}:
            return 'prescribed', 'exact observed sealed artifact Read'
        return 'not_prescribed', 'future, stale or helper-owned stage file is not a current Read'
    if tool_name != 'Write':
        return 'not_prescribed', 'selected responses require one whole Write, never edits'
    if view.correction_window:
        return 'not_prescribed', 'report-only correction cannot mutate selected stage artifacts'
    if (view.state != 'awaiting_response' or path != view.response.path
            or set(tool_input) != {'file_path', 'content'} or type(tool_input.get('content')) is not str):
        return 'not_prescribed', 'only the exact current whole response destination is writable'
    if view.request_read_observation_sha256 is None:
        return 'not_prescribed', 'current complete settled request Read has not been observed'
    if view.response_intent_observation_sha256 is not None:
        return 'not_prescribed', 'first response intent is already consumed; no replacement or retry'
    try:
        raw = tool_input['content'].encode('utf-8')
    except UnicodeError:
        return 'not_prescribed', 'response must be complete UTF-8 bytes'
    if not raw or len(raw) > view.response.max_bytes:
        return 'not_prescribed', 'response exceeds its explicit complete-byte bound or is empty'
    return 'prescribed', 'first current bounded response Write after observed whole request Read'
