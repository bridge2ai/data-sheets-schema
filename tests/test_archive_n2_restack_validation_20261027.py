"""Archive preservation/refusal tests with synthetic completed evidence; #4354, 2026-10-27."""
import importlib.util
import json
from pathlib import Path
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('archive_n2_results', ROOT / 'scripts/adhoc/archive_n2_restack_validation_20261027.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def evidence(tmp_path):
    source = tmp_path.resolve() / 'source'
    source.mkdir()
    # Preserve the known historical reporting error as evidence; do not endorse it.
    raw = b'{"returncode":2,"source_unchanged":true,"junit":{"passed":611}}\n'
    (source / 'outcome.json').write_bytes(raw)
    (source / 'pytest.xml').write_bytes(b'<testsuites><testsuite><testcase/></testsuite></testsuites>')
    (source / 'pytest.log').write_bytes(b'interrupted\r\n\xff retained bytes\n')
    (source / 'pytest.log').chmod(0o640)
    (source / 'cases').mkdir()
    (source / 'cases' / 'large-case.json').write_text('not selected')
    (source / '__pycache__').mkdir()
    (source / '__pycache__' / 'cache.bin').write_bytes(b'cache')
    (source / 'neutral').mkdir()
    (source / 'neutral' / 'outcome.json').write_text('{"status":"failed"}')
    (source / 'neutral' / 'cases').mkdir()
    (source / 'neutral' / 'cases' / 'case.log').write_text('not selected either')
    return source, raw


def test_archive_preserves_interrupted_summary_and_stage_files_without_inventing_passes(tmp_path):
    source, raw = evidence(tmp_path)
    output = tmp_path.resolve() / 'archive'
    manifest = helper.archive_results([source], output)
    run = manifest['runs'][0]
    assert manifest['aggregate_pass_claim'] == 'not_made'
    assert run['observations']['outcomes']['outcome.json']['classification'] == 'nonzero_exit'
    shape = run['observations']['junit_shape_only']['pytest.xml']
    assert shape['unnamed_or_unclassified_entries'] == 1
    assert shape['unmarked_identified_entries'] == 0 and 'passed' not in shape
    assert run['archive_bytes_and_modes_verified'] and run['selected_original_bytes_and_modes_unchanged']
    with tarfile.open(output / run['archive']['file']) as archive:
        assert archive.extractfile('results/outcome.json').read() == raw
        assert archive.extractfile('results/pytest.log').read() == (source / 'pytest.log').read_bytes()
        assert archive.getmember('results/pytest.log').mode == 0o640
        assert 'results/neutral/outcome.json' in archive.getnames()
        assert not any('cases/' in name or '__pycache__/' in name for name in archive.getnames())
    assert (source / 'cases' / 'large-case.json').read_text() == 'not selected'
    assert json.loads((output / 'manifest.json').read_text()) == manifest


@pytest.mark.parametrize('kind', ['root', 'selected_file', 'excluded_directory', 'output_parent'])
def test_symlink_boundaries_are_refused_without_following_them(tmp_path, kind):
    source, _ = evidence(tmp_path)
    output = tmp_path.resolve() / 'archive'
    if kind == 'root':
        alias = tmp_path / 'alias'
        alias.symlink_to(source, target_is_directory=True)
        source = alias
    elif kind == 'selected_file':
        (source / 'linked.json').symlink_to(source / 'outcome.json')
    elif kind == 'excluded_directory':
        (source / 'linked-cases').symlink_to(source / 'cases', target_is_directory=True)
    else:
        alias = tmp_path / 'alias'
        alias.symlink_to(tmp_path.resolve(), target_is_directory=True)
        output = alias / 'archive'
    with pytest.raises(ValueError, match='physical|symlink'):
        helper.archive_results([source], output)
    assert not (tmp_path / 'archive').exists()


def test_existing_or_nested_destination_is_refused(tmp_path):
    source, _ = evidence(tmp_path)
    output = tmp_path.resolve() / 'archive'
    output.mkdir()
    (output / 'keep').write_bytes(b'prior evidence')
    with pytest.raises(ValueError, match='fresh physical'):
        helper.archive_results([source], output)
    with pytest.raises(ValueError, match='fresh physical'):
        helper.archive_results([source], source / 'nested-output')
    assert (output / 'keep').read_bytes() == b'prior evidence'


def test_mutating_original_is_detected_and_partial_archive_is_preserved(tmp_path, monkeypatch):
    source, _ = evidence(tmp_path)
    output = tmp_path.resolve() / 'archive'
    original = helper.write_archive
    def changed_after_copy(path, files):
        original(path, files)
        (source / 'pytest.log').write_bytes(b'concurrent change')
    monkeypatch.setattr(helper, 'write_archive', changed_after_copy)
    with pytest.raises(ValueError, match='original evidence changed'):
        helper.archive_results([source], output)
    assert (output / 'run-01.tar.gz').is_file()
    assert not (output / 'manifest.json').exists()


def test_bootstrap_or_unreadable_evidence_stays_unverified(tmp_path):
    source = tmp_path.resolve() / 'source'
    source.mkdir()
    (source / 'summary.json').write_text('{"status":"started"}')
    (source / 'pytest.xml').write_text('incomplete <xml')
    manifest = helper.archive_results([source], tmp_path.resolve() / 'archive')
    observations = manifest['runs'][0]['observations']
    assert observations['outcomes']['summary.json']['classification'] == 'reported_started'
    assert observations['junit_shape_only']['pytest.xml']['pass_inference'] == 'not_performed'
    assert observations['aggregate_pass_claim'] == 'not_made'
