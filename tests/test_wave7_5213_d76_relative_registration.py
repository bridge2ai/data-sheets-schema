"""D76-REG-3: freeze relative registered inputs, including chunk discovery.

The complete-capture display checker is the actual late SG2 guard; these fast
probes make no provider-shaped deliveries. Date: 2026-10-31, PR #5213.
"""
from dataclasses import replace
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, shared_generation as sg, chunking
from data_sheets_schema import source_heading_completed as complete
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec as shared_v1
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_source_heading_runtime_api import draft_files, selected_spec  # noqa: F401


def test_sg2_binding_relative_base_passes_actual_completed_path_guard(tmp_path, draft_files, monkeypatch):
    registered = selected_spec(tmp_path, draft_files, source_naming={})
    monkeypatch.chdir(tmp_path)
    base = replace(registered, condition='generic_v9', render_version=8,
        shared_generation_version=0, shared_generation_registration=None,
        api_playbook_version=0, receipt_completion_version=0, receipt_completion_registration=None)
    assert not base.bundle.is_absolute() and not base.chunk_manifest.is_absolute()
    assert not base.manifest.is_absolute()
    spec = replace(base, condition=registered.condition, render_version=27,
        shared_generation_version=2, shared_generation_registration=registered.shared_generation_registration,
        api_playbook_version=3, receipt_completion_version=3,
        receipt_completion_registration=registered.receipt_completion_registration)
    paths = {key: str(getattr(spec, key + '_path')) for key in ('full', 'core', 'report', 'provenance')}

    class Reader:
        def raw(self, path):
            return Path(path).read_bytes()

    complete._check_path_display(complete._live_path_display(spec), paths,
        json.loads(spec.shared_generation_registration), Reader())
    assert spec.bundle == registered.bundle
    assert spec.chunk_manifest == registered.chunk_manifest
    assert spec.manifest == registered.manifest


@pytest.mark.parametrize('selection', ['explicit', 'native', 'shared'])
def test_registered_relative_inputs_are_frozen_at_binding(external, monkeypatch, selection):
    if selection == 'shared':
        base = shared_v1(external, registration_for(external))
        changes = {}
    else:
        base = external
        changes = {'registered_input_paths': True} if selection == 'explicit' else {
            'condition': 'generic_v9', 'render_version': 16, 'runtime': 'Claude Code',
            'native_source_attribution_version': 1, 'native_source_attribution_max_checks': 3}
        if selection == 'native':
            # Renderer 16 also projects source metadata. Enrich only this
            # temporary case; the shared external fixture predates that rule.
            metadata = yaml.safe_load(external.manifest.read_bytes())
            metadata['projects'][external.project]['sources'][0]['processed_file'] = external.bundle.name
            external.manifest.write_text(yaml.safe_dump(metadata))
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(base, bundle=Path(external.bundle.name), manifest=Path(external.manifest.name),
        chunk_manifest=Path(external.chunk_manifest.name), **changes)
    assert spec.bundle == external.bundle
    assert spec.manifest == external.manifest
    assert spec.chunk_manifest == external.chunk_manifest
    rendered = spec.render_spec()
    replay = api.RunSpec.from_render_spec(rendered, project=spec.project, method=spec.method, label=spec.label)
    assert replay.render_spec() == rendered
    assert replay.instruction == spec.instruction


@pytest.mark.parametrize('selection', ['explicit', 'native', 'shared'])
@pytest.mark.parametrize('layout', ['external', 'conventional'])
def test_registered_discovered_chunk_path_is_absolute(external, tmp_path, monkeypatch, selection, layout):
    original = external
    owner = external.bundle.parent
    if layout == 'conventional':
        owner = tmp_path / 'conventional'
        bundle = owner / 'data/preprocessed/concatenated/EXTERNAL_preprocessed.txt'
        bundle.parent.mkdir(parents=True)
        bundle.write_bytes(external.bundle.read_bytes())
        manifest = owner / 'data/preprocessed/source_manifest.yaml'
        metadata = yaml.safe_load(external.manifest.read_bytes())
        metadata['projects']['EXTERNAL']['bundle'] = str(bundle)
        manifest.write_text(yaml.safe_dump(metadata))
        chunks = owner / 'data/preprocessed/chunks/EXTERNAL_chunks.yaml'
        chunks.parent.mkdir()
        chunks.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
        original = replace(external, bundle=bundle, manifest=manifest, chunk_manifest=chunks)
    if selection == 'shared':
        base = shared_v1(original, registration_for(original))
        changes = {}
    else:
        base = original
        changes = {'condition': 'generic_v8', 'registered_input_paths': True} if selection == 'explicit' else {
            'condition': 'generic_v9', 'render_version': 16, 'runtime': 'Claude Code',
            'native_source_attribution_version': 1, 'native_source_attribution_max_checks': 3}
    monkeypatch.chdir(owner)
    spec = replace(base, chunk_manifest=None, **changes)
    assert spec.bundle == original.bundle and spec.manifest == original.manifest
    assert spec.chunk_manifest == original.chunk_manifest
    assert spec.chunk_manifest.is_absolute()


def test_registered_mismatch_still_refuses(external, monkeypatch):
    base = shared_v1(external, registration_for(external))
    monkeypatch.chdir(external.bundle.parent)
    replacement = Path('different-bundle.txt')
    replacement.write_bytes(external.bundle.read_bytes())
    with pytest.raises(ValueError, match='registered project/profile/source selection differs'):
        replace(base, bundle=replacement)


def test_registered_absolute_freeze_preserves_symlink_parent_identity(tmp_path, monkeypatch):
    root = tmp_path / 'root'; root.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir()
    nested = outside / 'nested'; nested.mkdir()
    (root / 'link').symlink_to(nested, target_is_directory=True)
    (outside / 'bundle.txt').write_text('selected physical bytes\n')
    (root / 'bundle.txt').write_text('unrelated lexical decoy\n')
    monkeypatch.chdir(root)
    supplied = Path('link/../bundle.txt')
    spec = api.RunSpec(project='EXTERNAL', arm='baseline', method='custom', label='synthetic',
        condition='generic_v9', manifest=None, bundle=supplied, registered_input_paths=True)
    assert spec.bundle == root / supplied
    assert '..' in spec.bundle.parts
    assert spec.bundle.read_text() == 'selected physical bytes\n'
    assert spec.bundle.resolve() == outside / 'bundle.txt'


def test_registered_literal_replay_retains_historical_relative_spelling(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    unregistered = replace(external, condition='generic_v9')
    assert not unregistered.bundle.is_absolute()
    recorded = {**unregistered.render_spec(), 'registered_input_paths': True}
    replay = api.RunSpec.from_render_spec(recorded, project=external.project,
        method=external.method, label=external.label)
    assert replay.render_spec() == recorded
    assert str(replay.bundle) == recorded['bundle']
