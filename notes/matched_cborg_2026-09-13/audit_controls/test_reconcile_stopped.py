"""A stopped audit's one pending charge, settled under the standing authorization (#2467)."""
import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from budgeted_cborg import BudgetStop
from audit_controls import batch_native
from audit_controls import registration as r
from audit_controls import reconcile_stopped as tool
from audit_controls.test_registration import accounting, save  # noqa: F401  (fixture)

REQUEST = b'{"synthetic": "stalled request"}\n'


@pytest.fixture
def stopped(accounting):
    """A generation checkpoint, then one audit stopped on an unconfirmed charge, still the tip."""
    m, _, _, _, reg = accounting
    first = copy.deepcopy(m)
    first.update(kind='d4d_native_audit_continuation', repository=str(reg.parent), repository_commit='a' * 40)
    first['job']['attempt_dir'] = str(reg.parent / 'attempts' / first['job']['id'])
    save(reg, first)
    source_sha = r.sha(reg)
    with r.sequence_guard(first, source_sha):
        ledger = r.open_audit_ledger(first, reg, source_sha)
        attempt = r.attempt_identity(source_sha, first['job']['id'])
        settled = ledger.reserve(attempt, Decimal('1'), '1' * 64)
        ledger.settle(settled, Decimal('0.25'), response_sha256='synthetic', usage={})
        request_id = ledger.reserve(attempt, Decimal('2.4535'), hashlib.sha256(REQUEST).hexdigest())
        ledger.stop_attempt(attempt, 'upstream HTTP response did not confirm a completed charge')
    folder = Path(first['job']['attempt_dir']) / 'children' / 'worker_0001' / 'requests' / request_id
    folder.mkdir(parents=True)
    (folder / 'request.json').write_bytes(REQUEST)
    save(folder / 'admission.json', {'reserved_usd': '2.4535'})
    save(folder / 'http_status.json', {'status': 500, 'correlation_headers': {}})
    save(Path(first['job']['attempt_dir']) / 'result.json', {
        'registration_sha256': source_sha, 'job_id': first['job']['id'], 'scope': 'phase3_audit_only',
        'status': 'stopped', 'unresolved_requests': [request_id],
        'runtime': {'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0}})
    return m, first, reg, request_id, folder


def reconcile(reg, out, **kwargs):
    return tool.reconcile(reg, out, recorded_at='2026-09-25T19:00:00+00:00', **kwargs)


def successor_of(m, reg, first, value):
    successor = copy.deepcopy(m)
    folder = reg.parent.parent / 'next'
    folder.mkdir()
    ledger, result = Path(first['budget']['ledger_path']), Path(first['job']['attempt_dir']) / 'result.json'
    successor['budget']['ledger_path'] = str(folder / 'billing.json')
    successor['budget']['continuation'] = {'checkpoint': value['checkpoint'], 'sha256': value['checkpoint_sha256'],
        'cost_usd': value['cost_usd'], 'reconciliation': {'source_registration': str(reg),
        'source_ledger': str(ledger), 'receipt': value['receipt'], 'result': str(result)}}
    for path in (reg, ledger, result, value['receipt'], value['checkpoint']):
        successor['pinned_files'][str(path)] = r.sha(path)
    return successor, folder / 'registration.json'


def test_the_stopped_charge_is_settled_once_in_a_checkpoint_the_successor_accepts(stopped):
    m, first, reg, request_id, folder = stopped
    ledger = Path(first['budget']['ledger_path'])
    result = Path(first['job']['attempt_dir']) / 'result.json'
    before = {p: p.read_bytes() for p in (reg, ledger, result)}
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    assert before == {p: p.read_bytes() for p in before}
    receipt = json.loads(Path(value['receipt']).read_text())
    assert receipt['accounting_observation'] == {'file': 'http_status.json',
                                                 'sha256': r.sha(folder / 'http_status.json')}
    authority = receipt['user_authorization']
    assert authority['standing'] is True and authority['exact_response'] == '3- approved'
    assert authority['source_record'] == {'path': str(tool.STANDING_AUTHORIZATION),
                                          'sha256': tool.STANDING_AUTHORIZATION_SHA256}
    state = json.loads(Path(value['checkpoint']).read_text())
    row = next(x for x in state['requests'] if x['id'] == request_id)
    assert (row['status'], row['cost_usd'], row['provider_charge_confirmed']) == ('settled', '2.4535', False)
    marker = json.loads(Path(value['marker']).read_text())
    assert marker['checkpoint_sha256'] == value['checkpoint_sha256'] and marker['request_id'] == request_id
    assert not list(reg.parent.parent.glob('.reconciliation-*'))
    successor, path = successor_of(m, reg, first, value)
    assert r.validate_audit_reconciliation(successor) == state
    save(path, successor)
    with r.sequence_guard(successor, r.sha(path)):
        imported = r.read_json(r.open_audit_ledger(successor, path, r.sha(path)).path)
    assert imported['requests'] == state['requests']
    # One reconciliation per stopped audit, whatever directory a second run names.
    with pytest.raises(BudgetStop):
        reconcile(reg, reg.parent.parent / 'second')
    assert not (reg.parent.parent / 'second').exists()


def test_a_stop_a_successor_has_continued_from_is_not_reconciled_again(stopped):
    m, first, reg, request_id, folder = stopped
    state = Path(first['sequence_state'])
    value = json.loads(state.read_text())
    value['registration_sha256'] = 'f' * 64
    state.write_text(json.dumps(value))
    with pytest.raises(BudgetStop, match='no longer the sequence tip'):
        reconcile(reg, reg.parent.parent / 'reconciliation')


def test_the_sequence_lock_serialises_reconciliation(stopped):
    m, first, reg, request_id, folder = stopped
    with r.SequenceLock(first['sequence_state'] + '.lock').acquire(timeout=0):
        with pytest.raises(BudgetStop, match='sequence lock is held'):
            reconcile(reg, reg.parent.parent / 'reconciliation')


@pytest.mark.parametrize('damage', ['two_pending', 'no_pending', 'unresolved_mismatch', 'no_evidence',
                                    'other_request', 'symlinked_folder', 'inside_tree', 'kind', 'existing_out'])
def test_nothing_is_published_for_a_stop_the_standing_debit_does_not_cover(stopped, damage):
    m, first, reg, request_id, folder = stopped
    ledger = Path(first['budget']['ledger_path'])
    state = json.loads(ledger.read_text())
    result = Path(first['job']['attempt_dir']) / 'result.json'
    out = reg.parent.parent / 'reconciliation'
    if damage == 'two_pending':
        state['requests'][-2]['status'] = 'pending'; ledger.write_text(json.dumps(state))
    elif damage == 'no_pending':
        state['requests'][-1].update(status='settled', cost_usd='2.4535'); ledger.write_text(json.dumps(state))
    elif damage == 'unresolved_mismatch':
        value = json.loads(result.read_text()); value['unresolved_requests'] = ['another']
        result.write_text(json.dumps(value))
    elif damage == 'no_evidence':
        for name in ('admission.json', 'http_status.json'):
            (folder / name).unlink()
    elif damage == 'other_request':
        (folder / 'request.json').write_bytes(b'{"another": "request"}\n')
    elif damage == 'symlinked_folder':
        moved = folder.parent / 'elsewhere'
        folder.rename(moved)
        os.symlink(moved, folder)
    elif damage == 'inside_tree':
        out = reg.parent / 'reconciliation'
    elif damage == 'kind':
        value = json.loads(reg.read_text()); value['kind'] = 'd4d_native_transport_probe_v1'
        reg.write_text(json.dumps(value))
    else:
        out.mkdir()
    with pytest.raises(BudgetStop, match={'kind': 'only a native audit', 'existing_out': 'already exists',
                                          'inside_tree': "stopped audit's tree"}.get(damage, '')):
        reconcile(reg, out)
    assert damage == 'existing_out' or not out.exists()
    assert not list(out.parent.glob('.reconciliation-*'))
    assert not list((Path(first['sequence_state']).parent / tool.MARKERS).glob('*.json'))


def test_a_changed_authorization_record_is_refused(stopped, tmp_path, monkeypatch):
    m, first, reg, request_id, folder = stopped
    copied = tmp_path / 'authorization.json'
    copied.write_text(tool.STANDING_AUTHORIZATION.read_text().replace('3- approved', 'approved'))
    monkeypatch.setattr(tool, 'STANDING_AUTHORIZATION', copied)
    with pytest.raises(BudgetStop, match='standing authorization'):
        reconcile(reg, reg.parent.parent / 'reconciliation')
    monkeypatch.undo()
    assert json.loads(tool.STANDING_AUTHORIZATION.read_text())['exact_response'] == '3- approved'
    assert r.sha(tool.STANDING_AUTHORIZATION) == tool.STANDING_AUTHORIZATION_SHA256


def test_a_validator_refusal_leaves_nothing_behind_and_a_corrected_stop_reconciles(stopped):
    m, first, reg, request_id, folder = stopped
    result = Path(first['job']['attempt_dir']) / 'result.json'
    original = result.read_text()
    value = json.loads(original); value['runtime']['proxy_shutdown_complete'] = False
    result.write_text(json.dumps(value))
    out = reg.parent.parent / 'reconciliation'
    with pytest.raises(BudgetStop, match='closed runtime'):
        reconcile(reg, out)
    assert not out.exists() and not list(out.parent.glob('.reconciliation-*'))
    assert not list((Path(first['sequence_state']).parent / tool.MARKERS).glob('*.json'))
    result.write_text(original)
    assert reconcile(reg, out)['request_id'] == request_id


def test_a_batch_audit_pins_the_source_and_its_closure_for_the_validator(stopped, monkeypatch):
    m, first, reg, request_id, folder = stopped
    closure = reg.parent / 'attempts' / 'closure.json'
    save(closure, {'closed': True})
    pinned_input = reg.parent / 'pinned_input.txt'
    pinned_input.write_text('synthetic pinned input\n')
    value = json.loads(reg.read_text())
    value['audit_batches'] = {'synthetic': True}
    value['pinned_files'] = {str(pinned_input): r.sha(pinned_input)}
    reg.write_text(json.dumps(value))
    # The state and ledger name the registration by hash; rebind them to the batch form.
    for path in (Path(first['sequence_state']), Path(first['budget']['ledger_path'])):
        data = json.loads(path.read_text())
        key = 'registration_sha256' if path.name == 'audit_sequence.json' else 'manifest_sha256'
        old = data[key]; data[key] = r.sha(reg)
        text = json.dumps(data).replace(old, r.sha(reg))
        path.write_text(text)
    result = Path(first['job']['attempt_dir']) / 'result.json'
    data = json.loads(result.read_text()); data['registration_sha256'] = r.sha(reg); result.write_text(json.dumps(data))
    seen = []
    def closed(source, result):
        seen.append(source['audit_batches'])
        return {closure}
    monkeypatch.setattr(batch_native, 'require_closed_batch_runtime', closed)
    assert reconcile(reg, reg.parent.parent / 'reconciliation')['request_id'] == request_id
    assert seen == [{'synthetic': True}, {'synthetic': True}]       # the tool's pins and the validator's check



# --- the second review (#2491) ------------------------------------------------------------------

def test_a_second_run_while_the_audit_is_still_the_tip_is_refused_by_its_marker(stopped):
    m, first, reg, request_id, folder = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    with pytest.raises(BudgetStop, match='already reconciled; its checkpoint is in'):
        reconcile(reg, reg.parent.parent / 'second')
    assert not (reg.parent.parent / 'second').exists()
    Path(value['marker']).unlink()                    # without it, the same stop would reconcile again
    reconcile(reg, reg.parent.parent / 'third')


def test_an_output_made_meanwhile_is_refused_without_a_marker(stopped, monkeypatch):
    m, first, reg, request_id, folder = stopped
    out = reg.parent.parent / 'reconciliation'
    real = tool.verify
    def racing(*args):
        real(*args)
        out.mkdir()
    monkeypatch.setattr(tool, 'verify', racing)
    with pytest.raises(FileExistsError):
        reconcile(reg, out)
    monkeypatch.undo()
    assert not (Path(first['sequence_state']).parent / tool.MARKERS / f'{r.sha(reg)}.json').exists()
    assert not list(out.parent.glob('.reconciliation-*'))
    out.rmdir()
    assert reconcile(reg, out)['request_id'] == request_id


def test_an_interrupt_after_the_marker_is_reported_as_unpublished(stopped, monkeypatch):
    m, first, reg, request_id, folder = stopped
    out = reg.parent.parent / 'reconciliation'
    monkeypatch.setattr(tool.os, 'link', lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        reconcile(reg, out)
    monkeypatch.undo()
    with pytest.raises(BudgetStop, match='recorded but not published'):
        reconcile(reg, reg.parent.parent / 'again')


def test_a_marker_directory_that_is_not_a_directory_refuses_before_staging(stopped):
    m, first, reg, request_id, folder = stopped
    blocker = Path(first['sequence_state']).parent / tool.MARKERS
    blocker.write_text('not a directory')
    out = reg.parent.parent / 'reconciliation'
    with pytest.raises((BudgetStop, FileExistsError)):
        reconcile(reg, out)
    assert not out.exists() and not list(out.parent.glob('.reconciliation-*'))


def test_the_output_is_not_written_beside_the_sequence_state(stopped):
    m, first, reg, request_id, folder = stopped
    with pytest.raises(BudgetStop, match="sequence state's directory"):
        reconcile(reg, Path(first['sequence_state']).parent / 'reconciliation')


def test_a_symlinked_observation_is_refused_not_skipped(stopped, tmp_path):
    m, first, reg, request_id, folder = stopped
    moved = tmp_path / 'http_status.json'
    (folder / 'http_status.json').rename(moved)
    os.symlink(moved, folder / 'http_status.json')
    with pytest.raises(BudgetStop, match='not a regular file'):
        reconcile(reg, reg.parent.parent / 'reconciliation')


# --- the final review (#2499) --------------------------------------------------------------------

def test_a_marker_that_cannot_be_written_leaves_nothing_and_a_rerun_reconciles(stopped, monkeypatch):
    m, first, reg, request_id, folder = stopped
    out = reg.parent.parent / 'reconciliation'
    real = tool.os.fsync
    calls = []
    def failing(descriptor):
        calls.append(descriptor)
        if len(calls) == 3:                   # receipt, checkpoint, then the marker
            raise OSError('disk full')
        return real(descriptor)
    monkeypatch.setattr(tool.os, 'fsync', failing)
    with pytest.raises(OSError):
        reconcile(reg, out)
    monkeypatch.undo()
    assert not out.exists() and not list(out.parent.glob('.reconciliation-*'))
    assert not list((Path(first['sequence_state']).parent / tool.MARKERS).glob('*'))
    assert reconcile(reg, out)['request_id'] == request_id


def test_an_unwritable_markers_directory_refuses_before_staging(stopped):
    m, first, reg, request_id, folder = stopped
    markers = Path(first['sequence_state']).parent / tool.MARKERS
    markers.mkdir()
    markers.chmod(0o500)
    try:
        with pytest.raises(BudgetStop, match='not a writable directory'):
            reconcile(reg, reg.parent.parent / 'reconciliation')
    finally:
        markers.chmod(0o700)
    assert not list(reg.parent.parent.glob('.reconciliation-*'))


def test_a_rerun_into_the_same_directory_reports_the_earlier_reconciliation(stopped):
    m, first, reg, request_id, folder = stopped
    out = reg.parent.parent / 'reconciliation'
    reconcile(reg, out)
    with pytest.raises(BudgetStop, match='already reconciled; its checkpoint is in'):
        reconcile(reg, out)


def test_an_observation_that_is_not_a_regular_file_is_refused(stopped):
    m, first, reg, request_id, folder = stopped
    (folder / 'http_status.json').unlink()
    (folder / 'http_status.json').mkdir()
    with pytest.raises(BudgetStop, match='not a regular file'):
        reconcile(reg, reg.parent.parent / 'reconciliation')


# --- applied automatically at stop when the registration selects it (#2467) ------------------

def out_of(reg):
    return tool.default_output_dir(reg.parent)


def selected(first, reg):
    value = copy.deepcopy(first)
    value[tool.SELECTION_KEY] = tool.selection(out_of(reg))
    return value


def test_the_selected_debit_is_applied_at_stop_in_the_form_the_successor_accepts(stopped):
    m, first, reg, request_id, _ = stopped
    from audit_controls.native import after_stop
    stop = r.BudgetStop('upstream HTTP response did not confirm a completed charge')
    outcome = after_stop(stop, reg, selected(first, reg))
    assert outcome['status'] == 'reconciled' and stop.automatic_stop_reconciliation == outcome
    assert Path(outcome['checkpoint']).parent == out_of(reg)
    assert outcome['request_id'] == request_id and outcome['budget_debit_usd'] == '2.4535'
    successor, path = successor_of(m, reg, first, outcome)
    assert r.validate_audit_reconciliation(successor) == r.read_json(outcome['checkpoint'])


def test_without_the_selection_or_after_an_interrupt_nothing_is_applied(stopped):
    _, first, reg, _, _ = stopped
    from audit_controls.native import after_stop
    assert after_stop(r.BudgetStop('stopped'), reg, first) is None
    assert after_stop(KeyboardInterrupt(), reg, selected(first, reg)) is None
    assert not out_of(reg).exists()


def test_a_stop_the_debit_does_not_cover_is_reported_and_left_alone(stopped):
    _, first, reg, _, _ = stopped
    result = Path(first['job']['attempt_dir']) / 'result.json'
    value = r.read_json(result)
    save(result, {**value, 'unresolved_requests': []})
    assert tool.reconcile_at_stop(reg, selected(first, reg))['status'] == 'not_applicable'
    result.unlink()
    assert tool.reconcile_at_stop(reg, selected(first, reg)) == {
        'status': 'not_applicable', 'reason': 'the audit wrote no result'}


def test_a_refusal_is_returned_not_raised_and_publishes_nothing(stopped):
    _, first, reg, _, _ = stopped
    state = Path(first['sequence_state'])
    save(state, {**r.read_json(state), 'registration_sha256': '0' * 64})       # a successor took the tip
    outcome = tool.reconcile_at_stop(reg, selected(first, reg))
    assert outcome['status'] == 'refused' and 'no longer the sequence tip' in outcome['reason']
    assert not out_of(reg).exists()


@pytest.mark.parametrize('change', [
    lambda v: v.update(kind='another'), lambda v: v['authorization'].update(sha256='0' * 64),
    lambda v: v['authorization'].update(path='/elsewhere.json'), lambda v: v.update(extra=True)],
    ids=['kind', 'hash', 'path', 'extra'])
def test_the_selection_must_name_the_pinned_authorization_exactly(stopped, change):
    _, first, reg, _, _ = stopped
    manifest = selected(first, reg)
    change(manifest[tool.SELECTION_KEY])
    with pytest.raises(BudgetStop, match='pinned standing authorization'):
        r.automatic_stop_reconciliation(manifest)
    assert tool.reconcile_at_stop(reg, manifest)['status'] == 'refused'


def test_the_selection_is_audit_only_and_pinned(stopped):
    _, first, reg, _, _ = stopped
    manifest = selected(first, reg)
    assert r.automatic_stop_reconciliation(manifest) == tool.selection(out_of(reg))
    assert r.automatic_stop_reconciliation(first) is None
    with pytest.raises(BudgetStop, match='audit-only'):
        r.automatic_stop_reconciliation({**manifest, 'kind': 'd4d_native_generation'})



@pytest.mark.parametrize('where', ['audit_tree', 'state_dir', 'relative'])
def test_an_output_the_stop_could_not_write_is_refused_at_registration(stopped, where):
    """#2529: refused when registered, not discovered at stop."""
    _, first, reg, _, _ = stopped
    manifest = selected(first, reg)
    manifest[tool.SELECTION_KEY]['output_dir'] = {
        'audit_tree': str(reg.parent / 'inside'), 'relative': 'elsewhere',
        'state_dir': str(Path(first['sequence_state']).parent / 'inside')}[where]
    with pytest.raises(BudgetStop, match='output'):
        r.automatic_stop_reconciliation(manifest)
    assert tool.reconcile_at_stop(reg, manifest)['status'] == 'refused'



def _case_variant(path):
    path = Path(path)
    variant = path.with_name(path.name.swapcase())
    if variant == path or not variant.exists():
        pytest.skip('the filesystem is case-sensitive; no case variant names the same directory')
    return variant


@pytest.mark.parametrize('root', ['audit_tree', 'state_dir'])
def test_a_case_variant_of_a_protected_directory_is_refused(stopped, root):
    """#2536: on a case-insensitive filesystem a differently cased path is the same directory."""
    _, first, reg, _, _ = stopped
    protected = reg.parent if root == 'audit_tree' else Path(first['sequence_state']).parent
    out = _case_variant(protected) / 'inside'
    manifest = selected(first, reg)
    manifest[tool.SELECTION_KEY]['output_dir'] = str(out)
    with pytest.raises(BudgetStop, match='lies inside'):
        r.automatic_stop_reconciliation(manifest)
    with pytest.raises(BudgetStop, match='written outside'):
        tool.reconcile(reg, out)
    assert not (protected / 'inside').exists()


def test_within_compares_by_identity_through_a_symlink(tmp_path):
    root = tmp_path / 'root'; root.mkdir()
    link = tmp_path / 'link'; link.symlink_to(root)
    assert tool._within(link / 'new' / 'out', root) and tool._within(root, root)
    assert not tool._within(tmp_path / 'elsewhere' / 'out', root)


def test_a_refusal_names_the_error_it_hit(stopped):
    """#2535: the reason carries the error's own text, not only its class."""
    _, first, reg, _, _ = stopped
    manifest = selected(first, reg)
    manifest[tool.SELECTION_KEY]['output_dir'] = str(reg.parent.parent / 'not_yet' / 'out')
    outcome = tool.reconcile_at_stop(reg, manifest)
    assert outcome['status'] == 'refused' and outcome['reason'].startswith('FileNotFoundError: ')
