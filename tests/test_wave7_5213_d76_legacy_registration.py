"""D76 explicit binding for the older registration builders (2026-10-31).

All inputs are synthetic. The builder functions are exercised locally without
launching providers, native executables, or the live registration command.
"""
from dataclasses import replace
from pathlib import Path
import runpy

import pytest

from data_sheets_schema import api_runner as api
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


def _job(spec, runtime, method):
    return {'project': spec.project, 'method': method, 'bundle': str(spec.bundle),
        'label': spec.label, 'manifest': str(spec.manifest),
        'chunks': str(spec.chunk_manifest), 'profile': 'neutral',
        'runtime': runtime, 'render_version': 9, 'run_date': '2026-10-31',
        'render_spec': {'condition': 'generic_v9'}}


@pytest.mark.parametrize('builder,runtime,method', [
    ('notes/matched_cborg_2026-09-13/prepare_registration.py', 'Claude API (direct)', 'claudecode_api'),
    ('notes/matched_cborg_2026-09-13/prepare_registration.py', 'Claude Code', 'claudecode_agent'),
    ('notes/claudecode_direct/run_direct_canary.py', 'Claude Code (direct)', 'claudecode_direct'),
])
def test_registered_legacy_builder_keeps_paths_at_corpus_root(external, monkeypatch, builder, runtime, method):
    checkout = Path(__file__).resolve().parents[1]
    namespace = runpy.run_path(str(checkout / builder))
    job = _job(external, runtime, method)
    monkeypatch.chdir(external.bundle.parent)
    spec = namespace['spec_for'](job)
    assert spec.bundle == external.bundle
    assert spec.manifest == external.manifest
    assert spec.chunk_manifest == external.chunk_manifest
    rendered = spec.render_spec()
    assert rendered['registered_input_paths'] is True
    replay = api.RunSpec.from_render_spec(rendered, project=spec.project,
        method=spec.method, label=spec.label)
    assert replay.render_spec() == rendered
    assert replay.instruction == spec.instruction


def test_explicit_binding_keeps_absolute_inputs_and_roundtrips(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external, registered_input_paths=True)
    assert spec.bundle == external.bundle
    rendered = spec.render_spec()
    assert rendered['registered_input_paths'] is True
    replay = api.RunSpec.from_render_spec(rendered, project=spec.project,
        method=spec.method, label=spec.label)
    assert replay.render_spec() == rendered
    assert replay.instruction == spec.instruction


def test_unselected_binding_is_absent_and_legacy_replay_unchanged(external, monkeypatch):
    recorded = external.render_spec()
    assert 'registered_input_paths' not in recorded
    monkeypatch.chdir(external.bundle.parent)
    replay = api.RunSpec.from_render_spec(recorded, project=external.project,
        method=external.method, label=external.label)
    assert replay.render_spec() == recorded
    assert replay.instruction == external.instruction


@pytest.mark.parametrize('value', [1, 0, 'true', None])
def test_explicit_binding_requires_boolean(external, value):
    with pytest.raises(ValueError, match='registered_input_paths'):
        replace(external, registered_input_paths=value)


@pytest.mark.parametrize('value', [1, False, 'true', None])
def test_recorded_binding_is_present_only_as_true(external, value):
    recorded = {**external.render_spec(), 'registered_input_paths': value}
    with pytest.raises(ValueError, match='registered_input_paths'):
        api.RunSpec.from_render_spec(recorded, project=external.project,
            method=external.method, label=external.label)
