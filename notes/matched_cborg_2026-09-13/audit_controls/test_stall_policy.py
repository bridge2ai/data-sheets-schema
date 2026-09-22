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
from audit_controls.test_native import native_case, configure_execution, configure_receipt_runner, response_events
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
    """A valid policy; the authorization names the number of debits it covers."""
    value = {'kind': 'bounded_in_attempt_v1', 'count_attempts': 3, 'max_stall_debits': 4, **changes}
    if 'authorization' not in changes:
        value['authorization'] = ({**AUTHORIZATION, 'authorized_max_stall_debits': value['max_stall_debits']}
                                  if value['max_stall_debits'] != 0 else None)
    return value


RUNTIME = {'api_timeout_ms': 3600000, 'api_force_idle_timeout': False}
FULL = {**AUTHORIZATION, 'authorized_max_stall_debits': 4}


def manifest(value=None, **changes):
    return {'kind': 'd4d_native_audit_continuation', KEY: policy() if value is None else value,
            'native_runtime': dict(RUNTIME), 'job': {'deadline_seconds': 10800}, **changes}


def test_omission_preserves_the_historical_stop_and_a_valid_policy_is_reduced_to_its_bounds():
    assert registration.native_stall_policy({}) is None
    assert registration.native_stall_policy(manifest()) == {'count_attempts': 3, 'max_stall_debits': 4}
    counting_only = policy(max_stall_debits=0)
    assert counting_only['authorization'] is None
    assert registration.native_stall_policy(manifest(counting_only)) == {'count_attempts': 3, 'max_stall_debits': 0}
    # Counting retries debit nothing, so they need neither timeout margin nor idle-timer setting.
    assert registration.native_stall_policy(manifest(counting_only, native_runtime={})) == {
        'count_attempts': 3, 'max_stall_debits': 0}


@pytest.mark.parametrize('value', [None, True, [], 'on', {}, policy(kind='other'), policy(count_attempts=0),
    policy(count_attempts=6), policy(count_attempts=True), policy(max_stall_debits=-1), policy(max_stall_debits=11),
    policy(max_stall_debits=1.0), policy(extra=1), policy(authorization=None), policy(authorization={}),
    policy(authorization=dict(AUTHORIZATION)),                                  # names no number of debits
    policy(authorization={**FULL, 'authorized_max_stall_debits': 5}),           # authorizes another number (#2155)
    policy(authorization={**FULL, 'authorized_max_stall_debits': True}),
    policy(authorization={**FULL, 'exact_response': '  '}), policy(authorization={**FULL, 'more': 'x'}),
    policy(authorization={**FULL, 'quoted_request': 5}),
    policy(max_stall_debits=0, authorization=dict(FULL)), {k: v for k, v in policy().items() if k != 'authorization'}])
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


# Three count tries of 120 s with 5 s pauses, 20 s to connect and a minute of margin: 455 s before the read bound.
@pytest.mark.parametrize('api_timeout_ms, read, accepted', [
    (3600000, None, True), (None, None, False), (1800001, None, False),
    (2255000, None, True), (2254999, None, False),                 # the legacy 1800 s bound
    (1500000, 1000, True), (1455000, 1000, True), (1454999, 1000, False),   # a registered bound is what counts (#2155)
    (3600000, 2700, True), (3154999, 2700, False)])
def test_debits_need_the_child_to_outwait_everything_the_proxy_does_first(api_timeout_ms, read, accepted):
    """#2152: otherwise the child gives up first and there is no one left to tell to retry."""
    runtime = {'api_force_idle_timeout': False, **({'api_timeout_ms': api_timeout_ms} if api_timeout_ms else {})}
    m = manifest(native_runtime=runtime)
    if read is not None:
        m['native_upstream_read_timeout_seconds'] = read
    if accepted:
        assert registration.native_stall_policy(m)['max_stall_debits'] == 4
        assert api_timeout_ms >= registration.stall_policy_minimum_api_timeout_ms(m, 3)
    else:
        with pytest.raises(BudgetStop): registration.native_stall_policy(m)


def test_more_count_tries_need_a_longer_child_timeout():
    m = manifest(policy(count_attempts=5), native_runtime={**RUNTIME, 'api_timeout_ms': 2255000})
    with pytest.raises(BudgetStop, match='token-count tries'): registration.native_stall_policy(m)
    m['native_runtime']['api_timeout_ms'] = 2505000
    assert registration.native_stall_policy(m)['count_attempts'] == 5


def test_debits_need_the_native_idle_timer_registered_off():
    m = manifest(native_runtime={'api_timeout_ms': 3600000})
    with pytest.raises(BudgetStop, match='idle timer'): registration.native_stall_policy(m)


@pytest.mark.parametrize('missing', ['native_runtime', 'job'])
def test_a_manifest_without_its_runtime_or_job_is_refused_not_crashed(missing):
    m = manifest(); del m[missing]
    with pytest.raises(BudgetStop): registration.native_stall_policy(m)


@pytest.mark.parametrize('kind', ['d4d_native_finalization', 'd4d_evaluation_registration'])
def test_other_stages_reject_the_policy_before_shared_transport(kind, monkeypatch):
    m = manifest(kind=kind)
    monkeypatch.setattr(transport, 'Client', lambda **kw: pytest.fail('HTTP client constructed'))
    with pytest.raises(BudgetStop, match='audit-only'): transport.provider_clients(m, 'offline-key')


@pytest.mark.parametrize('schema_version', [1, 2])
def test_the_real_evaluation_verifier_refuses_the_policy_before_pins_or_ledger(tmp_path, monkeypatch, schema_version):
    """#2155: through the evaluation controls' own entry, under the kind they really use."""
    import subprocess
    from evaluation_controls import registration as evaluation
    repository = evaluation.HERE.parents[2]
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip()
    m = {'kind': 'd4d_evaluation_registration', 'schema_version': schema_version, 'repository': str(repository),
         'repository_commit': head, 'model': {'model': 'claude-opus-5'},
         'provider_base_url': 'https://api.cborg.lbl.gov', KEY: policy(),
         'native_runtime': dict(RUNTIME), 'job': {'deadline_seconds': 10800}}
    path = tmp_path / 'registration.json'; path.write_text(json.dumps(m))
    for name in ('open_ledger', 'Ledger'):
        if hasattr(evaluation, name):
            monkeypatch.setattr(evaluation, name, lambda *a, **k: pytest.fail('ledger before refusal'))
    with pytest.raises(BudgetStop, match='audit-only'):
        evaluation.verify_manifest(m, path, evaluation.sha(path))
    assert sorted(p.name for p in tmp_path.iterdir()) == ['registration.json']


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
    c.manifest['native_runtime'].update(RUNTIME)
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


@pytest.mark.parametrize('registered', [True, False])
def test_the_terminal_result_lists_debited_requests_only_under_a_registered_policy(native_case, monkeypatch, registered):
    """#2155/#2158: through run_job, which writes result.json; a legacy result keeps its exact keys.

    The upstream answers the first request with 524. Under the policy that
    stall is counted and the synthetic child carries on; this receipt harness
    then stops at its own validation-identity check, which is enough to see
    the terminal result. Without a policy the first stall stops the attempt."""
    c = native_case
    _, sdk, review = configure_receipt_runner(c, monkeypatch)
    if registered:
        c.manifest.update(kind='d4d_native_audit_continuation', **{KEY: policy()})
        c.manifest['native_runtime'].update(RUNTIME)
        c.job['deadline_seconds'] = 3600
    outcomes = iter([httpx.Response(524)])
    def respond(request):
        return next(outcomes, None) or httpx.Response(200, content=response_events(),
                                                      headers={'content-type': 'text/event-stream'})
    upstream = httpx.Client(transport=httpx.MockTransport(respond))
    def adapter(context): return native.execute_job(context, client=sdk, upstream=upstream)
    with pytest.raises(BudgetStop): native.run_job(c.registration, review, adapter=adapter)
    receipt = json.loads((c.attempt / 'result.json').read_text())
    requests = json.loads(c.ledger.path.read_text())['requests']
    assert receipt['status'] == 'stopped'
    if registered:
        # The stall did not stop it. What does stop this harness afterwards varies with
        # the synthetic child's timing, so only the stall's own outcome is asserted.
        assert receipt['reason'] != 'upstream HTTP response did not confirm a completed charge'
        assert requests[0]['settlement_basis'] == STALL_DEBIT_BASIS
        assert receipt['stall_debited_requests'] == [requests[0]['id']]
        assert requests[0]['id'] not in receipt['unresolved_requests']
    else:
        assert receipt['stop_source'] == 'native_proxy'
        assert [r['status'] for r in requests] == ['pending']
        assert 'stall_debited_requests' not in receipt and receipt['unresolved_requests'] == [requests[0]['id']]


def test_real_audit_entry_without_the_policy_still_stops_on_the_first_stall(native_case, monkeypatch):
    c = native_case
    context, sdk = configure_execution(c, monkeypatch)
    upstream = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(524)))
    with pytest.raises(BudgetStop, match='did not confirm a completed charge'):
        native.execute_job(context, client=sdk, upstream=upstream)
    (row,) = json.loads(c.ledger.path.read_text())['requests']
    assert row['status'] == 'pending' and not list(Path(c.attempt).rglob('stall.json'))


def test_fresh_policy_is_registered_pinned_and_scientifically_inert(ancestry, tmp_path):
    common = dict(ancestry[0], native_api_timeout_ms=3600000, native_api_force_idle_timeout=False,
                  staged_audit_output=True, context_recovery=True)
    # Equal-length destinations keep recovery frame boundaries comparable.
    legacy = prepare.prepare(**common, destination=tmp_path / 'legacy__')
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
    # A legacy plan is unchanged by this feature (#2158).
    assert KEY not in json.loads((legacy.parent / 'offline_plan.json').read_text())
    assert not Path(after['job']['attempt_dir']).exists() and not Path(after['budget']['ledger_path']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}


@pytest.mark.parametrize('value, sdk, idle, reason', [
    (policy(kind='x'), 3600000, False, 'audit-only'), (policy(), None, False, 'bounded native API timeout'),
    (policy(), 1800000, False, 'native SDK timeout'), (policy(), 3600000, None, 'idle timer'),
    (policy(authorization=None), 3600000, False, 'standing authorization'), ('on', 3600000, False, 'audit-only')])
def test_invalid_policy_refused_by_its_own_validator_before_destination_creation(tmp_path, value, sdk, idle, reason):
    """The reason is matched, because the preparer's later repository-root check would also raise (#2155)."""
    destination = tmp_path / 'uncreated'
    arguments = dict(parent_registration=None, parent_overlay=None, parent_job_id=None,
        reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
        job_id='unused', repository=tmp_path, native_api_timeout_ms=sdk, native_api_force_idle_timeout=idle)
    with pytest.raises(registration.BudgetStop, match=reason):
        prepare.prepare(**arguments, native_stall_policy=value)
    assert not destination.exists()
    # The same harness with a valid policy gets past the validator, to the next gate.
    with pytest.raises(registration.BudgetStop, match='repository root'):
        prepare.prepare(**{**arguments, 'native_api_timeout_ms': 3600000, 'native_api_force_idle_timeout': False},
                        native_stall_policy=policy())


@pytest.mark.parametrize('text, reason', [('null', 'one JSON object'), ('[]', 'one JSON object'), ('"on"', 'one JSON object'),
    ('{"max_stall_debits": 0, "max_stall_debits": 10}', 'unreadable: ValueError'), ('{not json', 'unreadable'),
    (None, 'unreadable: FileNotFoundError')])
def test_the_policy_file_is_read_strictly(tmp_path, monkeypatch, text, reason):
    """#2153: a named file never registers the legacy condition or a value nobody wrote."""
    path = tmp_path / 'policy.json'
    if text is not None:
        path.write_text(text)
    with pytest.raises(BudgetStop, match=reason): prepare.read_stall_policy(path)
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: pytest.fail('prepared with an unreadable policy'))
    monkeypatch.setattr(sys, 'argv', ['prepare', *[part for name in ('parent-registration', 'parent-overlay',
        'parent-job-id', 'reconciliation-receipt', 'reconciled-checkpoint', 'destination', 'job-id')
        for part in ('--' + name, 'x')], '--native-stall-policy', str(path)])
    with pytest.raises(BudgetStop, match=reason): prepare.main()


def test_the_command_line_passes_the_written_policy_through(tmp_path, monkeypatch):
    path = tmp_path / 'policy.json'; path.write_text(json.dumps(policy()))
    seen = {}
    monkeypatch.setattr(prepare, 'prepare', lambda **kw: seen.update(kw) or tmp_path / 'registration.json')
    monkeypatch.setattr(prepare, 'sha', lambda _: 'synthetic')
    monkeypatch.setattr(sys, 'argv', ['prepare', *[part for name in ('parent-registration', 'parent-overlay',
        'parent-job-id', 'reconciliation-receipt', 'reconciled-checkpoint', 'destination', 'job-id')
        for part in ('--' + name, 'x')], '--native-stall-policy', str(path)])
    prepare.main()
    assert seen['native_stall_policy'] == policy()


def test_real_phase4_preparation_keeps_an_accepted_policy_as_evidence_only(ancestry, tmp_path):
    with_policy = ({**ancestry[0], 'native_api_timeout_ms': 3600000, 'native_api_force_idle_timeout': False,
                    'native_stall_policy': policy()}, *ancestry[1:])
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
