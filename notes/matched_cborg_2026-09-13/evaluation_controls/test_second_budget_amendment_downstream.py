"""Real second-amendment audit/Phase4/evaluation financial handoff, no provider.

Acceptance and final scientific artifacts are wholly invented test fixtures;
financial closure, owner transition, rendering and composite registration run.
"""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import registration as evaluation_registration
import prepare_evaluation
import budget_amendment as amendment
import continuation_sequence as sequence
from budgeted_cborg import BudgetStop
from audit_controls.test_second_budget_amendment_registration import ancestry, second_approved, save, unchanged
from finalization_controls.test_second_budget_amendment_prepare import second_phase4
from finalization_controls.native import lineage


@pytest.fixture
def second_composite(second_phase4, tmp_path, monkeypatch):
    f = second_phase4; m = f['manifest']; path = f['path']
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
    # Only code attestation is outside the uncommitted test checkout; all
    # budget, source-pair, closure, owner and typed-ledger gates remain real.
    monkeypatch.setattr(prepare_evaluation, 'verify_implementation', lambda m: None)
    monkeypatch.setattr(evaluation_registration, 'verify_implementation', lambda m: None)
    destination = tmp_path/'evaluation'
    result = prepare_evaluation.build_composite_registration(destination,
        finalization_registration=path, finalization_acceptance=acceptance,
        context_path=context, native_executable=m['native_runtime']['executable'], durable_sequence_claim=True)
    return f, result


def test_real_composite_preparer_and_evaluation_handoff_preserve_second_increase(second_composite):
    f, result = second_composite; path = result['registration']; m = evaluation_registration.read_json(path)
    assert m['budget_amendment'] == f['case']['proof']
    assert m['budget']['additional_usd'] == '600' and m['budget']['per_attempt_usd'] == '5'
    assert 'per_job_attempt_usd' not in m['budget']
    assert amendment.paths(m) <= evaluation_registration.required_paths(m)
    assert evaluation_registration.allocation_total(m) == Decimal('600')
    assert evaluation_registration.verify_manifest(m, path, sequence.sha(path))
    counts = Counter(j['style'] for j in m['evaluation_jobs'])
    assert counts['semantic_agent'] == 12 and counts['field_agent'] == 4 and counts['direct_api_quality'] == 4
    assert not Path(m['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
    previous_path = Path(f['manifest']['budget']['ledger_path']); previous = previous_path.read_bytes()
    with sequence.owned_sequence(m, path, sequence.sha(path)) as owner:
        rows = sequence.read(owner.ledger.path)
        assert rows['additional_cap_usd'] == '600' and len(rows['requests']) == 260
        assert rows['requests'] == sequence.read(previous_path)['requests']
        assert 'budget_amendment_sha256' not in rows['continued_from']
        identity = sequence.sha(path)+':'+m['evaluation_jobs'][0]['id']
        ticket = owner.reserve(identity, '.02', 'synthetic-evaluation')
        owner.ledger.settle(ticket, '.01', response_sha256='synthetic-evaluation-response', usage={})
    assert previous_path.read_bytes() == previous
    assert len(sequence.read(m['budget']['ledger_path'])['requests']) == 261
    unchanged(f['case'], state=False)


@pytest.mark.parametrize('damage', ['drop_second', 'replace_with_first', 'unpin_first_evidence', 'stale_owner'])
def test_real_composite_admission_refuses_dropped_or_stale_second_authority(second_composite, damage):
    f, result = second_composite; path = result['registration']; m = evaluation_registration.read_json(path)
    if damage == 'drop_second': m.pop('budget_amendment')
    elif damage == 'replace_with_first': m['budget_amendment'] = deepcopy(f['case']['first'])
    elif damage == 'unpin_first_evidence': m['pinned_files'].pop(f['case']['first']['authorization']['path'])
    else: save(f['state'], {'synthetic': 'another current owner'})
    save(path, m); before = f['state'].read_bytes()
    with pytest.raises(BudgetStop):
        with sequence.owned_sequence(m, path, sequence.sha(path)):
            pytest.fail('invalid evaluation reached accounting')
    assert f['state'].read_bytes() == before
    assert not Path(m['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
