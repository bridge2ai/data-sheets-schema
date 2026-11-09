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
        'model': 'historical-native-fixture-model', 'auxiliary_models': [], 'effort': 'high',
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
    assert '# Model: historical-native-fixture-model' in text
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


@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
@pytest.mark.parametrize('alias', ['/./', '//'])
def test_native_replay_checks_raw_path_spelling_before_path_objects(native_spec, monkeypatch, field, alias):
    recorded = native_spec.render_spec()
    parent, name = recorded[field].rsplit('/', 1)
    recorded[field] = parent + alias + name
    with monkeypatch.context() as patch:
        _refuse_ambient_replay(patch)
        with pytest.raises(ValueError, match='canonical absolute path'):
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


def test_native_construction_and_replay_use_validated_shared_admission(native_spec, monkeypatch):
    recorded = native_spec.render_spec()
    calls = []
    original = shared_generation.select
    def admitted(spec):
        calls.append(spec.native_shared_generation_version)
        result = original(spec)
        assert result is None  # Native admission never selects an API mode.
        return result
    monkeypatch.setattr(shared_generation, 'select', admitted)
    current = replace(native_spec)
    assert current.native_shared_generation_version == 1
    restored = api.RunSpec.from_render_spec(recorded, project=native_spec.project,
        method=native_spec.method, label=native_spec.label)
    assert restored.render_spec() == recorded
    assert calls == [1, 1]
    # Mixed axes must fail the native validator before the API boundary cut.
    with pytest.raises(ValueError, match='cannot mix old/API axes'):
        replace(native_spec, shared_generation_version=1)
    assert calls == [1, 1]


def test_non_native_construction_still_enters_api_selector(native_spec, monkeypatch):
    calls = []
    original = shared_generation.select
    def selected(spec):
        calls.append(spec.native_shared_generation_version)
        return original(spec)
    monkeypatch.setattr(shared_generation, 'select', selected)
    historical = replace(native_spec, render_version=23, condition='generic_v9',
        native_shared_generation_version=0, native_shared_generation_registration=None)
    assert historical.native_shared_generation_version == 0
    assert calls == [0]


@pytest.mark.parametrize('change', ['condition', 'runtime', 'method', 'manifest', 'profile',
                                     'provider', 'prompt_env', 'api_axis', 'old_native_axis', 'missing_selection'])
def test_native_selectors_refuse_mixed_or_missing_inputs(native_spec, monkeypatch, change):
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
    # The API-only selector is unchanged. Native validity is enforced by the
    # public constructor before dispatch; malformed inputs cannot bypass it.
    monkeypatch.setattr(shared_generation, 'select',
                        lambda *a, **k: pytest.fail('invalid native route reached API selector'))
    with pytest.raises(ValueError):
        replace(spec)


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


def test_initial_and_final_receipt_commands_are_exact(native_spec, tmp_path):
    import hashlib
    import json
    import re
    import shlex

    commands = native.commands(native_spec)
    initial, final = commands['phase1_receipts'], commands['final_receipts']
    assert initial[-1] == '--initial-structure' and '--strict' not in initial
    assert final == (*initial[:-1], '--strict')
    text = native.instruction(native_spec)
    for command in (initial, final):
        assert text.count(shlex.join(command)) == 1
    assert 'phase1_receipts is structural only: floors remain pending' in text
    assert 'run final_receipts with strict floor acceptance' in text

    # Freeze the receipt-stage render, not a digest containing temporary paths.
    # These are independently stated expected bytes; neither expected prose nor
    # expected command spelling is obtained from the renderer under test.
    # The witness covers this paragraph and these two command blocks, not the
    # entire instruction, registration/admission, or a native execution.
    expected_paragraph = (
        'Run full_schema, full_terms and phase1_receipts on the current originals before advance. '
        'phase1_receipts is structural only: floors remain pending and no floor acceptance is claimed. '
        'Fix initial source-grounded full/receipt defects and repeat their checks before sealing. '
        'A nonzero phase1_receipts exit is retryable whatever its stdout; exit 0 with unparseable '
        'or contract-violating stdout is a sticky contract violation. '
        'After sealing, keep the original receipt at its model_files receipt path unchanged. '
        'The helper owns the completed effective receipt at the effective_receipt role; '
        'do not copy it over the original receipt. The selected final receipt check verifies the original '
        'against its seal and assesses the helper-owned effective receipt against the reconciled full record. '
        'After the receipt stage reports await_core, run derive_core, core_schema and pair; advance then binds the genuine core. '
        'Read original_source_inventory before completing typed audit stages. After assembly_complete, run audit_evidence '
        'before applying recommendations. Reconcile full, derive_final_core, validate full/core and pair, '
        'run final_receipts with strict floor acceptance and final_scope, and read final_source_inventory before each report rewrite. '
        'Run draft before final_evidence; run recorder last. Never use a stage or helper success as overall completion.'
    )
    paragraph_start = '\n\nRun full_schema, full_terms '
    paragraph_end = '\n\nRegistered maximum draft checks: '
    assert text.count(paragraph_start) == text.count(paragraph_end) == 1
    paragraph = 'Run full_schema, full_terms ' + text.split(paragraph_start, 1)[1].split(paragraph_end, 1)[0]

    paths = {
        native_spec._agentic_toolchain['python']: 'PYTHON',
        str(native_spec.manifest): 'SOURCE_MANIFEST',
        str(native_spec.bundle): 'BUNDLE',
        str(native_spec.chunk_manifest): 'CHUNK_MANIFEST',
        native_spec._native_shared_generation_capture.registration.pin.path: 'SELECTION',
    }
    assert len(paths) == 5

    def normalized_command_block(name):
        marker = '\n\n' + name + ':\n\n```bash\n'
        assert text.count(marker) == 1
        command, fence, _ = text.split(marker, 1)[1].partition('\n```\n\n')
        assert fence
        # Replace exactly one complete shell-quoted path token per input.
        # No prefix, substring, whitespace or arbitrary-absolute-path stripping:
        # a changed path, suffix, flag, quoting or prose byte remains visible.
        for path, token in paths.items():
            command, count = re.subn(
                r'(?<!\S)' + re.escape(shlex.quote(path)) + r'(?!\S)',
                token, command,
            )
            assert count == 1, (name, token, count)
        return name + ':\n\n```bash\n' + command + '\n```\n\n'

    common_command = (
        'PYTHON -m data_sheets_schema.cli --manifest SOURCE_MANIFEST receipts check '
        '--method claudecode_direct --label offline-test --project SYNTHETIC '
        '--bundle BUNDLE --chunk-manifest CHUNK_MANIFEST --native-shared-selection SELECTION '
    )
    expected = {
        'receipt_stage_contract': expected_paragraph,
        'phase1_receipts': 'phase1_receipts:\n\n```bash\n' + common_command + '--initial-structure\n```\n\n',
        'final_receipts': 'final_receipts:\n\n```bash\n' + common_command + '--strict\n```\n\n',
    }
    observed = {
        'receipt_stage_contract': paragraph,
        'phase1_receipts': normalized_command_block('phase1_receipts'),
        'final_receipts': normalized_command_block('final_receipts'),
    }
    witness = {
        'expected_normalized_sha256': hashlib.sha256(c.canonical(expected)).hexdigest(),
        'observed_normalized_sha256': hashlib.sha256(c.canonical(observed)).hexdigest(),
        'instruction_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'source_sha256': hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        'scope': 'normalized receipt-stage paragraph and two command blocks; synthetic rendering only',
    }
    (tmp_path / 'render-digests.json').write_text(json.dumps(witness, indent=2) + '\n')
    (tmp_path / 'new-instruction.txt').write_text(text)
    (tmp_path / 'normalized-receipt-render.json').write_bytes(c.canonical(observed))
    assert observed == expected
    assert witness['observed_normalized_sha256'] == witness['expected_normalized_sha256']


def test_split_receipt_commands_match_native_consumers(native_spec):
    """Integration requirement: consumers must admit the initial/final split.

    U3D-R9: retain the repaired exact eighteen-name consumer contract.
    """
    from data_sheets_schema import native_shared_phase as phase
    from data_sheets_schema import native_shared_policy as policy
    assert set(native.commands(native_spec)) == phase.COMMAND_NAMES == policy.HELPERS
