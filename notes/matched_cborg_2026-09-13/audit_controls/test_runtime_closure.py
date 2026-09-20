"""Offline continuation admission using a later independently reviewed reboot."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from . import registration as r
from .test_budget_exception import exception_case
from .test_registration import accounting, stopped_audit, save, repin


def descriptor(path):
    return {'path': str(path), 'sha256': r.sha(path)}


def rebind(case):
    """Rebind outer hashes so negative tests reach the changed semantic check."""
    m, source, receipt_path, checkpoint, _, proof_path, observation_path, launch_path = case
    bridge = m['budget']['continuation']['reconciliation']
    result_path = Path(bridge['result'])
    proof = r.read_json(proof_path)
    proof['observation'] = descriptor(observation_path)
    proof['launch_observation'] = descriptor(launch_path)
    save(proof_path, proof)
    receipt = r.read_json(receipt_path)
    receipt['runtime_closure'] = descriptor(proof_path)
    receipt['stopped_result_sha256'] = r.sha(result_path)
    save(receipt_path, receipt)
    copied = r.read_json(checkpoint)
    copied['requests'][-1]['reconciliation_receipt_sha256'] = r.sha(receipt_path)
    copied['requests'][-1]['runtime_closure_sha256'] = r.sha(proof_path)
    copied['reconciled_from']['receipt_sha256'] = r.sha(receipt_path)
    copied['reconciled_from']['runtime_closure_sha256'] = r.sha(proof_path)
    save(checkpoint, copied)
    for path in (result_path, receipt_path, checkpoint, proof_path, observation_path, launch_path):
        repin(m, path)


@pytest.fixture(params=['confirmed', 'full_debit'])
def later_closure(request):
    base = request.getfixturevalue('stopped_audit' if request.param == 'confirmed' else 'exception_case')
    m, source, receipt_path, checkpoint, reg = base
    bridge = m['budget']['continuation']['reconciliation']
    source_reg = r.read_json(bridge['source_registration'])
    result_path = Path(bridge['result'])
    result = r.read_json(result_path)
    result['runtime']['unfinished_handlers'] = 1
    save(result_path, result)
    root = reg.parent
    boot_seconds = int(datetime(2026, 9, 18, 0, 11, tzinfo=timezone.utc).timestamp())
    observation = root / 'boot-observation.json'
    save(observation, {'sysctl_boottime': f'{{ sec = {boot_seconds}, usec = 123456 }} retained raw output',
        'boot_at': '2026-09-18T00:11:00Z', 'observed_at': '2026-09-18T00:12:00Z',
        'boot_session_uuid': 'e2724d5b-b1af-4d23-9be3-d7fdb1a5cc39'})
    launch = root / 'launch-observation.json'
    save(launch, {'registration_sha256': r.sha(bridge['source_registration']), 'job_id': source_reg['job']['id'],
        'execution_repository': source_reg['repository'], 'repository_commit': source_reg['repository_commit'],
        'recorded_at': '2026-09-18T00:00:05Z', 'launch_observed': True})
    proof = root / 'runtime-closure.json'
    save(proof, {'schema_version': 1, 'kind': 'independently_reviewed_host_reboot_closure',
        'source_registration_sha256': r.sha(bridge['source_registration']), 'source_ledger_sha256': r.sha(source),
        'stopped_result_sha256': r.sha(result_path), 'job_id': source_reg['job']['id'],
        'billing_attempt': r.read_json(source)['requests'][-1]['attempt'],
        'execution_repository': source_reg['repository'], 'execution_commit': source_reg['repository_commit'],
        'observation': descriptor(observation), 'launch_observation': descriptor(launch),
        'review': {'verdict': 'accept', 'reviewer': 'independent-reviewer', 'observer': 'local-observer',
            'reviewed_at': '2026-09-18T00:13:00Z', 'same_execution_host': True,
            'host_identity_basis': 'independently_reviewed_local_provenance',
            'historical_host_identity': 'not_recorded',
            'basis': 'Synthetic independent review of launch and locally collected OS metadata; no historical host ID.'}})
    case = (*base, proof, observation, launch)
    rebind(case)
    return case


def test_later_closure_advances_once_preserving_historical_runtime_and_accounting(later_closure):
    m, source, receipt, checkpoint, reg, proof, observation, launch = later_closure
    result = Path(m['budget']['continuation']['reconciliation']['result'])
    originals = {p: p.read_bytes() for p in (source, result, receipt, proof, observation, launch)}
    assert r.validate_audit_reconciliation(m) == r.read_json(checkpoint)
    with r.sequence_guard(m, 'new-audit'):
        ledger = r.open_audit_ledger(m, reg, 'new-audit')
    copied = r.read_json(ledger.path)
    assert copied['requests'][:-1] == r.read_json(source)['requests'][:-1]
    row = copied['requests'][-1]
    assert row['runtime_closure_sha256'] == r.sha(proof)
    assert row['source_attempt_outcome'] == 'stopped' and row['provider_usage_is_final'] is False
    if row['settlement_basis'] == 'user_authorized_full_reservation_debit':
        assert row['cost_usd'] == row['reserved_usd']
        assert row['provider_charge_confirmed'] is False and row['provider_charge_usd'] is None
        assert row['released_excess_reservation_usd'] == '0'
        assert row['partial_usage'] == r.read_json(source)['requests'][-1]['partial_usage']
    assert r.read_json(source)['requests'][-1]['status'] == 'pending'
    assert r.read_json(result)['runtime']['unfinished_handlers'] == 1
    assert all(p.read_bytes() == raw for p, raw in originals.items())
    with pytest.raises(r.BudgetStop, match='already consumed'):
        with r.sequence_guard(m, 'new-audit'): pytest.fail('duplicate admission')


def assert_no_admission(case):
    m, source, _, _, _, _, _, _ = case
    original = source.read_bytes()
    state_path = Path(m['sequence_state']);state = state_path.read_bytes()
    with pytest.raises(r.BudgetStop):
        with r.sequence_guard(m, 'refused-successor'): pytest.fail('invalid closure admitted')
    assert source.read_bytes() == original and state_path.read_bytes() == state
    assert not Path(m['budget']['ledger_path']).exists()


@pytest.mark.parametrize('damage', ['source_registration_sha256', 'source_ledger_sha256',
    'stopped_result_sha256', 'job_id', 'billing_attempt', 'execution_repository', 'execution_commit',
    'wrong_host', 'missing_review', 'same_reviewer', 'invented_host_id', 'empty_basis', 'unreviewed',
    'review_before_observation', 'boot_before_stop', 'boot_at_stop', 'observation_before_boot',
    'boot_disagrees', 'timezone_missing', 'raw_boot_missing', 'invalid_uuid', 'launch_wrong_source',
    'launch_after_stop', 'schema_boolean', 'bare_process_disappearance', 'nonobject_observation'])
def test_rebound_invalid_later_closure_cannot_advance_either_accounting_variant(later_closure, damage):
    _, _, _, _, _, proof_path, observation_path, launch_path = later_closure
    proof = r.read_json(proof_path);observation = r.read_json(observation_path);launch = r.read_json(launch_path)
    if damage in {'source_registration_sha256', 'source_ledger_sha256', 'stopped_result_sha256',
                  'job_id', 'billing_attempt', 'execution_repository', 'execution_commit'}:
        proof[damage] = 'unrelated'
    elif damage == 'wrong_host': proof['review']['same_execution_host'] = False
    elif damage == 'missing_review': proof.pop('review')
    elif damage == 'same_reviewer': proof['review']['reviewer'] = proof['review']['observer']
    elif damage == 'invented_host_id': proof['review']['historical_host_identity'] = 'guessed-from-path'
    elif damage == 'empty_basis': proof['review']['basis'] = ' '
    elif damage == 'unreviewed': proof['review']['verdict'] = 'pending'
    elif damage == 'review_before_observation': proof['review']['reviewed_at'] = '2026-09-18T00:11:30Z'
    elif damage in {'boot_before_stop', 'boot_at_stop'}:
        stamp = '2026-09-18T00:09:00+00:00' if damage == 'boot_before_stop' else '2026-09-18T00:10:00+00:00'
        seconds = int(datetime.fromisoformat(stamp).timestamp())
        observation.update(boot_at=stamp, sysctl_boottime=f'{{ sec = {seconds}, usec = 0 }} raw')
    elif damage == 'observation_before_boot': observation['observed_at'] = '2026-09-18T00:10:30Z'
    elif damage == 'boot_disagrees': observation['boot_at'] = '2026-09-18T00:11:01Z'
    elif damage == 'timezone_missing': observation['observed_at'] = '2026-09-18T00:12:00'
    elif damage == 'raw_boot_missing': observation.pop('sysctl_boottime')
    elif damage == 'invalid_uuid': observation['boot_session_uuid'] = 'unrecorded'
    elif damage == 'launch_wrong_source': launch['registration_sha256'] = 'f' * 64
    elif damage == 'launch_after_stop': launch['recorded_at'] = '2026-09-18T00:10:01Z'
    elif damage == 'schema_boolean': proof['schema_version'] = True
    elif damage == 'bare_process_disappearance': observation = {'pid_not_found': True, 'tool_handle': 'unknown'}
    else: observation = []
    save(proof_path, proof);save(observation_path, observation);save(launch_path, launch)
    rebind(later_closure)
    assert_no_admission(later_closure)


@pytest.mark.parametrize('damage', ['missing_supplement', 'missing_pin', 'changed_evidence', 'missing_evidence',
    'boolean_handlers', 'unfinished_shutdown', 'never_initialized', 'unknown_handler_count',
    'missing_runtime', 'changed_original_result', 'different_request_authorization', 'missing_authorization'])
def test_runtime_and_evidence_fail_closed_for_both_accounting_variants(later_closure, damage):
    m, _, receipt_path, _, _, proof_path, observation_path, _ = later_closure
    result_path = Path(m['budget']['continuation']['reconciliation']['result'])
    result = r.read_json(result_path)
    if damage == 'boolean_handlers': result['runtime']['unfinished_handlers'] = False
    elif damage == 'unfinished_shutdown': result['runtime']['proxy_shutdown_complete'] = False
    elif damage == 'never_initialized': result['runtime']['proxy_initialized'] = False
    elif damage == 'unknown_handler_count': result['runtime']['unfinished_handlers'] = None
    elif damage == 'missing_runtime': result.pop('runtime')
    elif damage == 'changed_original_result': result['reason'] = 'rewritten'
    if result != r.read_json(result_path):
        save(result_path, result)
        # Preserve the original proof's result binding except for runtime type
        # tests, which must reach the common runtime gate despite fresh hashes.
        if damage != 'changed_original_result':
            proof = r.read_json(proof_path);proof['stopped_result_sha256'] = r.sha(result_path);save(proof_path, proof)
    rebind(later_closure)
    receipt = r.read_json(receipt_path)
    if damage == 'missing_supplement': receipt.pop('runtime_closure')
    elif damage == 'missing_pin': del m['pinned_files'][str(observation_path)]
    elif damage == 'changed_evidence': observation_path.write_text('{}')
    elif damage == 'missing_evidence': observation_path.unlink()
    elif damage == 'different_request_authorization': receipt['request_id'] = 'another-request'
    elif damage == 'missing_authorization':
        receipt.pop('user_authorization' if 'user_authorization' in receipt else 'user_confirmation')
    if receipt != r.read_json(receipt_path):
        save(receipt_path, receipt);repin(m, receipt_path)
    assert_no_admission(later_closure)


@pytest.mark.parametrize('finished_microseconds,accepted', [('100000', True), ('200000', False)])
def test_raw_boot_microseconds_control_order_even_when_normalized_time_is_truncated(
        later_closure, finished_microseconds, accepted):
    m, _, _, checkpoint, _, proof_path, _, _ = later_closure
    result_path = Path(m['budget']['continuation']['reconciliation']['result'])
    result = r.read_json(result_path)
    result['finished_at'] = f'2026-09-18T00:11:00.{finished_microseconds}Z'
    save(result_path, result)
    proof = r.read_json(proof_path);proof['stopped_result_sha256'] = r.sha(result_path);save(proof_path, proof)
    rebind(later_closure)
    if accepted:
        assert r.validate_audit_reconciliation(m) == r.read_json(checkpoint)
    else:
        assert_no_admission(later_closure)


def test_original_zero_does_not_hide_a_malformed_supplied_closure(later_closure):
    m, _, receipt_path, _, _, _, _, _ = later_closure
    result_path = Path(m['budget']['continuation']['reconciliation']['result'])
    result = r.read_json(result_path);result['runtime']['unfinished_handlers'] = 0;save(result_path, result)
    receipt = r.read_json(receipt_path);receipt['runtime_closure'] = None
    receipt['stopped_result_sha256'] = r.sha(result_path);save(receipt_path, receipt)
    repin(m, result_path);repin(m, receipt_path)
    assert_no_admission(later_closure)


@pytest.mark.parametrize('future_event', ['boot', 'observation', 'review'])
def test_future_closure_evidence_never_advances_current_owner(later_closure, future_event):
    """Ordered but not-yet-observed events cannot establish present closure (#2138)."""
    _, _, _, _, _, proof_path, observation_path, _ = later_closure
    proof = r.read_json(proof_path)
    observation = r.read_json(observation_path)
    proof['review']['reviewed_at'] = '2099-09-18T00:13:00Z'
    if future_event in {'boot', 'observation'}:
        observation['observed_at'] = '2099-09-18T00:12:00Z'
    if future_event == 'boot':
        seconds = int(datetime(2099, 9, 18, 0, 11, tzinfo=timezone.utc).timestamp())
        observation.update(boot_at='2099-09-18T00:11:00Z',
            sysctl_boottime=f'{{ sec = {seconds}, usec = 0 }} retained raw output')
    save(proof_path, proof)
    save(observation_path, observation)
    rebind(later_closure)
    assert_no_admission(later_closure)


@pytest.mark.parametrize('reviewer', ['local-observer ', ' local-observer', 'LOCAL-OBSERVER', '\tlocal-observer\n'])
def test_equivalent_observer_cannot_self_review(later_closure, reviewer):
    """Rebound identities must reach the semantic independence check (#2139)."""
    proof_path = later_closure[5]
    proof = r.read_json(proof_path)
    proof['review']['reviewer'] = reviewer
    save(proof_path, proof)
    rebind(later_closure)
    assert_no_admission(later_closure)
