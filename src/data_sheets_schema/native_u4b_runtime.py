"""Offline D106/D112 runtime evidence, 2026-11-08 (#4354).

Reads explicit saved probe and inert-or-real binary bytes; never executes or
copies a binary, discovers account state, or creates launch authority. The
versioned evidence lives in the existing limits_basis string, preserving the
historical closed runtime schema. Source-copy evidence is a local observation,
not authenticated history; a later updater change does not invalidate the copy.
Basis v3 takes limits and thinking from the separately authorized observation
phase, pins its complete saved evidence, and registers admission terms. The
later permission phase binds this final runtime without a hash back-edge.
No probe is run by this code; saved records are supplied evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from . import native_shared_runtime_values as values
from . import native_runtime_profiles as profiles
from .native_shared_evidence import read_regular
from .native_path_identity import contains

KIND = 'd4d_native_u4b_runtime_basis'
MODEL = 'claude-opus-5[1m]'
MAX_PROBE_BYTES = 4_000_000
MAX_BINARY_BYTES = 1_073_741_824
BASIS_KEYS = {'kind', 'version', 'probe', 'request', 'observed', 'thinking', 'durable_copy',
              'model_aliases', 'observation_probe', 'admission'}
PIN_KEYS = {'path', 'sha256', 'bytes', 'device', 'inode'}


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _physical(path, label):
    if type(path) is not str or not path or '\x00' in path:
        raise ValueError(label + ' requires an explicit physical path')
    target = Path(path)
    if not target.is_absolute() or str(target.resolve(strict=True)) != path:
        raise ValueError(label + ' requires an exact absolute physical path')
    return target


def _binary_pin(path):
    target = _physical(path, 'binary')
    before = target.lstat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_nlink', 'st_mtime_ns', 'st_ctime_ns')
    signature = lambda info: tuple(getattr(info, key) for key in fields)
    if (not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111
            or before.st_nlink != 1 or not 0 < before.st_size <= MAX_BINARY_BYTES):
        raise ValueError('binary must be a bounded executable regular single-link file')
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if signature(os.fstat(fd)) != signature(before):
            raise ValueError('binary changed before capture')
        digest, count = hashlib.sha256(), 0
        while True:
            block = os.read(fd, min(1_048_576, MAX_BINARY_BYTES + 1 - count))
            if not block:
                break
            count += len(block)
            if count > MAX_BINARY_BYTES:
                raise ValueError('binary exceeds capture bound')
            digest.update(block)
        if signature(os.fstat(fd)) != signature(before):
            raise ValueError('binary changed during capture')
    finally:
        os.close(fd)
    if (count != before.st_size or signature(target.lstat()) != signature(before)
            or str(target.resolve(strict=True)) != path):
        raise ValueError('binary changed after capture')
    return {'path': path, 'sha256': digest.hexdigest(), 'bytes': count,
            'device': before.st_dev, 'inode': before.st_ino}


def _saved_probe(path, model_pair=None):
    from .native_model_aliases import REQUESTED, RETURNED, require_frame_models
    pair = {'requested': REQUESTED, 'returned': RETURNED} if model_pair is None else model_pair
    model = pair['requested']
    member = read_regular(path, 'u4b_probe', max_bytes=MAX_PROBE_BYTES)
    raw = member.captured.raw
    rows = raw.splitlines()
    if not rows or len(rows) > 10_000:
        raise ValueError('saved probe requires bounded JSONL evidence')
    found, terminals, events = [], [], []
    for index, row in enumerate(rows, 1):
        if not row.strip():
            continue
        value = values._json(row)
        if type(value) is not dict:
            raise ValueError('saved probe requires JSON object lines')
        events.append((index, value))
        if value.get('type') == 'system' and value.get('subtype') == 'init':
            found.append((index, row, value))
        if value.get('type') == 'result':
            terminals.append((index, row, value))
    if len(found) != 1:
        raise ValueError('saved probe requires exactly one init line')
    line, row, init = found[0]
    if len(terminals) != 1:
        raise ValueError('saved probe requires exactly one terminal result')
    terminal_line, terminal_raw, terminal = terminals[0]
    if (terminal_line <= line or terminal_line != events[-1][0]
            or terminal.get('is_error') is not False or terminal.get('subtype') != 'success'):
        raise ValueError('saved probe requires a successful final terminal result after init')
    session = init.get('session_id')
    values._text(session, 'saved probe session')
    if any(event.get('session_id') != session for _, event in events
           if event.get('type') in ('assistant', 'user', 'result')):
        raise ValueError('saved probe terminal/messages differ from its init session')
    for _, event in events:
        if event.get('type') in ('assistant', 'user', 'result'):
            require_frame_models(event, pair)
    usage = terminal.get('modelUsage')
    values._closed(usage, {model}, 'saved terminal modelUsage')
    own = usage[model]
    if type(own) is not dict:
        raise ValueError('saved terminal modelUsage requires an object')
    limits = {key: own.get(key) for key in ('contextWindow', 'maxOutputTokens')}
    if (any(type(value) is not int or value <= 0 for value in limits.values())
            or limits['maxOutputTokens'] > limits['contextWindow']):
        raise ValueError('saved terminal limits must be explicit positive integer counts')
    if init.get('model') != model:
        raise ValueError('saved init does not name the D112 model')
    values._text(init.get('claude_code_version'), 'saved init version')
    pin = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
           'init_line': line, 'init_sha256': hashlib.sha256(row).hexdigest(),
           'terminal_line': terminal_line, 'terminal_sha256': hashlib.sha256(terminal_raw).hexdigest()}
    observation = {'model': init['model'], 'limits': dict(limits),
                   'init_version': init['claude_code_version']}
    return pin, observation


def _saved_request(path, model_pair=None):
    """Read the captured HTTP body, never infer thinking from init or effort."""
    from .native_model_aliases import RETURNED
    returned = RETURNED if model_pair is None else model_pair['returned']
    member = read_regular(path, 'u4b_native_request', max_bytes=MAX_PROBE_BYTES)
    raw = member.captured.raw
    body = values._json(raw)
    if type(body) is not dict or body.get('model') != returned:
        raise ValueError('saved request does not name the declared returned model')
    if any(name in body for name in ('thinkingEnabled', 'thinking_enabled', 'alwaysThinkingEnabled')):
        raise ValueError('unsupported saved request thinking field; explicit adaptation required')
    if 'thinking' not in body:
        raise ValueError('saved request must expose an observed thinking setting')
    pin = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    thinking = {'state': 'observed', 'field': 'thinking', 'value': _thinking(body['thinking'])}
    return pin, thinking


def _thinking(value):
    if value is None or type(value) not in (bool, str, dict):
        raise ValueError('thinking setting requires an explicit boolean, text or JSON object')
    encoded = _canonical(value)
    if len(encoded) > 1024 or (type(value) is str and not value.strip()) or value == {}:
        raise ValueError('thinking setting must be nonempty bounded JSON')
    return values._json(encoded)


def _profile(runtime):
    result = values.validate_runtime_v2(runtime)
    if profiles.profile_name(result) == profiles.SYNTHETIC_PROFILE:
        return result
    if (result['model'] != MODEL or result['effort'] != 'high'
            or result['environment']['CLAUDE_CODE_DISABLE_1M_CONTEXT'] != '0'
            or result['budget_guard_usd'] != '90' or result['auth']['subscriptionType'] != 'max'):
        raise ValueError('U4b requires D106 high/Max, D112 model/context and D110 decimal-string budget')
    return result


def _check_pin(value):
    values._closed(value, PIN_KEYS, 'durable binary pin')
    values._sha_text(value['sha256'], 'durable binary sha256')
    if (type(value['path']) is not str or '\x00' in value['path'] or not Path(value['path']).is_absolute()
            or str(Path(value['path'])) != value['path'] or '..' in Path(value['path']).parts
            or any(type(value[key]) is not int or value[key] < 0 for key in ('bytes', 'device', 'inode'))
            or not 0 < value['bytes'] <= MAX_BINARY_BYTES):
        raise ValueError('invalid captured durable binary identity')


def _copy_evidence(value):
    values._closed(value, {'updater_root', 'source', 'copy'}, 'durable copy evidence')
    root = value['updater_root']
    if (type(root) is not str or '\x00' in root or not Path(root).is_absolute() or str(Path(root)) != root
            or '..' in Path(root).parts):
        raise ValueError('updater root must be a captured absolute physical path')
    source, copied = value['source'], value['copy']
    _check_pin(source)
    _check_pin(copied)
    if (not contains(root, source['path']) or contains(root, copied['path'])
            or source['path'] == copied['path']
            or (source['device'], source['inode']) == (copied['device'], copied['inode'])
            or (source['sha256'], source['bytes']) != (copied['sha256'], copied['bytes'])):
        raise ValueError('durable binary must be a distinct same-byte copy outside the updater root')


def prepare_runtime(runtime, *, probe_init_path, native_request_path, updater_source, updater_root,
                    thinking_setting, thinking_basis, observation_probe_path, admission_policy):
    """Bind saved transcript and request; the old probe_init_path keyword is retained.

    That path now requires the complete init-to-terminal JSONL observation,
    never an init-only file. The observation manifest binds both supplied files
    to one authorization and provisional runtime; this is evidence consistency,
    not authentication of human authorization or a historical execution.
    """
    profiles.require_production(runtime)
    return _prepare(runtime, probe_init_path=probe_init_path, native_request_path=native_request_path,
        updater_source=updater_source, updater_root=updater_root, thinking_setting=thinking_setting,
        thinking_basis=thinking_basis, observation_probe_path=observation_probe_path,
        admission_policy=admission_policy)


def prepare_synthetic(runtime, *, probe_init_path, native_request_path, updater_source, updater_root,
                      thinking_setting, thinking_basis, observation_probe_path, admission_policy):
    """Bind only saved synthetic evidence over the exact isolated Python peer."""
    profiles.require_synthetic(runtime)
    return _prepare(runtime, probe_init_path=probe_init_path, native_request_path=native_request_path,
        updater_source=updater_source, updater_root=updater_root, thinking_setting=thinking_setting,
        thinking_basis=thinking_basis, observation_probe_path=observation_probe_path,
        admission_policy=admission_policy)


def _prepare(runtime, *, probe_init_path, native_request_path, updater_source, updater_root,
             thinking_setting, thinking_basis, observation_probe_path, admission_policy):
    result = _profile(runtime)
    from .native_model_aliases import model_aliases, REQUESTED, RETURNED
    pair = (model_aliases(result) if profiles.profile_name(result) == profiles.SYNTHETIC_PROFILE
            else {'requested': REQUESTED, 'returned': RETURNED})
    root = _physical(updater_root, 'updater root')
    if not root.is_dir():
        raise ValueError('updater root must name an existing directory')
    evidence = {'updater_root': str(root), 'source': _binary_pin(updater_source),
                'copy': _binary_pin(result['executable']['path'])}
    _copy_evidence(evidence)
    probe, observed = _saved_probe(probe_init_path, pair)
    request, thinking = _saved_request(native_request_path, pair)
    from .native_u4b_probe_sequence import validate_observation
    from .native_u4b_policy import validate_policy
    values._text(thinking_basis, 'declared thinking basis', 512)
    setting = _thinking(thinking_setting)
    if _canonical(thinking['value']) != _canonical(setting):
        raise ValueError('observed thinking differs from the registered setting')
    observation = validate_observation(observation_probe_path, final_runtime=result,
        transcript_path=probe_init_path, request_path=native_request_path)
    basis = {'kind': KIND, 'version': 3, 'probe': probe, 'request': request, 'observed': observed,
             'model_aliases': pair,
             'thinking': {'declared': setting, 'basis': thinking_basis, 'observed': thinking},
             'durable_copy': evidence, 'observation_probe': observation['pin'],
             'admission': validate_policy(admission_policy)}
    if profiles.profile_name(result) == profiles.SYNTHETIC_PROFILE:
        basis['profile'] = profiles.SYNTHETIC_PROFILE
    result['limits_basis'] = _canonical(basis)
    return validate_prepared_runtime(result)


def validate_prepared_runtime(runtime):
    """Recheck pins and required thinking observation; never infer missing values.

    The thinking field lives inside decoded limits_basis, not a new top-level
    runtime key. Updater-source history is recorded, not reread.
    """
    result = _profile(runtime)
    raw = result['limits_basis']
    if len(raw.encode('utf-8')) > 4096:
        raise ValueError('U4b registered basis exceeds its byte bound')
    basis = values._json(raw)
    profile_keys = {'profile'} if 'profile' in basis else set()
    values._closed(basis, BASIS_KEYS | profile_keys, 'U4b runtime basis')
    if basis['kind'] != KIND or type(basis['version']) is not int or basis['version'] != 3:
        raise ValueError('unknown U4b runtime basis')
    if _canonical(basis) != raw:
        raise ValueError('U4b runtime basis requires exact canonical JSON')
    from .native_model_aliases import model_aliases
    pair = model_aliases(result)
    values._closed(basis['probe'], {'path', 'sha256', 'bytes', 'init_line', 'init_sha256',
                                 'terminal_line', 'terminal_sha256'}, 'saved probe pin')
    values._closed(basis['request'], {'path', 'sha256', 'bytes'}, 'saved request pin')
    values._closed(basis['thinking'], {'declared', 'basis', 'observed'}, 'thinking basis')
    from .native_u4b_probe_sequence import validate_observation
    from .native_u4b_policy import registered_policy
    registered_policy(result)
    values._closed(basis['observation_probe'], {'path', 'sha256', 'bytes'}, 'observation probe pin')
    _copy_evidence(basis['durable_copy'])
    copied = _binary_pin(result['executable']['path'])
    if copied != basis['durable_copy']['copy'] or copied['sha256'] != result['executable']['sha256']:
        raise ValueError('durable binary differs from the registered copy')
    pin, observed = _saved_probe(basis['probe']['path'], pair)
    request, thinking = _saved_request(basis['request']['path'], pair)
    if (_canonical(pin) != _canonical(basis['probe'])
            or _canonical(observed) != _canonical(basis['observed'])
            or _canonical(thinking) != _canonical(basis['thinking']['observed'])):
        raise ValueError('saved probe differs from the registered observations')
    if _canonical(request) != _canonical(basis['request']):
        raise ValueError('saved request differs from the registered observations')
    if (result['limits'] != observed['limits'] or result['model'] != observed['model']
            or result['executable']['init_version'] != observed['init_version']):
        raise ValueError('runtime declarations differ from the saved probe observations')
    values._text(basis['thinking']['basis'], 'declared thinking basis', 512)
    declared = _thinking(basis['thinking']['declared'])
    if _canonical(thinking['value']) != _canonical(declared):
        raise ValueError('observed thinking differs from the registered setting')
    validate_observation(basis['observation_probe']['path'], expected_pin=basis['observation_probe'],
        final_runtime=result, transcript_path=basis['probe']['path'], request_path=basis['request']['path'])
    return result


def is_prepared_runtime(runtime):
    """Recognize the explicit discriminator, without validating the evidence.

    U4b callers must still require validate_prepared_runtime when it is absent.
    A malformed version cannot downgrade a recognized U4b document.
    """
    if type(runtime) is not dict or type(runtime.get('limits_basis')) is not str:
        return False
    raw = runtime['limits_basis']
    if len(raw.encode('utf-8')) > 4096:
        raise ValueError('runtime discriminator exceeds its byte bound')
    try:
        basis = values._json(raw)
    except (ValueError, TypeError):
        if raw.lstrip().startswith('{'):
            raise ValueError('ambiguous runtime JSON basis cannot select a historical route')
        return False
    return type(basis) is dict and basis.get('kind') == KIND
