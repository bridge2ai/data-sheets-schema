#!/usr/bin/env python3
"""Re-pin the D76 native helper closure after its source commit (#5213).

Inputs: local full Git commit containing the reviewed registration-builder
changes; the existing native source manifest and two source constants.
Outputs: optional three-file closure update and a JSON digest report on stdout.
Date: 2026-10-31. Offline only; verifies every module against the selected commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'src/data_sheets_schema/native_controller_sources_v1.json'
CONTROLLER = 'src/data_sheets_schema/native_attribution_controller.py'
SUPERVISOR = 'src/data_sheets_schema/native_supervisor_authority.py'
DIRECT = {
    'prepare_direct': 'notes/claudecode_direct/prepare_direct.py',
    'run_direct_canary': 'notes/claudecode_direct/run_direct_canary.py',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def at_commit(commit, path):
    return subprocess.check_output(['git', '-c', 'protocol.allow=never', 'show', f'{commit}:{path}'], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.source_commit):
        parser.error('--source-commit must be a full lowercase commit SHA')
    subprocess.run(['git', '-c', 'protocol.allow=never', 'cat-file', '-e', args.source_commit + '^{commit}'],
                   cwd=ROOT, check=True)
    before = {name: (ROOT / name).read_bytes() for name in (MANIFEST, CONTROLLER, SUPERVISOR)}
    manifest = json.loads(before[MANIFEST])
    original_manifest_sha = sha(before[MANIFEST])
    verified = {}
    for name, pin in manifest['modules'].items():
        local = (ROOT / pin['path']).read_bytes()
        committed = at_commit(args.source_commit, pin['path'])
        if local != committed:
            raise ValueError(f'current module differs from selected source commit: {pin["path"]}')
        digest = sha(committed)
        if name != 'prepare_registration' and pin['sha256'] != digest:
            raise ValueError(f'unrelated frozen module changed: {name}')
        pin['sha256'] = digest
        verified[pin['path']] = digest
    # This is a snapshot of every selected module, not a claim that the
    # unchanged members were first introduced in this commit.
    manifest['source_commit'] = args.source_commit
    manifest_raw = (json.dumps(manifest, indent=2) + '\n').encode()
    controller = before[CONTROLLER].decode()
    old = f"SOURCES_SHA256 = '{original_manifest_sha}'"
    if controller.count(old) != 1:
        raise ValueError('controller does not pin the exact existing manifest once')
    controller = controller.replace(old, f"SOURCES_SHA256 = '{sha(manifest_raw)}'")
    supervisor = before[SUPERVISOR].decode()
    for name, path in DIRECT.items():
        local = (ROOT / path).read_bytes()
        committed = at_commit(args.source_commit, path)
        if local != committed:
            raise ValueError(f'direct helper differs from source commit: {path}')
        digest = sha(committed)
        pattern = rf"('{name}': \{{'path': '{re.escape(path)}',\s*'sha256': ')[0-9a-f]{{64}}('\}})"
        supervisor, count = re.subn(pattern, lambda m: m[1] + digest + m[2], supervisor)
        if count != 1:
            raise ValueError(f'expected exactly one additional helper pin: {name}')
        verified[path] = digest
    after = {MANIFEST: manifest_raw, CONTROLLER: controller.encode(), SUPERVISOR: supervisor.encode()}
    if args.apply:
        # All input, commit and closure checks finish before the first write.
        for name, raw in after.items():
            (ROOT / name).write_bytes(raw)
        for name, raw in after.items():
            if (ROOT / name).read_bytes() != raw:
                raise ValueError(f'closure update was not persisted: {name}')
    print(json.dumps({'source_commit': args.source_commit, 'applied': args.apply,
        'verified_modules': verified,
        'files': {name: {'before_sha256': sha(before[name]), 'after_sha256': sha(raw)}
                  for name, raw in after.items()}}, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
