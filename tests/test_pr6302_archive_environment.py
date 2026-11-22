"""Software-only boundaries for the disposable archive environment helper."""
import base64
import csv
import hashlib
import io
from pathlib import Path

import pytest

from scripts.adhoc import pr6302_archive_environment_20261122 as environment
from scripts.adhoc import pr6302_archive_environment_scripts_20261122 as launchers


def test_record_targets_refuse_absolute_escape_and_parent_alias(tmp_path):
    source = tmp_path / 'live' / '.venv'
    site = source / 'lib/python3.13/site-packages'
    record = site / 'example-1.dist-info/RECORD'
    record.parent.mkdir(parents=True)
    (source / 'bin').mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    original = outside / 'keep'
    original.write_bytes(b'original')
    (site / 'alias').symlink_to(outside, target_is_directory=True)
    valid = b'example.py,,\n../../../bin/example,,\n'
    assert environment.record_targets(source, record, valid) == [site / 'example.py', source / 'bin/example']
    for raw in ((str(original) + ',,\n').encode(), b'../../../../outside/keep,,\n', b'alias/keep,,\n'):
        with pytest.raises(ValueError, match='relative paths|escapes environment'):
            environment.record_targets(source, record, raw)
        assert original.read_bytes() == b'original'


def test_fresh_destination_refuses_symlinks_and_hardlinks_without_writes(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    original = source / 'keep'
    original.write_bytes(b'unchanged')
    linked = tmp_path / 'hardlink'
    linked.hardlink_to(original)
    aliased = tmp_path / 'alias'
    aliased.symlink_to(source, target_is_directory=True)
    for target in (linked, aliased, source / 'nested'):
        with pytest.raises(ValueError, match='fresh independent'):
            environment.fresh_directory_target(source, target)
    assert original.read_bytes() == linked.read_bytes() == b'unchanged'
    assert not (source / 'nested').exists()


def test_relocation_write_gate_refuses_aliases_and_accepts_independent_copy(tmp_path):
    live = tmp_path / 'live'
    live.mkdir()
    original = live / 'keep'
    original.write_bytes(b'original')
    clone = tmp_path / 'clone'
    clone.mkdir()
    copied = clone / 'copy'
    copied.write_bytes(original.read_bytes())
    assert launchers.writable_payload(copied, clone, original) == b'original'
    linked = clone / 'hardlink'
    linked.hardlink_to(original)
    symbolic = clone / 'symlink'
    symbolic.symlink_to(original)
    parent = clone / 'parent-alias'
    parent.symlink_to(live, target_is_directory=True)
    for path in (linked, symbolic, parent / 'keep'):
        with pytest.raises(ValueError, match='physical clone|symlink or hardlink'):
            launchers.writable_payload(path, clone, original)
    with pytest.raises(ValueError, match='original source inode'):
        launchers.writable_payload(copied, clone, copied)
    assert original.read_bytes() == copied.read_bytes() == linked.read_bytes() == b'original'


def test_archive_live_project_overlap_refuses_before_output(tmp_path):
    project = tmp_path / 'live'
    source = project / '.venv'
    source.mkdir(parents=True)
    output = tmp_path / 'setup'
    for tree in (project, source, tmp_path):
        with pytest.raises(ValueError, match='disjoint'):
            environment.boundaries(source, tree, output)
        assert not output.exists()
    archive = tmp_path / 'archive'
    archive.mkdir()
    environment.boundaries(source, archive, output)


def test_source_drift_refuses_without_restoring_or_mutating_inputs(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    original = source / 'keep'
    original.write_bytes(b'before')
    expected = environment.inventory(source)
    original.write_bytes(b'after')
    with pytest.raises(ValueError, match='source changed'):
        environment.require_unchanged(source, expected, 'source')
    assert original.read_bytes() == b'after'
    assert list(source.iterdir()) == [original]


def _hash(raw):
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode()


def _record(rows):
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\n').writerows(rows)
    return stream.getvalue().encode()


def _planner_fixture(root, callables, *, known=True):
    source = root / '.venv'
    site = source / 'lib/python3.13/site-packages'
    (source / 'bin').mkdir(parents=True)
    maker = site / launchers.MAKER_SOURCE
    maker.parent.mkdir(parents=True)
    maker.write_text("SCRIPT_TEMPLATE = 'from %(module)s import %(import_name)s\\n'\n")
    script = source / 'bin/example'
    script_raw = ('#!' + str(source / 'bin/python') + '\nprint("fixture")\n').encode()
    script.write_bytes(script_raw)
    owners, distributions = [], []
    for number, callable_value in enumerate(callables):
        name = 'fixture' + str(number)
        directory = site / (name + '-1.dist-info')
        directory.mkdir()
        metadata = ('Name: ' + name + '\nVersion: 1\n').encode()
        points = ('[console_scripts]\n' + ('example' if known else 'unrelated')
                  + ' = ' + callable_value + '\n').encode()
        (directory / 'METADATA').write_bytes(metadata)
        (directory / 'entry_points.txt').write_bytes(points)
        relative = directory.name
        rows = [[relative + '/METADATA', _hash(metadata), str(len(metadata))],
                [relative + '/entry_points.txt', _hash(points), str(len(points))],
                ['../../../bin/example', _hash(script_raw), str(len(script_raw))],
                [relative + '/RECORD', '', '']]
        record = directory / 'RECORD'
        record.write_bytes(_record(rows))
        distributions.append({'name': name, 'version': '1', 'dist_info': str(directory),
            'record': launchers.pin(record), 'metadata_sha256': hashlib.sha256(metadata).hexdigest()})
        owners.append({'name': name, 'version': '1', 'record_path': str(record),
            'record_sha256': launchers.sha(record.read_bytes()), 'record_entry': '../../../bin/example',
            'recorded_hash': _hash(script_raw), 'recorded_size': str(len(script_raw))})
    return source, {'venv': str(source), 'site_packages': str(site),
        'duplicate_distribution_names': [], 'distributions': distributions,
        'python_launchers': [{**launchers.pin(script), 'owners': owners}]}


def test_planner_checks_shared_callable_and_unknown_launcher_without_writes(tmp_path):
    good, good_audit = _planner_fixture(tmp_path / 'good', ['fixture.cli:main', 'fixture.cli:main'])
    planned = launchers.plan_scripts(good, good_audit, expected_launcher_count=1)
    assert planned[0]['callable'] == 'fixture.cli:main'
    assert len(planned[0]['owners']) == 2
    for label, callables, known, message in (
            ('conflict', ['fixture.cli:main', 'fixture.cli:other'], True, 'disagree'),
            ('unknown', ['fixture.cli:main'], False, 'not a declared')):
        source, audit = _planner_fixture(tmp_path / label, callables, known=known)
        before = environment.inventory(source)
        with pytest.raises(ValueError, match=message):
            launchers.plan_scripts(source, audit, expected_launcher_count=1)
        assert environment.inventory(source) == before
    with pytest.raises(ValueError, match='reviewed launcher roster'):
        launchers.plan_scripts(good, good_audit)
