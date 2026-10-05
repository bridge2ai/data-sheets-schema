"""Native26 selection and rendering cannot inherit an API/default identity."""
from dataclasses import replace
import copy
from pathlib import Path

import pytest

from tests.test_native_shared_selection import declaration, artifact, pin, save
from data_sheets_schema import api_runner as api
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_render as native
from data_sheets_schema import native_shared_selection as selected
from data_sheets_schema import shared_generation


@pytest.fixture
def native_spec(declaration, tmp_path, monkeypatch):
    doc = declaration
    manifest = tmp_path.resolve() / 'source-manifest.yaml'
    raw = b'profile: neutral\nprojects: {}\n'
    manifest.write_bytes(raw)
    doc['inputs']['source_manifest'] = pin(manifest, raw)
    save(doc)
    monkeypatch.setattr(api, '_model_settings', lambda: pytest.fail('API model fallback'))
    monkeypatch.setattr(api, 'provider_identity', lambda: pytest.fail('API provider fallback'))
    spec = api.RunSpec(**doc['run'], bundle=Path(doc['inputs']['bundle']['path']),
        manifest=manifest, chunk_manifest=Path(doc['inputs']['chunk_manifest']['path']),
        condition='generic_v10', render_version=26, runtime=c.RUNTIME,
        profile='neutral', profile_basis='explicit caller', provider='synthetic provider',
        reasoning_effort='high', prompt_text_env=True, run_date='2026-10-05',
        native_shared_generation_version=1, native_shared_generation_registration=c.canonical(doc).decode())
    from data_sheets_schema.native_execution_registration import ROUTE
    runtime = {'route': ROUTE,
        'executable': {'path': '/synthetic/not-executed', 'sha256': 'a' * 64,
                       'version': 'synthetic', 'init_version': 'synthetic'},
        'model': 'synthetic-native-model', 'auxiliary_models': [], 'effort': 'high',
        'limits': {'contextWindow': 10000, 'maxOutputTokens': 1000},
        'limits_basis': 'synthetic test declaration, not observation',
        'provider': 'synthetic provider', 'auth': {'test': 'not authenticated'},
        'environment': {}, 'deadline_seconds': 60, 'budget_guard_usd': '1',
        'keep_awake': {'policy': 'not_applicable', 'host_platform': 'synthetic',
                       'basis': 'offline rendering only'}}
    spec._native_shared_runtime_capture = artifact('runtime_declaration', tmp_path.resolve() / 'runtime.json', c.canonical(runtime))
    spec._native_shared_max_draft_checks = 2
    return spec


def test_native_instruction_roundtrip_uses_only_sole_runtime(native_spec, monkeypatch):
    spec = native_spec
    text = spec.instruction
    recorded = spec.render_spec()
    assert '# Model: synthetic-native-model' in text
    assert '# Provider: synthetic provider' in text
    assert '# Temperature: unknown (not observed from the agent runtime)' in text
    assert 'Registered maximum draft checks: 2.' in text
    assert 'READ FIRST, IN THIS ORDER' not in text
    assert 'OUTPUTS — do not write outside these three' not in text
    assert 'Each worker runs in a fresh native context' not in text
    assert 'at most two immutable grammar drafts' not in text
    assert 'Write the Phase 3 audit JSON' not in text
    assert 'native_shared_stage advance --registration' in text
    assert 'run derive_core, core_schema and pair; advance then binds the genuine core' in text
    assert '--native-shared-selection' in text
    assert 'keep the original receipt at its model_files receipt path unchanged' in text
    assert 'assesses the helper-owned effective receipt against the reconciled full record' in text
    assert '## Role relationship review v1' in text
    assert recorded['native_shared_generation_context'] == spec._native_shared_generation_capture.generation_context()
    assert not any(key.startswith(('shared_generation_', 'receipt_completion_', 'api_playbook_',
                                  'native_source_attribution_')) for key in recorded)
    # Replay does not reread live user inputs. Fixed installed policy assets
    # are still verified independently, as for historical renderers.
    for name in ('bundle', 'chunk_manifest', 'context', 'source_manifest'):
        declared = spec._native_shared_generation_capture.document()['inputs'][name]
        Path(declared['path']).write_text('Changed live input after capture.\n')
    restored = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert restored.render_spec() == recorded
    assert restored.instruction == text


def _refuse_ambient_replay(patch):
    from data_sheets_schema import corpus
    def forbidden(*args, **kwargs):
        pytest.fail('captured native replay consulted ambient paths or bytes')
    patch.setattr(api, 'select_manifest', forbidden)
    patch.setattr(corpus, 'root', forbidden)
    for name in ('cwd', 'resolve', 'absolute', 'read_bytes', 'read_text', 'open'):
        patch.setattr(Path, name, forbidden)


def test_native_captured_restore_does_not_discover_or_normalize_paths(native_spec, monkeypatch):
    recorded = native_spec.render_spec()
    with monkeypatch.context() as patch:
        _refuse_ambient_replay(patch)
        restored = api.RunSpec.from_render_spec(recorded, project=native_spec.project,
            method=native_spec.method, label=native_spec.label)
        assert restored.render_spec() == recorded


@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
def test_native_captured_inputs_refuse_relative_paths_without_ambient_lookup(native_spec, monkeypatch, field):
    recorded = native_spec.render_spec()
    recorded[field] = 'relative/' + Path(recorded[field]).name
    with monkeypatch.context() as patch:
        _refuse_ambient_replay(patch)
        with pytest.raises(ValueError, match='path'):
            api.RunSpec.from_render_spec(recorded, project=native_spec.project,
                method=native_spec.method, label=native_spec.label)


def test_historical_native_replay_retains_existing_corpus_initialization(native_spec, monkeypatch):
    from data_sheets_schema import corpus
    historical = replace(native_spec, render_version=23, condition='generic_v9',
        native_shared_generation_version=0, native_shared_generation_registration=None)
    recorded = historical.render_spec()
    calls = []
    select, root = api.select_manifest, corpus.root
    def selected(*args, **kwargs):
        calls.append('manifest')
        return select(*args, **kwargs)
    def rooted(*args, **kwargs):
        calls.append('root')
        return root(*args, **kwargs)
    monkeypatch.setattr(api, 'select_manifest', selected)
    monkeypatch.setattr(corpus, 'root', rooted)
    restored = api.RunSpec.from_render_spec(recorded, project=historical.project,
        method=historical.method, label=historical.label)
    assert restored.render_spec() == recorded
    assert calls == ['manifest', 'root']


def test_no_runtime_or_draft_allowance_means_no_instruction(native_spec):
    native_spec._native_shared_runtime_capture = None
    with pytest.raises(ValueError, match='sole captured runtime'):
        native_spec.render_spec()
    with pytest.raises(ValueError, match='sole captured runtime'):
        api.resolve_prompt(native_spec)


@pytest.mark.parametrize('change', ['condition', 'runtime', 'method', 'manifest', 'profile',
                                     'provider', 'prompt_env', 'api_axis', 'old_native_axis', 'missing_selection'])
def test_native_selectors_refuse_mixed_or_missing_inputs(native_spec, change):
    spec = native_spec
    if change == 'condition': spec.condition = 'generic_v9'
    elif change == 'runtime': spec.runtime = 'Claude API (direct)'
    elif change == 'method': spec.method = 'claudecode_agent'
    elif change == 'manifest': spec.manifest = None
    elif change == 'profile': spec.profile = None
    elif change == 'provider': spec.provider = None
    elif change == 'prompt_env': spec.prompt_text_env = False
    elif change == 'api_axis': spec.shared_generation_version = 1
    elif change == 'old_native_axis': spec.native_source_attribution_version = 1
    else: spec.native_shared_generation_registration = None
    with pytest.raises(ValueError):
        native.validate_spec(spec)
    if change != 'api_axis':
        with pytest.raises(ValueError):
            shared_generation.select(spec)


@pytest.mark.parametrize('change', ['runtime_model', 'runtime_effort', 'runtime_hash', 'context_raw',
                                   'context_pin', 'descriptor', 'receipt_policy', 'extra', 'draft_bool'])
def test_recorded_native_metadata_tampering_is_rejected(native_spec, change):
    recorded = native_spec.render_spec()
    if change in {'runtime_model', 'runtime_effort'}:
        identity = recorded['native_shared_runtime_declaration']
        raw = c.strict_json(identity['raw_json'].encode())
        raw['model' if change == 'runtime_model' else 'effort'] = '--foreign' if change == 'runtime_model' else 'low'
        identity.update(raw_json=c.canonical(raw).decode(), sha256=c.sha(c.canonical(raw)))
    elif change == 'runtime_hash': recorded['native_shared_runtime_declaration']['sha256'] = 'f' * 64
    elif change == 'context_raw': recorded['native_shared_generation_context']['context']['raw_json'] += ' '
    elif change == 'context_pin': recorded['native_shared_generation_context']['context']['identity']['sha256'] = 'f' * 64
    elif change == 'descriptor': recorded['native_shared_generation_descriptor']['renderer'] = 25
    elif change == 'receipt_policy': recorded['native_shared_receipt_policy']['path'] = '/substituted/receipt.json'
    elif change == 'extra': recorded['native_shared_unknown'] = True
    else: recorded['native_shared_max_draft_checks'] = True
    with pytest.raises(ValueError):
        api.RunSpec.from_render_spec(recorded, project=native_spec.project, method=native_spec.method, label=native_spec.label)


def test_native_selection_cannot_dispatch_through_api(native_spec):
    with pytest.raises(ValueError, match='native stage controller'):
        api.build_phase(native_spec, 'full', carry={})
    with pytest.raises(ValueError, match='native execution registration'):
        api.execute(native_spec, dry_run=False)
    with pytest.raises(ValueError, match='native execution registration'):
        api.execute(native_spec, dry_run=True)


def test_native_assembly_has_separate_identity_and_reciprocal_axis_guards(native_spec):
    actual = api.assembly_digest(26, native_shared_generation_version=1)
    assert actual == native.assembly_digest()
    assert 'native_shared_generation_v1' in actual['layout']
    for arguments in ({}, {'shared_generation_version': 1},
                      {'native_shared_generation_version': 1, 'receipt_completion_version': 2},
                      {'native_shared_generation_version': True}):
        with pytest.raises(ValueError):
            api.assembly_digest(26, **arguments)
    with pytest.raises(ValueError):
        api.assembly_digest(25, native_shared_generation_version=1)


def test_command_roster_uses_stage_originals_and_complete_recorded_context(native_spec):
    commands = native.commands(native_spec)
    cap = native_spec._native_shared_generation_capture
    assert cap.role('phase1_full') in commands['audit_evidence']
    assert cap.role('phase1_core') in commands['audit_evidence']
    assert cap.role('audit') in commands['audit_evidence']
    assert commands['advance'][-1] == cap.registration.pin.path
    for name in ('derive_core', 'derive_final_core', 'pair'):
        for kind in ('full', 'core'):
            flag = '--' + kind + '-schema'
            assert commands[name].count(flag) == 1
            assert commands[name][commands[name].index(flag) + 1] == cap.document()['inputs'][kind + '_schema']['root']
    assert commands['draft'][2] == 'data_sheets_schema.source_attribution_preflight'
    assert commands['recorder'][-2:] == ('--prompt-text-env', 'D4D_LAUNCH_INSTRUCTION')
    assert tuple(commands['recorder'][i + 1] for i, item in enumerate(commands['recorder'])
                 if item == '--prompt') == tuple(selected.ASSET_HASHES)
    import json
    recorded = json.loads(commands['recorder'][commands['recorder'].index('--render-spec-json') + 1])
    assert recorded == native_spec.render_spec()
