"""Offline evidence capture controls; no native peer, helpers or providers run."""
from copy import deepcopy
import json
from pathlib import Path
import tarfile
from types import SimpleNamespace

import pytest

from utils import native_ci_evidence as evidence


NODE = next(iter(evidence.CASES))
SOURCE = {'head': 'a' * 40, 'tree': 'b' * 40, 'files': {}, 'scope': 'invented unit fixture'}
FAILED = {'setup': {'outcome': 'passed', 'duration_seconds': 0.1},
          'call': {'outcome': 'failed', 'duration_seconds': 900.0},
          'teardown': {'outcome': 'passed', 'duration_seconds': 0.2}}


def case(tmp_path):
    selected = tmp_path / evidence.CASES[NODE]
    selected.mkdir()
    (selected / 'actual-result.json').write_text(json.dumps({'state': 'failed', 'synthetic': True}))
    (selected / '.hidden').write_bytes(b'exact invented bytes\x00')
    (selected / '.hidden').chmod(0o600)
    return selected


def capture(tmp_path, output, **kwargs):
    return evidence.capture_case(tmp_path, output, node_id=NODE, worker='gw2',
                                 source=SOURCE, outcome=deepcopy(FAILED), **kwargs)


def test_failed_case_retains_exact_bytes_modes_and_original_failure(tmp_path):
    selected = case(tmp_path)
    original = evidence.snapshot(selected)
    result = capture(tmp_path, tmp_path / 'capture')
    assert result['status'] == 'retained' and result['unchanged'] is True
    assert result['before'] == result['archived'] == result['after'] == original
    assert evidence.snapshot(selected) == original
    assert result['test_outcome'] == FAILED and result['scientific_acceptance'] == 'not_assessed'
    assert result['source'] == SOURCE
    assert result['declared_limits']['attempt_seconds'] == 900
    assert result['declared_limits']['helper_seconds'] == 180
    assert result['declared_limits']['base_fixture_seconds'] == 120
    with tarfile.open(tmp_path / 'capture/case.tar.gz') as archive:
        assert archive.extractfile('case/.hidden').read() == b'exact invented bytes\x00'
        assert archive.getmember('case/.hidden').mode == 0o600
        assert archive.extractfile('case/actual-result.json').read() == (selected / 'actual-result.json').read_bytes()
    assert result['archive'] == evidence.pin((tmp_path / 'capture/case.tar.gz').read_bytes())


def test_early_partial_constructor_case_is_retained_without_inventing_a_result(tmp_path):
    selected = tmp_path / evidence.CASES[NODE]
    selected.mkdir()
    (selected / 'authority').mkdir()
    (selected / 'authority/first.json').write_text('{"incomplete":true}')
    result = capture(tmp_path, tmp_path / 'partial')
    assert result['status'] == 'retained'
    assert 'actual-result.json' not in result['before']
    assert result['availability']['actual-result.json'] == 'absent'
    assert result['availability']['native-attempt/transcript.jsonl'] == 'absent'
    assert result['case_completeness'] == 'not_assessed'
    assert result['test_outcome']['call']['outcome'] == 'failed'
    assert result['before']['authority/first.json']['type'] == 'file'


@pytest.mark.parametrize('tmp_available', [False, True])
def test_missing_case_is_explicit_and_never_an_empty_success_archive(tmp_path, tmp_available):
    result = capture(tmp_path if tmp_available else None, tmp_path / 'missing')
    assert result['status'] == 'case_unavailable'
    assert result['before'] is result['after'] is result['archive'] is None
    assert result['unchanged'] is False
    assert not (tmp_path / 'missing/case.tar.gz').exists()


def test_output_collision_preserves_original_capture(tmp_path):
    case(tmp_path)
    destination = tmp_path / 'capture'
    capture(tmp_path, destination)
    before = {p.name: p.read_bytes() for p in destination.iterdir()}
    with pytest.raises(FileExistsError):
        capture(tmp_path, destination)
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == before


def test_external_symlinks_and_json_authority_paths_are_never_followed(tmp_path):
    selected = case(tmp_path)
    outside = tmp_path / 'private-outside'
    outside.mkdir()
    secret = outside / 'unrelated.txt'
    secret.write_bytes(b'DO NOT CAPTURE THIS EXTERNAL CONTENT')
    (selected / 'file-link').symlink_to(secret)
    (selected / 'dir-link').symlink_to(outside, target_is_directory=True)
    (selected / 'authority.json').write_text(json.dumps({'path': str(secret)}))
    result = capture(tmp_path, tmp_path / 'capture')
    assert result['status'] == 'retained'
    assert result['before']['file-link'] == {'mode': 0o777, 'type': 'symlink', 'target': str(secret)}
    assert result['before']['dir-link']['type'] == 'symlink'
    with tarfile.open(tmp_path / 'capture/case.tar.gz') as archive:
        assert archive.getmember('case/file-link').issym()
        assert archive.getmember('case/dir-link').issym()
        assert not any('unrelated.txt' in name for name in archive.getnames())
        assert all(secret.read_bytes() not in archive.extractfile(member).read()
                   for member in archive.getmembers() if member.isfile())


@pytest.mark.parametrize('which', ['case', 'parent'])
def test_symlink_case_or_ancestor_refuses_without_reading_target(tmp_path, which):
    actual = tmp_path / 'actual'
    actual.mkdir()
    selected = case(actual)
    if which == 'case':
        (tmp_path / evidence.CASES[NODE]).symlink_to(selected, target_is_directory=True)
        root = tmp_path
    else:
        root = tmp_path / 'alias'
        root.symlink_to(actual, target_is_directory=True)
    result = capture(root, tmp_path / 'capture')
    assert result['status'] == 'capture_failed'
    assert result['before'] is None and result['archive'] is None
    assert not (tmp_path / 'capture/case.tar.gz').exists()


def test_mode_or_bytes_changed_during_archive_cannot_claim_preservation(tmp_path, monkeypatch):
    selected = case(tmp_path)
    original = evidence.snapshot
    def changed(path, archive=None):
        rows = original(path, archive)
        if archive is not None:
            (selected / '.hidden').write_bytes(b'changed after captured bytes')
            (selected / '.hidden').chmod(0o644)
        return rows
    monkeypatch.setattr(evidence, 'snapshot', changed)
    result = capture(tmp_path, tmp_path / 'capture')
    assert result['status'] == 'capture_changed' and result['unchanged'] is False
    assert result['before'] == result['archived']
    assert result['before'] != result['after']
    assert result['archive'] is not None


@pytest.mark.parametrize('limit', ['MAX_CASE_BYTES', 'MAX_CASE_ENTRIES'])
def test_capture_bounds_are_explicit_failure_and_preserve_case(tmp_path, monkeypatch, limit):
    selected = case(tmp_path)
    before = {p.name: p.read_bytes() for p in selected.iterdir()}
    monkeypatch.setattr(evidence, limit, 1)
    result = capture(tmp_path, tmp_path / 'capture')
    assert result['status'] == 'capture_failed'
    assert 'bound exceeded' in result['error']['message']
    assert {p.name: p.read_bytes() for p in selected.iterdir()} == before


def test_unapproved_node_or_overlapping_output_never_writes(tmp_path):
    selected = case(tmp_path)
    with pytest.raises(ValueError, match='two named'):
        evidence.capture_case(tmp_path, tmp_path / 'other', node_id='tests/other.py::test',
                              worker='gw0', source=SOURCE, outcome=FAILED)
    assert not (tmp_path / 'other').exists()
    with pytest.raises(ValueError, match='separate'):
        capture(tmp_path, selected / 'new-output')
    assert not (selected / 'new-output').exists()


def config(path, *, worker=None):
    value = SimpleNamespace(getoption=lambda name: None if path is None else str(path),
                            pluginmanager=SimpleNamespace(getplugin=lambda name: None))
    if worker is not None:
        value.workerinput = {'workerid': worker}
    return value


def report(item, when, outcome='passed'):
    value = SimpleNamespace(when=when, outcome=outcome, duration=0.25)
    hook = evidence.pytest_runtest_makereport(item, None)
    next(hook)
    with pytest.raises(StopIteration):
        hook.send(SimpleNamespace(get_result=lambda: value))
    assert value.when == when and value.outcome == outcome
    return value


def test_plugin_default_off_reads_no_source_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'source_identity', lambda: pytest.fail('unrequested identity read'))
    selected = config(None)
    evidence.pytest_configure(selected)
    item = SimpleNamespace(config=selected, nodeid=NODE, funcargs={'tmp_path': tmp_path})
    report(item, 'call', 'failed')
    evidence.pytest_sessionfinish(SimpleNamespace(config=selected), 1)
    assert not hasattr(selected, '_native_ci_evidence')
    assert list(tmp_path.iterdir()) == []


def test_distinct_worker_node_paths_and_capture_only_after_teardown(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'source_identity', lambda: deepcopy(SOURCE))
    destination = tmp_path / 'selected-evidence'
    controller = config(destination)
    evidence.pytest_configure(controller)
    for worker in ('gw0', 'gw1'):
        selected = config(destination, worker=worker)
        evidence.pytest_configure(selected)
        private = tmp_path / worker
        private.mkdir()
        case(private)
        item = SimpleNamespace(config=selected, nodeid=NODE, funcargs={'tmp_path': private})
        report(item, 'setup')
        report(item, 'call', 'failed')
        assert list((destination / worker).iterdir()) == []
        # Real teardown may clear funcargs: retention keeps the prior owned path.
        item.funcargs = None
        report(item, 'teardown')
        session = SimpleNamespace(config=selected, exitstatus=1)
        evidence.pytest_sessionfinish(session, 1)
        assert session.exitstatus == 1
        retained = list((destination / worker).glob('*/manifest.json'))
        assert len(retained) == 1
        assert json.loads(retained[0].read_text())['test_outcome']['call']['outcome'] == 'failed'
        assert json.loads((destination / worker / 'outcomes.json').read_text())['pytest_exitstatus'] == 1
    assert (destination / 'gw0').resolve() != (destination / 'gw1').resolve()


def test_capture_exception_cannot_replace_failed_test_or_pytest_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'source_identity', lambda: deepcopy(SOURCE))
    selected = config(tmp_path / 'evidence')
    evidence.pytest_configure(selected)
    def refuse(*args, **kwargs):
        raise OSError('invented diagnostic write failure')
    monkeypatch.setattr(evidence, 'capture_case', refuse)
    item = SimpleNamespace(config=selected, nodeid=NODE, funcargs={'tmp_path': tmp_path})
    report(item, 'call', 'failed')
    report(item, 'teardown')
    session = SimpleNamespace(config=selected, exitstatus=1)
    evidence.pytest_sessionfinish(session, 1)
    assert session.exitstatus == 1
    saved = json.loads((tmp_path / 'evidence/controller/outcomes.json').read_text())
    assert saved['pytest_exitstatus'] == 1
    assert saved['events'][0]['capture_status'] == 'capture_failed'
    assert saved['events'][0]['test_outcome']['call']['outcome'] == 'failed'


def test_unrun_nodes_are_explicit_and_setup_failure_has_no_invented_case(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'source_identity', lambda: deepcopy(SOURCE))
    selected = config(tmp_path / 'evidence')
    evidence.pytest_configure(selected)
    item = SimpleNamespace(config=selected, nodeid=NODE, funcargs={})
    report(item, 'setup', 'failed')
    report(item, 'teardown')
    evidence.pytest_sessionfinish(SimpleNamespace(config=selected), 1)
    saved = json.loads((tmp_path / 'evidence/controller/outcomes.json').read_text())
    assert saved['unobserved_nodes'] == [node for node in evidence.CASES if node != NODE]
    assert saved['events'][0]['capture_status'] == 'case_unavailable'
    assert saved['events'][0]['test_outcome']['setup']['outcome'] == 'failed'
    assert 'call' not in saved['events'][0]['test_outcome']
