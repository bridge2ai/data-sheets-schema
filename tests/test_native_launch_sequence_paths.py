"""Issues 6216/6224: output path refusals preserve all synthetic authority.

All native commands, host probes and launch claims are prohibited while the
invalid paths are presented. Corrected paths use only fabricated commands.
"""
from pathlib import Path

import pytest

from data_sheets_schema import native_host_power as host_power
from data_sheets_schema import native_launch_sequence as seq
from data_sheets_schema import native_sequence_start as start
from data_sheets_schema.native_u4b_policy import registered_policy
from tests import test_native_launch_sequence as fixture
from tests.test_native_launch_sequence import deny_real_commands  # noqa: F401


def saved_tree(root):
    """Include directories and ignored/hidden entries; no gitignore filtering."""
    return {str(path.relative_to(root)): None if path.is_dir() else path.read_bytes()
            for path in root.rglob('*')}


def registered_directories(paths):
    value = fixture.guard.strict_json(paths['registration'].read_bytes())['registration']
    return {name: Path(value[name]) for name in ('attempt_directory', 'evidence_directory')} | {
        'capture_state_directory': Path(registered_policy(value['runtime'])['capture_state_directory'])}


def assert_refusal_without_effects(paths, tmp_path, monkeypatch):
    before = saved_tree(tmp_path)
    called = []
    def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError('path refusal reached a probe, claim or command')
    with monkeypatch.context() as patch:
        patch.setattr(host_power, 'sequence_start', forbidden)
        patch.setattr(start, 'claim', forbidden)
        patch.setattr(seq.subprocess, 'Popen', forbidden)
        assert fixture.run_sequence(fixture.argv(paths)) == 1
    assert called == []
    assert saved_tree(tmp_path) == before
    reservations = registered_directories(paths)
    assert not reservations['attempt_directory'].exists()
    assert not reservations['evidence_directory'].exists()


@pytest.mark.parametrize('reserved', ['attempt_directory', 'evidence_directory', 'capture_state_directory'])
@pytest.mark.parametrize('relation', ['equal', 'ancestor', 'descendant'])
def test_packet_overlap_refuses_before_effects_and_corrected_packet_can_start(tmp_path, monkeypatch, reserved, relation):
    paths = fixture.paths(tmp_path)
    target = registered_directories(paths)[reserved]
    paths['packet-directory'] = {'equal': target, 'ancestor': target.parent,
                                 'descendant': target / 'packet'}[relation]
    assert_refusal_without_effects(paths, tmp_path, monkeypatch)
    # A mistaken packet must not consume the registered attempt or damage its
    # journal: correcting only that argument permits the existing fake flow.
    paths['packet-directory'] = tmp_path / 'corrected-packet'
    calls = fixture.fake_commands(monkeypatch, paths)
    assert fixture.run_sequence(fixture.argv(paths)) == 0
    assert len(calls) == 3
    assert fixture.record(paths)['status'] == 'completed'
    directories = registered_directories(paths)
    assert not directories['attempt_directory'].exists()
    assert not directories['evidence_directory'].exists()


def test_packet_prospective_case_alias_refuses_without_creating_either_spelling(tmp_path, monkeypatch):
    paths = fixture.paths(tmp_path)
    target = registered_directories(paths)['attempt_directory']
    alias = target.with_name(target.name.lower())
    assert alias != target
    paths['packet-directory'] = alias
    assert_refusal_without_effects(paths, tmp_path, monkeypatch)
    assert not alias.exists() and not target.exists()
