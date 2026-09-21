"""Renderer-17 continuation identity over synthetic, immutable Phase 1/2 inputs.

The reused fixtures stub historical transcript/accounting acceptance and Git
attestation. Real preparers, renderers, pin closure, authority selection and
registration validation remain active. No provider or ownership claim is used.
"""
from copy import deepcopy
from itertools import combinations
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import contract, contract_context, prepare, registration
from audit_controls.test_context_preparation import ancestry, accepted_audit, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry, v5_repositories
from audit_controls.test_staged_preparation import actual_renderer_history_root
from finalization_controls import contract as final_contract, prepare as final_prepare, registration as final_registration
from evaluation_controls import registration as evaluation_registration
from data_sheets_schema import api_runner
import run_api_canary

KEY = registration.TRANSITION
BLOCK = {'kind': 'frozen_pair_claim_clarification_v1'}
OPTIONS = ('upgrade_evidence_protocol', 'source_metadata_evidence', 'clarify_source_claims')


@pytest.mark.parametrize('value', [None, False, True, [], {}, BLOCK['kind'],
                                  {'kind': 'unknown'}, {**BLOCK, 'extra': True},
                                  {'kind': registration.SOURCE_METADATA_TRANSITION_KIND}])
def test_strict_transition_at_audit_and_phase4_entries(tmp_path, value):
    for kind, validator in [('d4d_native_audit_continuation', registration.validate_registration),
                            (final_registration.KIND, final_registration.validate_registration)]:
        path = save(tmp_path/'registration.json', {'kind': kind, 'schema_version': 1,
            'protocol_version': 5, 'render_version': 17, KEY: value})
        with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
            validator(path)
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('changes', [{'protocol_version': 4}, {'protocol_version': 5.0},
    {'protocol_version': True}, {'render_version': 16}, {'render_version': 17.0},
    {'render_version': True}])
def test_clarification_requires_exact_integer_versions(changes):
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.scientific_contract({'protocol_version': 5, 'render_version': 17,
                                         KEY: BLOCK, **changes})


def test_selector_is_required_and_all_historical_pairs_remain_supported():
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.scientific_contract({'protocol_version': 5, 'render_version': 17})
    for version, renderer, block in [(3, 14, None),
        (4, 15, {'kind': registration.TRANSITION_KIND}),
        (5, 16, {'kind': registration.SOURCE_METADATA_TRANSITION_KIND}), (5, 17, BLOCK)]:
        m = {'protocol_version': version, 'render_version': renderer}
        if block is not None:
            m[KEY] = block
        assert registration.scientific_contract(m) is (block is not None)


@pytest.mark.parametrize('value', [None, 0, 1, 'true', [], {}])
def test_option_is_boolean_before_any_preparation_write(tmp_path, value):
    destination = tmp_path/'never-created'
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, clarify_source_claims=value)
    assert not destination.exists()


@pytest.mark.parametrize('selected', [*combinations(OPTIONS, 2), OPTIONS])
def test_scientific_options_mutually_exclusive_in_python_and_cli(tmp_path, monkeypatch, selected):
    destination = tmp_path/'never-created'
    with pytest.raises(registration.BudgetStop, match='mutually exclusive'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, **dict.fromkeys(selected, True))
    required = [piece for name in ('parent-registration', 'parent-overlay', 'parent-job-id',
        'reconciliation-receipt', 'reconciled-checkpoint', 'destination', 'job-id')
        for piece in ('--'+name, 'unused')]
    monkeypatch.setattr(sys, 'argv', ['prepare', *required,
        *['--'+name.replace('_', '-') for name in selected]])
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: pytest.fail('conflicting CLI accepted'))
    with pytest.raises(SystemExit) as error:
        prepare.main()
    assert error.value.code == 2 and not destination.exists()


def test_cli_selects_only_explicit_clarification(monkeypatch):
    class Captured(Exception):
        pass
    def capture(**kwargs):
        assert kwargs['clarify_source_claims'] is True
        assert kwargs['upgrade_evidence_protocol'] is False
        assert kwargs['source_metadata_evidence'] is False
        raise Captured
    required = [piece for name in ('parent-registration', 'parent-overlay', 'parent-job-id',
        'reconciliation-receipt', 'reconciled-checkpoint', 'destination', 'job-id')
        for piece in ('--'+name, 'unused')]
    monkeypatch.setattr(sys, 'argv', ['prepare', *required, '--clarify-source-claims'])
    monkeypatch.setattr(prepare, 'prepare', capture)
    with pytest.raises(Captured):
        prepare.main()


@pytest.mark.parametrize('value', [None, True, BLOCK])
def test_actual_generation_and_evaluation_entries_reject_audit_selector(tmp_path, value):
    manifest = {KEY: value}
    path = save(tmp_path/'registration.json', manifest)
    with pytest.raises(registration.BudgetStop):
        run_api_canary.verify(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop):
        evaluation_registration.verify_manifest(manifest, path, 'unused')
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('recovery,staged', [(False, False), (True, True)])
def test_actual_preparation_changes_only_explicit_rendering_identity(metadata_ancestry, tmp_path,
                                                                   recovery, staged):
    args, _, preserved, state = metadata_ancestry
    old_path = prepare.prepare(**args, destination=tmp_path/'v16', source_metadata_evidence=True,
        persistent_audit_contract=True, clarify_source_claims=False,
        context_recovery=recovery, staged_audit_output=staged)
    old = registration.validate_registration(old_path)
    old_bytes = {p: p.read_bytes() for p in old_path.parent.rglob('*') if p.is_file()}
    path = prepare.prepare(**args, destination=tmp_path/'v17', clarify_source_claims=True,
        persistent_audit_contract=True, context_recovery=recovery, staged_audit_output=staged,
        durable_sequence_claim=True)
    m = registration.validate_registration(path)
    assert m[KEY] == BLOCK and (m['protocol_version'], m['render_version']) == (5, 17)
    assert old[KEY] == {'kind': registration.SOURCE_METADATA_TRANSITION_KIND}
    assert (old['protocol_version'], old['render_version']) == (5, 16)
    assert set(old['inputs']) == set(m['inputs']) and len(m['inputs']) == 11
    for role, prior in old['inputs'].items():
        assert Path(m['inputs'][role]).read_bytes() == Path(prior).read_bytes()
    for key in ('model', 'profile', 'provider_context_policy', 'native_runtime'):
        assert m[key] == old[key]
    assert m['budget']['continuation'] == old['budget']['continuation']
    assert m['budget']['prices_per_token'] == old['budget']['prices_per_token']
    assert m['sequence_state'] == old['sequence_state'] == str(state)
    instruction = Path(m['job']['instruction']).read_text()
    system = Path(m['job']['system_prompt']).read_text()
    assert 'protocol 5 / renderer 17' in instruction
    assert 'original generation remains renderer 14' in instruction
    assert api_runner.phase_instruction('audit', 17) in instruction
    assert api_runner.evidence_phase_contract('audit', 17) in system
    assert api_runner.phase_instruction('audit', 17) != api_runner.phase_instruction('audit', 16)
    assert contract_context.enabled(m)
    assert contract.source_metadata_arguments(m, {k: Path(v) for k,v in m['inputs'].items()}) == {
        'source_manifest': Path(m['inputs']['source_manifest']), 'project': 'EXAMPLE'}
    assert set(m['job']['readable_inputs']) >= set(m['inputs'].values())
    assert set(map(str, registration.required_paths(m))) <= set(m['pinned_files'])
    for relative in ('src/data_sheets_schema/source_metadata.py',
                     'src/data_sheets_schema/source_review.py',
                     'src/data_sheets_schema/evidence_assertions.py',
                     'src/download/prompts/evidence_protocol_v5.md'):
        selected = str(Path(m['repository'])/relative)
        assert m['pinned_files'][selected] == old['pinned_files'][selected]
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['job']['attempt_dir']).exists()
    assert not (path.parent/'sequence_claim').exists()
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    assert old_bytes == {name: name.read_bytes() for name in old_bytes}
    plan = registration.read_json(path.parent/'offline_plan.json')
    assert (plan['protocol_version'], plan['render_version'], plan['parent_render_version']) == (5, 17, 14)
    assert plan[KEY] == BLOCK and plan['scientific_instrument_unchanged'] is False


def test_phase4_inherits_exact_clarification_and_omits_audit_modes(metadata_ancestry, tmp_path, monkeypatch):
    original = prepare.prepare
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: original(
        **kw, clarify_source_claims=True, persistent_audit_contract=True))
    accepted, acceptance = accepted_audit(metadata_ancestry, tmp_path/'accepted')
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path/'final', job_id='synthetic_final', repository=metadata_ancestry[0]['repository'])
    m = final_registration.validate_registration(path)
    assert m[KEY] == BLOCK and (m['protocol_version'], m['render_version']) == (5, 17)
    assert not {'audit_contract_context','audit_output','native_stall_policy',
                'native_upstream_read_timeout_seconds'} & m.keys()
    assert api_runner.phase_instruction('reconcile_full', 17) in Path(m['job']['instruction']).read_text()
    suffix = final_contract._report_context(m, 'description: A sample dataset is planned.\n',
                                           'description: A sample dataset is planned.\n')
    assert api_runner.phase_instruction('report', 17) in suffix
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['job']['attempt_dir']).exists()
    assert metadata_ancestry[2] == {name: Path(name).read_bytes() for name in metadata_ancestry[2]}
    m['render_version'] = 16
    m[KEY] = {'kind': registration.SOURCE_METADATA_TRANSITION_KIND}
    save(path, m)
    with pytest.raises(registration.BudgetStop, match='accepted scientific contract version'):
        final_registration.validate_registration(path)


@pytest.mark.parametrize('relative', ['src/data_sheets_schema/api_runner.py',
    'src/data_sheets_schema/source_metadata.py', 'src/data_sheets_schema/source_review.py',
    'src/data_sheets_schema/evidence_assertions.py', 'src/download/prompts/evidence_protocol_v5.md'])
def test_phase4_refuses_repinning_changed_accepted_renderer_or_semantics(tmp_path, relative):
    m, accepted = v5_repositories(tmp_path)
    m['render_version'] = 17
    m[KEY] = deepcopy(BLOCK)
    final_registration.validate_scientific_identity(m, accepted)
    changed = Path(m['repository'])/relative
    changed.write_text('different but freshly pinned content')
    m['pinned_files'][str(changed)] = registration.sha(changed)
    with pytest.raises(registration.BudgetStop, match='accepted|inherited scientific'):
        final_registration.validate_scientific_identity(m, accepted)
