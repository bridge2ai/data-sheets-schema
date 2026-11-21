#!/usr/bin/env python3
"""Run PR6302 round2 mocked tests on a committed archive, 2026-11-21.

Inputs: this feature branch HEAD, selected local venv, output path and pytest args.
Outputs: retained archive, independent Git metadata, logs, import witness and pins.
No native binary or production source is executed by this helper.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python')
BASE = '5581d57f2476ac1d02270b39e3e4234f0403cff6'
TARGETED = ['tests/test_native_permission_probe.py', 'tests/test_native_shared_permissions.py',
            'tests/test_native_permission_source_read_variants.py', 'tests/test_native_model_aliases.py',
            'tests/test_native_permission_projection_derivation.py',
            'tests/test_native_permission_probe_stop_record.py', 'tests/test_native_u4b_probe_sequence.py',
            'tests/test_native_generation_frontdoor.py', 'tests/test_native_stage_root_grant.py',
            'tests/test_native_stage_root_diagnostic.py', 'tests/test_native_stage_root_boundary.py',
            'tests/test_native_permission_wire_profile.py', 'tests/test_native_shared_permission_protocol.py',
            'tests/test_native_shared_permission_split.py', 'tests/test_native_shared_registration.py',
            'tests/test_native_h1_scanner_authority.py']


class SourceProofFailureCapture:
    """Retain a failing Git proof without modifying the verifier or its inputs."""
    def __init__(self, directory):
        self.directory, self.captured = directory, False

    def pytest_exception_interact(self, node, call, report):
        if self.captured or call.excinfo is None:
            return
        error = call.excinfo.value
        if not str(error).startswith('consumed source is not committed at the reviewed head:'):
            return
        self.captured = True
        try:
            trace = error.__traceback__
            while trace is not None:
                frame, trace = trace.tb_frame, trace.tb_next
                if frame.f_code.co_name != 'require_committed':
                    continue
                values = frame.f_locals
                proc = values['proc']
                output = self.directory / 'source-proof-failure'
                output.mkdir(exist_ok=False)
                for name, raw in (('stdout', proc.stdout), ('stderr', proc.stderr), ('query', values['query'])):
                    if type(raw) is not bytes or len(raw) > 64 * 1024 * 1024:
                        raise ValueError('unexpected source-proof capture size or type')
                    (output / (name + '.bin')).write_bytes(raw)
                record = {'nodeid': node.nodeid, 'error': str(error),
                    'offset': values['offset'], 'path': values['path'],
                    'header_hex': [part.hex() for part in values['header']],
                    'stdout_bytes': len(proc.stdout), 'stderr_sha256': hashlib.sha256(proc.stderr).hexdigest(),
                    'query_sha256': hashlib.sha256(values['query']).hexdigest(),
                    'source_commit': values['base']['source_commit'], 'root': str(frame.f_globals['ROOT']),
                    'fullmatch': repr(frame.f_globals['re'].fullmatch),
                    'subprocess_run': repr(frame.f_globals['subprocess'].run),
                    'subprocess_popen': repr(frame.f_globals['subprocess'].Popen)}
                (output / 'failure.json').write_text(json.dumps(record, indent=2) + '\n')
                return
        except Exception as exc:
            (self.directory / 'proof-capture-error.txt').write_text(type(exc).__name__ + ': ' + str(exc) + '\n')


def isolated_pytest():
    tree = Path(sys.argv[2]).resolve()
    sys.path[:] = [value for value in sys.path
                   if not (Path(value) / 'data_sheets_schema').is_dir()
                   or Path(value).resolve() == tree / 'src']
    sys.path.insert(0, str(tree))
    import data_sheets_schema
    roots = [str(Path(value).resolve()) for value in data_sheets_schema.__path__]
    if set(roots) != {str(tree / 'src/data_sheets_schema')}:
        raise RuntimeError('test project namespace differs from selected archive')
    Path(sys.argv[3]).write_text(json.dumps({'python': sys.executable, 'version': sys.version,
                                          'package_roots': roots}, indent=2) + '\n')
    import pytest
    return pytest.main(sys.argv[4:], plugins=[SourceProofFailureCapture(Path(sys.argv[3]).parent)])


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    archive, tree = out / 'source.tar', out / 'tree'
    subprocess.run(['git', '-C', str(ROOT), 'archive', '--output', str(archive), head], check=True)
    tree.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(tree, filter='data')
    common = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', '--path-format=absolute', '--git-common-dir'], text=True).strip()
    subprocess.run(['git', '-C', str(tree), 'init', '-q'], check=True)
    (tree / '.git/objects/info/alternates').write_text(str(Path(common) / 'objects') + '\n')
    subprocess.run(['git', '-C', str(tree), 'update-ref', 'refs/heads/archive-test', head], check=True)
    subprocess.run(['git', '-C', str(tree), 'symbolic-ref', 'HEAD', 'refs/heads/archive-test'], check=True)
    subprocess.run(['git', '-C', str(tree), 'read-tree', head], check=True)
    paths = subprocess.check_output(
        ['git', '-C', str(ROOT), 'diff', '--name-only', BASE, head], text=True).splitlines()
    pins = {name: hashlib.sha256((tree / name).read_bytes()).hexdigest() for name in paths}
    helper = tree / 'scripts/adhoc' / Path(__file__).name
    env = dict(os.environ, PYTHONPATH=str(tree / 'src'), PYTHONDONTWRITEBYTECODE='1')
    command = [str(PYTHON), '-P', '-s', '-B', str(helper), '--pytest', str(tree), str(out / 'imports.json'),
               '-q', '-p', 'no:cacheprovider', '--basetemp', str(out / 'pytest')]
    command += sys.argv[2:] or TARGETED
    record = {'source_commit': head, 'cwd': str(tree), 'command': command,
              'environment': {'PYTHONPATH': env['PYTHONPATH'], 'PYTHONDONTWRITEBYTECODE': '1'},
              'started_utc': subprocess.check_output(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'], text=True).strip(),
              'changed_file_sha256': pins}
    (out / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    with (out / 'pytest.log').open('xb') as log:
        run = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
    record['exit_code'] = run.returncode
    (out / 'results.json').write_text(json.dumps(record, indent=2) + '\n')
    print((out / 'pytest.log').read_text()[-7000:], flush=True)
    return run.returncode


if __name__ == '__main__':
    raise SystemExit(isolated_pytest() if sys.argv[1] == '--pytest' else main())
