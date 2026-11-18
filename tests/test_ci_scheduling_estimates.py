"""Issue 6289: estimates are ordinary-lane hints bound to measured bytes."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utils import pytest_shard as shard


class Config:
    def __init__(self, *, lane='ordinary', timing=None, coordinate='1/1'):
        self.options = {'--ci-lane': lane, '--ci-shard': coordinate,
                        '--ci-shard-timings': timing, 'numprocesses': 0,
                        'maxschedchunk': 1}
        self.registered = []
        self.deselected = []
        self.pluginmanager = SimpleNamespace(register=self.register)
        self.hook = SimpleNamespace(pytest_deselected=self.reject)

    def getoption(self, name, default=None):
        return self.options.get(name, default)

    def register(self, plugin, name):
        self.registered.append((plugin, name))

    def reject(self, *, items):
        self.deselected.extend(items)


def documents(root):
    directory = root / 'utils'
    directory.mkdir(parents=True)
    measured = directory / 'ci_test_durations.json'
    estimates = directory / 'ci_scheduling_estimates.json'
    measured.write_text(json.dumps({'schema_version': 1, 'file_seconds': {
        'tests/test_known.py': 10, 'tests/test_retained.py': 2}}) + '\n')
    value = {'schema_version': 1,
             'base_sha256': hashlib.sha256(measured.read_bytes()).hexdigest(),
             'source': {'issue': 6289, 'basis': 'Invented scheduling test estimates'},
             'file_seconds': {'tests/test_known.py': 100,
                              'tests/test_added.py': 20,
                              'tests/test_removed.py': 10000}}
    estimates.write_text(json.dumps(value))
    return measured, estimates, value


def test_estimates_overlay_exact_keys_without_changing_measured_bytes(tmp_path):
    measured, estimates, _ = documents(tmp_path)
    original = measured.read_bytes()
    assert shard.read_weights(measured) == {
        'tests/test_known.py': 10, 'tests/test_retained.py': 2}
    assert shard.read_weights(measured, estimates_path=estimates) == {
        'tests/test_known.py': 100, 'tests/test_retained.py': 2,
        'tests/test_added.py': 20, 'tests/test_removed.py': 10000}
    assert measured.read_bytes() == original


def test_ordinary_repository_timings_activate_estimates_for_relative_and_absolute_paths(tmp_path, monkeypatch):
    measured, _, _ = documents(tmp_path)
    monkeypatch.setattr(shard, '__file__', str(tmp_path / 'utils/pytest_shard.py'))
    monkeypatch.chdir(tmp_path)
    for timing in (measured, Path('utils/ci_test_durations.json')):
        config = Config(timing=str(timing))
        shard.pytest_configure(config)
        assert config._d4d_shard_weights == {
            'tests/test_known.py': 100, 'tests/test_retained.py': 2,
            'tests/test_added.py': 20, 'tests/test_removed.py': 10000}


def test_other_timing_modes_do_not_read_repository_estimates(tmp_path, monkeypatch):
    measured, estimates, _ = documents(tmp_path)
    monkeypatch.setattr(shard, '__file__', str(tmp_path / 'utils/pytest_shard.py'))
    custom = tmp_path / 'custom.json'
    custom.write_bytes(measured.read_bytes())
    # An invalid sibling makes accidental activation fail rather than merely
    # produce the same weights through an irrelevant but valid document.
    estimates.write_text('not json')
    for lane, timing in ((None, measured), ('ordinary', custom), (None, custom)):
        config = Config(lane=lane, timing=str(timing))
        shard.pytest_configure(config)
        assert config._d4d_shard_weights == {
            'tests/test_known.py': 10, 'tests/test_retained.py': 2}
    config = Config(timing=None)
    shard.pytest_configure(config)
    assert not hasattr(config, '_d4d_shard_weights')


def test_dedicated_lane_refuses_timing_before_reading_estimates(tmp_path, monkeypatch):
    measured, estimates, _ = documents(tmp_path)
    estimates.write_text('not json')
    monkeypatch.setattr(shard, '__file__', str(tmp_path / 'utils/pytest_shard.py'))
    lane = next(iter(shard.DEDICATED_CASE_LANES))
    config = Config(lane=lane, timing=str(measured), coordinate=None)
    with pytest.raises(pytest.UsageError, match='dedicated.*forbids'):
        shard.pytest_configure(config)
    assert not config.registered


def test_missing_repository_estimates_cannot_silently_use_measured_weights(tmp_path, monkeypatch):
    measured, _, _ = documents(tmp_path)
    missing_root = tmp_path / 'missing'
    missing_root.mkdir()
    missing_utils = missing_root / 'utils'
    missing_utils.mkdir()
    selected = missing_utils / 'ci_test_durations.json'
    selected.write_bytes(measured.read_bytes())
    monkeypatch.setattr(shard, '__file__', str(missing_utils / 'pytest_shard.py'))
    config = Config(timing=str(selected))
    with pytest.raises(pytest.UsageError, match='estimates'):
        shard.pytest_configure(config)
    assert not hasattr(config, '_d4d_shard_weights')


def test_base_binding_covers_exact_bytes_including_whitespace(tmp_path):
    measured, estimates, _ = documents(tmp_path)
    measured.write_bytes(measured.read_bytes() + b'\n')
    with pytest.raises(pytest.UsageError, match='estimates'):
        shard.read_weights(measured, estimates_path=estimates)


def test_invalid_estimate_document_is_refused(tmp_path, field, replacement):
    measured, estimates, value = documents(tmp_path)
    value[field] = replacement
    estimates.write_text(json.dumps(value))
    with pytest.raises(pytest.UsageError, match='estimates'):
        shard.read_weights(measured, estimates_path=estimates)


test_invalid_estimate_document_is_refused = pytest.mark.parametrize(
    ('field', 'replacement'), [
        ('schema_version', True), ('schema_version', 2),
        ('schema_version', '1'), ('base_sha256', '0' * 64),
        ('base_sha256', None), ('base_sha256', 1),
        ('source', {}), ('source', []), ('source', None),
        ('file_seconds', {}), ('file_seconds', []),
        ('unknown', 'must not be ignored'),
    ])(test_invalid_estimate_document_is_refused)


def test_missing_estimate_field_is_refused(tmp_path, field):
    measured, estimates, value = documents(tmp_path)
    del value[field]
    estimates.write_text(json.dumps(value))
    with pytest.raises(pytest.UsageError, match='estimates'):
        shard.read_weights(measured, estimates_path=estimates)


test_missing_estimate_field_is_refused = pytest.mark.parametrize(
    'field', ['schema_version', 'base_sha256', 'source', 'file_seconds']
)(test_missing_estimate_field_is_refused)


def test_invalid_estimated_duration_is_refused(tmp_path, duration):
    measured, estimates, value = documents(tmp_path)
    value['file_seconds'] = {'tests/test_known.py': duration}
    estimates.write_text(json.dumps(value))
    with pytest.raises(pytest.UsageError, match='estimates'):
        shard.read_weights(measured, estimates_path=estimates)


test_invalid_estimated_duration_is_refused = pytest.mark.parametrize(
    'duration', [0, -1, float('nan'), float('inf'), float('-inf'), True,
                 False, None, '1', [], {}, 10 ** 1000]
)(test_invalid_estimated_duration_is_refused)


def test_estimated_paths_must_be_canonical_relative_python_files(tmp_path, name):
    measured, estimates, value = documents(tmp_path)
    value['file_seconds'] = {name: 1}
    estimates.write_text(json.dumps(value))
    with pytest.raises(pytest.UsageError, match='estimates'):
        shard.read_weights(measured, estimates_path=estimates)


test_estimated_paths_must_be_canonical_relative_python_files = pytest.mark.parametrize(
    'name', ['/test.py', '../test.py', 'tests/../test.py', 'tests//test.py',
             './test.py', 'tests\\test.py', 'tests/test.txt', '']
)(test_estimated_paths_must_be_canonical_relative_python_files)


def test_malformed_and_duplicate_estimates_are_refused(tmp_path):
    measured, estimates, value = documents(tmp_path)
    valid = json.dumps(value)
    duplicates = [
        valid.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'),
        valid.replace('"tests/test_known.py": 100',
                      '"tests/test_known.py": 100, "tests/test_known.py": 100'),
        valid.replace('"issue": 6289', '"issue": 6289, "issue": 6289'),
    ]
    for raw in [b'not json', b'[]', b'null', b'\xff',
                *(item.encode() for item in duplicates)]:
        estimates.write_bytes(raw)
        with pytest.raises(pytest.UsageError, match='estimates'):
            shard.read_weights(measured, estimates_path=estimates)


def test_estimated_ordinary_partition_retains_untimed_files_and_duplicate_occurrences(tmp_path, monkeypatch):
    measured, _, _ = documents(tmp_path)
    monkeypatch.setattr(shard, '__file__', str(tmp_path / 'utils/pytest_shard.py'))
    dedicated = 'tests/test_dedicated.py::test_required'
    monkeypatch.setattr(shard, 'DEDICATED_CASE_LANES', {'isolated': dedicated})
    ordinary = ['tests/test_known.py::test_one', 'tests/test_known.py::test_duplicate',
                'tests/test_known.py::test_duplicate', 'tests/test_new.py::test_untimed',
                'tests/test_added.py::test_estimated']
    all_nodes = [ordinary[0], dedicated, *ordinary[1:]]
    for total in (8, 12):
        collected, owners = [], {}
        for index in range(1, total + 1):
            config = Config(timing=str(measured), coordinate=f'{index}/{total}')
            shard.pytest_configure(config)
            items = [SimpleNamespace(nodeid=node) for node in all_nodes]
            shard.pytest_collection_modifyitems(config, items)
            selected = [item.nodeid for item in items]
            collected.extend(selected)
            assert Counter(selected + [item.nodeid for item in config.deselected]) == Counter(all_nodes)
            for node in selected:
                path = node.split('::', 1)[0]
                assert owners.setdefault(path, index) == index
        assert Counter(collected) == Counter(ordinary)
        assert set(owners) == {node.split('::', 1)[0] for node in ordinary}
        config = Config(lane='isolated', timing=None, coordinate=None)
        shard.pytest_configure(config)
        items = [SimpleNamespace(nodeid=node) for node in all_nodes]
        shard.pytest_collection_modifyitems(config, items)
        assert [item.nodeid for item in items] == [dedicated]
        assert Counter(collected + [item.nodeid for item in items]) == Counter(all_nodes)


def test_committed_estimates_are_bound_to_the_unchanged_measured_base():
    root = Path(__file__).resolve().parents[1]
    measured = root / 'utils/ci_test_durations.json'
    estimates = root / 'utils/ci_scheduling_estimates.json'
    raw = measured.read_bytes()
    base = json.loads(raw)
    overlay = json.loads(estimates.read_bytes())
    assert overlay['base_sha256'] == hashlib.sha256(raw).hexdigest()
    assert 'issue_6289_20261118' not in base['source']
    previous = deepcopy(base)
    key = 'successful_ordinary_refresh_43536007079_20261114'
    refresh = previous['source'].pop(key)
    previous['file_seconds'] = refresh['previous_file_seconds']
    prior_bytes = (json.dumps(previous, indent=2) + '\n').encode()
    assert hashlib.sha256(prior_bytes).hexdigest() == refresh['previous_snapshot_sha256']
    effective = shard.read_weights(measured, estimates_path=estimates)
    assert effective == {**base['file_seconds'], **overlay['file_seconds']}
    assert set(effective) == set(base['file_seconds']) | set(overlay['file_seconds'])
