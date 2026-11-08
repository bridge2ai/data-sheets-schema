"""A4 physical containment regressions, 2026-11-08 (#4354).

All files/links are inert scratch fixtures. Producer boundary tests isolate
unrelated authority prerequisites and prohibit process/filesystem effects;
they are not complete registration or native execution acceptance tests.
"""
from copy import deepcopy
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_path_identity as paths
from data_sheets_schema import native_subscription_capture as capture
from data_sheets_schema import native_permission_probe as permission
from data_sheets_schema import native_u4b_runtime as runtime


def _case_alias(path):
    # Prefer the review's actual /users spelling when this fixture is under
    # /Users; otherwise find an existing case alias without creating one.
    indexes = list(range(1, len(path.parts)))
    for index in indexes:
        parts = list(path.parts)
        parts[index] = 'users' if parts[index] == 'Users' else parts[index].swapcase()
        alias = Path(*parts)
        if alias == path:
            continue
        try:
            if alias.samefile(path):
                return alias
        except FileNotFoundError:
            continue
    pytest.skip('filesystem does not expose an existing case alias')


def test_existing_and_prospective_containment_preserves_disjoint_siblings(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    nested = source / 'future' / 'leaf'
    sibling = tmp_path / 'sibling' / 'future'
    assert paths.contains(source, nested)
    assert paths.overlaps(nested, source)
    assert not paths.contains(nested, source)
    assert not paths.overlaps(sibling, source)
    assert not paths.overlaps(tmp_path / 'left', tmp_path / 'right' / 'leaf')
    assert paths.contains(tmp_path / 'future', tmp_path / 'future' / 'leaf')
    assert not nested.exists() and not sibling.exists()


@pytest.mark.parametrize('names', [('Attempt', 'attempt'), ('caf\u00e9', 'cafe\u0301')])
def test_both_absent_alias_suffixes_refuse_ambiguity_without_rewriting(tmp_path, names):
    first, second = tmp_path / names[0], tmp_path / names[1] / 'capture'
    for a, b in ((first, second), (second, first)):
        with pytest.raises(ValueError, match='ambiguous prospective'):
            paths.overlaps(a, b)
    assert not first.exists() and not second.exists()


def test_symlink_and_hardlink_aliases_are_physical_overlap(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    alias = tmp_path / 'linked-source'; alias.symlink_to(source, target_is_directory=True)
    assert paths.contains(source, alias / 'new' / 'leaf')
    assert paths.overlaps(alias / 'new', source)
    first = source / 'first'; first.write_bytes(b'inert fixture')
    second = tmp_path / 'hardlink'; os.link(first, second)
    assert paths.overlaps(first, second)
    assert paths.contains(first, second)
    assert not (source / 'new').exists()


@pytest.mark.parametrize('kind', ['dangling', 'dangling_parent', 'loop', 'file_parent'])
def test_unverifiable_ancestry_refuses(tmp_path, kind):
    target = tmp_path / 'target'
    if kind in ('dangling', 'dangling_parent'):
        target.symlink_to(tmp_path / 'missing')
        if kind == 'dangling_parent': target = target / 'future'
    elif kind == 'loop':
        target.symlink_to(target)
    else:
        target.write_bytes(b'not a directory')
        target = target / 'future'
    with pytest.raises(ValueError, match='physical containment'):
        paths.overlaps(tmp_path / 'ordinary', target)


def test_unreadable_ancestor_is_not_treated_as_missing(tmp_path, monkeypatch):
    denied = tmp_path / 'denied'; denied.mkdir()
    original = Path.stat
    def inspected(path, *args, **kwargs):
        if path == denied:
            raise PermissionError('explicit isolated unreadable ancestor')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', inspected)
    with pytest.raises(ValueError, match='could not verify'):
        paths.overlaps(denied / 'future', tmp_path / 'ordinary')


@pytest.mark.skipif(sys.platform != 'darwin', reason='real macOS case-alias check')
def test_real_case_alias_contains_descendants_and_ancestors(tmp_path):
    source = tmp_path / 'physical-source'; source.mkdir()
    alias = _case_alias(source)
    assert alias != source and alias.samefile(source)
    assert paths.contains(source, alias / 'future' / 'leaf')
    assert paths.overlaps(alias / 'future', source)
    assert paths.overlaps(alias, source / 'future')
    assert not (source / 'future').exists()


def _copy_evidence(source, copied, root):
    # Actual source bytes/pins; neither path is executed.
    return {'updater_root': str(root), 'source': runtime._binary_pin(str(source)),
            'copy': runtime._binary_pin(str(copied))}


@pytest.mark.skipif(sys.platform != 'darwin', reason='real macOS durable-copy case alias')
def test_durable_copy_case_alias_inside_updater_is_not_outside(tmp_path):
    root = tmp_path / 'updater'; root.mkdir()
    source, copied = root / 'source', root / 'copy'
    for path in (source, copied):
        path.write_bytes(b'inert executable fixture'); path.chmod(0o700)
    evidence = _copy_evidence(source, copied, root)
    evidence['copy']['path'] = str(_case_alias(root) / copied.name)
    with pytest.raises(ValueError, match='outside the updater'):
        runtime._copy_evidence(evidence)


def test_durable_copy_keeps_removed_updater_source_supported(tmp_path):
    root = tmp_path / 'updater'; root.mkdir()
    source, copied = root / 'source', tmp_path / 'copy'
    for path in (source, copied):
        path.write_bytes(b'inert executable fixture'); path.chmod(0o700)
    evidence = _copy_evidence(source, copied, root)
    runtime._copy_evidence(evidence)
    source.unlink()
    runtime._copy_evidence(evidence)


@pytest.mark.skipif(sys.platform != 'darwin', reason='real macOS capture alias boundary')
def test_capture_alias_overlap_refuses_with_authority_prerequisites_isolated(tmp_path, monkeypatch):
    from data_sheets_schema import native_launch_review as review
    from data_sheets_schema import native_shared_registration_orchestration as registration
    from data_sheets_schema import native_u4b_policy as policy
    attempt = tmp_path / 'attempt'; attempt.mkdir()
    directory = _case_alias(attempt) / 'capture'
    value = {'runtime': {'deadline_seconds': 60, 'executable': {'path': str(tmp_path / 'inert')}},
        'attempt_directory': str(attempt), 'evidence_directory': str(tmp_path / 'evidence'),
        'composition': str(tmp_path / 'composition'), 'system_path': str(tmp_path / 'system'),
        'permission_probe': str(tmp_path / 'permission'), 'attempt_id': 'isolated-path-boundary',
        'composition_raw_json': '{"policy":{"readonly_lookups":{"inputs":[],"output_directories":[]}}}'}
    request = {'kind': capture.REQUEST_KIND, 'version': capture.REQUEST_VERSION,
        'count': capture.MAX_CAPTURES, 'directory': str(directory), 'deadline_seconds': 60,
        'prompt_sha256': capture.sha(capture.CAPTURE_PROMPT.encode()),
        'max_stdout_bytes': capture.MAX_STREAM_BYTES, 'max_stderr_bytes': capture.MAX_STREAM_BYTES}
    monkeypatch.setattr(registration, 'verified', lambda *a: deepcopy(value))
    monkeypatch.setattr(review, 'validate_bundle', lambda *a: {'quota_capture': request})
    monkeypatch.setattr(runtime, 'validate_prepared_runtime', lambda value: value)
    monkeypatch.setattr(policy, 'registered_policy', lambda value: {'capture_state_directory': str(directory)})
    monkeypatch.setattr(capture.subprocess, 'Popen', lambda *a, **k: pytest.fail('overlap spawned'))
    monkeypatch.setattr(Path, 'mkdir', lambda *a, **k: pytest.fail('overlap created state'))
    with pytest.raises(ValueError, match='overlaps'):
        capture._authority(b'isolated registration', b'isolated review', b'{}', directory)
    assert not directory.exists()


@pytest.mark.skipif(sys.platform != 'darwin', reason='real macOS permission alias boundary')
def test_permission_producer_alias_refuses_before_effects_with_source_checks_real(tmp_path, monkeypatch):
    authority = tmp_path / 'authority'; authority.mkdir()
    directory = _case_alias(authority) / 'permission-output'
    sources = []
    for name in ('native_permission_probe', 'native_probe_provider', 'native_subscription_guard'):
        path = Path(permission.__file__).with_name(name + '.py')
        raw = path.read_bytes()
        sources.append({'module': 'data_sheets_schema.' + name, 'path': str(path.resolve()),
                        'sha256': permission.sha(raw), 'bytes': len(raw)})
    expected = {'production_sources': sources, 'policy': {'readonly_lookups': {
        'repository': str(authority), 'inputs': [], 'output_directories': []}},
        'source': {'path': str(tmp_path / 'source')},
        'runtime': {'executable': {'path': str(tmp_path / 'inert')}},
        'permission_environment': {}, 'selection': {'path': str(tmp_path / 'selection')}}
    monkeypatch.setattr(permission, '_identity', lambda *a: None)
    monkeypatch.setattr(permission, '_remaining', lambda *a: pytest.fail('overlap passed admission'))
    monkeypatch.setattr(Path, 'mkdir', lambda *a, **k: pytest.fail('overlap created output'))
    with pytest.raises(ValueError, match='overlaps'):
        permission._produce_captured(expected, directory, 1, SimpleNamespace(MAX_MEMBER=1_000_000),
            None, None, None, {'stage_root': str(tmp_path / 'stage')}, b'isolated selection')
    assert not directory.exists()
