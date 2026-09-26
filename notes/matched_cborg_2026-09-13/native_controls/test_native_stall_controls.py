"""Stall controls: stop on a repeated identical stall (#2465) and a separate stall allowance (#2466).

Synthetic upstreams and ledgers only."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

import httpx
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]

from budgeted_cborg import (BudgetStop, Ledger, REPEATED_STALL_REASON, RepeatedStall, STALL_DEBIT_BASIS,
                            attempt_spend)
from native_proxy import validated_stall_policy
from native_controls.test_native_proxy import REQUEST
from native_controls.test_native_stall_policy import good, post, proxy_with, rows
from audit_controls import registration
from audit_controls.test_stall_policy import AUTHORIZATION, manifest, policy
from audit_controls.test_registration import accounting  # noqa: F401  (fixture)

REPEAT = {'count_attempts': 3, 'max_stall_debits': 4, 'identical_stall_stop': 2}


# --- #2465: the same bytes stalling again end the attempt, with every debit recorded ----------

def test_a_second_stall_of_the_same_bytes_is_debited_and_ends_the_attempt(tmp_path):
    proxy, ledger, calls = proxy_with(tmp_path, [httpx.Response(500), httpx.Response(500), good()], policy=REPEAT)
    with proxy.running() as url:
        first = post(url, proxy)
        second = post(url, proxy)
        third = post(url, proxy)
    assert first.status_code == 503 and first.headers['x-should-retry'] == 'true'
    # Not asked to resend: the attempt stops with nothing left pending.
    assert second.status_code == 402 and third.status_code == 402 and len(calls) == 2
    assert proxy.failure == REPEATED_STALL_REASON and proxy.stalls_survived == 1     # the stop was not survived
    state = json.loads(ledger.path.read_bytes())
    assert [r['status'] for r in state['requests']] == ['settled', 'settled']
    assert all(r['settlement_basis'] == STALL_DEBIT_BASIS for r in state['requests'])
    (stop,) = state['stopped_attempts'].values()
    assert stop['reason'] == REPEATED_STALL_REASON and stop['identical_stalls'] == 2 and stop['paid_request'] is True
    assert stop['repeated_request_sha256'] == state['requests'][0]['request_sha256']
    assert all(type(r['stall_evidence']['upstream_elapsed_seconds']) is float for r in state['requests'])
    # Both stalls keep their evidence beside the request, the stopping one included (#2525).
    replies = sorted(json.loads(p.read_text())['child_reply_attempted'] for p in (tmp_path / 'requests').rglob('stall.json'))
    assert replies == [402, 503]


def test_different_request_bytes_are_not_a_repeat(tmp_path):
    proxy, ledger, calls = proxy_with(tmp_path, [httpx.Response(500), httpx.Response(500), good()], policy=REPEAT)
    other = {**REQUEST, 'messages': [{'role': 'user', 'content': 'a later turn'}]}
    with proxy.running() as url:
        assert post(url, proxy).status_code == 503
        assert httpx.post(url + '/v1/messages?beta=true', json=other,
                          headers={'x-api-key': proxy.token}).status_code == 503
        assert post(url, proxy).status_code == 200
    assert not proxy.failed.is_set() and len(calls) == 3


def test_without_the_stop_identical_stalls_are_retried_as_before(tmp_path):
    policy_without = {'count_attempts': 3, 'max_stall_debits': 4}
    proxy, ledger, calls = proxy_with(tmp_path, [httpx.Response(500)] * 3 + [good()], policy=policy_without)
    with proxy.running() as url:
        assert [post(url, proxy).status_code for _ in range(4)] == [503, 503, 503, 200]
    assert 'upstream_elapsed_seconds' not in rows(ledger)[0]['stall_evidence']      # legacy evidence shape


@pytest.mark.parametrize('value', [1, 5, True, '2', 2.0])
def test_a_malformed_repeat_stop_is_refused(value):
    with pytest.raises(BudgetStop):
        validated_stall_policy({**REPEAT, 'identical_stall_stop': value})


def test_the_ledger_records_the_repeated_debit_before_it_stops(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.json', manifest_sha256='offline', attempt_cap=20)
    for index in (1, 2):
        ticket = ledger.reserve('attempt', Decimal('2'), 'same-bytes')
        if index == 1:
            assert ledger.debit_unconfirmed(ticket, maximum=4, evidence={}, identical_stop=2) == 1
        else:
            with pytest.raises(RepeatedStall):
                ledger.debit_unconfirmed(ticket, maximum=4, evidence={}, identical_stop=2)
    state = json.loads(ledger.path.read_bytes())
    assert all(r['status'] == 'settled' for r in state['requests'])
    with pytest.raises(BudgetStop, match='previously stopped'):
        ledger.reserve('attempt', Decimal('1'), 'other-bytes')


# --- #2466: stall debits are charged to their own allowance before the attempt cap ------------

def _stall_then_reserve(ledger, stalls, next_reservation='2'):
    for index in range(stalls):
        ticket = ledger.reserve('attempt', Decimal('2'), f'bytes-{index}')
        ledger.debit_unconfirmed(ticket, maximum=10, evidence={})
    return ledger.reserve('attempt', Decimal(next_reservation), 'after-stalls')


def test_stall_debits_use_the_allowance_before_the_attempt_cap(tmp_path):
    # Two $2 stalls under a $5 cap leave no room for a third $2 request...
    plain = Ledger(tmp_path / 'plain.json', manifest_sha256='offline', attempt_cap=5)
    with pytest.raises(BudgetStop, match='exceeds remaining budget'):
        _stall_then_reserve(plain, 2)
    # ...unless a $4 stall allowance absorbs them.
    allowed = Ledger(tmp_path / 'allowed.json', manifest_sha256='offline', attempt_cap=5, stall_allowance_usd='4')
    assert _stall_then_reserve(allowed, 2)
    assert json.loads(allowed.path.read_bytes())['stall_allowance_usd'] == '4'
    # Stalls beyond the allowance count against the cap again.
    beyond = Ledger(tmp_path / 'beyond.json', manifest_sha256='offline', attempt_cap=5, stall_allowance_usd='2')
    with pytest.raises(BudgetStop, match='exceeds remaining budget'):
        _stall_then_reserve(beyond, 2, next_reservation='3.5')


def test_the_sequence_cap_still_counts_every_stall(tmp_path):
    ledger = Ledger(tmp_path / 'ledger.json', manifest_sha256='offline', total_cap=5, attempt_cap=5,
                    stall_allowance_usd='4')
    # The attempt had $5 left once the allowance absorbed the stalls; the sequence had $1 (#2526).
    with pytest.raises(BudgetStop, match=r'attempt \$5, sequence \$1\b'):
        _stall_then_reserve(ledger, 2)


def test_attempt_spend_charges_stalls_to_the_allowance_first():
    stall = {'settlement_basis': STALL_DEBIT_BASIS, 'cost_usd': '2.5'}
    ordinary = {'cost_usd': '1.25'}
    assert attempt_spend([stall, stall, ordinary]) == Decimal('6.25')
    assert attempt_spend([stall, stall, ordinary], Decimal('4')) == Decimal('2.25')
    assert attempt_spend([stall, ordinary], Decimal('10')) == Decimal('1.25')
    # Like the plain sum it replaces, a row without a cost is refused, never skipped (#2526).
    with pytest.raises((KeyError, TypeError, ArithmeticError)):
        attempt_spend([{'status': 'pending'}])


@pytest.mark.parametrize('value', ['0', '-1', 'x', 4, 'NaN', 'Infinity', '1e6', '1_000', ' 5 ', '5.', '05'])
def test_a_malformed_allowance_is_refused(tmp_path, value):
    with pytest.raises(BudgetStop):
        Ledger(tmp_path / 'ledger.json', manifest_sha256='offline', stall_allowance_usd=value)


# --- registration -------------------------------------------------------------------------------

def _with(**changes):
    value = policy(**{k: v for k, v in changes.items() if k != 'authorized'})
    if 'authorized' in changes:
        value['authorization'] = {**value['authorization'], **changes['authorized']}
    # An allowance is bounded by max_stall_debits times the job's attempt cap (#2524).
    return manifest(value, job={'id': 'audit', 'deadline_seconds': 10800},
                    budget={'per_job_attempt_usd': {'audit': '20'}})


def test_registration_carries_the_repeat_stop_and_quotes_the_allowance():
    assert registration.native_stall_policy(_with(identical_stall_stop=2)) == {
        'count_attempts': 3, 'max_stall_debits': 4, 'identical_stall_stop': 2}
    accepted = _with(stall_allowance_usd='12.5', authorized={'authorized_stall_allowance_usd': '12.5'})
    registration.native_stall_policy(accepted)
    assert registration.stall_allowance(accepted) == Decimal('12.5')
    assert registration.stall_allowance(manifest()) == Decimal(0)


@pytest.mark.parametrize('changes', [
    {'identical_stall_stop': 1}, {'identical_stall_stop': 5},
    {'stall_allowance_usd': '12.5'},                                                      # not authorized
    {'stall_allowance_usd': '12.5', 'authorized': {'authorized_stall_allowance_usd': '10'}},
    {'stall_allowance_usd': 12.5, 'authorized': {'authorized_stall_allowance_usd': 12.5}},
    {'authorized': {'authorized_stall_allowance_usd': '12.5'}},                           # quote without a field
    {'stall_allowance_usd': None, 'authorized': {'authorized_stall_allowance_usd': None}},
    {'stall_allowance_usd': '1e1', 'authorized': {'authorized_stall_allowance_usd': '1e1'}},
    {'stall_allowance_usd': '80.01', 'authorized': {'authorized_stall_allowance_usd': '80.01'}},  # > 4 x $20
])
def test_registration_refuses_an_unbounded_or_unquoted_control(changes):
    with pytest.raises(BudgetStop):
        registration.native_stall_policy(_with(**changes))


def test_an_allowance_needs_a_policy_that_debits(tmp_path):
    value = policy(max_stall_debits=0, stall_allowance_usd='5')
    with pytest.raises(BudgetStop, match='allows stall debits'):
        registration.native_stall_policy(manifest(value))


def test_the_audit_ledger_carries_the_registered_allowance(accounting):
    from copy import deepcopy
    m, _, _, _, reg = accounting
    audit = deepcopy(m)
    audit['native_stall_policy'] = policy(stall_allowance_usd='7.5',
                                          authorization={**AUTHORIZATION, 'authorized_max_stall_debits': 4,
                                                         'authorized_stall_allowance_usd': '7.5'})
    Path(reg).parent.mkdir(parents=True, exist_ok=True)
    Path(reg).write_text(json.dumps(audit))
    identity = hashlib.sha256(Path(reg).read_bytes()).hexdigest()
    ledger = registration.open_audit_ledger(audit, reg, identity)
    assert ledger.stall_allowance == Decimal('7.5')
    assert json.loads(ledger.path.read_bytes())['stall_allowance_usd'] == '7.5'
    # Reopened without its allowance, the ledger refuses rather than drop it (#2523).
    del audit['native_stall_policy']
    with pytest.raises(BudgetStop, match='registration or budget changed'):
        registration.open_audit_ledger(audit, reg, identity).check_attempt('any')



def test_the_allowance_bound_admits_exactly_its_maximum():
    registration.native_stall_policy(_with(stall_allowance_usd='80', authorized={'authorized_stall_allowance_usd': '80'}))


def test_a_ledger_keeps_its_allowance_both_ways_on_reopen(tmp_path):
    with_allowance = Ledger(tmp_path / 'a.json', manifest_sha256='m', attempt_cap=5, stall_allowance_usd='4')
    with_allowance.reserve('att', Decimal('1'), 'x')
    for other in ({}, {'stall_allowance_usd': '4.0'}):
        with pytest.raises(BudgetStop, match='registration or budget changed'):
            Ledger(tmp_path / 'a.json', manifest_sha256='m', attempt_cap=5, **other).check_attempt('att')
    Ledger(tmp_path / 'plain.json', manifest_sha256='m', attempt_cap=5).reserve('att', Decimal('1'), 'x')
    with pytest.raises(BudgetStop, match='registration or budget changed'):
        Ledger(tmp_path / 'plain.json', manifest_sha256='m', attempt_cap=5, stall_allowance_usd='4').check_attempt('att')


def test_elapsed_time_is_the_provider_exchange_not_the_count(tmp_path):
    """#2522: a slow token count before an instant 500 is not upstream time."""
    import time
    from types import SimpleNamespace
    def slow_count(**kw):
        time.sleep(1.0)
        return SimpleNamespace(input_tokens=100)
    policy_count = {'count_attempts': 3, 'max_stall_debits': 4, 'identical_stall_stop': 3}
    proxy, ledger, _ = proxy_with(tmp_path, [httpx.Response(500)], policy=policy_count, count=slow_count)
    with proxy.running() as url:
        assert post(url, proxy).status_code == 503
    assert rows(ledger)[0]['stall_evidence']['upstream_elapsed_seconds'] < 0.5


def test_a_buffered_stall_records_its_elapsed_time_and_can_stop(tmp_path):
    """#2521: the response-buffer path carries the same evidence and the same stop."""
    from native_controls.test_native_stall_policy import OFFLINE
    from native_controls.test_native_response_buffer import BUFFER, response
    from native_controls.test_native_proxy import events, wire
    partial = wire(events()[:2])
    proxy, ledger, _ = proxy_with(tmp_path, [response([partial], httpx.ReadError('x', request=OFFLINE)),
                                             response([partial], httpx.ReadError('x', request=OFFLINE))],
                                  policy=REPEAT, response_buffer=BUFFER)
    with proxy.running() as url:
        assert post(url, proxy).status_code == 503
        assert post(url, proxy).status_code == 402
    assert proxy.failure == REPEATED_STALL_REASON
    assert all(type(r['stall_evidence']['upstream_elapsed_seconds']) is float for r in rows(ledger))


def test_a_batch_child_launches_on_the_stage_the_allowance_left(tmp_path, monkeypatch):
    """#2520: stall debits the allowance absorbed do not refuse or shrink the next child."""
    import threading
    from types import SimpleNamespace
    from audit_controls import batch_native
    stall = lambda i: {'id': f's{i}', 'attempt': 'reg:job', 'status': 'settled', 'cost_usd': '2.45',
                       'settlement_basis': STALL_DEBIT_BASIS}
    before = [stall(0), stall(1), {'id': 'ok', 'attempt': 'reg:job', 'status': 'settled', 'cost_usd': '1.2'}]
    launched = {}
    class Launched(Exception):
        pass
    def record(root, value):
        if Path(root).name == 'started.json':
            launched.update(value)
            raise Launched
    for name, value in (('build_policy', lambda *a: {'readonly_lookups': {'inputs': []}}),
                        ('_history', lambda *a, **k: None), ('_own_rows', lambda m, i: before),
                        ('_remaining', lambda *a, **k: 100), ('write_new', record),
                        ('provider_clients', lambda manifest, key: (SimpleNamespace(), SimpleNamespace())),
                        ('permission_arguments', lambda policy: []),
                        ('BatchProxy', lambda **kw: SimpleNamespace(token='offline', frozen=False, failure=None,
                                                                    failed=threading.Event(), unfinished_handlers=0))):
        monkeypatch.setattr(batch_native, name, value)
    monkeypatch.setattr(batch_native.native, 'verify_runtime', lambda manifest: Path('/bin/true'))
    manifest = _with(stall_allowance_usd='5', authorized={'authorized_stall_allowance_usd': '5'})
    manifest.update({'audit_batches': {'worker_total_cap_usd': '6'}, 'model': {'model': 'claude-opus-5'},
                     'repository': str(tmp_path), 'python': str(tmp_path / 'bin/python'),
                     'provider_base_url': 'https://api.cborg.lbl.gov'})
    manifest['budget']['prices_per_token'] = {}
    registration.native_stall_policy(manifest)
    ledger = Ledger(tmp_path / 'l.json', manifest_sha256='reg', total_cap=500, attempt_cap=5,
                    attempt_caps_usd={'reg:job': '20'}, stall_allowance_usd='5')
    context = SimpleNamespace(manifest=manifest, manifest_sha256='reg', job=manifest['job'],
                              registration_path=tmp_path / 'r.json', ledger=ledger)
    row = {'id': 'w2', 'kind': 'worker', 'attempt_dir': str(tmp_path / 'w2'), 'output_dir': str(tmp_path / 'w2out'),
           'rounds': [], 'system_prompt': str(tmp_path / 'system.md')}
    (tmp_path / 'system.md').write_text('synthetic')
    # Launch is interrupted at its record; the stubbed runtime's cleanup then fails, which is not under test.
    with pytest.raises(BaseException):
        batch_native._execute_child(context, row, deadline=10**9, clock=lambda: 0)
    # $6 stage, $1.20 counted: the child's own budget is the $4.80 the ledger would admit.
    assert Decimal(launched['child_cli_cap_usd']) == Decimal('4.8') and launched['stage_cap_usd'] == '6'
