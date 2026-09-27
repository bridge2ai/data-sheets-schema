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
    for path in (reg, ledger, result, value['receipt'], value['checkpoint'], value['marker']):
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



# --- a standing debit is bound by the pinned record and the tool's marker (#2492) -------------

def test_a_successor_must_pin_the_tools_marker(stopped):
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    successor, _ = successor_of(m, reg, first, value)
    assert r.validate_audit_reconciliation(successor) == r.read_json(value['checkpoint'])
    assert Path(value['marker']) in r.continuation_paths(successor)
    del successor['pinned_files'][value['marker']]
    with pytest.raises(BudgetStop, match='registered input'):
        r.validate_audit_reconciliation(successor)


@pytest.mark.parametrize('field, changed', [('checkpoint_sha256', '0' * 64), ('receipt_sha256', '0' * 64),
    ('request_id', 'another'), ('source_registration_sha256', '0' * 64), ('out', '/elsewhere')])
def test_a_marker_naming_another_reconciliation_is_refused(stopped, field, changed):
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    marker = Path(value['marker'])
    recorded = r.read_json(marker); recorded[field] = changed
    save(marker, recorded)
    successor, _ = successor_of(m, reg, first, value)            # repinned: only the content can refuse
    with pytest.raises(BudgetStop, match='marker records'):
        r.validate_audit_reconciliation(successor)


def test_the_tool_will_not_write_a_debit_against_another_record(stopped, tmp_path, monkeypatch):
    """A receipt written against another record, even with valid bytes, is refused by the tool's
    own check before anything is published (the successor's check is #2587's test)."""
    _, first, reg, _, _ = stopped
    other = tmp_path / 'other_standing_record.json'
    save(other, {'kind': tool.AUTHORIZATION_KIND,
        'exact_response': 'another answer', 'quoted_request': 'another request', 'recorded_at': '2026-09-25T00:00:00Z'})
    monkeypatch.setattr(tool, 'standing_authorization',
                        lambda: (r.read_json(other), {'path': str(other), 'sha256': r.sha(other)}))
    out = reg.parent.parent / 'reconciliation'
    with pytest.raises(BudgetStop, match='pinned standing authorization exactly'):
        reconcile(reg, out)
    assert not out.exists() and not tool.marker_path(first, r.sha(reg)).exists()


def test_a_per_charge_debit_without_standing_keeps_its_own_checks(stopped):
    """A hand-made per-charge receipt, as audit27's was, needs no marker (#2492)."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    receipt = Path(value['receipt']); body = r.read_json(receipt)
    body['user_authorization'] = {'exact_response': 'yes, debit it', 'quoted_request': 'May I debit this charge?'}
    save(receipt, body)
    checkpoint = Path(value['checkpoint']); state = r.read_json(checkpoint)
    row = next(x for x in state['requests'] if x['id'] == request_id)
    row['reconciliation_receipt_sha256'] = r.sha(receipt)
    state['reconciled_from']['receipt_sha256'] = r.sha(receipt)
    save(checkpoint, state)
    Path(value['marker']).unlink()
    value = {**value, 'checkpoint_sha256': r.sha(checkpoint)}
    successor, _ = successor_of(m, reg, first, {**value, 'marker': value['receipt']})
    assert r.validate_audit_reconciliation(successor) == state



def test_a_standing_debit_must_quote_the_pinned_record_exactly(stopped, monkeypatch):
    """The right record named with other words is refused: the quote is checked on its own."""
    m, first, reg, _, _ = stopped
    real = tool.standing_authorization
    quote, reference = real()
    monkeypatch.setattr(tool, 'standing_authorization',
                        lambda: ({**quote, 'exact_response': quote['exact_response'] + ' (edited)'}, reference))
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    monkeypatch.setattr(tool, 'standing_authorization', real)
    successor, _ = successor_of(m, reg, first, value)
    with pytest.raises(BudgetStop, match='pinned standing authorization exactly'):
        r.validate_audit_reconciliation(successor)


# --- review round 1 of #2568: #2582-#2590 -----------------------------------------------------

def reauthorize(value, request_id, change):
    """Apply `change` to the tool's receipt's user_authorization, then re-hash the checkpoint
    and the marker that name it, so only the authorization itself can refuse."""
    receipt = Path(value['receipt']); body = r.read_json(receipt)
    change(body['user_authorization'])
    save(receipt, body)
    checkpoint = Path(value['checkpoint']); state = r.read_json(checkpoint)
    next(x for x in state['requests'] if x['id'] == request_id)['reconciliation_receipt_sha256'] = r.sha(receipt)
    state['reconciled_from']['receipt_sha256'] = r.sha(receipt)
    save(checkpoint, state)
    marker = Path(value['marker']); recorded = r.read_json(marker)
    recorded.update(receipt_sha256=r.sha(receipt), checkpoint_sha256=r.sha(checkpoint))
    save(marker, recorded)
    return {**value, 'checkpoint_sha256': r.sha(checkpoint)}


def test_a_standing_debit_made_in_another_checkout_is_accepted(stopped, tmp_path, monkeypatch):
    """#2582: the reconciling checkout's copy of the record has the same bytes at another path."""
    m, first, reg, _, _ = stopped
    elsewhere = tmp_path / 'other_checkout' / 'audit_controls' / tool.STANDING_AUTHORIZATION.name
    elsewhere.parent.mkdir(parents=True)
    elsewhere.write_bytes(tool.STANDING_AUTHORIZATION.read_bytes())
    monkeypatch.setattr(tool, 'STANDING_AUTHORIZATION', elsewhere)
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    monkeypatch.undo()
    recorded = r.read_json(value['receipt'])['user_authorization']['source_record']
    assert recorded == {'path': str(elsewhere), 'sha256': tool.STANDING_AUTHORIZATION_SHA256}
    assert recorded['path'] != str(tool.STANDING_AUTHORIZATION)
    successor, _ = successor_of(m, reg, first, value)
    assert r.validate_audit_reconciliation(successor) == r.read_json(value['checkpoint'])


@pytest.mark.parametrize('record', [
    lambda ref: {**ref, 'sha256': '0' * 64},                                   # other bytes, same name
    lambda ref: {**ref, 'path': str(Path(ref['path']).with_name('other.json'))},  # same bytes, other name
    lambda ref: {**ref, 'path': Path(ref['path']).name},                         # not absolute
    lambda ref: {**ref, 'size': 1},                                               # not exactly a reference
    lambda ref: None,
], ids=['other_digest', 'other_name', 'relative', 'extra_key', 'missing'])
def test_a_standing_debit_must_name_the_pinned_record_by_digest(stopped, record):
    """#2587: the quote is the pinned record's exactly, so only the record reference can refuse."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    value = reauthorize(value, request_id, lambda a: a.update(source_record=record(a['source_record'])))
    successor, _ = successor_of(m, reg, first, value)
    with pytest.raises(BudgetStop, match='pinned standing authorization exactly'):
        r.validate_audit_reconciliation(successor)


@pytest.mark.parametrize('field', tool.QUOTE_FIELDS)
def test_every_quoted_field_of_a_standing_debit_is_compared(stopped, field):
    """#2590."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    value = reauthorize(value, request_id, lambda a: a.update({field: a[field] + ' (edited)'}))
    successor, _ = successor_of(m, reg, first, value)
    with pytest.raises(BudgetStop, match='pinned standing authorization exactly'):
        r.validate_audit_reconciliation(successor)


@pytest.mark.parametrize('standing', ['absent', 'true', 1, None, False])
def test_a_receipt_citing_the_standing_record_is_a_standing_debit_whatever_its_flag(stopped, standing):
    """#2583: citing the standing record, or carrying any `standing` key, invokes it; only
    `standing: true` with the exact record and quote and the tool's marker passes."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    value = reauthorize(value, request_id, lambda a: a.pop('standing') if standing == 'absent'
                        else a.update(standing=standing))
    successor, _ = successor_of(m, reg, first, value)
    assert Path(value['marker']) in r.continuation_paths(successor)
    with pytest.raises(BudgetStop, match='pinned standing authorization exactly'):
        r.validate_audit_reconciliation(successor)
    Path(value['marker']).unlink()
    with pytest.raises(BudgetStop, match='no reconciliation marker'):
        r.continuation_paths(successor)


def test_a_per_charge_debit_pins_no_marker(stopped):
    """#2588: audit27's per-charge receipt names its own record and has no `standing` key."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    value = reauthorize(value, request_id, lambda a: (a.pop('standing'), a.update(
        exact_response='yes, debit it', quoted_request='May I debit this charge?',
        source_record={'path': '/elsewhere/user_authorization_2026-09-24.json', 'sha256': '6' * 64})))
    marker = Path(value['marker'])
    marker.unlink()
    successor, _ = successor_of(m, reg, first, {**value, 'marker': value['receipt']})
    paths = r.continuation_paths(successor)
    assert not any(p.parent.name == tool.MARKERS for p in paths) and marker not in paths
    assert r.validate_audit_reconciliation(successor) == r.read_json(value['checkpoint'])


def test_a_standing_debits_checkpoint_must_sit_beside_its_receipt(stopped):
    """#2589: a byte-identical copy of the checkpoint in another directory is refused."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    moved = reg.parent.parent / 'moved' / 'reconciled_billing.json'
    moved.parent.mkdir()
    moved.write_bytes(Path(value['checkpoint']).read_bytes())
    successor, _ = successor_of(m, reg, first, {**value, 'checkpoint': str(moved)})
    with pytest.raises(BudgetStop, match='marker records'):
        r.validate_audit_reconciliation(successor)


def test_a_case_variant_spelling_of_the_reconciliation_directory_is_the_same_directory(stopped):
    """#2584: on a case-insensitive filesystem the marker's directory is compared by identity."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'Reconciliation')
    variant = reg.parent.parent / 'reconciliation'
    if not variant.exists():
        pytest.skip('case-sensitive filesystem: the variant spelling names no directory')
    spelled = {**value, 'receipt': str(variant / Path(value['receipt']).name),
               'checkpoint': str(variant / Path(value['checkpoint']).name)}
    successor, _ = successor_of(m, reg, first, spelled)
    assert r.validate_audit_reconciliation(successor) == r.read_json(value['checkpoint'])


def test_a_malformed_authorization_is_refused_with_a_budget_stop(stopped):
    """#2585: continuation_paths does not raise AttributeError; the validator names the defect."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    receipt = Path(value['receipt']); body = r.read_json(receipt)
    body['user_authorization'] = 'approved'
    save(receipt, body)
    checkpoint = Path(value['checkpoint']); state = r.read_json(checkpoint)
    next(x for x in state['requests'] if x['id'] == request_id)['reconciliation_receipt_sha256'] = r.sha(receipt)
    state['reconciled_from']['receipt_sha256'] = r.sha(receipt)
    save(checkpoint, state)
    successor, _ = successor_of(m, reg, first, {**value, 'checkpoint_sha256': r.sha(checkpoint)})
    r.continuation_paths(successor)
    with pytest.raises(BudgetStop, match='lacks explicit confirmation evidence'):
        r.validate_audit_reconciliation(successor)


# --- review round 2 of #2568: #2630-#2632 -----------------------------------------------------

@pytest.mark.parametrize('standing', [False, 1, 'true', None])
def test_any_standing_key_invokes_the_standing_authorization_whatever_record_it_cites(stopped, standing):
    """#2630: a `standing` key of any value makes a standing debit even when the record it cites
    is not the standing one, so it needs the marker and is refused unless it is exactly right."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    value = reauthorize(value, request_id, lambda a: a.update(
        standing=standing, source_record={'path': '/elsewhere/user_authorization.json', 'sha256': '6' * 64}))
    assert tool.claims_standing(r.read_json(value['receipt']))
    successor, _ = successor_of(m, reg, first, value)
    assert Path(value['marker']) in r.continuation_paths(successor)
    with pytest.raises(BudgetStop, match='pinned standing authorization exactly'):
        r.validate_audit_reconciliation(successor)
    Path(value['marker']).unlink()
    with pytest.raises(BudgetStop, match='no reconciliation marker'):
        r.continuation_paths(successor)


def test_a_marker_naming_another_existing_directory_is_refused(stopped):
    """#2631: the marker's `out` must be the receipt's own directory, not merely a directory."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    other = reg.parent.parent / 'another_directory'
    other.mkdir()
    marker = Path(value['marker'])
    recorded = r.read_json(marker); recorded['out'] = str(other)
    save(marker, recorded)
    successor, _ = successor_of(m, reg, first, value)
    with pytest.raises(BudgetStop, match='marker records'):
        r.validate_audit_reconciliation(successor)


def test_a_relocated_receipt_and_checkpoint_are_refused(stopped):
    """#2631: byte-identical copies of both files beside each other elsewhere keep every hash,
    but the marker records where the tool wrote them."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    moved = reg.parent.parent / 'moved'
    moved.mkdir()
    copies = {key: moved / Path(value[key]).name for key in ('receipt', 'checkpoint')}
    for key, target in copies.items():
        target.write_bytes(Path(value[key]).read_bytes())
    successor, _ = successor_of(m, reg, first, {**value, **{k: str(v) for k, v in copies.items()}})
    with pytest.raises(BudgetStop, match='marker records'):
        r.validate_audit_reconciliation(successor)


def test_the_marker_directory_is_compared_by_identity_on_any_filesystem(stopped):
    """#2631: a marker naming the reconciliation directory through an alias is the same
    directory. The case-variant test below needs a case-insensitive filesystem; a symlink
    alias is another spelling of one directory that CI's filesystem also has."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    alias = reg.parent.parent / 'alias'
    alias.symlink_to(Path(value['receipt']).parent, target_is_directory=True)
    marker = Path(value['marker'])
    recorded = r.read_json(marker); recorded['out'] = str(alias)
    save(marker, recorded)
    successor, _ = successor_of(m, reg, first, value)
    assert r.validate_audit_reconciliation(successor) == r.read_json(value['checkpoint'])


def test_the_checkpoint_directory_is_compared_by_identity_on_any_filesystem(stopped, monkeypatch):
    """#2631: the receipt and the checkpoint spelled differently name one directory. On a
    case-insensitive filesystem canonical_path accepts both spellings; this models that on any
    filesystem with a symlink alias the canonical check is told to accept."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    alias = reg.parent.parent / 'alias'
    alias.symlink_to(Path(value['receipt']).parent, target_is_directory=True)
    real = r.canonical_path

    def insensitive(path_value, *, exists=False):
        if isinstance(path_value, str) and Path(path_value).parent == alias:
            if exists and not Path(path_value).exists():
                raise BudgetStop('registered path is not absolute and canonical')
            return Path(path_value)
        return real(path_value, exists=exists)
    monkeypatch.setattr(r, 'canonical_path', insensitive)
    spelled = {**value, 'checkpoint': str(alias / Path(value['checkpoint']).name)}
    successor, _ = successor_of(m, reg, first, spelled)
    assert r.validate_audit_reconciliation(successor) == r.read_json(value['checkpoint'])


def test_mixed_case_spellings_of_the_receipt_and_checkpoint_are_one_directory(stopped):
    """#2631: on a case-insensitive filesystem the checkpoint and the receipt may be named in
    different case spellings of the tool's directory."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'Reconciliation')
    variant = reg.parent.parent / 'reconciliation'
    if not variant.exists():
        pytest.skip('case-sensitive filesystem: covered by the alias test above')
    spelled = {**value, 'receipt': str(variant / Path(value['receipt']).name)}
    successor, _ = successor_of(m, reg, first, spelled)
    assert r.validate_audit_reconciliation(successor) == r.read_json(value['checkpoint'])


@pytest.mark.parametrize('out', [None, ['x'], 'descriptor', 'nul'], ids=['null', 'list', 'int_fd', 'nul'])
def test_a_malformed_marker_directory_is_a_budget_stop(stopped, out):
    """#2632: a marker whose `out` is not a path is refused by name, not with a TypeError.
    An integer is a file descriptor to os.path.samefile, so the case uses a real one open
    on the reconciliation directory: without the string guard it would be taken for that
    directory (#2656). A NUL in the spelling is refused too, not a ValueError (#2655)."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    marker = Path(value['marker'])
    recorded = r.read_json(marker)
    descriptor = os.open(Path(value['receipt']).parent, os.O_RDONLY)
    try:
        recorded['out'] = (descriptor if out == 'descriptor' else recorded['out'] + '\x00x' if out == 'nul'
                           else out)
        save(marker, recorded)
        successor, _ = successor_of(m, reg, first, value)
        with pytest.raises(BudgetStop, match='marker records'):
            r.validate_audit_reconciliation(successor)
    finally:
        os.close(descriptor)


@pytest.mark.parametrize('body', [[], 'x', 7, None], ids=['list', 'string', 'number', 'null'])
def test_a_marker_that_is_not_an_object_is_a_budget_stop(stopped, body):
    """#2655: a hand-edited marker body is refused by name, not with an AttributeError."""
    m, first, reg, _, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    save(Path(value['marker']), body)
    successor, _ = successor_of(m, reg, first, value)
    with pytest.raises(BudgetStop, match='marker records'):
        r.validate_audit_reconciliation(successor)


def test_same_directory_compares_identity_not_resolved_spelling(tmp_path, monkeypatch):
    """#2657: on a case-insensitive filesystem resolve() keeps the spelling it is given,
    so a resolve()-based comparison would call one directory two. Resolution that keeps
    an alias's spelling models that on any filesystem, CI's included; the identity
    comparison still sees one directory."""
    target = tmp_path / 'reconciliation'; target.mkdir()
    alias = tmp_path / 'alias'; alias.symlink_to(target)
    monkeypatch.setattr(os.path, 'realpath', lambda path, *a, **k: os.fspath(path))
    monkeypatch.setattr(Path, 'resolve', lambda self, strict=False: self)
    assert tool.same_directory(str(alias), target)
    assert not tool.same_directory(str(tmp_path), target)


@pytest.mark.parametrize('path', [None, 7, ['x']], ids=['null', 'int', 'list'])
def test_a_malformed_standing_record_path_is_a_budget_stop(stopped, path):
    """#2632: a record reference whose path is not a string is refused by name."""
    m, first, reg, request_id, _ = stopped
    value = reconcile(reg, reg.parent.parent / 'reconciliation')
    value = reauthorize(value, request_id, lambda a: a['source_record'].update(path=path))
    successor, _ = successor_of(m, reg, first, value)
    with pytest.raises(BudgetStop, match='pinned standing authorization exactly'):
        r.validate_audit_reconciliation(successor)
