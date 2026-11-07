#!/usr/bin/env python3
"""Save f719's separate U3-D pure-preparation proposal, 2026-11-07.

Inputs: local donor f719de581 and its parent. Output: one forward diff under
notes; never applies it, edits production source, executes tests or goes online.
The two recovered test modules use scoped v2 controls and the genuine C fixture.
"""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DONOR = 'f719de58104338ce89a364a0284f8e856037b99c'
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
        cwd=ROOT, env=ENV, timeout=30).decode()


def main():
    if git('branch', '--show-current').strip() != 'codex/native-u3d-integration-20261107':
        raise SystemExit('only the assigned U3-D worktree')
    patch = git('diff', DONOR + '^', DONOR, '--',
        'src/data_sheets_schema/native_shared_permissions.py',
        'src/data_sheets_schema/native_shared_registration.py')
    for name in ('test_native_permission_projection_derivation.py', 'test_native_lexical_ancestry.py'):
        path = 'tests/' + name
        source = git('show', DONOR + ':' + path)
        if 'projection' in name:
            source = source.replace('    controls = p.composition.load_controls()\n', '')
            source = source.replace('def test_actual_twenty_five_classifications_keep_independent_view_and_classifier_calls(inputs, monkeypatch):',
                'def test_actual_twenty_five_classifications_keep_independent_view_and_classifier_calls(inputs, monkeypatch, controls):')
            source = source.replace('def test_trace_and_derived_reuse_keeps_all_views_classifiers_and_exact_bytes(inputs, fixture, monkeypatch):',
                'def test_trace_and_derived_reuse_keeps_all_views_classifiers_and_exact_bytes(inputs, fixture, monkeypatch, controls):')
            source += '''\n\n@pytest.fixture\ndef controls():\n    with p.authority.loaded_dependencies(p.authority.dependency_identity()) as loaded:\n        yield loaded\n'''
        patch += 'diff --git a/' + path + ' b/' + path + '\nnew file mode 100644\n'
        patch += ''.join(difflib.unified_diff([], source.splitlines(keepends=True),
            fromfile='/dev/null', tofile='b/' + path))
    output = ROOT / 'notes/native_u3d_permission_preparation_reuse.diff'
    with output.open('x') as stream:
        stream.write(patch)
    raw = output.read_bytes()
    print(json.dumps({'path': str(output), 'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(), 'donor': DONOR,
        'applied': False}, sort_keys=True))


if __name__ == '__main__':
    main()
