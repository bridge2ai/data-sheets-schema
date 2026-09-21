"""Real opt-in drafting preparation over synthetic immutable 3/14 ancestry.

The reused ancestry fixture stubs historical transcript/accounting acceptance
and uncommitted Git attestation, not the preparer, rendering, authority or pin
closure. No provider is constructed and no ownership or live ledger is opened.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import contract, contract_context, prepare, registration
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root, RegisteredSession
from audit_controls.test_draft_native import DraftSession
from finalization_controls import prepare as final_prepare, registration as final_registration
from evaluation_controls import registration as evaluation_registration
from data_sheets_schema import api_runner
import run_api_canary
import native_context as frames
import sequence_claim

KEY = registration.TRANSITION
BLOCK = {'kind': 'frozen_pair_draft_grammar_v1'}
CONFLICTS = ('staged_audit_output', 'upgrade_evidence_protocol',
             'source_metadata_evidence', 'clarify_source_claims')


def minimal(**extra):
    return {'kind': 'd4d_native_audit_continuation', 'schema_version': 1,
            'protocol_version': 6, 'render_version': 18, KEY: deepcopy(BLOCK), **extra}


@pytest.mark.parametrize('value', [None, False, True, [], {}, BLOCK['kind'],
    {'kind': 'unknown'}, {**BLOCK, 'extra': True}, {'kind': registration.CLAIM_CLARIFICATION_TRANSITION_KIND}])
def test_transition_is_exact_before_any_audit_or_phase4_setup(tmp_path, value):
    for validator, kind in ((registration.validate_registration, 'd4d_native_audit_continuation'),
                            (final_registration.validate_registration, final_registration.KIND)):
        path = save(tmp_path/'registration.json', minimal(kind=kind, **{KEY: value}))
        with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
            validator(path)
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('changes', [{'protocol_version': 5}, {'protocol_version': 6.0},
    {'protocol_version': True}, {'render_version': 17}, {'render_version': 18.0}, {'render_version': True}])
def test_draft_transition_requires_exact_integer_versions(changes):
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.scientific_contract(minimal(**changes))


def test_protocol6_requires_both_transition_and_explicit_native_drafting_mode(tmp_path):
    m = minimal()
    del m[KEY]
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.scientific_contract(m)
    path = save(tmp_path/'registration.json', minimal())
    with pytest.raises(registration.BudgetStop, match='requires.*drafting registration'):
        registration.validate_registration(path)
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('value', [None, 0, 1, 'true', [], {}])
def test_drafting_option_is_boolean_before_preparation_writes(tmp_path, value):
    destination = tmp_path/'never-created'
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, draft_audit_grammar=value)
    assert not destination.exists()


@pytest.mark.parametrize('other', CONFLICTS)
def test_draft_mode_cannot_mix_scientific_or_output_selectors_before_writes(tmp_path, other):
    destination = tmp_path/'never-created'
    with pytest.raises(registration.BudgetStop, match='exclusively'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, draft_audit_grammar=True, **{other: True})
    assert not destination.exists()


def required_cli():
    return [piece for name in ('parent-registration', 'parent-overlay', 'parent-job-id',
        'reconciliation-receipt', 'reconciled-checkpoint', 'destination', 'job-id')
        for piece in ('--'+name, 'unused')]


@pytest.mark.parametrize('other', CONFLICTS[1:])
def test_cli_rejects_multiple_scientific_selectors_before_preparer(monkeypatch, other):
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(), '--draft-audit-grammar',
                                    '--'+other.replace('_', '-')])
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: pytest.fail('conflicting CLI reached preparation'))
    with pytest.raises(SystemExit) as error:
        prepare.main()
    assert error.value.code == 2


def test_cli_selects_new_drafting_without_silently_selecting_legacy_modes(monkeypatch):
    class Captured(Exception):
        pass
    def capture(**kw):
        assert kw['draft_audit_grammar'] is True
        assert all(kw[name] is False for name in CONFLICTS)
        raise Captured
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(), '--draft-audit-grammar'])
    monkeypatch.setattr(prepare, 'prepare', capture)
    with pytest.raises(Captured):
        prepare.main()


@pytest.mark.parametrize('value', [None, False, True, [], {}, {'protocol': 'bounded_draft_grammar_v1'}])
def test_actual_generation_phase4_evaluation_entries_reject_draft_key_presence(tmp_path, value):
    manifest = {'audit_drafting': value}
    path = save(tmp_path/'registration.json', manifest)
    with pytest.raises(registration.BudgetStop, match='audit_drafting is audit-only'):
        run_api_canary.verify(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop, match='audit_drafting is audit-only'):
        evaluation_registration.verify_manifest(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop, match='audit_drafting is audit-only'):
        final_registration.validate_registration(path)
    assert [p.name for p in tmp_path.iterdir()] == ['registration.json']


@pytest.mark.parametrize('recovery', [False, True])
def test_actual_preparation_preserves_science_and_registers_fresh_draft_mode(
        metadata_ancestry, tmp_path, recovery):
    from audit_controls import draft_output
    args, _, preserved, state = metadata_ancestry
    old_path = prepare.prepare(**args, destination=tmp_path/'v17', clarify_source_claims=True,
        persistent_audit_contract=True, context_recovery=recovery, staged_audit_output=True)
    old = registration.validate_registration(old_path)
    old_bytes = {p: p.read_bytes() for p in old_path.parent.rglob('*') if p.is_file()}
    path = prepare.prepare(**args, destination=tmp_path/'v18', draft_audit_grammar=True,
        persistent_audit_contract=True, context_recovery=recovery, durable_sequence_claim=True)
    m = registration.validate_registration(path)
    assert (m['protocol_version'], m['render_version'], m[KEY]) == (6, 18, BLOCK)
    assert 'audit_output' not in m and 'audit_drafting' in m
    assert draft_output.configuration(m, path) == m['audit_drafting']
    assert set(m['inputs']) == set(old['inputs']) and len(m['inputs']) == 11
    for role, prior in old['inputs'].items():
        if role != 'protocol':
            assert Path(m['inputs'][role]).read_bytes() == Path(prior).read_bytes()
    assert Path(m['inputs']['protocol']).name == 'evidence_protocol_v6.md'
    assert Path(old['inputs']['protocol']).name == 'evidence_protocol_v5.md'
    for key in ('model', 'profile', 'provider_context_policy', 'native_runtime'):
        assert m[key] == old[key]
    assert m['budget']['continuation'] == old['budget']['continuation']
    assert m['budget']['prices_per_token'] == old['budget']['prices_per_token']
    assert m['sequence_state'] == old['sequence_state'] == str(state)
    assert sequence_claim.enabled(m) and not (path.parent/'sequence_claim').exists()
    instruction = Path(m['job']['instruction']).read_text()
    system = Path(m['job']['system_prompt']).read_text()
    assert 'protocol 6 / renderer 18' in instruction and 'original generation remains renderer 14' in instruction
    assert api_runner.phase_instruction('audit', 18) in instruction
    assert api_runner.evidence_phase_contract('audit', 18) in system
    assert draft_output.instruction(m) in instruction and contract_context.enabled(m)
    assert contract.source_metadata_arguments(m, {k: Path(v) for k,v in m['inputs'].items()}) == {
        'source_manifest': Path(m['inputs']['source_manifest']), 'project': 'EXAMPLE'}
    readable = set(m['inputs'].values()) | {m['job']['instruction'], m['job']['system_prompt']}
    if recovery:
        readable.update(frames.bounded_paths(m['context_recovery']))
    assert set(m['job']['readable_inputs']) == readable
    assert set(map(str, registration.required_paths(m))) <= set(m['pinned_files'])
    for module in ('draft_output.py', 'draft_history.py', 'output_parts.py'):
        helper = str(BASE/'audit_controls'/module)
        assert m['pinned_files'][helper] == registration.sha(helper)
        assert helper not in readable
    grammar = str(Path(m['repository'])/'src/data_sheets_schema/audit_grammar.py')
    assert m['pinned_files'][grammar] == registration.sha(grammar) and grammar not in readable
    assert not Path(m['budget']['ledger_path']).exists() and not Path(m['job']['attempt_dir']).exists()
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    assert old_bytes == {name: name.read_bytes() for name in old_bytes}
    plan = registration.read_json(path.parent/'offline_plan.json')
    assert (plan['protocol_version'], plan['render_version'], plan['parent_render_version']) == (6, 18, 14)
    assert plan[KEY] == BLOCK and plan['scientific_instrument_unchanged'] is False
    assert plan['audit_drafting'] == m['audit_drafting']


@pytest.mark.parametrize('explicit_false', [False, True])
def test_legacy_preparation_does_not_pin_or_enable_drafting(metadata_ancestry, tmp_path, explicit_false):
    options = {'draft_audit_grammar': False} if explicit_false else {}
    path = prepare.prepare(**metadata_ancestry[0], destination=tmp_path/'legacy', **options)
    m = registration.validate_registration(path)
    assert 'audit_drafting' not in m and (m['protocol_version'], m['render_version']) == (3, 14)
    for module in ('draft_output.py', 'draft_history.py'):
        assert str(BASE/'audit_controls'/module) not in m['pinned_files']
    assert Path(m['job']['system_prompt']).read_bytes() == prepare.SYSTEM.encode()
    assert not Path(m['job']['attempt_dir']).exists()
    assert metadata_ancestry[2] == {name: Path(name).read_bytes() for name in metadata_ancestry[2]}


@pytest.mark.parametrize('damage', ['no_mode', 'null_mode', 'legacy_output', 'runtime_pin', 'grammar_pin'])
def test_actual_registration_cannot_drop_or_mix_draft_mode_or_its_executing_pins(
        metadata_ancestry, tmp_path, damage):
    path = prepare.prepare(**metadata_ancestry[0], destination=tmp_path/'draft', draft_audit_grammar=True)
    m = registration.validate_registration(path)
    if damage == 'no_mode':
        del m['audit_drafting']
    elif damage == 'null_mode':
        m['audit_drafting'] = None
    elif damage == 'legacy_output':
        from audit_controls import output_parts
        output_parts.select(m, path, True)
    else:
        target = (BASE/'audit_controls/draft_history.py' if damage == 'runtime_pin'
                  else Path(m['repository'])/'src/data_sheets_schema/audit_grammar.py')
        del m['pinned_files'][str(target)]
    save(path, m)
    with pytest.raises(registration.BudgetStop):
        registration.validate_registration(path)
    assert not Path(m['job']['attempt_dir']).exists() and not Path(m['budget']['ledger_path']).exists()


class PreparedDraftSession(RegisteredSession, DraftSession):
    """Use real registered model/version metadata with the real draft lifecycle."""


def accepted_drafted_audit(ancestry, destination, *, correction=False, schema_semantic_context=False):
    from audit_controls import draft_output, native
    path = prepare.prepare(**ancestry[0], destination=destination, draft_audit_grammar=True,
        persistent_audit_contract=True, context_recovery=True, durable_sequence_claim=True,
        schema_semantic_context=schema_semantic_context)
    m = registration.validate_registration(path)
    for row in m['audit_drafting']['rounds']:
        Path(row['parts'][0]).parent.mkdir(parents=True)
    text = Path(ancestry[1]['job']['audit_path']).read_text().replace(
        'The service is planned.', 'A sample dataset is planned.')
    case = SimpleNamespace(m=m, reg=path, identity=registration.sha(path),
        policy=native.build_policy(m, path), attempt=Path(m['job']['attempt_dir']),
        target=Path(m['job']['audit_path']), text=text, audit=json.loads(text))
    session = PreparedDraftSession(case)
    if correction:
        session.write('{incomplete synthetic JSON')
        assert session.check()['grammar']['passed'] is False
    session.prepare_parts()
    assert session.check()['grammar']['passed'] is True
    session.seal()
    session.validate()  # Pure scientific check and an observed successful typed result.
    evidence = session.finish()  # Real callbacks and ordinary native replay.
    assert evidence['phase3'] == session.history.finish()
    result = save(case.attempt/'result.json', {
        'status': 'completed_pending_independent_review', 'scope': 'phase3_audit_only',
        'job_id': m['job']['id'], 'registration_sha256': case.identity,
        'audit_path': str(case.target), 'audit_sha256': registration.sha(case.target),
        'validation': evidence['phase3']['validation'], 'evidence': evidence})
    ledger = save(m['budget']['ledger_path'], {
        'requests': [{'id': 'fixture-settled', 'status': 'settled', 'cost_usd': '1.25'}]})
    acceptance = save(destination/'synthetic_acceptance.json', {
        'verdict': 'accept', 'registration_sha256': case.identity,
        'result_sha256': registration.sha(result), 'ledger_sha256': registration.sha(ledger)})
    closure = draft_output.closure_paths(m, path, registration.read_json(result))
    return case, acceptance, evidence, closure


@pytest.mark.parametrize('correction', [False, True])
def test_actual_phase4_inherits_science_and_pins_every_draft_without_active_mode(
        metadata_ancestry, tmp_path, correction):
    from audit_controls import draft_output
    case, acceptance, evidence, closure = accepted_drafted_audit(
        metadata_ancestry, tmp_path/'accepted', correction=correction)
    preserved = {p: p.read_bytes() for p in (tmp_path/'accepted').rglob('*') if p.is_file()}
    path = final_prepare.prepare(accepted_audit_registration=case.reg, acceptance=acceptance,
        destination=tmp_path/'phase4', job_id='synthetic_final', repository=metadata_ancestry[0]['repository'],
        context_recovery=True, durable_sequence_claim=True)
    m = final_registration.validate_registration(path)
    assert (m['protocol_version'], m['render_version'], m[KEY]) == (6, 18, BLOCK)
    assert not {'audit_drafting', 'audit_output', 'audit_contract_context', 'native_stall_policy',
                'native_upstream_read_timeout_seconds'} & m.keys()
    assert m['inputs'] == {**case.m['inputs'], 'audit': str(case.target)}
    assert m['parent'] == case.m['parent'] and sequence_claim.enabled(m)
    assert m['budget']['per_job_attempt_usd'] == {'synthetic_final': '20'}
    assert m['job']['deadline_seconds'] == 10800
    assert len(evidence['phase3']['audit_drafts']) == (2 if correction else 1)
    assert closure and closure <= final_registration.required_paths(m)
    assert set(case.m['pinned_files']) <= set(m['pinned_files'])
    assert set(map(str, final_registration.required_paths(m))) <= set(m['pinned_files'])
    for p in closure:
        assert m['pinned_files'][str(p)] == registration.sha(p)
        assert str(p) not in m['job']['readable_inputs']
    if correction:
        first = Path(case.m['audit_drafting']['rounds'][0]['parts'][0])
        assert first in closure and first.read_bytes() == b'{incomplete synthetic JSON'
        assert draft_output.check_paths(case.m, 1)[0] in closure
    assert api_runner.phase_instruction('reconcile_full', 18) in Path(m['job']['instruction']).read_text()
    assert not Path(m['job']['attempt_dir']).exists() and not Path(m['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
    assert preserved == {p: p.read_bytes() for p in preserved}
    assert metadata_ancestry[2] == {name: Path(name).read_bytes() for name in metadata_ancestry[2]}
    m.update(protocol_version=5, render_version=17)
    m[KEY] = {'kind': registration.CLAIM_CLARIFICATION_TRANSITION_KIND}
    save(path, m)
    with pytest.raises(registration.BudgetStop, match='accepted scientific contract version'):
        final_registration.validate_registration(path)


@pytest.mark.parametrize('damage', ['part', 'round_snapshot', 'receipt', 'ready', 'result_receipt'])
def test_phase4_cannot_repin_changed_draft_or_result_bound_receipt(metadata_ancestry, tmp_path, damage):
    from audit_controls import draft_output
    case, acceptance, _, _ = accepted_drafted_audit(metadata_ancestry, tmp_path/'accepted', correction=True)
    if damage == 'part':
        Path(case.m['audit_drafting']['rounds'][0]['parts'][0]).write_bytes(b'changed failed draft')
    elif damage == 'round_snapshot':
        draft_output.draft_path(case.m, 1).write_bytes(b'changed failed snapshot')
    elif damage == 'receipt':
        draft_output.check_paths(case.m, 1)[0].write_bytes(b'{}')
    elif damage == 'ready':
        draft_output.check_paths(case.m, 1)[1].unlink()
    else:
        result_path = case.attempt/'result.json'
        result = registration.read_json(result_path)
        result['evidence']['phase3']['audit_drafts'][0]['receipt_sha256'] = '0' * 64
        save(result_path, result)
        approval = registration.read_json(acceptance)
        approval['result_sha256'] = registration.sha(result_path)
        save(acceptance, approval)
    with pytest.raises(registration.BudgetStop):
        final_prepare.prepare(accepted_audit_registration=case.reg, acceptance=acceptance,
            destination=tmp_path/'refused', job_id='synthetic_final', repository=metadata_ancestry[0]['repository'])
    assert not (tmp_path/'refused'/'registration.json').exists()
