"""Lifecycle and admission locking for the selected control; invented data only."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop
from native_control import CONTRACT, HISTORY_CONTRACT
import native_control
import run_native_canary as runner
from . import native, batch_native as batch_runtime
from .test_batch_runtime import batch


SELECTOR = {'kind': 'responsive_history_v1'}


def history_proxy(tmp_path, *, selected=True):
    policy = {'pretool_control': deepcopy(HISTORY_CONTRACT if selected else CONTRACT)}
    history = native.AuditHistory({'job': {'audit_path': str(tmp_path/'audit'),
        'attempt_dir': str(tmp_path)}}, 'synthetic', policy)
    proxy = native.AuditProxy.__new__(native.AuditProxy)
    proxy.audit_history = history
    proxy.state = threading.Condition(threading.RLock())
    proxy.closed = proxy.frozen = False
    proxy.admission_closed = threading.Event()
    history.admission_cancelled = proxy.admission_closed if selected else None
    return history, proxy


def async_call(call):
    failures = []
    def run():
        try: call()
        except BaseException as error: failures.append(error)
    thread = threading.Thread(target=run)
    thread.start()
    return thread, failures


def test_selected_stop_does_not_wait_for_blocked_history_or_reserve_after_return(tmp_path):
    history, proxy = history_proxy(tmp_path)
    entered, release = threading.Event(), threading.Event()
    reserved = []
    def verify():
        with history.admission_lock():
            entered.set()
            assert release.wait(3)
    history.verify_admission = verify
    def admission():
        with proxy.mutation_guard('admit'): reserved.append('would reserve')
    thread, failures = async_call(admission)
    try:
        assert entered.wait(1)
        # This is the real lock needed by close_admission and proxy finalization.
        assert proxy.state.acquire(timeout=.2)
        proxy.state.release()
        started = time.monotonic(); proxy.close_admission()
        assert time.monotonic()-started < .2
        proxy.frozen = True
        assert not reserved
    finally:
        release.set(); thread.join(2)
    assert not thread.is_alive() and len(failures) == 1
    assert isinstance(failures[0], BudgetStop) and not reserved


def test_selected_waiting_for_observer_lock_is_cancelled_without_waiting_125_seconds(tmp_path):
    history, proxy = history_proxy(tmp_path)
    held, release = threading.Event(), threading.Event()
    def observe():
        with history.lock:
            held.set(); assert release.wait(3)
    observer, errors = async_call(observe)
    assert held.wait(1)
    waiter, failures = async_call(proxy.preflight_open)
    try:
        proxy.close_admission(); waiter.join(.5)
        assert not waiter.is_alive() and len(failures) == 1
        assert isinstance(failures[0], BudgetStop)
    finally:
        release.set(); observer.join(2); waiter.join(2)
    assert not errors


def test_selected_guard_holds_verified_history_through_short_mutation(tmp_path):
    history, proxy = history_proxy(tmp_path)
    acquired = []
    def observer():
        ok = history.lock.acquire(timeout=.04)
        acquired.append(ok)
        if ok: history.lock.release()
    with proxy.mutation_guard('admit'):
        worker = threading.Thread(target=observer); worker.start(); worker.join(.5)
        assert acquired == [False]
    assert history.lock.acquire(timeout=.1)
    history.lock.release()


def test_preflight_rechecks_history_without_proxy_lock_and_selected_require_open_is_short(tmp_path):
    history, proxy = history_proxy(tmp_path)
    calls = []
    history.verify_admission = lambda: calls.append(proxy.state._is_owned())
    proxy.preflight_open()
    with proxy.state: proxy.require_open()
    assert calls == [False]


def test_legacy_proxy_keeps_original_verification_order_and_wait(tmp_path):
    history, proxy = history_proxy(tmp_path, selected=False)
    calls = []
    history.verify_admission = lambda: calls.append(proxy.state._is_owned())
    proxy.preflight_open()
    with proxy.mutation_guard('admit'): pass
    assert calls == [True, True]
    assert history.result_wait_seconds == 2
    selected, _ = history_proxy(tmp_path)
    assert selected.result_wait_seconds == 125


@pytest.mark.parametrize('snapshot,expected', [
    ({'control_shutdown_complete': True, 'unfinished_control_workers': 0}, (True, 0)),
    ({'control_shutdown_complete': False, 'unfinished_control_workers': 1}, (False, 1)),
    ({'control_shutdown_complete': True, 'unfinished_control_workers': False}, (False, None)),
    ({'control_shutdown_complete': True, 'unfinished_control_workers': 1}, (False, None)),
])
def test_shutdown_snapshot_preserves_unfinished_or_rejects_malformed_workers(snapshot, expected):
    proxy = SimpleNamespace(frozen=True, unfinished_handlers=0, control_shutdown={'control_initialized': True, **snapshot})
    out = native.shutdown_evidence(proxy)
    assert (out['control_shutdown_complete'], out['unfinished_control_workers']) == expected
    assert out['proxy_shutdown_complete'] is True


def test_legacy_shutdown_shape_is_exact():
    assert native.shutdown_evidence(SimpleNamespace(frozen=True, unfinished_handlers=0)) == {
        'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}
    assert native.shutdown_evidence(None) == {
        'proxy_initialized': False, 'proxy_shutdown_complete': False, 'unfinished_handlers': None}


@pytest.mark.parametrize('bad', [{}, {'control_shutdown_complete': False, 'unfinished_control_workers': 1},
    {'control_shutdown_complete': True, 'unfinished_control_workers': False},
    {'control_shutdown_complete': True, 'unfinished_control_workers': 1},
    {'control_shutdown_complete': 1, 'unfinished_control_workers': 0}])
def test_selected_child_cannot_claim_closed_with_missing_or_invalid_worker_state(batch, bad):
    batch.m['native_history_control'] = deepcopy(SELECTOR)
    with pytest.raises(BudgetStop, match='control worker'):
        batch_runtime._require_control_closed(batch.m, bad)
    # Worker children remain exact v2 even in the selected registration.
    batch_runtime._require_control_closed(batch.m, {}, child_id='worker_001')


@pytest.mark.parametrize('closed', [True, False])
def test_stopped_snapshot_cannot_freeze_unfinished_control_despite_closed_proxy(batch, closed):
    batch.m['native_history_control'] = deepcopy(SELECTOR)
    batch.reg.write_text(json.dumps(batch.m)); batch.identity = native.sha(batch.reg)
    row = next(r for r in batch.m['audit_batches']['children'] if r['id'] == 'integration')
    root = Path(row['attempt_dir']); root.mkdir(parents=True)
    runtime = {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0,
        'control_initialized': True, 'control_shutdown_complete': closed, 'unfinished_control_workers': 0 if closed else 1}
    (root/'stopped.json').write_text(json.dumps({'child_id': row['id'], 'registration_sha256': batch.identity,
        'status': 'stopped', 'runtime': runtime}))
    children, aggregate = batch_runtime.stopped_runtime_snapshot(batch.m)
    result = {'batch_runtime_children': children, 'runtime': aggregate}
    assert aggregate['control_shutdown_complete'] is closed
    if closed: assert batch_runtime.require_closed_batch_runtime(batch.m, result)
    else:
        with pytest.raises(BudgetStop, match='control worker'):
            batch_runtime.require_closed_batch_runtime(batch.m, result)


def test_successful_aggregate_cannot_omit_selected_control_metadata(batch):
    batch.m['native_history_control'] = deepcopy(SELECTOR)
    batch.reg.write_text(json.dumps(batch.m)); batch.identity = native.sha(batch.reg)
    with pytest.raises(BudgetStop, match='control worker'):
        batch_runtime.verify_aggregate_closure(batch.m, batch.reg, {
            'registration_sha256': batch.identity, 'job_id': batch.m['job']['id'], 'runtime': {}})


@pytest.mark.parametrize('primary', [True, False])
def test_execute_child_preserves_primary_and_captures_frozen_worker_snapshot(tmp_path, monkeypatch, primary):
    instruction = tmp_path/'instruction'; instruction.write_text('synthetic')
    channel = SimpleNamespace(contract=deepcopy(HISTORY_CONTRACT),
        control_shutdown_complete=False, unfinished_control_workers=1)
    calls = []
    def close():
        calls.append('control_close')
        raise BudgetStop('native control worker remains active; closure incomplete')
    channel.close = close
    channel.retain_pipe_tail = lambda path: calls.append('retain')
    channel.start = lambda *args: None
    channel.finish = lambda: None
    channel.stdout_closed = True
    monkeypatch.setattr(runner, 'NativeControl', lambda *a, **k: channel)
    monkeypatch.setattr(runner, 'terminate_group', lambda process: calls.append('terminate'))
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *a, **k: SimpleNamespace(poll=lambda: 0, returncode=0))
    stop = []
    proxy = SimpleNamespace(failed=threading.Event(), close_admission=lambda: calls.append('close_admission'))
    def verify():
        if primary: raise BudgetStop('original primary stop')
    with pytest.raises(BudgetStop, match='original primary stop' if primary else 'worker remains active'):
        runner.execute_child(['synthetic', '--input-format', 'stream-json'], proxy=proxy, instruction=instruction,
            attempt=tmp_path, cwd=tmp_path, env={}, deadline_seconds=2, verify_launch=verify,
            command_policy={'pretool_control': deepcopy(HISTORY_CONTRACT)}, record_stop=stop.append)
    assert calls[-3:] == ['terminate', 'retain', 'control_close']
    assert proxy.control_shutdown == {'control_initialized': True, 'control_shutdown_complete': False, 'unfinished_control_workers': 1}
    if primary: assert stop == ['original primary stop']


def test_execute_child_real_blocked_observer_stays_unclosed_and_cli_is_reaped(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    instruction = tmp_path/'instruction'; instruction.write_text('synthetic')
    channel = []
    constructor = native_control.NativeControl
    def capture(*a, **k):
        value = constructor(*a, **k); channel.append(value); return value
    monkeypatch.setattr(runner, 'NativeControl', capture)
    def observe(event):
        entered.set(); assert release.wait(4)
    child = r'''import json,sys,time
init=json.loads(sys.stdin.readline())
print(json.dumps({'type':'control_response','response':{'subtype':'success','request_id':init['request_id'],'response':{}}}),flush=True)
time.sleep(5)
'''
    proxy = SimpleNamespace(failed=threading.Event(), failure=None, close_admission=lambda: None)
    try:
        with pytest.raises(BudgetStop, match='deadline elapsed'):
            runner.execute_child([sys.executable, '-c', child, '--input-format', 'stream-json'], proxy=proxy,
                instruction=instruction, attempt=tmp_path, cwd=tmp_path, env={}, deadline_seconds=.2,
                verify_launch=lambda: None, command_policy={'pretool_control': deepcopy(HISTORY_CONTRACT)},
                event_observer=observe)
        assert entered.is_set()
        assert proxy.control_shutdown == {'control_initialized': True, 'control_shutdown_complete': False, 'unfinished_control_workers': 1}
        assert channel[0].process.poll() is not None
    finally:
        release.set()
        # Never leave an invented non-daemon observer alive after this test.
        for thread in threading.enumerate():
            if thread is not threading.current_thread() and not thread.daemon:
                thread.join(2)
    # Snapshot remains immutable even after the worker finally exits.
    assert channel[0].unfinished_control_workers == 1


@pytest.mark.parametrize('integration', [False, True])
def test_known_not_started_control_closes_without_claiming_success(batch, integration):
    batch.m['native_history_control'] = deepcopy(SELECTOR)
    batch.reg.write_text(json.dumps(batch.m)); batch.identity = native.sha(batch.reg)
    row = (next(r for r in batch.m['audit_batches']['children'] if r['id'] == 'integration')
           if integration else batch.m['audit_batches']['children'][0])
    root = Path(row['attempt_dir']); root.mkdir(parents=True)
    state = {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}
    if integration:
        state.update(control_initialized=False, control_shutdown_complete=True, unfinished_control_workers=0)
    (root/'stopped.json').write_text(json.dumps({'child_id': row['id'], 'registration_sha256': batch.identity,
        'status': 'stopped', 'runtime': state}))
    children, aggregate = batch_runtime.stopped_runtime_snapshot(batch.m)
    assert aggregate['control_initialized'] is False
    assert aggregate['control_shutdown_complete'] is True and aggregate['unfinished_control_workers'] == 0
    assert batch_runtime.require_closed_batch_runtime(batch.m, {'batch_runtime_children': children, 'runtime': aggregate})
    with pytest.raises(BudgetStop, match='control worker'):
        batch_runtime._require_control_closed(batch.m, aggregate)


def test_existing_unknown_integration_cannot_be_treated_as_not_started(batch):
    batch.m['native_history_control'] = deepcopy(SELECTOR)
    batch.reg.write_text(json.dumps(batch.m)); batch.identity = native.sha(batch.reg)
    row = next(r for r in batch.m['audit_batches']['children'] if r['id'] == 'integration')
    Path(row['attempt_dir']).mkdir(parents=True)
    children, aggregate = batch_runtime.stopped_runtime_snapshot(batch.m)
    assert aggregate['control_initialized'] is None
    assert aggregate['control_shutdown_complete'] is False and aggregate['unfinished_control_workers'] is None
    with pytest.raises(BudgetStop):
        batch_runtime.require_closed_batch_runtime(batch.m, {'batch_runtime_children': children, 'runtime': aggregate})


def test_real_child_receipt_requires_selected_control_state_before_replay(batch):
    batch.m['native_history_control'] = deepcopy(SELECTOR)
    batch.reg.write_text(json.dumps(batch.m)); batch.identity = native.sha(batch.reg)
    row = next(r for r in batch.m['audit_batches']['children'] if r['id'] == 'integration')
    root = Path(row['attempt_dir']); root.mkdir(parents=True)
    from budgeted_cborg import attempt_identity
    receipt = {'child_id': row['id'], 'registration_sha256': batch.identity,
        'job_id': batch.m['job']['id'], 'billing_attempt': attempt_identity(batch.identity, batch.m['job']['id']),
        'status': 'completed_proposal', 'runtime': {'exit_code': 0, 'proxy_initialized': True,
            'proxy_shutdown_complete': True, 'unfinished_handlers': 0}}
    (root/'closed.json').write_text(json.dumps(receipt))
    with pytest.raises(BudgetStop, match='control worker'):
        batch_runtime.verify_child_closure(batch.m, batch.identity, row['id'])


def test_stop_record_and_close_never_wait_for_history_held_by_admission(tmp_path):
    history, proxy = history_proxy(tmp_path)
    entered, release = threading.Event(), threading.Event()
    def verification():
        with history.admission_lock(): entered.set(); assert release.wait(3)
    history.verify_admission = verification
    def admit():
        with proxy.mutation_guard('admit'): pytest.fail('reservation after stop')
    thread, failures = async_call(admit)
    records = []
    try:
        assert entered.wait(1)
        started = time.monotonic()
        runner.record_then_close(proxy, records.append, 'synthetic deadline')
        assert time.monotonic()-started < .2 and records == ['synthetic deadline']
        assert proxy.admission_closed.is_set()
    finally:
        release.set(); thread.join(2)
    assert len(failures) == 1 and isinstance(failures[0], BudgetStop)


def test_selected_constructor_failure_records_known_not_initialized(tmp_path, monkeypatch):
    instruction = tmp_path/'instruction'; instruction.write_text('synthetic')
    def reject(*a, **k): raise BudgetStop('synthetic constructor refusal')
    monkeypatch.setattr(runner, 'NativeControl', reject)
    proxy = SimpleNamespace(close_admission=lambda: None)
    with pytest.raises(BudgetStop, match='constructor refusal'):
        runner.execute_child(['synthetic', '--input-format', 'stream-json'], proxy=proxy,
            instruction=instruction, attempt=tmp_path, cwd=tmp_path, env={}, deadline_seconds=1,
            verify_launch=lambda: pytest.fail('constructor failure reached launch'),
            command_policy={'pretool_control': deepcopy(HISTORY_CONTRACT)})
    assert proxy.control_shutdown == {'control_initialized': False,
        'control_shutdown_complete': True, 'unfinished_control_workers': 0}
