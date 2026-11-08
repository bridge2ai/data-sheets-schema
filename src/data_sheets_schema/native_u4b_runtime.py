"""Offline D106/D112 runtime evidence, 2026-11-08 (#4354).

Reads explicit saved probe and inert-or-real binary bytes; never executes or
copies a binary, discovers account state, or creates launch authority. The
versioned evidence lives in the existing limits_basis string, preserving the
historical closed runtime schema. Source-copy evidence is a local observation,
not authenticated history; a later updater change does not invalidate the copy.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from . import native_shared_runtime_values as values
from .native_shared_evidence import read_regular

KIND = 'd4d_native_u4b_runtime_basis'
MODEL = 'claude-opus-5[1m]'
MAX_PROBE_BYTES = 4_000_000
MAX_BINARY_BYTES = 1_073_741_824
BASIS_KEYS = {'kind', 'version', 'probe', 'observed', 'thinking', 'durable_copy'}
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


def _saved_init(path):
    member = read_regular(path, 'u4b_probe', max_bytes=MAX_PROBE_BYTES)
    raw = member.captured.raw
    rows = raw.splitlines()
    if not rows or len(rows) > 10_000:
        raise ValueError('saved probe requires bounded JSONL evidence')
    found = []
    for index, row in enumerate(rows, 1):
        if not row.strip():
            continue
        value = values._json(row)
        if type(value) is not dict:
            raise ValueError('saved probe requires JSON object lines')
        if value.get('type') == 'system' and value.get('subtype') == 'init':
            found.append((index, row, value))
    if len(found) != 1:
        raise ValueError('saved probe requires exactly one init line')
    line, row, init = found[0]
    limits = init.get('limits')
    values._closed(limits, {'contextWindow', 'maxOutputTokens'}, 'saved init limits')
    if (any(type(value) is not int or value <= 0 for value in limits.values())
            or limits['maxOutputTokens'] > limits['contextWindow']):
        raise ValueError('saved init limits must be explicit positive integer counts')
    if init.get('model') != MODEL:
        raise ValueError('saved init does not name the D112 model')
    values._text(init.get('claude_code_version'), 'saved init version')
    pin = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
           'init_line': line, 'init_sha256': hashlib.sha256(row).hexdigest()}
    observation = {'model': init['model'], 'limits': dict(limits),
                   'init_version': init['claude_code_version']}
    # Do not infer a thinking setting from effort, model or an account config.
    # Recognize one explicit field; ambiguous aliases cannot become "missing".
    if any(name in init for name in ('thinkingEnabled', 'thinking_enabled', 'alwaysThinkingEnabled')):
        raise ValueError('unsupported saved init thinking field; explicit adaptation required')
    thinking = {'state': 'not_emitted', 'field': None, 'value': None}
    if 'thinking' in init:
        thinking = {'state': 'observed', 'field': 'thinking', 'value': _thinking(init['thinking'])}
    return pin, observation, thinking


def _thinking(value):
    if value is None or type(value) not in (bool, str, dict):
        raise ValueError('thinking setting requires an explicit boolean, text or JSON object')
    encoded = _canonical(value)
    if len(encoded) > 1024 or (type(value) is str and not value.strip()) or value == {}:
        raise ValueError('thinking setting must be nonempty bounded JSON')
    return values._json(encoded)


def _profile(runtime):
    result = values.validate_runtime(runtime)
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
    if (not Path(source['path']).is_relative_to(root) or Path(copied['path']).is_relative_to(root)
            or source['path'] == copied['path']
            or (source['device'], source['inode']) == (copied['device'], copied['inode'])
            or (source['sha256'], source['bytes']) != (copied['sha256'], copied['bytes'])):
        raise ValueError('durable binary must be a distinct same-byte copy outside the updater root')


def prepare_runtime(runtime, *, probe_init_path, updater_source, updater_root,
                    thinking_setting, thinking_basis):
    """Bind existing local evidence, with no copy, process or authority creation."""
    result = _profile(runtime)
    root = _physical(updater_root, 'updater root')
    if not root.is_dir():
        raise ValueError('updater root must name an existing directory')
    evidence = {'updater_root': str(root), 'source': _binary_pin(updater_source),
                'copy': _binary_pin(result['executable']['path'])}
    _copy_evidence(evidence)
    probe, observed, thinking = _saved_init(probe_init_path)
    values._text(thinking_basis, 'declared thinking basis', 512)
    setting = _thinking(thinking_setting)
    if thinking['state'] == 'observed' and _canonical(thinking['value']) != _canonical(setting):
        raise ValueError('observed thinking differs from the registered setting')
    basis = {'kind': KIND, 'version': 1, 'probe': probe, 'observed': observed,
             'thinking': {'declared': setting, 'basis': thinking_basis, 'observed': thinking},
             'durable_copy': evidence}
    result['limits_basis'] = _canonical(basis)
    return validate_prepared_runtime(result)


def validate_prepared_runtime(runtime):
    """Recheck pinned evidence; updater-source history is recorded, not reread."""
    result = _profile(runtime)
    raw = result['limits_basis']
    if len(raw.encode('utf-8')) > 4096:
        raise ValueError('U4b registered basis exceeds its byte bound')
    basis = values._json(raw)
    values._closed(basis, BASIS_KEYS, 'U4b runtime basis')
    if basis['kind'] != KIND or type(basis['version']) is not int or basis['version'] != 1:
        raise ValueError('unknown U4b runtime basis')
    if _canonical(basis) != raw:
        raise ValueError('U4b runtime basis requires exact canonical JSON')
    values._closed(basis['probe'], {'path', 'sha256', 'bytes', 'init_line', 'init_sha256'}, 'saved probe pin')
    values._closed(basis['thinking'], {'declared', 'basis', 'observed'}, 'thinking basis')
    _copy_evidence(basis['durable_copy'])
    copied = _binary_pin(result['executable']['path'])
    if copied != basis['durable_copy']['copy'] or copied['sha256'] != result['executable']['sha256']:
        raise ValueError('durable binary differs from the registered copy')
    pin, observed, thinking = _saved_init(basis['probe']['path'])
    if (_canonical(pin) != _canonical(basis['probe'])
            or _canonical(observed) != _canonical(basis['observed'])
            or _canonical(thinking) != _canonical(basis['thinking']['observed'])):
        raise ValueError('saved probe differs from the registered observations')
    if (result['limits'] != observed['limits'] or result['model'] != observed['model']
            or result['executable']['init_version'] != observed['init_version']):
        raise ValueError('runtime declarations differ from the saved init observations')
    values._text(basis['thinking']['basis'], 'declared thinking basis', 512)
    declared = _thinking(basis['thinking']['declared'])
    if thinking['state'] == 'observed' and _canonical(thinking['value']) != _canonical(declared):
        raise ValueError('observed thinking differs from the registered setting')
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
