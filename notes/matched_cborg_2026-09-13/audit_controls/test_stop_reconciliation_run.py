"""run_job applies the standing debit at stop (#2467, #2527, #2528); adapted from the #2518 review."""
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from budgeted_cborg import BudgetStop
from audit_controls import native
from audit_controls import registration as r
from audit_controls import reconcile_stopped as tool
from audit_controls.test_registration import accounting, save  # noqa: F401
from audit_controls.test_reconcile_stopped import successor_of

REQUEST = b'{"synthetic": "stalled request"}\n'


@pytest.fixture
def fresh(accounting, monkeypatch):
    """An audit registration that selected the debit, not yet run; run_job's gates stubbed except
    the real sequence_guard and open_audit_ledger."""
    m, _, _, _, reg = accounting
    first = copy.deepcopy(m)
    first.update(kind='d4d_native_audit_continuation', repository=str(reg.parent), repository_commit='a' * 40)
    first['job']['attempt_dir'] = str(reg.parent / 'attempts' / first['job']['id'])
    first['job']['output_dir'] = str(reg.parent / 'attempts' / first['job']['id'] / 'output')
    first[tool.SELECTION_KEY] = tool.selection(tool.default_output_dir(reg.parent))
    save(reg, first)
    review = reg.parent.parent / 'review.json'
    save(review, {'verdict': 'approve', 'registration_sha256': r.sha(reg), 'ci_conclusion': 'success',
                  'repository_commit': 'a' * 40, 'allowed_jobs': [first['job']['id']]})
    monkeypatch.setattr(r, 'validate_registration', lambda _: copy.deepcopy(first))
    monkeypatch.setattr(r, 'verify', lambda *_: None)
    monkeypatch.setattr(native, 'build_policy', lambda *_: None)
    monkeypatch.setattr(native, 'verify_runtime', lambda *_: None)
    return m, first, reg, review


def stopping_adapter(runtime=None, exc=None):
    """Reserve one request, leave it pending with evidence, then stop."""
    def adapter(context):
        ledger = context.ledger
        attempt = r.attempt_identity(context.manifest_sha256, context.job['id'])
        request_id = ledger.reserve(attempt, Decimal('2.4535'), hashlib.sha256(REQUEST).hexdigest())
        folder = context.attempt / 'requests' / request_id
        folder.mkdir(parents=True)
        (folder / 'request.json').write_bytes(REQUEST)
        save(folder / 'http_status.json', {'status': 500})
        error = exc or BudgetStop('upstream HTTP response did not confirm a completed charge')
        error.native_stop = {'stop_source': 'native_proxy', 'runtime': runtime or
                             {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}}
        raise error
    return adapter


def out_of(reg):
    return tool.default_output_dir(reg.parent)




def test_run_job_applies_the_debit_to_its_own_stop_after_releasing_the_lock(fresh, monkeypatch):
    m, first, reg, review = fresh
    seen = {}
    original = tool.reconcile_at_stop
    def spy(path, manifest):
        lock = r.SequenceLock(first['sequence_state'] + '.lock')
        lock.acquire(timeout=0)       # raises if run_job still held it
        lock.__exit__()
        seen['lock_free'] = True
        return original(path, manifest)
    monkeypatch.setattr(tool, 'reconcile_at_stop', spy)
    with pytest.raises(BudgetStop) as error:
        native.run_job(reg, review, adapter=stopping_adapter())
    outcome = error.value.automatic_stop_reconciliation
    assert seen == {'lock_free': True} and outcome['status'] == 'reconciled'
    successor, _ = successor_of(m, reg, first, outcome)
    assert r.validate_audit_reconciliation(successor) == r.read_json(outcome['checkpoint'])


def test_a_refused_relaunch_never_debits_an_earlier_stop(fresh):
    """#2527: an interrupted stop stays for a person, and so does any stop a relaunch finds."""
    m, first, reg, review = fresh
    with pytest.raises(KeyboardInterrupt) as error:
        native.run_job(reg, review, adapter=stopping_adapter(exc=KeyboardInterrupt()))
    assert not hasattr(error.value, 'automatic_stop_reconciliation')
    with pytest.raises(BudgetStop, match='already consumed') as second:
        native.run_job(reg, review, adapter=lambda _: pytest.fail('must not launch'))
    assert not hasattr(second.value, 'automatic_stop_reconciliation')
    assert not out_of(reg).exists()


@pytest.mark.parametrize('runtime', [
    {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 1},
    {'proxy_initialized': True, 'proxy_shutdown_complete': False, 'unfinished_handlers': None}],
    ids=['live_handler', 'not_closed'])
def test_a_runtime_that_may_still_hold_the_request_is_refused_and_publishes_nothing(fresh, runtime):
    m, first, reg, review = fresh
    with pytest.raises(BudgetStop) as error:
        native.run_job(reg, review, adapter=stopping_adapter(runtime=runtime))
    assert error.value.automatic_stop_reconciliation['status'] == 'refused'
    assert not out_of(reg).exists()


def test_the_original_stop_is_raised_unchanged_even_if_the_debit_cannot_load(fresh, monkeypatch):
    import sys
    m, first, reg, review = fresh
    original = BudgetStop('upstream HTTP response did not confirm a completed charge')
    monkeypatch.setitem(sys.modules, 'audit_controls.reconcile_stopped', None)
    with pytest.raises(BudgetStop) as error:
        native.run_job(reg, review, adapter=stopping_adapter(exc=original))
    assert error.value is original and error.value.automatic_stop_reconciliation['status'] == 'refused'
