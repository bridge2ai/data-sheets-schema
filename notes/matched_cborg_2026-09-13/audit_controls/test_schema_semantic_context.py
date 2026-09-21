"""Real frozen-pair preparation and ancestry for selected schema semantics.

Historical acceptance/accounting and Git attestation use the shared synthetic
ancestry fixture. Rendering, schema authority, pins, draft lifecycle and Phase 4
preparation are real; no provider, owner or ledger API is invoked.
"""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import contract, contract_context, draft_output, prepare, registration
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_draft_registration import accepted_drafted_audit, required_cli
from finalization_controls import prepare as final_prepare, registration as final_registration
from evaluation_controls import registration as evaluation_registration
from data_sheets_schema import api_runner, profiles, schema_semantics
import native_context as frames
import run_api_canary
import run_native_canary
import sequence_claim

KEY = registration.TRANSITION
BLOCK = {'kind': 'frozen_pair_schema_semantics_v1'}


def selected(**extra):
    return {'kind': 'd4d_native_audit_continuation', 'schema_version': 1,
            'protocol_version': 6, 'render_version': 19, KEY: deepcopy(BLOCK), **extra}


@pytest.mark.parametrize('value', [None, False, True, [], {}, BLOCK['kind'],
    {'kind': 'unknown'}, {**BLOCK, 'extra': True}, {'kind': registration.DRAFT_GRAMMAR_TRANSITION_KIND}])
def test_exact_transition_precedes_audit_and_phase4_setup(tmp_path, value):
    for validator, kind in ((registration.validate_registration, 'd4d_native_audit_continuation'),
                            (final_registration.validate_registration, final_registration.KIND)):
        path = save(tmp_path/'registration.json', selected(kind=kind, **{KEY: value}))
        with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
            validator(path)
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('changes', [{'protocol_version': 5}, {'protocol_version': 6.0},
    {'protocol_version': True}, {'render_version': 18}, {'render_version': 19.0}, {'render_version': True}])
def test_exact_integer_instrument(changes):
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.scientific_contract(selected(**changes))


@pytest.mark.parametrize('value', [None, 0, 1, 'true', [], {}])
def test_option_requires_boolean_before_writes(tmp_path, value):
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=tmp_path/'absent',
            job_id='unused', repository=tmp_path, schema_semantic_context=value)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('other', [None, 'staged_audit_output', 'upgrade_evidence_protocol',
                                'source_metadata_evidence', 'clarify_source_claims'])
def test_requires_drafts_and_rejects_contradictory_selectors_before_writes(tmp_path, other):
    flags = {} if other is None else {'draft_audit_grammar': True, other: True}
    with pytest.raises(registration.BudgetStop, match='explicit draft|exclusively'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=tmp_path/'absent',
            job_id='unused', repository=tmp_path, schema_semantic_context=True, **flags)
    assert not list(tmp_path.iterdir())


def test_cli_requires_explicit_coupled_selection(monkeypatch):
    class Captured(Exception):
        pass
    def capture(**kwargs):
        assert kwargs['schema_semantic_context'] is True and kwargs['draft_audit_grammar'] is True
        assert not any(kwargs[name] for name in ('staged_audit_output', 'upgrade_evidence_protocol',
                                               'source_metadata_evidence', 'clarify_source_claims'))
        raise Captured
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(), '--schema-semantic-context',
                                    '--draft-audit-grammar'])
    monkeypatch.setattr(prepare, 'prepare', capture)
    with pytest.raises(Captured):
        prepare.main()


def test_renderer19_draft_helper_requires_exact_transition_and_mode(tmp_path):
    m = selected(audit_drafting={})
    del m[KEY]
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        draft_output.configuration(m)
    path = save(tmp_path/'registration.json', selected())
    with pytest.raises(registration.BudgetStop, match='drafting registration'):
        registration.validate_registration(path)


@pytest.mark.parametrize('persistent,recovery', [(False, False), (True, False), (True, True)])
def test_real_preparation_preserves_pair_and_delivers_exact_selected_schema_context(
        metadata_ancestry, tmp_path, monkeypatch, persistent, recovery):
    args, _, preserved, state = metadata_ancestry
    options = dict(draft_audit_grammar=True, persistent_audit_contract=persistent,
                   context_recovery=recovery, durable_sequence_claim=True)
    old_path = prepare.prepare(**args, destination=tmp_path/'v18', **options)
    old = registration.validate_registration(old_path)
    old_bytes = {p: p.read_bytes() for p in old_path.parent.rglob('*') if p.is_file()}
    actual_build = api_runner.build_phase
    passed_schemas = []
    def build(spec, phase, **kwargs):
        if spec.render_version == 19 and phase == 'audit':
            passed_schemas.append(kwargs.get('_audit_schema_paths'))
        return actual_build(spec, phase, **kwargs)
    monkeypatch.setattr(api_runner, 'build_phase', build)
    path = prepare.prepare(**args, destination=tmp_path/'v19', schema_semantic_context=True, **options)
    m = registration.validate_registration(path)
    assert (m['protocol_version'], m['render_version'], m[KEY]) == (6, 19, BLOCK)
    assert len(m['inputs']) == 11 and set(m['inputs']) == set(old['inputs'])
    for role in m['inputs']:
        assert Path(m['inputs'][role]).read_bytes() == Path(old['inputs'][role]).read_bytes()
    assert passed_schemas and set(passed_schemas) == {
        (Path(m['inputs']['full_schema']), Path(m['inputs']['core_schema']))}
    instruction = Path(m['job']['instruction']).read_text()
    system = Path(m['job']['system_prompt']).read_text()
    assert 'protocol 6 / renderer 19' in instruction and 'original generation remains renderer 14' in instruction
    assert instruction.count(api_runner.SCHEMA_SEMANTICS_HEADER_V19) == 1
    guidance = schema_semantics.render_pair(
        Path(m['inputs']['original_full']).read_text(),
        Path(m['inputs']['original_core']).read_text(),
        schema_paths=(Path(m['inputs']['full_schema']), Path(m['inputs']['core_schema'])),
        profile=profiles.profile_named(m['profile']))
    assert guidance in instruction
    marker = '## Exact registered protocol (reference data)'
    assert (marker in instruction) is not persistent
    assert marker in Path(old['job']['instruction']).read_text()
    protocol = Path(m['inputs']['protocol']).read_bytes().decode('utf-8')
    if persistent:
        assert system.count(protocol) == 1
        assert api_runner.evidence_phase_contract('audit', 19) in system
    assert api_runner.SCHEMA_SEMANTICS_HEADER_V19 not in system
    helper = str(Path(m['repository'])/'src/data_sheets_schema/schema_semantics.py')
    assert helper not in old['pinned_files']
    assert m['pinned_files'][helper] == registration.sha(helper)
    assert set(map(str, registration.schema_semantic_paths(m))) <= m['pinned_files'].keys()
    readable = set(m['inputs'].values()) | {m['job']['instruction'], m['job']['system_prompt']}
    if recovery:
        readable.update(frames.bounded_paths(m['context_recovery']))
    assert set(m['job']['readable_inputs']) == readable and helper not in readable
    for key in ('model', 'profile', 'provider_context_policy', 'native_runtime'):
        assert m[key] == old[key]
    assert m['budget']['continuation'] == old['budget']['continuation']
    assert m['budget']['prices_per_token'] == old['budget']['prices_per_token']
    assert m['sequence_state'] == old['sequence_state'] == str(state)
    assert sequence_claim.enabled(m) and not (path.parent/'sequence_claim').exists()
    assert not Path(m['budget']['ledger_path']).exists() and not Path(m['job']['attempt_dir']).exists()
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    assert old_bytes == {name: name.read_bytes() for name in old_bytes}
    plan = registration.read_json(path.parent/'offline_plan.json')
    assert (plan['protocol_version'], plan['render_version'], plan['parent_render_version']) == (6, 19, 14)
    assert plan[KEY] == BLOCK and plan['scientific_instrument_unchanged'] is False


@pytest.mark.parametrize('damage', ['helper_pin', 'schema_input', 'protocol_system', 'null_persistent'])
def test_repinning_cannot_drop_authority_or_required_persistent_protocol(
        metadata_ancestry, tmp_path, damage):
    path = prepare.prepare(**metadata_ancestry[0], destination=tmp_path/'v19',
        draft_audit_grammar=True, schema_semantic_context=True, persistent_audit_contract=True)
    m = registration.validate_registration(path)
    if damage == 'helper_pin':
        del m['pinned_files'][str(Path(m['repository'])/'src/data_sheets_schema/schema_semantics.py')]
    elif damage == 'schema_input':
        copied = tmp_path/'different-authority.yaml'
        copied.write_bytes(Path(m['inputs']['full_schema']).read_bytes())
        m['inputs']['full_schema'] = str(copied)
        m['pinned_files'][str(copied)] = registration.sha(copied)
        with pytest.raises(ValueError, match='full_schema authority'):
            contract.render_instruction(m)
    elif damage == 'protocol_system':
        system = Path(m['job']['system_prompt'])
        system.write_bytes(system.read_bytes().replace(Path(m['inputs']['protocol']).read_bytes(), b''))
        m['pinned_files'][str(system)] = registration.sha(system)
    else:
        m['audit_contract_context'] = None
        with pytest.raises(registration.BudgetStop, match='persistent audit contract'):
            contract.render_instruction(m)
    save(path, m)
    with pytest.raises(registration.BudgetStop):
        registration.validate_registration(path)
    assert not Path(m['job']['attempt_dir']).exists()


def test_transitive_schema_imports_are_selected_pins(tmp_path):
    imported = tmp_path/'nested.yaml'
    imported.write_text('id: https://example.org/nested\nname: nested\nclasses:\n  Nested:\n    description: Complete nested meaning.\n')
    schema = tmp_path/'schema.yaml'
    schema.write_text('id: https://example.org/schema\nname: schema\nimports: [nested]\nclasses:\n  Dataset:\n    attributes:\n      member:\n        range: Nested\n')
    m = selected(inputs={'full_schema': str(schema), 'core_schema': str(schema)})
    assert registration.schema_semantic_paths(m) == {schema, imported}
    old = dict(m, render_version=18, **{KEY: {'kind': registration.DRAFT_GRAMMAR_TRANSITION_KIND}})
    assert registration.schema_semantic_paths(old) == set()


@pytest.mark.parametrize('correction', [False, True])
def test_real_phase4_inherits_selected_instrument_and_all_draft_pins_but_no_audit_mode(
        metadata_ancestry, tmp_path, correction):
    case, acceptance, evidence, closure = accepted_drafted_audit(metadata_ancestry,
        tmp_path/'accepted', correction=correction, schema_semantic_context=True)
    preserved = {p: p.read_bytes() for p in case.reg.parent.rglob('*') if p.is_file()}
    path = final_prepare.prepare(accepted_audit_registration=case.reg, acceptance=acceptance,
        destination=tmp_path/'phase4', job_id='synthetic_final', repository=metadata_ancestry[0]['repository'],
        context_recovery=True, durable_sequence_claim=True)
    m = final_registration.validate_registration(path)
    assert (m['protocol_version'], m['render_version'], m[KEY]) == (6, 19, BLOCK)
    assert not {'audit_drafting', 'audit_output', 'audit_contract_context', 'schema_semantic_context',
                'native_stall_policy', 'native_upstream_read_timeout_seconds'} & m.keys()
    assert m['inputs'] == {**case.m['inputs'], 'audit': str(case.target)}
    assert m['parent'] == case.m['parent'] and sequence_claim.enabled(m)
    assert m['budget']['per_job_attempt_usd'] == {'synthetic_final': '20'}
    assert m['job']['deadline_seconds'] == 10800
    assert len(evidence['phase3']['audit_drafts']) == (2 if correction else 1)
    assert closure <= final_registration.required_paths(m)
    assert set(case.m['pinned_files']) <= m['pinned_files'].keys()
    helper = str(Path(m['repository'])/'src/data_sheets_schema/schema_semantics.py')
    assert m['pinned_files'][helper] == case.m['pinned_files'][helper]
    assert api_runner.SCHEMA_SEMANTICS_HEADER_V19 not in Path(m['job']['instruction']).read_text()
    assert api_runner.phase_instruction('reconcile_full', 19) in Path(m['job']['instruction']).read_text()
    assert not Path(m['job']['attempt_dir']).exists() and not Path(m['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
    assert preserved == {p: p.read_bytes() for p in preserved}


def test_phase4_cannot_repin_a_different_semantics_implementation(tmp_path):
    accepted_root, descendant_root = tmp_path/'accepted', tmp_path/'descendant'
    shared = ('api_runner.py', 'evidence_assertions.py', 'source_review.py', 'report_claims.py',
              'derive_core.py', 'd4d_pair_consistency.py', 'profiles.py', 'schema_digest.py')
    for root in (accepted_root, descendant_root):
        (root/'src/data_sheets_schema').mkdir(parents=True)
        for name in shared:
            (root/'src/data_sheets_schema'/name).write_bytes(b'identical inherited implementation')
        (root/'src/data_sheets_schema/schema_semantics.py').write_text(str(root))
    m = selected(kind=final_registration.KIND, repository=str(descendant_root))
    with pytest.raises(registration.BudgetStop, match='accepted schema-semantics implementation'):
        final_registration.validate_scientific_identity(m, {'repository': str(accepted_root)})


@pytest.mark.parametrize('value', [None, False, BLOCK])
def test_general_generation_and_evaluation_reject_active_transition(tmp_path, value):
    m = {KEY: value}
    path = save(tmp_path/'registration.json', m)
    for validator in (run_api_canary.verify, evaluation_registration.verify_manifest):
        with pytest.raises(registration.BudgetStop, match='audit|transition'):
            validator(m, path, 'unused')


@pytest.mark.parametrize('version', [18, 19])
def test_actual_native_generation_per_job_guard_precedes_setup(tmp_path, monkeypatch, version):
    base = {'repository': str(Path(api_runner.__file__).resolve().parents[2]),
            'python': sys.executable, 'python_version': sys.version, 'pinned_files': {},
            'generation': {'jobs': [{'id': 'synthetic', 'render_spec': {'render_version': version}}]}}
    path = save(tmp_path/'registration.json', base)
    overlay = save(tmp_path/'overlay.json', {'registration': str(path),
        'registration_sha256': registration.sha(path), 'allowed_jobs': ['synthetic'], 'pinned_files': {}})
    review = save(tmp_path/'review.json', {'verdict': 'approve', 'ci_conclusion': 'success',
        'overlay_sha256': registration.sha(overlay), 'allowed_jobs': ['synthetic']})
    # The actual shared verifier must run first. Its historical next operation
    # is a sentinel, so the legacy18 control proves it reached the old path.
    class LegacyReached(Exception):
        pass
    def old_check(*args, **kwargs):
        raise LegacyReached
    monkeypatch.chdir(base['repository'])
    monkeypatch.setattr(run_native_canary, 'verify_history', old_check)
    monkeypatch.setattr(run_native_canary, 'verified_executable', lambda *a: pytest.fail('runtime setup reached'))
    monkeypatch.setattr(run_native_canary, 'open_ledger', lambda *a, **k: pytest.fail('ledger constructed'))
    monkeypatch.setattr(sys, 'argv', ['native', '--overlay', str(overlay), '--review', str(review), '--job', 'synthetic'])
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    error = registration.BudgetStop if version == 19 else LegacyReached
    with pytest.raises(error):
        run_native_canary.main()
    assert before == {p: p.read_bytes() for p in tmp_path.iterdir()}
