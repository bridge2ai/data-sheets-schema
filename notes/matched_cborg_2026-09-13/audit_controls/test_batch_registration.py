"""Prospective batch preparation, exact replay and version isolation; offline only.

Ancestry stubs only old transcript/accounting checks and Git attestation. Actual
preparation, scientific context, immutable pins and selectors remain exercised.
"""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE/'native_controls')]
from audit_controls import batch_registration as selected, batch_output, contract, prepare, registration
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_draft_registration import required_cli
from data_sheets_schema import api_runner, evidence_assertions

CONFIG = {'kind': 'fresh_context_integrated_v1', 'worker_total_cap_usd': '12'}


def empty_prepare(tmp_path, **kwargs):
    return prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
        reconciliation_receipt=None, reconciled_checkpoint=None, destination=tmp_path/'absent',
        job_id='unused', repository=tmp_path, **kwargs)


@pytest.mark.parametrize('value', [False, True, {}, [], 'fresh_context_integrated_v1',
    {**CONFIG, 'extra': 1}, {**CONFIG, 'kind': 'unknown'},
    *[{**CONFIG, 'worker_total_cap_usd': x} for x in (None, True, 0, -1, 'NaN', 'Infinity')],
    *[{**CONFIG, 'max_paths': x} for x in (True, 0, -1, 1.5, '96')]])
def test_bad_selector_rejected_before_any_writes(tmp_path, value):
    with pytest.raises(registration.BudgetStop):
        empty_prepare(tmp_path, audit_batches=value)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('raw', ['null', '{"kind":"one","kind":"two"}', '[]', 'false', 'NaN'])
def test_config_file_is_strict_and_null_never_selects_legacy(tmp_path, raw):
    path = tmp_path/'config.json'; path.write_text(raw)
    with pytest.raises(registration.BudgetStop):
        selected.read_selection(path)


@pytest.mark.parametrize('other', ['context_recovery', 'staged_audit_output', 'persistent_audit_contract',
    'upgrade_evidence_protocol', 'source_metadata_evidence', 'clarify_source_claims',
    'draft_audit_grammar', 'schema_semantic_context'])
def test_conflicting_mode_rejected_before_writes(tmp_path, other):
    with pytest.raises(registration.BudgetStop, match='exclusively'):
        empty_prepare(tmp_path, audit_batches=CONFIG, **{other: True})
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('cap', ['12', '11', 'NaN', 'Infinity', '-1'])
def test_worker_cap_must_leave_positive_integration_allowance_before_writes(tmp_path, cap):
    with pytest.raises(registration.BudgetStop, match='integration allowance'):
        empty_prepare(tmp_path, audit_batches=CONFIG, attempt_cap=cap)
    assert not list(tmp_path.iterdir())


def test_cli_reads_explicit_configuration_before_preparation(tmp_path, monkeypatch):
    path = save(tmp_path/'config.json', CONFIG)
    class Captured(Exception): pass
    def capture(**kwargs):
        assert kwargs['audit_batches'] == selected.selection(CONFIG)
        assert kwargs['draft_audit_grammar'] is False
        raise Captured
    monkeypatch.setattr(prepare, 'prepare', capture)
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(), '--audit-batches', str(path)])
    with pytest.raises(Captured): prepare.main()


def test_protocol7_requires_explicit_transition_and_batch_selector(tmp_path):
    manifest = {'kind': 'd4d_native_audit_continuation', 'schema_version': 1,
                'protocol_version': 7, 'render_version': 20,
                registration.TRANSITION: {'kind': registration.BATCH_TRANSITION_KIND}}
    with pytest.raises(registration.BudgetStop, match='batch registration'):
        registration.validate_registration(save(tmp_path/'registration.json', manifest))
    manifest['protocol_version'] = 7.0
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.scientific_contract(manifest)


def test_real_preparation_freezes_all_static_inputs_and_keeps_parent_bytes(metadata_ancestry, tmp_path):
    args, _, preserved, state = metadata_ancestry
    old_path = prepare.prepare(**args, destination=tmp_path/'old',
        draft_audit_grammar=True, schema_semantic_context=True, persistent_audit_contract=True)
    old = registration.read_json(old_path)
    old_bytes = {p: p.read_bytes() for p in old_path.parent.rglob('*') if p.is_file()}
    path = prepare.prepare(**args, destination=tmp_path/'batch', audit_batches=CONFIG,
        durable_sequence_claim=True)
    manifest = registration.validate_registration(path)
    assert (manifest['protocol_version'], manifest['render_version']) == (7, 20)
    assert manifest[registration.TRANSITION] == {'kind': registration.BATCH_TRANSITION_KIND}
    assert not {'audit_drafting', 'audit_output', 'audit_contract_context', 'context_recovery'} & manifest.keys()
    for role in manifest['inputs']:
        if role != 'protocol':
            assert Path(manifest['inputs'][role]).read_bytes() == Path(old['inputs'][role]).read_bytes()
    assert manifest['budget']['continuation'] == old['budget']['continuation']
    for key in ('model', 'native_runtime', 'provider_context_policy', 'profile', 'sequence_state'):
        assert manifest[key] == old[key]
    assert manifest['sequence_state'] == str(state)
    assert Path(manifest['job']['instruction']).read_text() == contract.render_instruction(manifest)
    assert Path(manifest['job']['system_prompt']).read_text() == prepare.render_system(manifest)
    protocol = Path(manifest['inputs']['protocol']).read_text()
    block = batch_output.configuration(manifest, path)
    for child in block['children']:
        system = Path(child['system_prompt']).read_text()
        assert system.count(protocol) == 1
        assert api_runner.phase_instruction('audit', 20) in system
        assert 'protocol v7' in system and 'protocol v6' not in system
        assert system == selected.child_system(manifest, child['id'])
        assert str(child['system_prompt']) in manifest['pinned_files']
        if child['kind'] == 'worker':
            assert str(child['instruction']) in manifest['pinned_files']
        else:
            assert not Path(child['instruction']).exists()
    assert set(map(str, registration.required_paths(manifest))) <= manifest['pinned_files'].keys()
    helpers = ('batch_registration.py', 'batch_native.py', 'batch_history.py', 'batch_output.py',
               'output_parts.py', 'draft_output.py')
    for name in helpers:
        assert str(BASE/'audit_controls'/name) in manifest['pinned_files']
    assert not Path(manifest['job']['attempt_dir']).exists()
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    assert old_bytes == {name: name.read_bytes() for name in old_bytes}


@pytest.mark.parametrize('damage', ['system', 'instruction', 'integration_base', 'plan', 'helper_pin'])
def test_repinning_does_not_bypass_exact_replay(metadata_ancestry, tmp_path, damage):
    path = prepare.prepare(**metadata_ancestry[0], destination=tmp_path/'batch', audit_batches=CONFIG)
    manifest = registration.read_json(path)
    block = manifest['audit_batches']
    if damage == 'helper_pin':
        del manifest['pinned_files'][str(BASE/'audit_controls/batch_registration.py')]
    else:
        target = Path({'system': block['children'][0]['system_prompt'],
                       'instruction': block['children'][0]['instruction'],
                       'integration_base': block['integration_base'],
                       'plan': block['plan_path']}[damage])
        if damage == 'plan':
            plan = registration.read_json(target); plan['workers'][0]['paths'] = ['/invented']
            save(target, plan)
        else:
            target.write_text(target.read_text() + '\nUnregistered instruction.\n')
        manifest['pinned_files'][str(target)] = registration.sha(target)
    save(path, manifest)
    with pytest.raises((registration.BudgetStop, ValueError)):
        registration.validate_registration(path)
    assert not Path(manifest['job']['attempt_dir']).exists()


def test_protocol7_checker_identity_and_legacy_phase_bytes():
    assert evidence_assertions.protocol_for_renderer(20) == 7
    assert evidence_assertions.protocol_for_renderer(19) == 6
    assert 'v7' in evidence_assertions.instrument(7)
    assert 'bounded grammar' in api_runner.evidence_phase_contract('audit', 20)
    assert api_runner.DRAFT_GRAMMAR_CONTRACT_V18 not in api_runner.evidence_phase_contract('audit', 20)
    assert api_runner.DRAFT_GRAMMAR_CONTRACT_V18 in api_runner.evidence_phase_contract('audit', 19)


def test_crlf_original_identity_is_preserved_in_plan_and_inventory(metadata_ancestry, tmp_path):
    args = metadata_ancestry[0]
    generation = registration.read_json(args['parent_registration'])
    core = Path(generation['generation']['jobs'][0]['render_spec']['agentic_artifact_paths']['core'])
    original = core.parent/'evidence'/'original_full.yaml'
    raw = original.read_bytes().replace(b'\n', b'\r\n')
    original.write_bytes(raw)
    path = prepare.prepare(**args, destination=tmp_path/'batch', audit_batches=CONFIG)
    manifest = registration.validate_registration(path)
    inventory = registration.read_json(manifest['inputs']['source_inventory'])
    plan = batch_output.plan(manifest)
    assert inventory == plan['inventory']
    assert inventory['sha256'] == registration.sha(original)
    assert original.read_bytes() == raw


def test_offline_cost_basis_names_actual_child_text_and_pending_dynamic_inputs(metadata_ancestry, tmp_path):
    path = prepare.prepare(**metadata_ancestry[0], destination=tmp_path/'batch', audit_batches=CONFIG)
    manifest = registration.read_json(path)
    report = registration.read_json(path.parent/'offline_plan.json')
    rows = report['audit_batch_inputs']
    assert [r['id'] for r in rows] == [r['id'] for r in manifest['audit_batches']['children']]
    assert report['input_estimate_tokens'] == sum(r['known_initial_text_estimate_tokens'] for r in rows)
    assert report['inline_instruction_bytes'] == sum(r['known_user_bytes'] for r in rows)
    assert report['inline_instruction_bytes'] > report['controller_instruction_bytes']
    assert report['complete_workload_cost_estimate_available'] is False
    assert [r['dynamic_proposal_inputs_pending'] for r in rows] == [False]*(len(rows)-1)+[True]
    assert 'subsequent turns' in report['estimate_basis']
    assert report['worker_total_cap_usd'] == CONFIG['worker_total_cap_usd']
