#!/usr/bin/env python3
"""Apply diagnostic U0 T2 exact catalog initialization, 2026-11-06.

Input: a fresh clean treatment worktree descended from T1 2747e86; adjacent
initialization payload. Output: three source changes plus exact pin/diff manifest.
No import-timing change, T1 change, recorder, provider, network, commit or push.
"""
from __future__ import annotations
import difflib
import hashlib
import importlib.util
from pathlib import Path

BASE = '2747e86c3f0521c1ef5c455d9be82428e4ca5be7'
GUARD = 'src/data_sheets_schema/native_catalog_reuse.py'
RECEIPTS = 'src/data_sheets_schema/native_shared_receipts.py'
ADDED = 'src/data_sheets_schema/native_catalog_initialization.py'
TOOL = Path(__file__).resolve().parents[2]
PAYLOAD = Path(__file__).with_name('native_u0_catalog_initialization_payload_20261106.py')
_spec = importlib.util.spec_from_file_location('u0_t1_applier',
    Path(__file__).with_name('native_u0_parser_event_treatment_20261106.py'))
_t1 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_t1)
git, replace_once = _t1.git, _t1.replace_once


def build_changes(guard, receipts, payload=None):
    guard = replace_once(guard, b'from . import audit_omissions as omissions\n',
        b'from . import audit_omissions as omissions\nfrom . import native_catalog_initialization as initialization\n')
    guard = replace_once(guard, b"'extended_str', 'extended_int', 'extended_float'})",
        b"'extended_str', 'extended_int', 'extended_float', 'Mark'})")
    guard = replace_once(guard,
        b'for module in _YAML_DEFINITIONS for name, cls in sorted(vars(module).items())\n',
        b'for module in _YAML_DEFINITIONS for name, cls in sorted(\n'
        b'                         (dict(vars(module), Mark=initialization.ORIGINAL_MARK)\n'
        b'                          if module is yaml.error else vars(module)).items())\n')
    guard = replace_once(guard,
        b'aliases = tuple((module.__name__, tuple((name, vars(module)[name]) for name in sorted(_YAML_NAMES)\n',
        b'aliases = tuple((module.__name__, tuple((name, initialization.ORIGINAL_MARK\n'
        b"                                            if module is yaml.error and name == 'Mark' else vars(module)[name])\n"
        b'                                            for name in sorted(_YAML_NAMES)\n')
    guard = replace_once(guard, b'    _STATE = _state()\n',
        b'    initialization.phase()\n    _STATE = _state()\n')
    guard = replace_once(guard,
        b'        if _FUNCTIONS.ready:\n            actual = _state()\n'
        b'            if actual == _STATE or actual == _INITIALIZED_STATE:\n                return _READY\n',
        b'        if _FUNCTIONS.ready:\n            marker = initialization.marker()\n'
        b'            actual = _state()\n'
        b'            if actual == _STATE or actual == _INITIALIZED_STATE:\n'
        b'                if initialization.marker() is marker:\n                    return marker\n')
    receipts = replace_once(receipts, b'        self._entry = None\n',
        b'        self._entry = None\n        self._entry_marker = None\n')
    receipts = replace_once(receipts,
        b'        key = _catalog_key(selection, snapshot)\n        with self._lock:\n'
        b'            entry = self._entry if self._entry is not None and self._entry[0] == key else None\n',
        b'        key = _catalog_key(selection, snapshot)\n'
        b'        current_marker = catalog_reuse.runtime_token()\n'
        b'        with self._lock:\n'
        b'            entry = (self._entry if current_marker is not None\n'
        b'                     and self._entry_marker is current_marker\n'
        b'                     and self._entry is not None and self._entry[0] == key else None)\n')
    receipts = replace_once(receipts, b'                    self._typed_marker = marker\n',
        b'                    self._typed_marker = marker\n                    self._entry_marker = marker\n')
    receipts = replace_once(receipts,
        b"        return entry[2], contract.strict_json(entry[1], 'captured schema catalog', omissions.MAX_SCHEMA_BYTES)\n",
        b"        result = contract.strict_json(entry[1], 'captured schema catalog', omissions.MAX_SCHEMA_BYTES)\n"
        b'        if catalog_reuse.runtime_token() is not current_marker:\n'
        b'            # A changing dependency cannot authorize a prior successful catalog.\n'
        b'            return self._fresh_schema_data(selection, snapshot, key)\n'
        b'        return entry[2], result\n')
    start = receipts.index(b'        if entry is None:\n', receipts.index(b'    def schema_data('))
    end = receipts.index(b"        result = contract.strict_json(entry[1]", start)
    original_cold = receipts[start:end]
    # Move exactly the previous cold path into a bounded fallback; do not retry
    # recursively if hostile code keeps changing initialization state.
    cold_body = b'\n'.join(line[4:] if line.startswith(b'    ') else line
                           for line in original_cold.split(b'\n')[1:])
    receipts = replace_once(receipts, original_cold,
        b'        if entry is None:\n            return self._fresh_schema_data(selection, snapshot, key)\n')
    receipts = replace_once(receipts, b'    def _typed_catalog(self, selection, path, snapshot):\n',
        b'    def _fresh_schema_data(self, selection, snapshot, key):\n' + cold_body + b'\n'
        b'    def _typed_catalog(self, selection, path, snapshot):\n')
    return {GUARD: guard, RECEIPTS: receipts, ADDED: PAYLOAD.read_bytes() if payload is None else payload}


def apply_treatment(root):
    root = Path(root)
    if (root != root.resolve(strict=True) or not root.is_relative_to(_t1.EXEC_ROOT)
            or root == TOOL or 'treatment' not in root.name or not root.name.startswith('codex-native-u0-')):
        raise ValueError('requires a new canonical native-u0 treatment worktree')
    branch = git(root, 'symbolic-ref', '--short', 'HEAD').decode().strip()
    if not branch.startswith('codex/native-u0-') or 'treatment' not in branch:
        raise ValueError('requires a dedicated native-u0 treatment branch')
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('treatment tree must be clean')
    git(root, 'merge-base', '--is-ancestor', BASE, 'HEAD')
    originals = {}
    for name in (GUARD, RECEIPTS):
        path = root / name
        if not path.is_file() or path.resolve(strict=True) != path:
            raise ValueError('source must be a canonical regular file')
        originals[name] = path.read_bytes()
        if originals[name] != git(root, 'show', BASE + ':' + name):
            raise ValueError('T1 source preimage differs: ' + name)
    if (root / ADDED).exists() or (root / ADDED).is_symlink():
        raise ValueError('T2 helper already exists')
    changes = build_changes(originals[GUARD], originals[RECEIPTS])
    manifest = {'base': BASE, 'control_head': git(root, 'rev-parse', 'HEAD').decode().strip(),
        'root': str(root), 'branch': branch, 'changed_paths': sorted(changes), 'files': [],
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'payload_sha256': hashlib.sha256(changes[ADDED]).hexdigest(),
        'treatment': 'exact known loader states with distinct markers and one fresh catalog per transition'}
    for name, raw in changes.items():
        before = originals.get(name, b'')
        manifest['files'].append({'path': name, 'before_sha256': hashlib.sha256(before).hexdigest() if before else None,
            'after_sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
            'diff': ''.join(difflib.unified_diff(before.decode().splitlines(True), raw.decode().splitlines(True),
                                              fromfile='a/'+name, tofile='b/'+name))})
    for name, raw in changes.items():
        (root / name).write_bytes(raw)
        if (root / name).read_bytes() != raw:
            raise OSError('T2 write verification failed')
    return manifest
