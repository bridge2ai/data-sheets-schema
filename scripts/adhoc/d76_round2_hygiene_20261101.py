#!/usr/bin/env python3
"""Classify only CI-permitted, newly generated notes bytecode for PR #5213 round 2.

Inputs: frozen tracked-source snapshot, fresh notes tree and raw Git status.
Output: explicit hygiene evidence; no deletion, imports of cached code or writes.
2026-11-01. Ordinary tests retain the existing strict unchanged-tree rule.
"""
import hashlib
import importlib.util
import marshal
import os
from pathlib import Path
import re
import stat
import sys
from collections import defaultdict


MATCHED = 'notes/matched_cborg_2026-09-13'
CI_PATHS = ('src', MATCHED, MATCHED + '/native_controls')
NOTES_TARGETS = {
    'offline-canary': (
        MATCHED + '/native_controls/test_native_command_policy.py',
        MATCHED + '/native_controls/test_native_launch.py',
        'notes/claudecode_direct/test_direct_arm.py'),
    'offline-audit': tuple(MATCHED + '/audit_controls/' + name for name in (
        'test_source_metadata_upgrade.py', 'test_response_buffer_selection.py',
        'test_budget_amendment_registration.py', 'test_upstream_timeout.py')),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def notes_listing(root):
    paths = set()
    for directory, directories, files in os.walk(root / 'notes', followlinks=False):
        paths.update(str((Path(directory) / name).relative_to(root)) for name in directories + files)
    return paths


def validate_targets(job, targets):
    """Allow exact requested files or individual canaries, never a mixed session."""
    allowed = NOTES_TARGETS[job]
    if not targets or any(value.split('::', 1)[0] not in allowed for value in targets):
        raise ValueError('notes CI mode requires only its explicit approved notes targets')


def regular_chain(root, path):
    relative = path.relative_to(root)
    if '..' in relative.parts:
        raise ValueError('parent traversal')
    current = root
    for component in relative.parts:
        current = current / component
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError('symlink in bytecode/source path')
        if current != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError('non-directory bytecode/source ancestor')
    return path.lstat()


def bytecode_record(root, relative, snapshot):
    if not isinstance(relative, str) or relative.startswith('/') or '..' in Path(relative).parts:
        raise ValueError('foreign or traversing bytecode path')
    path = root / relative
    if not relative.startswith('notes/') or path.parent.name != '__pycache__':
        raise ValueError('not notes/__pycache__ bytecode')
    pattern = r'(.+)\.' + re.escape(sys.implementation.cache_tag) + r'(?:\.opt-([12]))?\.pyc'
    match = re.fullmatch(pattern, path.name)
    if not match or not stat.S_ISREG(regular_chain(root, path).st_mode):
        raise ValueError('not regular current-interpreter bytecode')
    source = path.parent.parent / (match.group(1) + '.py')
    source_relative = str(source.relative_to(root))
    entry = snapshot['entries'].get(source_relative, {})
    if entry.get('mode') not in ('100644', '100755'):
        raise ValueError('bytecode source is not a tracked regular Python file')
    source_stat = regular_chain(root, source)
    if not stat.S_ISREG(source_stat.st_mode):
        raise ValueError('source is not regular')
    source_raw = source.read_bytes()
    if sha(source_raw) != entry.get('sha256'):
        raise ValueError('tracked source changed')
    raw = path.read_bytes()
    if len(raw) < 17 or raw[:4] != importlib.util.MAGIC_NUMBER:
        raise ValueError('invalid bytecode magic/header')
    flags = int.from_bytes(raw[4:8], 'little')
    if flags == 0:
        expected = ((int(source_stat.st_mtime) & 0xffffffff).to_bytes(4, 'little')
                    + (len(source_raw) & 0xffffffff).to_bytes(4, 'little'))
        kind = 'timestamp'
    elif flags in (1, 3):
        expected = importlib.util.source_hash(source_raw)
        kind = 'checked_hash' if flags == 3 else 'unchecked_hash'
    else:
        raise ValueError('unknown bytecode flags')
    if raw[8:16] != expected:
        raise ValueError('bytecode header does not match tracked source')
    # Compile, never execute or unmarshal, the already tracked source. Matching
    # only a header would let arbitrary bytecode claim an unchanged source.
    optimize = int(match.group(2) or 0)
    # Keep the code object referenced as py_compile/importlib do. marshal's
    # reference-table encoding differs for an unreferenced inline temporary.
    compiled = compile(source_raw, str(source), 'exec', dont_inherit=True, optimize=optimize)
    expected_code = marshal.dumps(compiled)
    if raw[16:] != expected_code:
        raise ValueError('bytecode payload is not compiled tracked source')
    return {'path': relative, 'sha256': sha(raw), 'bytes': len(raw),
            'source': source_relative, 'source_sha256': sha(source_raw),
            'header_kind': kind, 'flags': flags, 'optimization': optimize,
            'header_and_compiled_payload_verified': True}


def classify(root, snapshot, before_listing, before_status, after_status):
    """Keep raw differences and accept only new source-derived notes caches."""
    after_listing = notes_listing(root)
    added = sorted(after_listing - set(before_listing))
    removed = sorted(set(before_listing) - after_listing)
    reasons, records = [], []
    if before_status:
        reasons.append('notes CI checkout did not start with empty global ignored/untracked status')
    if removed:
        reasons.append('paths disappeared from notes')
    permitted_directories = set()
    for relative in added:
        path = root / relative
        try:
            info = regular_chain(root, path)
            if stat.S_ISDIR(info.st_mode):
                if path.name != '__pycache__':
                    raise ValueError('new non-cache directory')
                permitted_directories.add(relative)
            else:
                records.append(bytecode_record(root, relative, snapshot))
        except (ValueError, OSError) as exc:
            reasons.append(relative + ': ' + str(exc))
    allowed = {row['path'] for row in records}
    for directory in permitted_directories:
        if not any(str(Path(value).parent) == directory for value in allowed):
            reasons.append(directory + ': empty or invalid cache directory')
    # -z is essential: literal tabs/newlines cannot disguise paths as other rows.
    status_covered = set()
    for row in after_status.split('\0'):
        if not row:
            continue
        if row[:3] != '!! ':
            reasons.append('non-ignored Git status entry: ' + repr(row))
            continue
        value = row[3:]
        if value in allowed:
            status_covered.add(value)
        elif value.rstrip('/') in permitted_directories:
            status_covered.update(path for path in allowed if str(Path(path).parent) == value.rstrip('/'))
        else:
            reasons.append('unclassified Git status entry: ' + repr(row))
    if status_covered != allowed:
        reasons.append('physical new bytecode differs from raw Git status coverage')
    return {'hygiene_mode': 'notes_ci_new_tracked_source_bytecode',
            'before': before_status, 'after': after_status,
            'unchanged': before_status == after_status and not added and not removed,
            'added_paths': added, 'removed_paths': removed,
            'allowed_new_bytecode': records, 'refusals': reasons, 'passed': not reasons,
            'policy': 'CI #3865 exception only; caches retained, never deleted; tracked source must remain exact'}


def expected_notes_imports(root, snapshot):
    """Derive bare modules and package/namespace prefixes from frozen source."""
    files, packages = defaultdict(set), defaultdict(set)
    for base in (*CI_PATHS[1:], 'notes/claudecode_direct'):
        for relative, entry in snapshot['entries'].items():
            if not relative.startswith(base + '/') or not relative.endswith('.py') or entry.get('mode') not in ('100644', '100755'):
                continue
            parts = Path(relative).relative_to(base).with_suffix('').parts
            if not all(part.isidentifier() for part in parts):
                continue
            for length in range(1, len(parts)):
                packages['.'.join(parts[:length])].add(root / base / Path(*parts[:length]))
            name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
            if name:
                files[name].add(root / relative)
    return files, packages


def notes_origins(root, snapshot):
    """Attest tracked bare/package imports, including namespace __path__ entries."""
    expected_files, expected_packages = expected_notes_imports(root, snapshot)
    package_roots = {name.split('.', 1)[0] for name in expected_packages}
    found = {}
    for name, module in tuple(sys.modules.items()):
        value = getattr(module, '__file__', None)
        known = name in expected_files or name in expected_packages or name.split('.', 1)[0] in package_roots
        package_paths = list(getattr(module, '__path__', ()))
        if not known and (not value or '/notes/' not in str(value)):
            continue
        paths = [Path(path).resolve(strict=True) for path in package_paths]
        if known and (any(path not in expected_packages.get(name, set()) for path in paths)
                      or (not value and not paths)):
            raise ValueError('foreign or missing notes package path: ' + name)
        if value:
            path = Path(value).resolve(strict=True)
            local = path.is_relative_to(root / 'notes')
            if known and (not local or path not in expected_files.get(name, set())):
                raise ValueError('foreign notes module: ' + name)
            if not local:
                continue
            relative = str(path.relative_to(root))
            if sha(path.read_bytes()) != snapshot['entries'].get(relative, {}).get('sha256'):
                raise ValueError('notes module differs from frozen source: ' + name)
            found[name] = {'path': str(path), 'sha256': sha(path.read_bytes()),
                           'package_paths': [str(item) for item in paths]}
        else:
            found[name] = {'path': None, 'package_paths': [str(item) for item in paths],
                           'namespace_verified_against_tracked_source': True}
    return found
