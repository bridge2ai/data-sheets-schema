#!/usr/bin/env python3
"""Apply one source-bound native parser-event treatment; U0, 2026-11-06.

Inputs: a NEW clean diagnostic treatment worktree descended from frozen 01969cbed;
the adjacent saved payload. Outputs: three source files and a returned pin/diff
manifest. No commits, network, execution of the recorder, or existing-run writes.
M7 comparison: 5c952d210 reuses one checked stream within an admission; this
diagnostic additionally reuses immutable events across equal-byte native reads.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess


BASE = '01969cbed8eed93f420c640c1f1c306e5f58b033'
EXEC_ROOT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
TOOL_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = Path(__file__).with_name('native_u0_parser_event_reuse_payload_20261106.py')
AUDIT = 'src/data_sheets_schema/audit_omissions.py'
SNAPSHOT = 'src/data_sheets_schema/schema_snapshot.py'
ADDED = 'src/data_sheets_schema/native_schema_event_reuse.py'


def git(root, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(['git', '--no-optional-locks', '--no-replace-objects',
        '-C', str(root), *args], env=env)


def replace_once(raw, old, new):
    if raw.count(old) != 1:
        raise ValueError('expected source seam is not unique')
    return raw.replace(old, new, 1)


def build_changes(audit, snapshot, payload=None):
    """Pure transform for review/tests; callers verify the frozen preimages."""
    audit = replace_once(audit,
        b'          _schema_events: bool = False):',
        b'          _schema_events: bool = False, _native_events=None):')
    audit = replace_once(audit,
        b'        text = raw.decode("utf-8")\n        if _schema_events and not json_only:',
        b'        text = raw.decode("utf-8")\n        native_candidate = None\n'
        b'        if _schema_events and not json_only:')
    audit = replace_once(audit,
        b'        else:\n            value = _load_yaml(text)\n'
        b'        _validate_json(value, max_nodes=MAX_NODES, max_depth=MAX_DEPTH)',
        b'        elif _native_events is not None:\n'
        b'            if _native_events is not True:\n'
        b'                raise ValueError("native parser replay must be explicit true")\n'
        b'            from .native_schema_event_reuse import load_native\n'
        b'            value, native_candidate = load_native(text, limit=limit)\n'
        b'        else:\n            value = _load_yaml(text)\n'
        b'        _validate_json(value, max_nodes=MAX_NODES, max_depth=MAX_DEPTH)\n'
        b'        if native_candidate is not None and isinstance(value, dict):\n'
        b'            from .native_schema_event_reuse import retain_native\n'
        b'            retain_native(native_candidate, limit=limit)')
    snapshot = replace_once(snapshot,
        b"doc = _mapping(raw, 'native schema', limit=member_bytes)",
        b"doc = _mapping(raw, 'native schema', limit=member_bytes, _native_events=True)")
    return {AUDIT: audit, SNAPSHOT: snapshot,
            ADDED: PAYLOAD.read_bytes() if payload is None else payload}


def apply_treatment(root: Path):
    """Apply once to a new clean treatment branch, refusing other preimages."""
    root = Path(root)
    if (root != root.resolve(strict=True) or not root.is_relative_to(EXEC_ROOT)
            or root == TOOL_ROOT or root == EXEC_ROOT
            or 'treatment' not in root.name or not root.name.startswith('codex-native-u0-')):
        raise ValueError('requires a new canonical codex-native-u0-*treatment* worktree')
    branch = git(root, 'symbolic-ref', '--short', 'HEAD').decode().strip()
    if not branch.startswith('codex/native-u0-') or 'treatment' not in branch:
        raise ValueError('requires a dedicated native-u0 treatment branch')
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('treatment worktree must be clean before its one-time patch')
    git(root, 'merge-base', '--is-ancestor', BASE, 'HEAD')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    original = {}
    for name in (AUDIT, SNAPSHOT):
        path = root / name
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError('source seam is not a canonical regular file')
        original[name] = path.read_bytes()
        if original[name] != git(root, 'show', BASE + ':' + name):
            raise ValueError('source preimage differs from frozen 01969cbed: ' + name)
    if (root / ADDED).exists() or (root / ADDED).is_symlink():
        raise ValueError('treatment module already exists')
    changes = build_changes(original[AUDIT], original[SNAPSHOT])
    manifest = {'base': BASE, 'control_head': head, 'branch': branch, 'root': str(root),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'payload_sha256': hashlib.sha256(changes[ADDED]).hexdigest(), 'files': [],
        'changed_paths': sorted(changes),
        'm7_comparison': '5c952d210 retains a single checked parse; this treatment adds bounded cross-call native-only reuse',
        'limits': {'entries': 4, 'events_per_entry': 131072, 'total_events': 262144,
                   'event_characters': 8000000, 'payload_bytes': 40000000, 'input_bytes': 8000000}}
    for name, raw in changes.items():
        before = original.get(name, b'')
        manifest['files'].append({'path': name,
            'before_sha256': hashlib.sha256(before).hexdigest() if before else None,
            'after_sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
            'diff': ''.join(difflib.unified_diff(before.decode().splitlines(True),
                raw.decode().splitlines(True), fromfile='a/' + name, tofile='b/' + name))})
    # All refusal checks complete before the first write. No branch/ref changes.
    for name, raw in changes.items():
        with (root / name).open('xb' if name == ADDED else 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if (root / name).read_bytes() != raw:
            raise OSError('treatment write verification failed: ' + name)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    if args.manifest.exists() or args.manifest.is_symlink():
        parser.error('manifest must be a new file outside the worktree')
    if args.manifest.resolve().is_relative_to(args.tree.resolve()):
        parser.error('manifest must be outside the worktree')
    result = apply_treatment(args.tree)
    with args.manifest.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'manifest': str(args.manifest), 'files': len(result['files'])}))


if __name__ == '__main__':
    main()
