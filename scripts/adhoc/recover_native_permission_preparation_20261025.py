#!/usr/bin/env python3
"""Recover default-only permission preparation, 2026-10-25 (#4354).

Inputs: cached 13d4c6077, 87dfe8208, 6f016c25f and db0573d96 tests.
Outputs: scoped permission/registration patches and a SHA256 patch manifest.
Owner reconstruction, stream coordination and capture changes are excluded.
No runtime, provider, network, GitHub or push operation occurs.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PERMISSIONS = 'src/data_sheets_schema/native_shared_permissions.py'
REGISTRATION = 'src/data_sheets_schema/native_shared_registration.py'
PATCHES = (
    ('13d4c6077', [PERMISSIONS], ['_view_factory', '_view', 'projection']),
    ('87dfe8208', [PERMISSIONS], ['_classification', '_classify_view', '_trace_body', '_derived_controls']),
    ('6f016c25f', [PERMISSIONS, REGISTRATION], ['_verify isolation roots', '_paths lexical ancestry']),
)
TESTS = (
    'tests/test_native_permission_projection_derivation.py',
    'tests/test_native_lexical_ancestry.py',
)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    rows = []
    for commit, paths, functions in PATCHES:
        patch = git('diff', commit + '^', commit, '--', *paths)
        subprocess.run(['git', 'apply', '--check'], input=patch, cwd=ROOT, check=True)
        subprocess.run(['git', 'apply'], input=patch, cwd=ROOT, check=True)
        rows.append({'source_commit': git('rev-parse', commit).decode().strip(),
            'paths': paths, 'selected_functions': functions,
            'patch_sha256': hashlib.sha256(patch).hexdigest()})
    for path in TESTS:
        raw = git('show', 'db0573d96:' + path)
        (ROOT / path).write_bytes(raw)
        rows.append({'source_commit': git('rev-parse', 'db0573d96').decode().strip(),
            'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
    output = ROOT / 'notes/native_n2_permission_preparation_2026-10-25.json'
    output.write_text(json.dumps({'scope': 'default-only pure preparation; no owner hooks',
        'omitted': ['13d registration/capture changes', '87 stream coordination changes'],
        'rows': rows}, sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
    main()
