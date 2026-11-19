"""Offline draft-producer coverage for the 2026-11-19 model-label amendment.

Operator wrappers (fast path, post-probe chain, envelope comparison) are not
in this repository; they are updated and checked with the operator tooling
(issues 6297, 6298).

Inputs are explicit declarations and inert file bytes. Outputs are temporary
draft packets only; no native executable, account, provider or host gate runs.
"""
import importlib.util
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_model_aliases as aliases

ROOT = Path(__file__).resolve().parents[1]


def load_script(relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location('_label_producer_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def draft_inputs(tmp_path):
    binary = tmp_path / 'INERT-NEVER-EXECUTE'
    binary.write_bytes(b'Inert fingerprint only; never executable code.\n')
    binary.chmod(0o700)
    manifest = tmp_path / 'manifest.yaml'
    manifest.write_text('projects:\n  CHORUS: []\n')
    return binary, manifest


def read_draft(path):
    return json.loads((path / 'provisional-runtime.DRAFT.json').read_bytes())['candidate_runtime']


def test_explicit_legacy_draft_is_byte_identical_to_default(tmp_path):
    draft = load_script('scripts/draft_native_probe_packet.py')
    binary, manifest = draft_inputs(tmp_path)
    first, second = tmp_path / 'default', tmp_path / 'explicit'
    kwargs = dict(project='CHORUS', source_manifest=manifest)
    draft.generate(ROOT, binary, first, **kwargs)
    draft.generate(ROOT, binary, second, model_label_version=1, **kwargs)
    for name in ('provisional-runtime.DRAFT.json', 'authorization.DRAFT.json',
                 'probe-packet.DRAFT.json', 'probe-packet.DRAFT.md'):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    runtime = read_draft(first)
    basis = json.loads(runtime['limits_basis'])
    assert basis == dict(kind=aliases.PROVISIONAL_KIND, version=1,
        model_aliases=dict(requested=aliases.REQUESTED, returned=aliases.RETURNED))


def test_explicit_new_draft_declares_reported_label_and_exact_window(tmp_path):
    draft = load_script('scripts/draft_native_probe_packet.py')
    binary, manifest = draft_inputs(tmp_path)
    output = tmp_path / 'new'
    draft.generate(ROOT, binary, output, project='CHORUS', source_manifest=manifest,
                   model_label_version=2)
    runtime = read_draft(output)
    basis = json.loads(runtime['limits_basis'])
    assert basis == dict(kind=aliases.PROVISIONAL_KIND, version=2,
        model_aliases=dict(requested=aliases.REQUESTED, returned=aliases.RETURNED,
                           reported=aliases.RETURNED))
    assert runtime['model'] == aliases.REQUESTED
    assert runtime['limits']['contextWindow'] == 1000000
    assert aliases.model_aliases(runtime) == basis['model_aliases']
    packet = json.loads((output / 'probe-packet.DRAFT.json').read_bytes())
    assert packet['no_execution'] is True
    assert any(fact.get('function') == 'validate_provisional_runtime'
               and fact.get('field') == 'version' and fact['value'] == 2
               for fact in packet['source_facts'])
    authorization = json.loads((output / 'authorization.DRAFT.json').read_bytes())
    assert authorization['candidate_authorization']['word'] == 'DRAFT_NOT_AUTHORIZED'


def test_draft_refuses_nonexplicit_or_unknown_label_version_before_writing(tmp_path):
    draft = load_script('scripts/draft_native_probe_packet.py')
    binary, manifest = draft_inputs(tmp_path)
    for index, version in enumerate((False, True, '2', None, 0, 3)):
        output = tmp_path / str(index)
        with pytest.raises(ValueError, match='explicit 1 or 2'):
            draft.generate(ROOT, binary, output, project='CHORUS', source_manifest=manifest,
                           model_label_version=version)
        assert not output.exists()


def test_draft_alias_declaration_ignores_imported_checkout(tmp_path, monkeypatch):
    draft = load_script('scripts/draft_native_probe_packet.py')
    binary, manifest = draft_inputs(tmp_path)

    def unexpected_imported_validator(runtime):
        raise AssertionError('draft consulted an imported alias validator')

    monkeypatch.setattr(aliases, 'model_aliases', unexpected_imported_validator)
    monkeypatch.setattr(aliases, 'REQUESTED', 'stale-imported-requested-model')
    monkeypatch.setattr(aliases, 'RETURNED', 'stale-imported-returned-model')
    output = tmp_path / 'selected-source'
    draft.generate(ROOT, binary, output, project='CHORUS', source_manifest=manifest,
                   model_label_version=2)
    runtime = read_draft(output)
    assert runtime['model'] == 'claude-opus-5[1m]'
    assert json.loads(runtime['limits_basis'])['model_aliases'] == dict(
        requested='claude-opus-5[1m]', returned='claude-opus-5', reported='claude-opus-5')
