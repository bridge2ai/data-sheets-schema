"""Explicit frozen-pair version changes; synthetic offline ancestry only."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import contract, contract_context, prepare, registration
from audit_controls.test_context_preparation import ancestry, accepted_audit
from audit_controls.test_staged_preparation import actual_renderer_history_root
from finalization_controls import contract as final_contract, prepare as final_prepare, registration as final_registration
from data_sheets_schema import api_runner
from evaluation_controls import registration as evaluation_registration
import run_api_canary

KEY = registration.TRANSITION
BLOCK = {'kind': 'frozen_pair_protocol_v4'}


@pytest.mark.parametrize('value', [None, True, BLOCK])
def test_other_actual_entrypoints_reject_continuation_selector_before_setup(tmp_path, value):
    manifest = {KEY: value}
    path = tmp_path/'registration.json'
    path.write_text(json.dumps(manifest))
    with pytest.raises(registration.BudgetStop):
        run_api_canary.verify(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop):
        evaluation_registration.verify_manifest(manifest, path, 'unused')
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('value', [None, False, True, [], {}, 'frozen_pair_protocol_v4',
                                  {'kind': 'unknown'}, {**BLOCK, 'extra': 1}])
def test_invalid_transition_rejected_at_real_registration_entries(tmp_path, value):
    for kind, validator in [('d4d_native_audit_continuation', registration.validate_registration),
                            (final_registration.KIND, final_registration.validate_registration)]:
        manifest = {'schema_version': 1, 'kind': kind, 'protocol_version': 4,
                    'render_version': 15, KEY: value}
        path = tmp_path / 'registration.json'
        path.write_text(json.dumps(manifest))
        with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
            validator(path)
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('changes', [{'protocol_version': 3}, {'render_version': 14},
                                   {'protocol_version': 4.0}, {'render_version': 15.0}])
def test_transition_requires_exact_new_version_pair(changes):
    manifest = {KEY: BLOCK, 'protocol_version': 4, 'render_version': 15, **changes}
    with pytest.raises(registration.BudgetStop):
        registration.scientific_contract(manifest)


@pytest.mark.parametrize('value', [None, 0, 1, 'true', {}])
def test_upgrade_option_rejected_before_preparation_mutation(tmp_path, value):
    destination = tmp_path / 'never-created'
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, upgrade_evidence_protocol=value)
    assert not destination.exists()


@pytest.mark.parametrize('recovery,staged', [(False, False), (True, True)])
def test_real_upgrade_preparation_preserves_parent_and_selects_current_contract(ancestry, tmp_path, recovery, staged):
    args, _, preserved, _ = ancestry
    old = prepare.prepare(**args, destination=tmp_path/'legacy')
    path = prepare.prepare(**args, destination=tmp_path/'upgraded',
        upgrade_evidence_protocol=True, persistent_audit_contract=True,
        context_recovery=recovery, staged_audit_output=staged)
    m = registration.validate_registration(path)
    legacy = registration.read_json(old)
    assert m[KEY] == BLOCK and (m['protocol_version'], m['render_version']) == (4, 15)
    assert KEY not in legacy
    assert Path(legacy['job']['system_prompt']).read_bytes() == prepare.SYSTEM.encode()
    for role, original in legacy['inputs'].items():
        if role != 'protocol':
            assert Path(m['inputs'][role]).read_bytes() == Path(original).read_bytes()
    assert Path(m['inputs']['protocol']).name == 'evidence_protocol_v4.md'
    assert Path(legacy['inputs']['protocol']).name == 'evidence_protocol_v3.md'
    assert m['pinned_files'][legacy['inputs']['protocol']] == registration.sha(legacy['inputs']['protocol'])
    for name in registration.VERSIONED_SCIENTIFIC_FILES:
        original = str(Path(m['parent']['repository'])/'src/data_sheets_schema'/name)
        assert m['pinned_files'][original] == registration.sha(original)
    instruction = Path(m['job']['instruction']).read_text()
    system = Path(m['job']['system_prompt']).read_text()
    assert 'original generation remains renderer 14' in instruction
    assert api_runner.phase_instruction('audit', 15) in instruction
    assert 'anonymous_structure_v1' in instruction
    assert 'renderer-14 scientific/evidence contracts above' not in instruction
    assert api_runner.evidence_phase_contract('audit', 15) in system
    assert contract_context.enabled(m)
    assert set(m['job']['readable_inputs']) >= set(m['inputs'].values())
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['job']['attempt_dir']).exists()
    assert not (path.parent/'sequence_claim').exists()
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    plan = registration.read_json(path.parent/'offline_plan.json')
    assert plan['scientific_instrument_unchanged'] is False
    assert plan['parent_render_version'] == 14


def test_new_version_without_selector_fails_in_real_registration(ancestry, tmp_path):
    path = prepare.prepare(**ancestry[0], destination=tmp_path/'new', upgrade_evidence_protocol=True)
    m = registration.read_json(path); del m[KEY]
    path.write_text(json.dumps(m))
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.validate_registration(path)


def test_phase4_inherits_accepted_version_but_not_audit_delivery(ancestry, tmp_path, monkeypatch):
    actual_prepare = prepare.prepare
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: actual_prepare(
        **kw, upgrade_evidence_protocol=True, persistent_audit_contract=True))
    accepted, acceptance = accepted_audit(ancestry, tmp_path/'accepted')
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path/'final', job_id='synthetic_final', repository=ancestry[0]['repository'])
    m = final_registration.validate_registration(path)
    assert m[KEY] == BLOCK and (m['protocol_version'], m['render_version']) == (4, 15)
    assert 'audit_contract_context' not in m
    assert api_runner.phase_instruction('reconcile_full', 15) in Path(m['job']['instruction']).read_text()
    suffix = final_contract._report_context(m, 'description: A sample dataset is planned.\n',
                                           'description: A sample dataset is planned.\n')
    assert api_runner.phase_instruction('report', 15) in suffix
    assert not Path(m['budget']['ledger_path']).exists()
    assert not Path(m['job']['attempt_dir']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}
    m.update(protocol_version=3, render_version=14); del m[KEY]
    path.write_text(json.dumps(m))
    with pytest.raises(registration.BudgetStop, match='accepted scientific contract version'):
        final_registration.validate_registration(path)


def test_pure_audit_validator_dispatches_new_protocol_and_keeps_legacy(ancestry, tmp_path, monkeypatch):
    from audit_controls.test_contract import audit_fixture
    (tmp_path/'pure').mkdir()
    m, _ = audit_fixture(tmp_path/'pure')
    seen = []
    original = contract.evidence_assertions.check_files
    def checked(**kw):
        seen.append(kw['protocol_version']); return original(**kw)
    monkeypatch.setattr(contract.evidence_assertions, 'check_files', checked)
    assert contract.validate_audit(m)['passed']
    m.update(protocol_version=4, render_version=15); m[KEY] = BLOCK
    assert contract.validate_audit(m)['passed']
    assert seen == [3, 4]


def scientific_repositories(tmp_path):
    files = ('api_runner.py', 'evidence_assertions.py', 'source_review.py', 'profiles.py',
             'schema_digest.py', 'anonymous_removals.py', 'report_claims.py', 'derive_core.py',
             'd4d_pair_consistency.py')
    roots = [tmp_path/'old', tmp_path/'new']
    pins = {}
    for root in roots:
        for relative in [*(Path('src/data_sheets_schema')/name for name in files),
                         Path('src/download/prompts/evidence_protocol_v4.md')]:
            path = root/relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('same synthetic implementation ' + str(relative))
            pins[str(path)] = registration.sha(path)
    manifest = {'repository': str(roots[1]), 'parent': {'repository': str(roots[0])},
        'protocol_version': 4, 'render_version': 15, KEY: BLOCK, 'pinned_files': pins}
    accepted = {'repository': str(roots[0]),
        'inputs': {'protocol': str(roots[0]/'src/download/prompts/evidence_protocol_v4.md')}}
    return manifest, accepted


def test_only_explicit_versioned_files_can_differ_from_parent(tmp_path):
    m, _ = scientific_repositories(tmp_path)
    changed = Path(m['repository'])/'src/data_sheets_schema/api_runner.py'
    changed.write_text('new protocol dispatch')
    m['pinned_files'][str(changed)] = registration.sha(changed)
    registration.validate_scientific_identity(m)
    legacy = deepcopy(m); del legacy[KEY]; legacy.update(protocol_version=3, render_version=14)
    with pytest.raises(registration.BudgetStop, match='shared scientific instrument changed'):
        registration.validate_scientific_identity(legacy)
    unpinned = deepcopy(m); del unpinned['pinned_files'][str(changed)]
    with pytest.raises(registration.BudgetStop, match='implementation changed'):
        registration.validate_scientific_identity(unpinned)
    protected = Path(m['repository'])/'src/data_sheets_schema/source_review.py'
    protected.write_text('unexpected scientific drift')
    m['pinned_files'][str(protected)] = registration.sha(protected)
    with pytest.raises(registration.BudgetStop, match='source_review.py'):
        registration.validate_scientific_identity(m)


@pytest.mark.parametrize('relative', ['src/data_sheets_schema/anonymous_removals.py',
                                    'src/download/prompts/evidence_protocol_v4.md'])
def test_phase4_cannot_replace_accepted_helper_or_protocol_even_with_fresh_pins(tmp_path, relative):
    m, accepted = scientific_repositories(tmp_path)
    final_registration.validate_scientific_identity(m, accepted)
    path = Path(m['repository'])/relative
    path.write_text('different locally pinned content')
    m['pinned_files'][str(path)] = registration.sha(path)
    with pytest.raises(registration.BudgetStop, match='accepted'):
        final_registration.validate_scientific_identity(m, accepted)
