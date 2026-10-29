"""F2/F3/F5/F7/F19: selection follows declarations, never project spelling."""
import json
from pathlib import Path
import pytest
import yaml

from scripts import build_draft_contexts as contexts, build_api_registrations as builder


@pytest.mark.parametrize('name', ['NEWPROJ', 'KIDS_FIRST', 'CHORUS'])
def test_undeclared_profile_and_ranking_are_neutral_for_every_name(tmp_path, monkeypatch, name):
    monkeypatch.delenv('D4D_PROFILE', raising=False)
    manifest = tmp_path / 'manifest.yaml'
    manifest.write_text(yaml.safe_dump({'projects': {name: {'sources': []}},
        'scope': {name: {'referent_id': 'example:release', 'release': None}}}))
    doc = builder.build_draft_context(name, manifest, write_to_disk=False)
    assert doc['vocabulary'] == {}
    assert doc['source_policy'] == {'priority': [], 'basis': 'No source ranking declared.'}
    assert doc['scopes'][0]['release'] is None
    metadata = yaml.safe_load(manifest.read_bytes())
    del metadata['scope'][name]['release']
    assert contexts.build_draft_scope_context(name, metadata)['scopes'][0]['release'] == 'example:release'


def test_unknown_context_profile_refuses(monkeypatch):
    monkeypatch.delenv('D4D_PROFILE', raising=False)
    with pytest.raises(ValueError, match='unknown profile'):
        contexts.build_draft_scope_context('NEWPROJ', {'profile': 'invented'})


@pytest.mark.parametrize('project', ['NEWPROJ', 'KIDS_FIRST'])
def test_no_implicit_study_or_named_manifest(tmp_path, monkeypatch, project):
    monkeypatch.delenv('D4D_MANIFEST', raising=False)
    with pytest.raises(ValueError, match='No manifest declares'):
        builder.build_registration(project, 'synthetic', registration_path=tmp_path / 'reg.json',
            audit_limits={'max_paths': 80, 'max_inventory_bytes': 12288, 'max_workers': 4,
                          'aggregate_input_tokens': 4000000})
    assert list(tmp_path.iterdir()) == []


def test_explicit_manifest_cannot_claim_undeclared_project(tmp_path):
    manifest = tmp_path / 'manifest.yaml'
    manifest.write_text('projects: {OTHER: {sources: []}}\nprofile: bridge2ai\n')
    with pytest.raises(ValueError, match='does not declare'):
        builder.build_registration('NEWPROJ', 'synthetic', source_manifest_path=manifest,
            registration_path=tmp_path / 'reg.json', audit_limits={
                'max_paths': 80, 'max_inventory_bytes': 12288, 'max_workers': 4,
                'aggregate_input_tokens': 4000000})
    assert not (tmp_path / 'reg.json').exists()
