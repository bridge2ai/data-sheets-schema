"""The registered audit-only stall policy: validation, preparation, wiring and non-inheritance (#2150)."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import native, prepare, registration, transport
from audit_controls.test_native import native_case, configure_execution, response_events
from audit_controls.test_context_preparation import ancestry, accepted_audit, save
from audit_controls.test_staged_preparation import actual_renderer_history_root
from budgeted_cborg import BudgetStop, STALL_DEBIT_BASIS
from finalization_controls import native as final_native
from finalization_controls import prepare as final_prepare, registration as final_registration
import run_api_canary

KEY = 'native_stall_policy'
AUTHORIZATION = {'exact_response': 'synthetic standing approval', 'recorded_at': '2026-09-21T00:00:00+00:00',
                 'quoted_request': 'May stalled requests be counted at their whole reservation, at most N per attempt?'}


def policy(**changes):
    return {'kind': 'bounded_in_attempt_v1', 'count_attempts': 3, 'max_stall_debits': 4,
            'authorization': dict(AUTHORIZATION), **changes}


def manifest(value=None, **changes):
    return {'kind': 'd4d_native_audit_continuation', KEY: policy() if value is None else value,
            'native_runtime': {'api_timeout_ms': 3600000}, 'job': {'deadline_seconds': 10800}, **changes}


def test_omission_preserves_the_historical_stop_and_a_valid_policy_is_reduced_to_its_bounds():
    assert registration.native_stall_policy({}) is None
    assert registration.native_stall_policy(manifest()) == {'count_attempts': 3, 'max_stall_debits': 4}
    counting_only = policy(max_stall_debits=0, authorization=None)
    assert registration.native_stall_policy(manifest(counting_only)) == {'count_attempts': 3, 'max_stall_debits': 0}


@pytest.mark.parametrize('value', [None, True, [], 'on', {}, policy(kind='other'), policy(count_attempts=0),
    policy(count_attempts=6), policy(count_attempts=True), policy(max_stall_debits=-1), policy(max_stall_debits=11),
    policy(max_stall_debits=1.0), policy(extra=1), policy(authorization=None), policy(authorization={}),
    policy(authorization={**AUTHORIZATION, 'exact_response': '  '}), policy(authorization={**AUTHORIZATION, 'more': 'x'}),
    policy(authorization={**AUTHORIZATION, 'quoted_request': 5}),
    policy(max_stall_debits=0), {k: v for k, v in policy().items() if k != 'authorization'}])
def test_a_malformed_policy_is_refused_before_runtime_setup_or_client(value, tmp_path, monkeypatch):
    m = manifest(); m[KEY] = value
    monkeypatch.setattr(native, 'build_policy', lambda *_: pytest.fail('policy before selector validation'))
    monkeypatch.setattr(native, 'verify_runtime', lambda *_: pytest.fail('runtime before selector validation'))
    monkeypatch.setattr(transport, 'Client', lambda **kw: pytest.fail('HTTP client before selector validation'))
    context = SimpleNamespace(manifest=m, job=m['job'], attempt=tmp_path)
    with pytest.raises(BudgetStop): registration.native_stall_policy(m)
    with pytest.raises(BudgetStop): native.execute_job(context)
    with pytest.raises(BudgetStop): transport.provider_clients(m, 'offline-key')
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('runtime, read, accepted', [({'api_timeout_ms': 3600000}, None, True),
    ({}, None, False), ({'api_timeout_ms': 1800000}, None, False), ({'api_timeout_ms': 1800001}, None, True),
    ({'api_timeout_ms': 3600000}, 2700, True), ({'api_timeout_ms': 2700000}, 2699, True)])
def test_debits_need_the_child_to_outwait_the_upstream_read_bound(runtime, read, accepted):
    """Otherwise the child gives up first and there is no one left to tell to retry."""
    m = manifest(native_runtime=runtime)
    if read is not None:
        m['native_upstream_read_timeout_seconds'] = read
    if accepted:
        assert registration.native_stall_policy(m)['max_stall_debits'] == 4
    else:
        with pytest.raises(BudgetStop): registration.native_stall_policy(m)
    # Counting retries alone carry no such requirement: nothing is debited.
    m[KEY] = policy(max_stall_debits=0, authorization=None)
    assert registration.native_stall_policy(m)['max_stall_debits'] == 0


@pytest.mark.parametrize('kind', ['d4d_native_finalization', 'd4d_evaluation', 'd4d_evaluation_source_pair'])
def test_other_stages_reject_the_policy_before_shared_transport(kind, monkeypatch):
    m = manifest(kind=kind)
    monkeypatch.setattr(transport, 'Client', lambda **kw: pytest.fail('HTTP client constructed'))
    with pytest.raises(BudgetStop, match='audit-only'): transport.provider_clients(m, 'offline-key')


@pytest.mark.parametrize('kind', ['d4d_native_finalization', 'd4d_native_audit_continuation'])
def test_actual_phase4_entry_rejects_the_policy_even_with_audit_kind(tmp_path, monkeypatch, kind):
    m = manifest(kind=kind)
    monkeypatch.setattr(final_native, 'build_policy', lambda *_: pytest.fail('Phase4 policy constructed'))
    context = SimpleNamespace(manifest=m, job=m['job'], attempt=tmp_path)
    with pytest.raises(BudgetStop, match='audit-only|native audit controller'):
        final_native.execute_job(context)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('value', [policy(), None, True])
def test_shared_generation_verifier_rejects_the_policy_before_other_checks(tmp_path, monkeypatch, value):
    from audit_controls.test_upstream_timeout import generation_manifest
    m = generation_manifest(tmp_path, monkeypatch)
    m[KEY] = value
    path = tmp_path / 'registration.json'; path.write_text(json.dumps(m))
    digest = run_api_canary.sha(path)
    monkeypatch.setattr(run_api_canary, 'sha', lambda *_: pytest.fail('hash check before audit-only rejection'))
    with pytest.raises(BudgetStop, match='audit-only'):
        run_api_canary.verify(m, path, digest)


def test_real_audit_entry_survives_a_registered_stall_and_reports_it(native_case, monkeypatch):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    c.manifest.update(kind='d4d_native_audit_continuation', **{KEY: policy()})
    c.manifest['native_runtime']['api_timeout_ms'] = 3600000
    c.job['deadline_seconds'] = 3600
    outcomes = iter([httpx.Response(524, content=b'synthetic origin timeout')])
    def respond(request):
        stalled = next(outcomes, None)
        return stalled or httpx.Response(200, content=response_events(), headers={'content-type': 'text/event-stream'})
    result = native.execute_job(context, client=sdk, upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    assert result['validation']['passed'] and result['runtime']['unfinished_handlers'] == 0
    requests = json.loads(c.ledger.path.read_text())['requests']
    assert [r['status'] for r in requests] == ['settled'] * len(requests) and len(requests) >= 2
    assert [r.get('settlement_basis') for r in requests] == [STALL_DEBIT_BASIS] + [None] * (len(requests) - 1)
    assert len(list(Path(c.attempt).rglob('stall.json'))) == 1


def test_real_audit_entry_without_the_policy_still_stops_on_the_first_stall(native_case, monkeypatch):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    upstream = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(524)))
    with pytest.raises(BudgetStop, match='did not confirm a completed charge'):
        native.execute_job(context, client=sdk, upstream=upstream)
    (row,) = json.loads(c.ledger.path.read_text())['requests']
    assert row['status'] == 'pending' and not list(Path(c.attempt).rglob('stall.json'))


def test_fresh_policy_is_registered_pinned_and_scientifically_inert(ancestry, tmp_path):
    common = dict(ancestry[0], native_api_timeout_ms=3600000, staged_audit_output=True, context_recovery=True)
    legacy = prepare.prepare(**common, destination=tmp_path / 'legacy')
    selected = prepare.prepare(**common, destination=tmp_path / 'selected', native_stall_policy=policy())
    before = registration.validate_registration(legacy)
    after = registration.validate_registration(selected)
    assert KEY not in before and after[KEY] == policy()
    assert registration.native_stall_policy(after) == {'count_attempts': 3, 'max_stall_debits': 4}
    for key in ('model', 'profile', 'provider_base_url', 'provider_context_policy', 'native_runtime', 'budget'):
        expected = deepcopy(before[key])
        if key == 'budget':     # only the exclusive ledger location follows the fresh destination
            expected['ledger_path'] = after[key]['ledger_path']
        assert after[key] == expected
    for key in ('instruction', 'system_prompt'):
        assert Path(after['job'][key]).read_text().replace(str(selected.parent), str(legacy.parent)).replace(
            after['context_recovery']['index']['sha256'], before['context_recovery']['index']['sha256']) == Path(before['job'][key]).read_text()
    for role, path in after['inputs'].items():
        assert Path(path).read_bytes() == Path(before['inputs'][role]).read_bytes()
    for path in registration.required_paths(after):
        assert after['pinned_files'][str(path)] == registration.sha(path)
    plan = json.loads((selected.parent / 'offline_plan.json').read_text())
    assert plan['native_stall_policy'] == {'kind': 'bounded_in_attempt_v1', 'count_attempts': 3, 'max_stall_debits': 4}
    assert json.loads((legacy.parent / 'offline_plan.json').read_text())['native_stall_policy'] == 'stop_on_first_stall'
    assert not Path(after['job']['attempt_dir']).exists() and not Path(after['budget']['ledger_path']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}


@pytest.mark.parametrize('value, sdk', [(policy(kind='x'), 3600000), (policy(), None), (policy(), 1800000),
                                        (policy(authorization=None), 3600000), ('on', 3600000)])
def test_invalid_policy_refused_before_destination_creation(tmp_path, value, sdk):
    destination = tmp_path / 'uncreated'
    with pytest.raises(registration.BudgetStop):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, native_api_timeout_ms=sdk, native_stall_policy=value)
    assert not destination.exists()


def test_real_phase4_preparation_keeps_an_accepted_policy_as_evidence_only(ancestry, tmp_path):
    with_policy = ({**ancestry[0], 'native_api_timeout_ms': 3600000, 'native_stall_policy': policy()}, *ancestry[1:])
    accepted, acceptance = accepted_audit(with_policy, tmp_path / 'accepted')
    accepted_bytes = accepted.read_bytes()
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=tmp_path / 'phase4', job_id='synthetic_final', repository=ancestry[0]['repository'])
    phase4 = final_registration.validate_registration(path)
    assert KEY not in phase4 and registration.read_json(accepted)[KEY] == policy()
    assert accepted.read_bytes() == accepted_bytes
    phase4[KEY] = policy(); save(path, phase4)
    with pytest.raises(registration.BudgetStop, match='audit-only'):
        final_registration.validate_registration(path)
    assert not Path(phase4['job']['attempt_dir']).exists()
