"""Causal offline tests of neutral-before-omission admission; #4354, 2026-10-27."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('n2_public_driver', ROOT / 'scripts/adhoc/validate_n2_restack_20261026.py')
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


def write_evidence(output, label, baseline, origins, *, defect=None):
    output.mkdir()
    for name in ('source-before.json', 'source-after.json'):
        value = copy.deepcopy(baseline)
        if defect == 'source' and name == 'source-after.json':
            value['tree'] = 'changed'
        driver.save(output / name, value)
    for name in ('origins-before.json', 'origins-after.json'):
        if defect == 'missing_origins' and name == 'origins-after.json':
            continue
        value = copy.deepcopy(origins)
        if defect == 'foreign_origin' and name == 'origins-after.json':
            value[driver.POSITIVE_MODULES[0]] = [str(Path(__file__).resolve())]
        driver.save(output / name, value)
    driver.save(output / 'dependency-bootstrap.json', {'site_startup': 'disabled', 'pth_execution': 'disabled'})
    if defect == 'missing_xml':
        return
    path, name = driver.positive_node(label).split('::')
    root = ET.Element('testsuites')
    suite = ET.SubElement(root, 'testsuite', tests='1', failures='0', errors='0', skipped='0')
    case = ET.SubElement(suite, 'testcase', name=name, classname=path.removesuffix('.py').replace('/', '.'))
    if defect == 'wrong_class':
        case.set('classname', 'tests.foreign_test')
    if defect == 'wrong_name':
        case.set('name', 'not_the_requested_test')
    if defect in ('failure', 'skipped'):
        ET.SubElement(case, defect)
    if defect == 'extra_case':
        ET.SubElement(suite, 'testcase', name='extra', classname='tests.extra')
    ET.ElementTree(root).write(output / 'pytest.xml')


@pytest.fixture
def setup_driver(tmp_path, monkeypatch):
    from utils import native_shared_acceptance as acceptance
    root = (tmp_path / 'tree').resolve()
    root.mkdir()
    monkeypatch.setattr(driver, 'ROOT', root)
    baseline = {'head': 'a' * 40, 'tree': 'same', 'tracked_exact': True, 'entries': {}}
    monkeypatch.setattr(acceptance, 'source', lambda _root: copy.deepcopy(baseline))
    monkeypatch.setattr(driver, 'git', lambda *args: b'')
    origins = {}
    for name in driver.POSITIVE_MODULES:
        path = root / 'src' / Path(*name.split('.')).with_suffix('.py')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# offline origin fixture\n')
        origins[name] = [str(path)]
    return root, baseline, origins, tmp_path / 'evidence'


@pytest.mark.parametrize('defect', [
    'exit', 'source', 'missing_origins', 'foreign_origin', 'missing_xml',
    'wrong_class', 'wrong_name', 'failure', 'skipped', 'extra_case',
])
def test_neutral_failure_or_incomplete_proof_never_dispatches_omission(setup_driver, monkeypatch, defect):
    _root, baseline, origins, output = setup_driver
    calls = []
    def child(group, stage_output, expected, *, positive_label):
        calls.append(positive_label)
        assert expected == baseline['head'] and group == 'positive'
        write_evidence(stage_output, positive_label, baseline, origins, defect=defect)
        return 1 if defect == 'exit' else 0
    monkeypatch.setattr(driver, 'run', child)
    assert driver.run_positive(output, baseline['head']) == 1
    assert calls == ['neutral']
    result = json.loads((output / 'outcome.json').read_text())
    assert result['stages']['neutral']['status'] == 'failed'
    assert result['stages']['omission']['status'] == 'pending'
    assert result['omission_not_run'] and not result['runtime_gates_passed']
    assert not (output / 'omission').exists()


def test_two_exact_passes_use_distinct_children_and_source_proofs(setup_driver, monkeypatch):
    _root, baseline, origins, output = setup_driver
    calls = []
    def child(group, stage_output, expected, *, positive_label):
        calls.append((positive_label, stage_output))
        if positive_label == 'omission':
            assert (output / 'source-after-neutral.json').is_file()
        write_evidence(stage_output, positive_label, baseline, origins)
        return 0
    monkeypatch.setattr(driver, 'run', child)
    assert driver.run_positive(output, baseline['head']) == 0
    assert calls == [('neutral', output / 'neutral'), ('omission', output / 'omission')]
    result = json.loads((output / 'outcome.json').read_text())
    assert result['runtime_gates_passed'] and result['source_unchanged']
    assert result['scientific_acceptance'] == 'not_assessed'
    assert 'omission_not_run' not in result
    assert all(stage['status'] == 'passed' for stage in result['stages'].values())


def test_actual_source_drift_after_valid_neutral_blocks_omission(setup_driver, monkeypatch):
    from utils import native_shared_acceptance as acceptance
    _root, baseline, origins, output = setup_driver
    calls = []
    state = {'snapshot': baseline}
    monkeypatch.setattr(acceptance, 'source', lambda _root: copy.deepcopy(state['snapshot']))
    def child(group, stage_output, expected, *, positive_label):
        calls.append(positive_label)
        write_evidence(stage_output, positive_label, baseline, origins)
        # Mutate the observed source state through the function already captured
        # by the parent; rebinding the module attribute would not change it.
        state['snapshot'] = {**baseline, 'tree': 'drifted'}
        return 0
    monkeypatch.setattr(driver, 'run', child)
    assert driver.run_positive(output, baseline['head']) == 1
    assert calls == ['neutral']
    result = json.loads((output / 'outcome.json').read_text())
    assert not result['source_unchanged'] and result['omission_not_run']


def test_omission_failure_remains_failed_after_successful_neutral(setup_driver, monkeypatch):
    _root, baseline, origins, output = setup_driver
    calls = []
    def child(group, stage_output, expected, *, positive_label):
        calls.append(positive_label)
        write_evidence(stage_output, positive_label, baseline, origins)
        return int(positive_label == 'omission')
    monkeypatch.setattr(driver, 'run', child)
    assert driver.run_positive(output, baseline['head']) == 1
    assert calls == ['neutral', 'omission']
    result = json.loads((output / 'outcome.json').read_text())
    assert result['stages']['neutral']['status'] == 'passed'
    assert result['stages']['omission']['status'] == 'failed'
    assert 'omission_not_run' not in result


def test_selected_positive_child_preserves_closed_command_and_sanitized_environment(setup_driver, monkeypatch):
    _root, baseline, origins, output = setup_driver
    monkeypatch.setattr(driver, 'PROTECTED', ())
    monkeypatch.setattr(driver, 'roster', lambda: {'positive': list(driver.POSITIVE), 'native': [], 'legacy': []})
    monkeypatch.setattr(driver.importlib.metadata, 'distributions', lambda: [])
    monkeypatch.setenv('CBORG_API_KEY', 'fixture-secret-must-be-removed')
    observed = []
    def subprocess_run(command, **kwargs):
        observed.append(command)
        assert command[1:4] == ['-S', '-P', '-B']
        assert command[-2:] == ['--positive-label', 'neutral']
        assert 'CBORG_API_KEY' not in kwargs['env']
        assert kwargs['env']['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] == '1'
        assert kwargs['env']['PYTHONPATH'].split(':')[0] == str(driver.ROOT / 'src')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(driver.subprocess, 'run', subprocess_run)
    assert driver.run('positive', output, baseline['head'], positive_label='neutral') == 0
    assert len(observed) == 1


def test_positive_label_cannot_select_arbitrary_nodes():
    with pytest.raises(ValueError, match='exact registered test label'):
        driver.positive_node('tests/test_unrelated.py::test_other')
    with pytest.raises(ValueError, match='positive label'):
        driver.run('native', Path('/unused'), 'unused', positive_label='neutral')
