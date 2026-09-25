"""A chained $800 proof through Phase 4 and composite evaluation (#2468, #2489).

Ported from the v2 downstream tests; every artifact is invented and no provider is contacted.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import sys
import pytest
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(BASE/'evaluation_controls'))
import registration as evaluation_registration
import prepare_evaluation
import budget_amendment as amendment
import continuation_sequence as sequence
from budgeted_cborg import BudgetStop, attempt_identity
from audit_controls import registration as audit_registration
from audit_controls.test_second_budget_amendment_registration import ancestry, second_approved, prepare_second, save, unchanged  # noqa
from audit_controls.test_budget_amendment_chain_registration import chained
from finalization_controls import prepare as fprepare, registration as fregistration
from finalization_controls.native import lineage

REAL_SEQUENCE_VALIDATE = sequence._validate
REAL_SEAL = sequence.seal_document


def refs(value):
    if type(value) is dict:
        if set(value) == {'path', 'sha256'}: yield value
        else:
            for child in value.values(): yield from refs(child)


@pytest.fixture
def chain_approved(second_approved, tmp_path):
    c = second_approved
    proof, checkpoint, previous = chained(c, tmp_path/'chain-setup')
    c2 = dict(c, proof=proof, first=c['proof'], args={**c['args'], 'continuation_checkpoint': checkpoint})
    c2['immutable'] = {Path(r['path']): Path(r['path']).read_bytes() for r in refs(proof)}
    return c2


@pytest.fixture
def chain_phase4(chain_approved, tmp_path, monkeypatch):
    c = chain_approved
    increased_path, increased = prepare_second(c, tmp_path/'first-chain-increase')
    increased_sha = audit_registration.sha(increased_path)
    with audit_registration.sequence_guard(increased, increased_sha):
        increased_ledger = audit_registration.open_audit_ledger(increased, increased_path, increased_sha)
        assert audit_registration.read_json(increased_ledger.path)['additional_cap_usd'] == '800'
        ticket = increased_ledger.reserve(attempt_identity(increased_sha, increased['job']['id']), '.02', 'x')
        increased_ledger.settle(ticket, '.01', response_sha256='synthetic-response', usage={})
    audit_path, audit = prepare_second(c, tmp_path/'accepted-same-cap-audit', continuation_checkpoint=increased_ledger.path)
    identity = audit_registration.sha(audit_path)
    with audit_registration.sequence_guard(audit, identity):
        ledger = audit_registration.open_audit_ledger(audit, audit_path, identity)
        ticket = ledger.reserve(attempt_identity(identity, audit['job']['id']), '.02', 'synthetic-audit')
        ledger.settle(ticket, '.01', response_sha256='synthetic-audit-response', usage={})
    output = Path(audit['job']['audit_path']); output.parent.mkdir(parents=True)
    output.write_bytes(Path(c['example']['job']['audit_path']).read_bytes())
    artifacts = {str(output): audit_registration.sha(output)}
    result = save(Path(audit['job']['attempt_dir'])/'result.json', {
        'scope': 'phase3_audit_only', 'job_id': audit['job']['id'], 'registration_sha256': identity,
        'status': 'completed_pending_independent_review', 'unresolved_requests': [],
        'audit_path': str(output), 'audit_sha256': artifacts[str(output)],
        'validation': {'checked': True, 'passed': True, 'job_id': audit['job']['id'],
                       'audit_sha256': artifacts[str(output)], 'findings': [], 'errors': []},
        'runtime': {'exit_code': 0, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}})
    acceptance = save(tmp_path/'synthetic-audit-acceptance.json', {'verdict': 'accept',
        'registration_sha256': identity, 'result_sha256': audit_registration.sha(result),
        'ledger_sha256': audit_registration.sha(ledger.path), 'artifacts': artifacts})
    monkeypatch.setattr(sequence, '_validate', REAL_SEQUENCE_VALIDATE)
    monkeypatch.setattr(fprepare, 'seal_document', REAL_SEAL)
    path = fprepare.prepare(accepted_audit_registration=audit_path, acceptance=acceptance,
        destination=tmp_path/'phase4', job_id='synthetic_final', repository=c['args']['repository'])
    manifest = fregistration.validate_registration(path)
    return {'case': c, 'path': path, 'manifest': manifest, 'audit': audit,
            'audit_path': audit_path, 'audit_ledger': Path(ledger.path), 'acceptance': acceptance, 'state': c['state']}


def test_a_chained_phase4_carries_the_proof_at_its_cap(chain_phase4):
    f = chain_phase4; m = f['manifest']; c = f['case']; path = f['path']
    assert m['budget_amendment'] == c['proof'] and m['budget']['additional_usd'] == '800'
    assert amendment.paths(m) <= fregistration.required_paths(m)
    audit_rows = sequence.read(f['audit_ledger'])['requests']
    with sequence.owned_sequence(m, path, sequence.sha(path)) as owner:
        state = sequence.read(owner.ledger.path)
        assert state['additional_cap_usd'] == '800'
        assert 'budget_amendment_sha256' not in state['continued_from']
        assert amendment._canonical(state['requests'][:len(audit_rows)]) == amendment._canonical(audit_rows)
    unchanged(c, state=False)


@pytest.mark.parametrize('damage', ['drop', 'replace_with_v2', 'unpin_v1_authority', 'unpin_v2_authority'])
def test_a_chained_phase4_refuses_a_dropped_replaced_or_unpinned_proof(chain_phase4, damage):
    f = chain_phase4; m = deepcopy(f['manifest']); path = f['path']; c = f['case']
    if damage == 'drop': m.pop('budget_amendment')
    elif damage == 'replace_with_v2': m['budget_amendment'] = deepcopy(c['first'])
    elif damage == 'unpin_v1_authority': m['pinned_files'].pop(c['first']['prior_amendment']['authorization']['path'])
    else: m['pinned_files'].pop(c['first']['authorization']['path'])
    save(path, m)
    with pytest.raises(BudgetStop):
        with sequence.owned_sequence(m, path, sequence.sha(path)):
            pytest.fail('reached accounting')


def test_a_chained_composite_evaluation_carries_the_proof_at_its_cap(chain_phase4, tmp_path, monkeypatch):
    f = chain_phase4; m = f['manifest']; path = f['path']
    with sequence.owned_sequence(m, path, sequence.sha(path)) as owner:
        ticket = owner.reserve(sequence.sha(path)+':synthetic_final', '.02', 'synthetic-finalization')
        owner.ledger.settle(ticket, '.01', response_sha256='synthetic-finalization-response', usage={})
    output = Path(m['job']['output_dir']); output.mkdir(parents=True)
    Path(m['job']['full_path']).write_bytes(Path(m['inputs']['original_full']).read_bytes())
    from data_sheets_schema.derive_core import core_text
    from data_sheets_schema.d4d_pair_consistency import load_pair_schema
    schemas = load_pair_schema(Path(m['inputs']['full_schema']), Path(m['inputs']['core_schema']))
    Path(m['job']['core_path']).write_text(core_text(Path(m['job']['full_path']), schemas, phase4_complete=True)[0])
    Path(m['job']['report_path']).write_text('# Synthetic accepted finalization fixture\n')
    artifacts = {m['job'][role+'_path']: sequence.sha(m['job'][role+'_path']) for role in ('full', 'core', 'report')}
    observed = {'phase4': {'synthetic': 'invented acceptance, no scientific execution'}}
    lin = save(Path(m['job']['attempt_dir'])/'lineage.json', lineage(m, sequence.sha(path), artifacts, observed))
    all_artifacts = {**artifacts, str(lin): sequence.sha(lin)}
    result = save(Path(m['job']['attempt_dir'])/'result.json', {
        'scope': 'phase4_reconciliation', 'job_id': m['job']['id'], 'registration_sha256': sequence.sha(path),
        'status': 'completed_pending_independent_review', 'unresolved_requests': [],
        'validation': {'checked': True, 'passed': True, 'errors': [], 'findings': [], 'artifacts': artifacts},
        'runtime': {'exit_code': 0, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0},
        'evidence': observed, 'artifacts': all_artifacts})
    acceptance = save(tmp_path/'synthetic-finalization-acceptance.json', {'verdict': 'accept',
        'registration_sha256': sequence.sha(path), 'result_sha256': sequence.sha(result),
        'ledger_sha256': sequence.sha(m['budget']['ledger_path']), 'artifacts': all_artifacts})
    context = save(tmp_path/'evaluation-context.json', {})
    monkeypatch.setattr(prepare_evaluation, 'verify_implementation', lambda m: None)
    monkeypatch.setattr(evaluation_registration, 'verify_implementation', lambda m: None)
    res = prepare_evaluation.build_composite_registration(tmp_path/'evaluation',
        finalization_registration=path, finalization_acceptance=acceptance,
        context_path=context, native_executable=m['native_runtime']['executable'], durable_sequence_claim=True)
    epath = res['registration']; em = evaluation_registration.read_json(epath)
    assert em['budget_amendment'] == f['case']['proof']
    assert amendment.paths(em) <= evaluation_registration.required_paths(em)
    assert evaluation_registration.allocation_total(em) == Decimal('800')
    assert evaluation_registration.verify_manifest(em, epath, sequence.sha(epath))
    with sequence.owned_sequence(em, epath, sequence.sha(epath)) as owner:
        rows = sequence.read(owner.ledger.path)
        assert rows['additional_cap_usd'] == '800'
