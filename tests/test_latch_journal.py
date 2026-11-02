"""D41 causal local-integrity checks, #5138/#5142, 2026-10-26; no provider calls."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import latch_journal as journal, snapshot_store, usage_ledger as ledger
from tests.test_download.test_api_runner import spec


def start(tmp_path):
    selected = spec(out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=False)
    return selected


def disk_edit(selected, mutate):
    path = ledger.ledger_path(selected)
    data = json.loads(path.read_bytes())
    mutate(data)
    path.write_text(json.dumps(data))


def raw_events(selected):
    return [json.loads(line) for line in journal.journal_path(selected).read_text().splitlines()]


def latch_event(selected, prefix):
    return next(event for event in reversed(raw_events(selected))
                if event['kind'] == 'latch' and event['payload']['key'].startswith(prefix))


def acknowledge(selected, hashes):
    data = ledger._read(selected)
    value = {'format': journal.OVERRIDE_FORMAT, 'identity': ledger.run_identity(selected),
             'generation_id': data['generation_id'], 'event_sha256s': hashes,
             'authorization': 'Owner accepts this exact discrepancy as assisted evidence only.',
             'authorized_by': 'offline-test-owner', 'authorized_at': '2026-10-26T12:00:00-07:00'}
    journal.override_path(selected).write_text(json.dumps(value))
    return value


def delivered(selected, tmp_path):
    path = tmp_path / 'response.json'
    path.write_text('{"response":"original"}\n')
    snapshot_store.record(selected, 'response.json', path, usage_id='call-1')
    return path


def test_saved_response_is_bound_to_usage_name_path_index_and_actual_bytes(tmp_path):
    selected = start(tmp_path)
    path = delivered(selected, tmp_path)
    metadata = journal.check(selected)
    assert journal.eligibility_problem(metadata) is None
    pin = ledger._read(selected)['latch_snapshots'][0]
    assert pin == {'name': 'response.json', 'path': str(path), 'usage_id': 'call-1',
                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'index_path': str(snapshot_store.index_path(selected.metadata_dir, selected.project))}
    assert latch_event(selected, 'snapshot:')['payload']['value'] == pin
    assert metadata['journal']['sha256'] == hashlib.sha256(journal.journal_path(selected).read_bytes()).hexdigest()


def transcript_pin(selected, tmp_path, call):
    path = tmp_path / f'exchange-{call}.json'
    path.write_text(json.dumps({'usage_id': call, 'response': call}))
    snapshot_store.record(selected, f'{selected.project}_receipt_completion_transcript.json',
                          path, usage_id=call)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def test_transcript_selector_advances_without_rewriting_prior_exchanges(tmp_path):
    selected = start(tmp_path)
    first = transcript_pin(selected, tmp_path, 'full')
    data = ledger._read(selected)
    data['receipt_completion_transcript'] = first
    ledger._write(selected, data)
    second = transcript_pin(selected, tmp_path, 'readdress')
    data = ledger._read(selected)
    data['receipt_completion_transcript'] = second
    ledger._write(selected, data)
    assert journal.check(selected)['verified'] is True
    selectors = [event['payload']['value'] for event in raw_events(selected)
                 if event['kind'] == 'latch'
                 and event['payload']['key'] == 'controller:receipt_completion_transcript']
    assert selectors == [first, second]
    assert len(ledger._read(selected)['latch_snapshots']) == 2
    disk_edit(selected, lambda current: current.update(receipt_completion_transcript=first))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


@pytest.mark.parametrize('boundary', ['receipt_completion', 'receipt_completion_full'])
@pytest.mark.parametrize('side', ['previous', 'proposed'])
def test_transcript_selector_cannot_move_past_a_seal_or_intent(tmp_path, boundary, side):
    selected = start(tmp_path)
    first = transcript_pin(selected, tmp_path, 'full')
    data = ledger._read(selected)
    data['receipt_completion_transcript'] = first
    ledger._write(selected, data)
    second = transcript_pin(selected, tmp_path, 'readdress')
    data = ledger._read(selected)
    data[boundary] = {'state': 'prepared', 'transcript': first}
    if side == 'previous':
        ledger._write(selected, data)
        data = ledger._read(selected)
    data['receipt_completion_transcript'] = second
    before = ledger.ledger_path(selected).read_bytes(), journal.journal_path(selected).read_bytes()
    with pytest.raises(ledger.UsageLedgerError, match='cannot change after the full seal or completion intent'):
        ledger._write(selected, data)
    assert before == (ledger.ledger_path(selected).read_bytes(), journal.journal_path(selected).read_bytes())


@pytest.mark.parametrize('kind', ['missing', 'same-write', 'wrong-name'])
def test_transcript_selector_requires_a_previously_journaled_exchange(tmp_path, kind):
    selected = start(tmp_path)
    path = tmp_path / 'untrusted-exchange.json'
    path.write_text('{}')
    pin = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if kind == 'wrong-name':
        snapshot_store.record(selected, 'other-response.json', path, usage_id='other')
    data = ledger._read(selected)
    data['receipt_completion_transcript'] = pin
    if kind == 'same-write':
        data['latch_snapshots'] = [{**pin, 'usage_id': 'new',
            'name': f'{selected.project}_receipt_completion_transcript.json',
            'index_path': str(snapshot_store.index_path(selected.metadata_dir, selected.project))}]
    with pytest.raises(ledger.UsageLedgerError, match='requires a previously journaled exchange'):
        ledger._write(selected, data)


def test_removing_full_seal_cannot_restore_a_consumed_boundary(tmp_path):
    selected = start(tmp_path)
    data = ledger._read(selected)
    data['receipt_completion_full'] = {'full_sha256': 'a' * 64, 'usage_id': 'full'}
    ledger._write(selected, data)
    event = latch_event(selected, 'allowance:receipt_completion_full')
    disk_edit(selected, lambda account: account.pop('receipt_completion_full'))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)
    acknowledge(selected, [event['sha256']])
    with pytest.raises(ledger.UsageLedgerError, match='control-state discrepancy cannot authorize a call'):
        journal.check(selected)


@pytest.mark.parametrize('damage', ['bytes', 'index', 'ledger-pin', 'all-three', 'delete-file'])
def test_saved_response_rewriting_is_refused_even_if_mutable_pins_agree(tmp_path, damage):
    selected = start(tmp_path)
    path = delivered(selected, tmp_path)
    changed = b'{"response":"rewritten"}\n'
    digest = hashlib.sha256(changed).hexdigest()
    if damage in {'bytes', 'all-three'}:
        path.write_bytes(changed)
    if damage == 'delete-file':
        path.unlink()
    if damage in {'index', 'all-three'}:
        index_path = snapshot_store.index_path(selected.metadata_dir, selected.project)
        index = json.loads(index_path.read_bytes())
        index['snapshots'][0]['sha256'] = digest
        index_path.write_text(json.dumps(index))
    if damage in {'ledger-pin', 'all-three'}:
        disk_edit(selected, lambda data: data['latch_snapshots'][0].update(sha256=digest))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


@pytest.mark.parametrize('controller', ['typed_audit', 'receipt_completion'])
@pytest.mark.parametrize('damage', ['state', 'failure-type', 'delete', 'stage-admission'])
def test_inherited_failure_cannot_be_edited_back_to_live(tmp_path, controller, damage):
    selected = start(tmp_path)
    data = ledger._read(selected)
    data[controller] = {'state': 'failed', 'failure_type': 'ValueError',
                        'stages': [{'state': 'admitted', 'usage_id': 'spent-call'}]}
    ledger._write(selected, data)

    def mutate(account):
        if damage == 'state':
            account[controller]['state'] = 'running'
        elif damage == 'failure-type':
            account[controller].pop('failure_type')
        elif damage == 'delete':
            account.pop(controller)
        else:
            account[controller]['stages'][0] = {'state': 'prepared'}
    disk_edit(selected, mutate)
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)
    # A normal writer cannot bless an already edited on-disk account.
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        ledger.persist_usage(selected, {'usage_id': 'another', 'phase': 'full'})


def test_terminal_override_is_refused_without_recording_assistance(tmp_path):
    selected = start(tmp_path)
    data = ledger._read(selected)
    data['typed_audit'] = {'state': 'failed', 'failure_type': 'ValueError'}
    ledger._write(selected, data)
    affected_events = [latch_event(selected, prefix) for prefix in (
        'controller:typed_audit', 'terminal:field:["typed_audit","state"]',
        'terminal:typed_audit')]
    disk_edit(selected, lambda account: account['typed_audit'].update(state='running'))
    acknowledge(selected, [event['sha256'] for event in affected_events])
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    with pytest.raises(ledger.UsageLedgerError, match='historical terminal failure'):
        journal.check(selected)
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())
    assert ledger._read(selected)['latch_overrides'] == []
    assert ledger._read(selected)['typed_audit']['state'] == 'running'


def test_pending_admission_can_be_accepted_only_by_a_validated_writer(tmp_path):
    selected = start(tmp_path)
    row = {'usage_id': 'call-1', 'source_review_admission': {'state': 'pending', 'response_sha256': 'a' * 64}}
    ledger.persist_usage(selected, row)
    changed = copy.deepcopy(row)
    changed['source_review_admission']['state'] = 'accepted'
    ledger.persist_usage(selected, changed)
    journal.check(selected)
    disk_edit(selected, lambda data: data['rows'][0]['source_review_admission'].update(response_sha256='b' * 64))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


def test_manual_pending_to_accepted_cannot_bypass_source_review(tmp_path):
    selected = start(tmp_path)
    ledger.persist_usage(selected, {'usage_id': 'call-1', 'source_review_admission':
                                   {'state': 'pending', 'response_sha256': 'a' * 64}})
    disk_edit(selected, lambda data: data['rows'][0]['source_review_admission'].update(state='accepted'))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


def test_deleted_evidence_refusal_remains_terminal(tmp_path):
    selected = start(tmp_path)
    ledger.record_evidence_refusal(selected, 'report', {'findings': ['unsupported claim']})
    disk_edit(selected, lambda data: data.pop('evidence_refusal'))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


def test_report_rejections_are_nonterminal_and_preserve_one_regate_allowance(tmp_path):
    selected = start(tmp_path)
    ledger.record_report_rejection(selected, 'report', 'a' * 64, {'findings': ['first']})
    journal.check(selected)
    assert not ledger.report_regate_attempted(selected)
    identifier = ledger.begin_call(selected, 'report_regate', 1, '2026-10-26T12:00:00Z')
    ledger.cancel_call(selected, identifier)
    ledger.record_report_rejection(selected, 'report_regate', 'b' * 64, {'findings': ['second']})
    journal.check(selected)
    assert len(ledger._read(selected)['report_rejections']) == 2
    with pytest.raises(ledger.UsageLedgerError, match='already attempted'):
        ledger.begin_call(selected, 'report_regate', 2, '2026-10-26T12:00:01Z')
    disk_edit(selected, lambda data: data['report_rejections'].pop(0))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


@pytest.mark.parametrize('damage', ['delete', 'truncate', 'payload', 'checkpoint', 'ledger-delete', 'duplicate-key'])
def test_chain_and_checkpoint_corruption_refuse_continuation(tmp_path, damage):
    selected = start(tmp_path)
    ledger.record_report_rejection(selected, 'report', 'a' * 64, {'findings': ['first']})
    path = journal.journal_path(selected)
    if damage == 'delete':
        path.unlink()
    elif damage == 'truncate':
        path.write_bytes(path.read_bytes().splitlines(keepends=True)[0])
    elif damage == 'payload':
        path.write_bytes(path.read_bytes().replace(b'"findings"', b'"renamed"'))
    elif damage == 'duplicate-key':
        path.write_bytes(path.read_bytes().replace(b'"version":1', b'"version":1,"version":1', 1))
    elif damage == 'ledger-delete':
        ledger.ledger_path(selected).unlink()
    else:
        disk_edit(selected, lambda data: data.pop('latch_journal'))
    with pytest.raises(ledger.UsageLedgerError):
        journal.check(selected)


def test_exact_override_is_durable_and_does_not_cover_a_later_mutation(tmp_path):
    selected = start(tmp_path)
    ledger.record_report_rejection(selected, 'report', 'a' * 64, {'findings': ['first']})
    event = latch_event(selected, 'report:')
    disk_edit(selected, lambda data: data['report_rejections'][0].update(reason='edited reason'))
    acknowledgement = acknowledge(selected, [event['sha256']])
    metadata = journal.check(selected)
    assert metadata['verified'] is True
    assert metadata['assisted'] is metadata['evidence_only'] is True
    assert metadata['overrides'][0]['acknowledgement'] == acknowledgement
    journal.override_path(selected).unlink()
    assert journal.provenance(selected)['overrides'] == metadata['overrides']
    assert journal.check(selected)['assisted'] is True
    # A still-permitted ordinary call may proceed; no extra regate allowance is granted.
    identifier = ledger.begin_call(selected, 'report_regate', 1, '2026-10-26T12:00:00Z')
    ledger.cancel_call(selected, identifier)
    assert ledger.report_regate_attempted(selected)
    disk_edit(selected, lambda data: data['report_rejections'][0].update(reason='another edit'))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


def test_existing_override_file_cannot_acknowledge_new_bytes_of_same_event(tmp_path):
    selected = start(tmp_path)
    path = delivered(selected, tmp_path)
    event = latch_event(selected, 'snapshot:')
    path.write_text('edit A')
    acknowledge(selected, [event['sha256']])
    assert journal.check(selected)['assisted'] is True
    before = journal.journal_path(selected).read_bytes()
    path.write_text('edit B')
    with pytest.raises(ledger.UsageLedgerError, match='already-applied override'):
        journal.check(selected)
    assert journal.journal_path(selected).read_bytes() == before


@pytest.mark.parametrize('damage', ['wrong-line', 'extra-line', 'wrong-generation', 'no-timezone', 'empty-owner'])
def test_override_is_exact_and_attributable(tmp_path, damage):
    selected = start(tmp_path)
    ledger.record_report_rejection(selected, 'report', 'a' * 64, {})
    event = latch_event(selected, 'report:')
    disk_edit(selected, lambda data: data['report_rejections'][0].update(reason='edited'))
    value = acknowledge(selected, [event['sha256']])
    if damage == 'wrong-line':
        value['event_sha256s'] = ['f' * 64]
    elif damage == 'extra-line':
        value['event_sha256s'].append('f' * 64)
    elif damage == 'wrong-generation':
        value['generation_id'] = 'different'
    elif damage == 'no-timezone':
        value['authorized_at'] = '2026-10-26T12:00:00'
    else:
        value['authorized_by'] = ' '
    journal.override_path(selected).write_text(json.dumps(value))
    with pytest.raises(ledger.UsageLedgerError, match='invalid explicit override'):
        journal.check(selected)


def test_legacy_account_requires_explicit_unverifiable_baseline(tmp_path):
    selected = spec(out_dir=tmp_path)
    data = ledger._empty(selected, accept_legacy=True)
    data['rows'] = [{'usage_id': 'already-spent', 'phase': 'full'}]
    ledger._write_unlatched(selected, data)
    old = ledger.ledger_path(selected).read_bytes()
    with pytest.raises(ledger.UsageLedgerError, match='inspection only'):
        journal.check(selected)
    digest = journal.provenance(selected)['binding_sha256']
    assert not journal.journal_path(selected).exists()
    assert ledger.ledger_path(selected).read_bytes() == old
    acknowledge(selected, [digest])
    metadata = journal.provenance(selected)
    assert metadata['verified'] is False
    assert metadata['assisted'] is metadata['evidence_only'] is True
    assert ledger._read(selected)['rows'] == data['rows']
    with pytest.raises(ledger.UsageLedgerError, match='inspection only'):
        journal.check(selected)
    assert ledger.ledger_path(selected).read_bytes() == old
    assert not journal.journal_path(selected).exists()


def test_legacy_binding_and_override_are_stable_without_git(tmp_path, monkeypatch):
    import yaml
    from tests.test_d68_legacy_readonly import tree
    selected = spec(out_dir=tmp_path)
    ledger._write_unlatched(selected, ledger._empty(selected, accept_legacy=True))
    selected.provenance_path.write_text(yaml.safe_dump({
        "run": ledger.run_identity(selected),
        "repo": {"commit": "f8c5ac73caba610d40c49aaceddb31ead3590a72"}}))
    initial = journal.provenance(selected)
    assert initial["record_age"] == "pre-D41"
    assert set(initial["legacy_unverifiable"]) == {"ledger_sha256", "reason"}
    acknowledge(selected, [initial["binding_sha256"]])
    with_git = journal.provenance(selected)
    before = tree(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "no-git-binary"))
    without_git = journal.provenance(selected)
    assert without_git["record_age"] == "age unestablished"
    assert without_git["binding_sha256"] == with_git["binding_sha256"] == initial["binding_sha256"]
    assert without_git["legacy_unverifiable"] == with_git["legacy_unverifiable"]
    assert without_git["overrides"] == with_git["overrides"]
    assert without_git["assisted"] and without_git["evidence_only"]
    assert tree(tmp_path) == before


def test_journal_separates_flat_identities_and_retains_explicit_generation_history(tmp_path):
    selected = start(tmp_path)
    generation = ledger.generation_id(selected)
    other = replace(selected, label='other_rep1')
    ledger.prepare_usage(other, resume=False)
    journal.check(selected)
    journal.check(other)
    ledger.prepare_usage(selected, resume=False)
    assert generation in ledger.prior_generation_ids(selected)
    assert len([event for event in raw_events(selected) if event['kind'] == 'generation']) == 3
    journal.check(selected)
    journal.check(other)


def test_snapshot_index_write_crash_keeps_delivery_latched_and_refuses_restart(tmp_path, monkeypatch):
    selected = start(tmp_path)
    snapshot_store.finish_activation(selected)
    path = tmp_path / 'response.json'
    path.write_text('{"response":"delivered"}')
    before = snapshot_store.index_path(selected.metadata_dir, selected.project).read_bytes()

    def fail(*args):
        raise OSError('synthetic index write failure')
    monkeypatch.setattr(snapshot_store, '_write', fail)
    with pytest.raises(OSError, match='synthetic index write failure'):
        snapshot_store.record(selected, 'response.json', path, usage_id='spent-call')
    assert ledger._read(selected)['latch_snapshots'][0]['usage_id'] == 'spent-call'
    assert snapshot_store.index_path(selected.metadata_dir, selected.project).read_bytes() == before
    assert path.exists()
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


def test_recovery_roster_includes_journal_and_dangling_override_sidecar(tmp_path):
    selected = start(tmp_path)
    journal.override_path(selected).symlink_to(tmp_path / 'missing-override')
    found = ledger.recovery_files(selected.metadata_dir, selected.project)
    assert journal.journal_path(selected) in found
    assert journal.override_path(selected) in found


@pytest.mark.parametrize('field,value', [('verified', 1), ('verified', False), ('assisted', True),
    ('assisted', 0), ('evidence_only', True), ('evidence_only', 0), ('overrides', None),
    ('authentication', 'authenticated')])
def test_eligibility_requires_strict_clean_metadata(tmp_path, field, value):
    selected = start(tmp_path)
    block = journal.provenance(selected)
    assert journal.eligibility_problem(block) is None
    block[field] = value
    assert journal.eligibility_problem(block)


@pytest.mark.parametrize('field,value', [('path', ''), ('sha256', 'invalid'), ('head_sha256', None),
    ('line_count', True), ('line_count', 0)])
def test_eligibility_requires_complete_journal_pins(tmp_path, field, value):
    selected = start(tmp_path)
    block = journal.provenance(selected)
    block['journal'][field] = value
    assert journal.eligibility_problem(block)


@pytest.mark.parametrize('shape', ['scalar', 'nested', 'list-nested'])
def test_every_controller_failure_type_is_latched_without_freezing_siblings(tmp_path, shape):
    selected = start(tmp_path)
    data = ledger._read(selected)
    if shape == 'scalar':
        data['failure_type'] = 'ValueError'
        def erase(account):
            account.pop('failure_type')
    elif shape == 'nested':
        data['controller_extra'] = {'diagnostic': {'failure_type': 'ValueError'}, 'counter': 1}
        def erase(account):
            account['controller_extra']['diagnostic'].pop('failure_type')
    else:
        data['controller_extra'] = {'diagnostics': [{'failure_type': 'ValueError'}], 'counter': 1}
        def erase(account):
            account['controller_extra']['diagnostics'][0].pop('failure_type')
    ledger._write(selected, data)
    if shape != 'scalar':
        data = ledger._read(selected)
        data['controller_extra']['counter'] = 2
        ledger._write(selected, data)  # unrelated observations may still be recorded
    disk_edit(selected, erase)
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)


@pytest.mark.parametrize('damage', ['false', 'deleted'])
def test_spent_transport_regate_allowance_cannot_be_refunded(tmp_path, damage):
    selected = start(tmp_path)
    identifier = ledger.begin_call(selected, 'report_regate', 1, '2026-10-26T12:00:00Z')
    ledger.cancel_call(selected, identifier)
    if damage == 'false':
        disk_edit(selected, lambda data: data.update(report_regate_attempted=False))
    else:
        disk_edit(selected, lambda data: data.pop('report_regate_attempted'))
    with pytest.raises(ledger.UsageLedgerError, match='unacknowledged discrepancy'):
        journal.check(selected)
    event = latch_event(selected, 'allowance:report_regate_attempted')
    acknowledge(selected, [event['sha256']])
    with pytest.raises(ledger.UsageLedgerError, match='cannot authorize a call or refund'):
        journal.check(selected)
    with pytest.raises(ledger.UsageLedgerError, match='cannot authorize a call or refund'):
        ledger.begin_call(selected, 'report_regate', 2, '2026-10-26T12:00:01Z')
    assert ledger._read(selected)['latch_overrides'] == []


def test_pending_call_cannot_be_erased_then_blessed_by_an_ordinary_write(tmp_path):
    selected = start(tmp_path)
    identifier = ledger.begin_call(selected, 'full', 1, '2026-10-26T12:00:00Z')
    event = latch_event(selected, 'intent:pending_call')
    disk_edit(selected, lambda data: data.pop('pending_call'))
    acknowledge(selected, [event['sha256']])
    with pytest.raises(ledger.UsageLedgerError, match='cannot authorize a call'):
        journal.check(selected)
    # D56 refuses the ineffective override, including ordinary ledger writes.
    with pytest.raises(ledger.UsageLedgerError, match='cannot authorize a call'):
        ledger.persist_usage(selected, {'usage_id': 'independent-evidence', 'phase': 'diagnostic'})
    assert ledger._read(selected)['latch_overrides'] == []
    assert latch_event(selected, 'intent:pending_call')['payload']['value']['usage_id'] == identifier
    with pytest.raises(ledger.UsageLedgerError, match='cannot authorize a call'):
        journal.check(selected)


def test_prepared_controller_cannot_replace_unresolved_admitted_state(tmp_path):
    selected = start(tmp_path)
    data = ledger._read(selected)
    data['typed_audit'] = {'state': 'running', 'stages': [{'state': 'admitted', 'usage_id': 'spent'}]}
    ledger._write(selected, data)
    disk_edit(selected, lambda account: account['typed_audit']['stages'][0].update(state='prepared'))
    event = latch_event(selected, 'controller:typed_audit')
    acknowledge(selected, [event['sha256']])
    with pytest.raises(ledger.UsageLedgerError, match='cannot authorize a call'):
        journal.check(selected)


@pytest.mark.parametrize('artifact', ['provenance', 'progress', 'snapshot-index', 'unowned-output'])
def test_missing_ledger_legacy_history_never_becomes_a_clean_resume(tmp_path, artifact):
    import yaml
    selected = spec(out_dir=tmp_path)
    identity = ledger.run_identity(selected)
    if artifact == 'provenance':
        selected.provenance_path.parent.mkdir(parents=True, exist_ok=True)
        selected.provenance_path.write_text(yaml.safe_dump({'run': identity, 'api_usage': [{'phase': 'full'}]}))
    elif artifact == 'progress':
        selected.metadata_dir.mkdir(parents=True, exist_ok=True)
        (selected.metadata_dir / f'{selected.project}_api_progress.json').write_text(
            json.dumps({'label': selected.label, 'completed': ['full']}))
    elif artifact == 'snapshot-index':
        path = snapshot_store.index_path(selected.metadata_dir, selected.project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'run_identity': identity, 'generation_id': 'old', 'snapshots': []}))
    else:
        selected.full_path.parent.mkdir(parents=True, exist_ok=True)
        selected.full_path.write_text('id: prior-output\n')
    with pytest.raises(ledger.UsageLedgerError, match='historical evidence cannot become a clean resume'):
        journal.check(selected)
    with pytest.raises(ledger.UsageLedgerError, match='inspection only|relaunch with a new label|cannot become a clean resume'):
        ledger.prepare_usage(selected, resume=True)
    assert not journal.journal_path(selected).exists()
    # D68/D69: a fresh generation needs a new label, never this residue.
    with pytest.raises(ledger.UsageLedgerError, match='inspection only|relaunch with a new label|cannot become a clean resume'):
        journal.check(selected, spending=False)
    with pytest.raises(ledger.UsageLedgerError, match='inspection only'):
        ledger.prepare_usage(selected, resume=False)
    assert not journal.journal_path(selected).exists()


def test_foreign_flat_label_provenance_does_not_masquerade_as_current_history(tmp_path):
    import yaml
    selected = spec(out_dir=tmp_path)
    foreign = replace(selected, label='old_rep1')
    selected.provenance_path.parent.mkdir(parents=True, exist_ok=True)
    selected.provenance_path.write_text(yaml.safe_dump({'run': ledger.run_identity(foreign)}))
    selected.full_path.write_text('id: foreign-output\n')
    # D68: a different label cannot overwrite an unguarded evidence directory.
    with pytest.raises(ledger.UsageLedgerError, match='inspection only|relaunch with a new label|cannot become a clean resume'):
        journal.check(selected)
    with pytest.raises(ledger.UsageLedgerError, match='inspection only|relaunch with a new label|cannot become a clean resume'):
        ledger.prepare_usage(selected, resume=True)
    assert not journal.journal_path(selected).exists()


def test_discrepancy_error_names_key_expected_and_found_without_large_payload(tmp_path):
    selected = start(tmp_path)
    ledger.persist_usage(selected, {'usage_id': 'call', 'source_review_admission':
                                   {'state': 'pending', 'response_sha256': 'a' * 64}})
    disk_edit(selected, lambda data: data['rows'][0]['source_review_admission'].update(state='accepted'))
    with pytest.raises(ledger.UsageLedgerError) as caught:
        journal.check(selected)
    message = str(caught.value)
    assert 'admission:call' in message
    assert '"expected":{"response_sha256"' in message and '"found":{"response_sha256"' in message
    assert '"state":"pending"' in message and '"state":"accepted"' in message
