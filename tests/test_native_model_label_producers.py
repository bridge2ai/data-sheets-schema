"""Offline producer/readback coverage for the 2026-11-19 model-label amendment.

Inputs are explicit declarations and inert file bytes. Outputs are temporary
draft packets only; no native executable, account, provider or host gate runs.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_model_aliases as aliases
from data_sheets_schema import native_runtime_profiles as profiles

ROOT = Path(__file__).resolve().parents[1]
HELPERS = (
    'post_merge_fast_path_20261117.py',
    'run_post_probe_chain_e772_20261119.py',
    'compare_post_probe_envelopes_e772_20261119.py',
)


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


def runtime_for(version, *, final=False, synthetic=False):
    requested = profiles.SYNTHETIC_REQUESTED if synthetic else aliases.REQUESTED
    returned = profiles.SYNTHETIC_RETURNED if synthetic else aliases.RETURNED
    pair = dict(requested=requested, returned=returned)
    if version == (4 if final else 2):
        pair['reported'] = returned
    basis = dict(kind=aliases.KIND if final else aliases.PROVISIONAL_KIND,
                 version=version, model_aliases=pair)
    if synthetic:
        basis['profile'] = profiles.SYNTHETIC_PROFILE
    return dict(model=requested, auxiliary_models=[], limits_basis=json.dumps(basis),
                limits=dict(contextWindow=1000000, maxOutputTokens=64000))


def test_all_helper_reads_follow_declared_reported_model_and_preserve_old_profiles():
    for name in HELPERS:
        helper = load_script('scripts/adhoc/' + name)
        for runtime, label in (
                (runtime_for(1), aliases.REQUESTED),
                (runtime_for(2), aliases.RETURNED),
                (runtime_for(2, final=True), aliases.REQUESTED),
                (runtime_for(3, final=True), aliases.REQUESTED),
                (runtime_for(4, final=True), aliases.RETURNED),
                (runtime_for(1, synthetic=True), profiles.SYNTHETIC_REQUESTED),
                (dict(model='historical-model', limits_basis='historical'), 'historical-model')):
            usage = dict(contextWindow=1000000, maxOutputTokens=64000)
            terminal = dict(modelUsage={label: usage})
            before = deepcopy((runtime, terminal))
            assert helper.observed_model_usage(runtime, terminal) == usage
            assert (runtime, terminal) == before


def test_all_helper_reads_refuse_label_downgrade_mixing_and_non1m():
    for name in HELPERS:
        helper = load_script('scripts/adhoc/' + name)
        for version, labels, context in (
                (2, (aliases.REQUESTED,), 1000000),
                (1, (aliases.RETURNED,), 1000000),
                (2, (aliases.RETURNED, aliases.REQUESTED), 1000000),
                (2, (aliases.RETURNED,), 200000)):
            terminal = dict(modelUsage={label: dict(contextWindow=context, maxOutputTokens=64000)
                                        for label in labels})
            with pytest.raises(ValueError):
                helper.observed_model_usage(runtime_for(version), terminal)


def test_fastpath_switch_default_and_reentry_are_explicit():
    helper = load_script('scripts/adhoc/post_merge_fast_path_20261117.py')
    helper.A = SimpleNamespace()
    assert helper.model_label_args() == []
    helper.A.model_label_version = 1
    assert helper.model_label_args() == []
    helper.A.model_label_version = 2
    assert helper.model_label_args() == ['--model-label-version', '2']
    helper.A.model_label_version = True
    with pytest.raises(ValueError, match='explicit 1 or 2'):
        helper.model_label_args()
    assert helper.HERE == ROOT / 'scripts/adhoc/post_merge_fast_path_20261117.py'
