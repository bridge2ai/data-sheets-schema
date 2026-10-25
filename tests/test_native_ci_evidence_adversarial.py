"""Independent archive and actual pytest-lifetime controls, with invented cases.

The tiny child suite imports only the retention plugin and creates a few bytes.
It never imports or invokes native execution, a helper or a provider.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from types import SimpleNamespace

import pytest

from utils import native_ci_evidence as evidence


ROOT = Path(__file__).resolve().parents[1]
NODE = next(iter(evidence.CASES))
SOURCE = {'head': 'a' * 40, 'tree': 'b' * 40,
          'scope': 'Invented retention-only test source, not native run provenance.'}


@pytest.mark.parametrize('empty', [False, True])
def test_archive_contains_exact_selected_root_mode_even_when_empty(tmp_path, empty):
    case = tmp_path / evidence.CASES[NODE]
    case.mkdir(mode=0o710)
    case.chmod(0o710)
    if not empty:
        (case / 'partial.txt').write_bytes(b'invented early construction bytes')
    output = tmp_path / 'capture'
    result = evidence.capture_case(tmp_path, output, node_id=NODE, worker='gw0',
        source=SOURCE, outcome={'call': {'outcome': 'failed', 'duration_seconds': 0.1}})
    assert result['unchanged'] is True
    assert result['before']['.'] == {'type': 'directory', 'mode': 0o710}
    with tarfile.open(output / 'case.tar.gz') as archive:
        members = archive.getmembers()
        assert len([member for member in members if member.name.rstrip('/') == 'case']) == 1
        root = archive.getmember('case')
        assert root.isdir() and root.mode == 0o710
        assert len(members) == (1 if empty else 2)
        inventory = {}
        for member in members:
            name = '.' if member.name.rstrip('/') == 'case' else member.name.removeprefix('case/')
            if member.isdir():
                inventory[name] = {'type': 'directory', 'mode': member.mode}
            else:
                assert member.isfile()
                raw = archive.extractfile(member).read()
                inventory[name] = {'type': 'file', 'mode': member.mode,
                                   'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        assert inventory == result['archived'] == result['before'] == result['after']


def test_leaf_replaced_by_external_link_is_refused_before_target_read(tmp_path, monkeypatch):
    case = tmp_path / evidence.CASES[NODE]
    case.mkdir()
    leaf = case / 'selected.bin'
    leaf.write_bytes(b'original selected bytes')
    outside = tmp_path / 'outside.bin'
    outside.write_bytes(b'never archive or read this target')
    original_open = evidence.os.open
    replaced = False

    def swap_before_open(path, flags, *args, **kwargs):
        nonlocal replaced
        if path == leaf.name and not replaced:
            replaced = True
            leaf.unlink()
            leaf.symlink_to(outside)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(evidence.os, 'open', swap_before_open)
    output = tmp_path / 'capture'
    result = evidence.capture_case(tmp_path, output, node_id=NODE, worker='gw0',
        source=SOURCE, outcome={'call': {'outcome': 'failed', 'duration_seconds': 0.1}})
    assert replaced
    assert result['status'] == 'capture_failed'
    assert result['before'] is None and result['archive'] is None
    assert result['unchanged'] is False
    assert not (output / 'case.tar.gz').exists()
    assert outside.read_bytes() == b'never archive or read this target'


def test_other_node_never_captures_even_with_matching_case_directory(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('unselected test caused evidence collection')

    monkeypatch.setattr(evidence, 'capture_case', forbidden)
    selected = SimpleNamespace(_native_ci_evidence={
        'worker': 'gw0', 'worker_root': tmp_path, 'events': [], 'source': SOURCE})
    item = SimpleNamespace(config=selected, nodeid='tests/other.py::test_unselected',
                           funcargs={'tmp_path': tmp_path})
    hook = evidence.pytest_runtest_makereport(item, None)
    next(hook)
    report = SimpleNamespace(when='teardown', outcome='passed', duration=0.1)
    with pytest.raises(StopIteration):
        hook.send(SimpleNamespace(get_result=lambda: report))
    assert selected._native_ci_evidence['events'] == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('assertion_fails,capture_fails', [(True, False), (False, True)])
def test_actual_pytest_teardown_and_exit_survive_retention(tmp_path, assertion_fails, capture_fails):
    project = tmp_path / 'tiny-suite'
    (project / 'tests').mkdir(parents=True)
    shim = project / 'invented_retention_plugin.py'
    shim.write_text(
        'from utils.native_ci_evidence import *\n'
        'from utils import native_ci_evidence as selected\n'
        f'selected.source_identity = lambda: {SOURCE!r}\n'
        + ('def fail_capture(*a, **k):\n'
           '    raise OSError("invented retention failure")\n'
           'selected.capture_case = fail_capture\n' if capture_fails else ''), encoding='utf-8')
    function = NODE.split('::')[1]
    (project / 'tests/test_native_shared_execution.py').write_text(
        f'def {function}(tmp_path, request):\n'
        f'    case = tmp_path / {evidence.CASES[NODE]!r}\n'
        '    case.mkdir()\n'
        '    (case / "call.txt").write_text("invented call bytes")\n'
        '    request.addfinalizer(lambda: (case / "teardown.txt").write_text("finalizer completed"))\n'
        + ('    assert False, "original assertion retained"\n' if assertion_fails else
           '    assert (case / "call.txt").is_file()\n'), encoding='utf-8')
    destination = tmp_path / 'evidence'
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=os.pathsep.join((str(project), str(ROOT))))
    environment.pop('PYTEST_ADDOPTS', None)
    completed = subprocess.run([
        sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '-p', 'invented_retention_plugin', '--basetemp', str(tmp_path / 'pytest-temp'),
        '--native-ci-evidence-root', str(destination), NODE,
    ], cwd=project, env=environment, capture_output=True, text=True, timeout=30)
    assert completed.returncode == int(assertion_fails), completed.stdout + completed.stderr
    outcomes = json.loads((destination / 'controller/outcomes.json').read_text())
    assert outcomes['pytest_exitstatus'] == int(assertion_fails)
    assert len(outcomes['events']) == 1
    event = outcomes['events'][0]
    assert event['node_id'] == NODE
    assert event['test_outcome']['setup']['outcome'] == 'passed'
    assert event['test_outcome']['call']['outcome'] == ('failed' if assertion_fails else 'passed')
    assert event['test_outcome']['teardown']['outcome'] == 'passed'
    if capture_fails:
        assert event['capture_status'] == 'capture_failed'
        assert event['error']['message'] == 'invented retention failure'
        assert not (destination / 'controller' / event['directory']).exists()
    else:
        assert 'original assertion retained' in completed.stdout
        manifest_path = destination / 'controller' / event['directory'] / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        assert manifest['source'] == SOURCE
        assert manifest['status'] == 'retained' and manifest['case_completeness'] == 'not_assessed'
        assert manifest['before']['teardown.txt']['type'] == 'file'
        with tarfile.open(manifest_path.parent / 'case.tar.gz') as archive:
            assert archive.extractfile('case/teardown.txt').read() == b'finalizer completed'
            assert archive.extractfile('case/call.txt').read() == b'invented call bytes'
