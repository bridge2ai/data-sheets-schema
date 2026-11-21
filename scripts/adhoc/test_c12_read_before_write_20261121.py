#!/usr/bin/env python3
"""Archive-only C12 Read-before-Write regression checks, 2026-11-21.

Inputs: M git archive, this branch's two source and three test files, local venv.
Outputs: frozen baseline/fixed trees, source pins, commands, logs and exit codes
under the supplied fresh agent-work directory. Serves the codex197 C12 assignment.
Native calls remain mocked by the tests; no production or pass-bundle writes.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = '724f6b349bae034218a9dd55ca2a41963bebe132'
PYTHON = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python')
SOURCES = ['src/data_sheets_schema/native_permission_probe.py',
           'src/data_sheets_schema/native_shared_permissions.py']
TESTS = ['tests/test_native_permission_probe.py', 'tests/test_native_shared_permissions.py',
         'tests/test_native_model_aliases.py']
TARGETED = TESTS + ['tests/test_native_permission_probe_stop_record.py',
                   'tests/test_native_u4b_probe_sequence.py',
                   'tests/test_native_permission_projection_derivation.py',
                   'tests/test_native_generation_frontdoor.py']
REGRESSIONS = [
    'tests/test_native_permission_probe.py::test_shared_producer_actual_capture_paths_with_mocked_native_events[False]',
    'tests/test_native_permission_probe.py::test_stop_trace_without_parent_stop_has_named_refusal',
    'tests/test_native_shared_permissions.py::test_stop_existing_targets_have_verified_read_preconditions',
]


def isolated_pytest():
    tree = Path(sys.argv[2]).resolve()
    witness_path = Path(sys.argv[3])
    # Ignore the installed editable-project path without changing its pth file.
    # Third-party dependencies stay in the selected venv; all project code is
    # imported from the archive whose PYTHONPATH the parent explicitly set.
    sys.path[:] = [value for value in sys.path
                   if not (Path(value) / 'data_sheets_schema').is_dir()
                   or Path(value).resolve() == tree / 'src']
    sys.path.insert(0, str(tree))
    import data_sheets_schema
    roots = [str(Path(value).resolve()) for value in data_sheets_schema.__path__]
    if set(roots) != {str(tree / 'src/data_sheets_schema')}:
        raise RuntimeError('test project namespace differs from selected archive')
    witness_path.write_text(json.dumps({'python': sys.executable, 'version': sys.version,
                                       'package_roots': roots}, indent=2) + '\n')
    import pytest
    return pytest.main(sys.argv[4:])


def pin(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    archive = out / 'base.tar'
    subprocess.run(['git', '-C', str(ROOT), 'archive', '--output', str(archive), BASE], check=True)
    runs = []
    fixed_head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    labels = ('fixed',) if '--fixed-only' in sys.argv[2:] else ('baseline', 'fixed')
    for label in labels:
        tree = out / label
        tree.mkdir()
        with tarfile.open(archive) as bundle:
            bundle.extractall(tree, filter='data')
        # Fixtures inspect git identity. Give the archive its own metadata and
        # index, borrowing immutable local objects without checking out files.
        common = subprocess.check_output(
            ['git', '-C', str(ROOT), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
            text=True).strip()
        subprocess.run(['git', '-C', str(tree), 'init', '-q'], check=True)
        (tree / '.git/objects/info/alternates').write_text(str(Path(common) / 'objects') + '\n')
        source_head = BASE if label == 'baseline' else fixed_head
        subprocess.run(['git', '-C', str(tree), 'update-ref', 'refs/heads/archive-test', source_head], check=True)
        subprocess.run(['git', '-C', str(tree), 'symbolic-ref', 'HEAD', 'refs/heads/archive-test'], check=True)
        subprocess.run(['git', '-C', str(tree), 'read-tree', source_head], check=True)
        for relative in TESTS + (SOURCES if label == 'fixed' else []):
            shutil.copyfile(ROOT / relative, tree / relative)
        helper = Path('scripts/adhoc') / Path(__file__).name
        (tree / helper).parent.mkdir(exist_ok=True)
        shutil.copyfile(Path(__file__), tree / helper)
        env = dict(os.environ, PYTHONPATH=str(tree / 'src'), PYTHONDONTWRITEBYTECODE='1')
        command = [str(PYTHON), '-P', '-s', '-B', str(tree / helper), '--pytest',
                   str(tree), str(out / (label + '-imports.json')), '-q', '-p', 'no:cacheprovider',
                   '--basetemp', str(out / (label + '-pytest'))]
        command += REGRESSIONS if label == 'baseline' else TARGETED
        started = subprocess.check_output(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'], text=True).strip()
        with (out / (label + '.log')).open('xb') as log:
            run = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
        row = {'label': label, 'source_commit': source_head, 'cwd': str(tree), 'command': command,
               'environment': {'PYTHONPATH': env['PYTHONPATH'], 'PYTHONDONTWRITEBYTECODE': '1'},
               'started_utc': started, 'exit_code': run.returncode,
               'input_pins': {relative: pin(tree / relative) for relative in SOURCES + TESTS}}
        runs.append(row)
        (out / 'results.json').write_text(json.dumps({'base': BASE, 'runs': runs}, indent=2) + '\n')
        print(label + ' exit=' + str(run.returncode), flush=True)
        print((out / (label + '.log')).read_text()[-6000:], flush=True)
        if label == 'fixed' and run.returncode:
            return run.returncode
    return 0 if labels == ('fixed',) or runs[0]['exit_code'] == 1 else 1


if __name__ == '__main__':
    raise SystemExit(isolated_pytest() if sys.argv[1] == '--pytest' else main())
