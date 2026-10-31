"""D55/D56/D57 regression contracts for PR #5212; offline, 2026-10-28."""
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api, latch_journal as journal, usage_ledger as ledger
from tests.test_latch_journal import acknowledge, delivered, disk_edit, raw_events, start


def test_cli_passes_expected_head_to_runner(tmp_path, monkeypatch):
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    from data_sheets_schema.cli import api as command
    selected = start(tmp_path)
    head = raw_events(selected)[-1]['sha256']
    monkeypatch.setattr(command, '_spec', lambda *a, **kw: selected)
    monkeypatch.setattr(command, '_require_bundle', lambda *a: None)
    monkeypatch.setattr(command, '_require_canonical_prompts', lambda *a: None)
    monkeypatch.setattr(command, '_refuse_condition_mismatch', lambda *a: None)
    monkeypatch.setattr(command, '_plan_or_refuse', lambda *a: {
        'approx_total_input_tokens': 0, 'model': {'name': 'offline'}})
    seen = []
    def execute(spec, **kwargs):
        seen.append(kwargs)
        raise ValueError('offline reached runner')
    monkeypatch.setattr(api, 'execute', execute)
    result = CliRunner().invoke(cli, ['api', 'run', '--project', selected.project,
        '--label', selected.label, '--yes', '--expect-journal-head-sha256', head])
    assert seen == [{'expect_journal_head_sha256': head}], result.output
    assert 'offline reached runner' in result.output


def test_batch_cli_requires_unique_launch_heads():
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    result = CliRunner().invoke(cli, ['api', 'batch', '--help'])
    assert result.exit_code == 0 and '--expect-journal-head PROJECT LABEL SHA256' in result.output
    result = CliRunner().invoke(cli, ['api', 'batch', '--label-prefix', 'offline',
        '--expect-journal-head', 'EXTERNAL', 'offline_rep1', 'a' * 64,
        '--expect-journal-head', 'EXTERNAL', 'offline_rep1', 'b' * 64, '--yes'])
    assert 'duplicate expected journal head' in result.output


@pytest.mark.parametrize('kind', ['terminal', 'allowance', 'controller', 'prefix-edited', 'foreign-suffix'])
def test_interrupted_recovery_never_blesses_control_or_nonmatching_prefix(tmp_path, monkeypatch, kind):
    selected = start(tmp_path)
    original = ledger._write_unlatched
    data = ledger._read(selected)
    if kind == 'terminal':
        data['evidence_refusal'] = {'findings': ['terminal evidence rejection']}
    elif kind == 'allowance':
        data['report_regate_attempted'] = True
    elif kind == 'controller':
        data['typed_audit'] = {'state': 'running'}
    else:
        data['pending_call'] = {'usage_id': 'intent', 'phase': 'audit', 'attempt': 1, 'started_at': 'now'}
    with monkeypatch.context() as m:
        m.setattr(ledger, '_write_unlatched', lambda *a: (_ for _ in ()).throw(KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):
            ledger._write(selected, data)
    if kind == 'prefix-edited':
        disk_edit(selected, lambda d: d.update(pending_call={'usage_id': 'different', 'phase': 'audit',
                                                           'attempt': 1, 'started_at': 'now'}))
    if kind == 'foreign-suffix':
        events = journal._events(selected)
        event = journal._event(selected, {**data, 'generation_id': 'foreign'}, events, 'latch',
                               {'key': 'intent:pending_call', 'value': None})
        journal._append(selected, events, event)
    acknowledge(selected, [raw_events(selected)[-1]['sha256']])
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    with pytest.raises(ledger.UsageLedgerError):
        journal.check(selected)
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())
    assert ledger._read(selected)['latch_overrides'] == []


@pytest.mark.parametrize('stale_fields', ['missing', 'prefix'])
def test_guard_owns_fields_across_a_stale_writer(tmp_path, stale_fields):
    selected = start(tmp_path)
    delivered(selected, tmp_path)
    stale = ledger._read(selected)
    path = tmp_path / 'second.json'
    path.write_text('second delivery')
    from data_sheets_schema import snapshot_store
    snapshot_store.record(selected, path.name, path, usage_id='second')
    expected = ledger._read(selected)
    if stale_fields == 'missing':
        for key in ('latch_snapshots', 'latch_journal', 'latch_overrides'):
            stale.pop(key, None)
    stale['diagnostic'] = 'ordinary caller mutation'
    ledger._write(selected, stale)
    actual = ledger._read(selected)
    for key in ('latch_snapshots', 'latch_journal', 'latch_overrides'):
        assert actual[key] == expected[key]
    assert actual['diagnostic'] == 'ordinary caller mutation'
    journal.check(selected)


@pytest.mark.parametrize('key', ['latch_snapshots', 'latch_journal', 'latch_overrides'])
def test_guard_owned_conflicting_value_is_refused(tmp_path, key):
    selected = start(tmp_path)
    delivered(selected, tmp_path)
    data = ledger._read(selected)
    if key == 'latch_snapshots':
        data[key][0]['sha256'] = 'f' * 64
    elif key == 'latch_journal':
        data[key]['head_sha256'] = 'f' * 64
    else:
        data[key] = [{'forged': True}]
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    with pytest.raises(ledger.UsageLedgerError, match='guard-owned'):
        ledger._write(selected, data)
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())


def test_interrupted_intent_requires_exact_acknowledgement_and_can_continue(tmp_path, monkeypatch):
    selected = start(tmp_path)
    original = ledger._write_unlatched
    def interrupt_intent(spec, data):
        if data.get('pending_call'):
            raise KeyboardInterrupt()
        return original(spec, data)
    with monkeypatch.context() as m:
        m.setattr(ledger, '_write_unlatched', interrupt_intent)
        with pytest.raises(KeyboardInterrupt):
            ledger.begin_call(selected, 'audit', 1, '2026-10-28T07:02:00Z')
    suffix = raw_events(selected)[-1]
    with pytest.raises(ledger.UsageLedgerError, match='required event_sha256s='):
        journal.check(selected)
    acknowledge(selected, [suffix['sha256']])
    # Recovery itself can also be interrupted after its durable acknowledgement.
    with monkeypatch.context() as m:
        m.setattr(ledger, '_write_unlatched', lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):
            journal.check(selected)
    assert ledger._write_unlatched is original
    assert journal.check(selected)['assisted'] is True
    assert raw_events(selected)[-1]['kind'] == 'aborted_update'
    assert ledger._read(selected).get('pending_call') is None
    identifier = ledger.begin_call(selected, 'audit', 1, '2026-10-28T07:03:00Z')
    ledger.cancel_call(selected, identifier)
    assert len([e for e in raw_events(selected) if e['kind'] == 'aborted_update']) == 1


@pytest.mark.parametrize('mutation', ['terminal', 'control', 'allowance'])
def test_ineffective_override_is_refused_without_assistance(tmp_path, mutation):
    selected = start(tmp_path)
    data = ledger._read(selected)
    if mutation == 'terminal':
        data['typed_audit'] = {'state': 'failed', 'failure_type': 'ReadTimeout'}
    elif mutation == 'control':
        data['typed_audit'] = {'state': 'running', 'stages': [{'state': 'admitted'}]}
    else:
        data['report_regate_attempted'] = True
    ledger._write(selected, data)
    disk_edit(selected, lambda d: d.pop('typed_audit' if mutation != 'allowance' else 'report_regate_attempted'))
    current = ledger._read(selected)
    mismatches = journal._mismatches(selected, current, journal._events(selected))
    acknowledge(selected, sorted({m['event_sha256'] for m in mismatches}))
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    with pytest.raises(ledger.UsageLedgerError):
        journal.check(selected)
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())
    assert ledger._read(selected)['latch_overrides'] == []


@pytest.mark.parametrize('kind', ['terminal', 'control'])
def test_pre_d56_ineffective_acknowledgement_cannot_bypass_startup(tmp_path, kind):
    selected = start(tmp_path)
    data = ledger._read(selected)
    data['typed_audit'] = ({'state': 'failed', 'failure_type': 'ReadTimeout'} if kind == 'terminal'
                           else {'state': 'running', 'stages': [{'state': 'admitted', 'usage_id': 'spent'}]})
    ledger._write(selected, data)
    if kind == 'terminal':
        disk_edit(selected, lambda d: d['typed_audit'].update(state='running'))
    else:
        disk_edit(selected, lambda d: d['typed_audit']['stages'][0].update(state='prepared'))
    data = ledger._read(selected)
    events = journal._events(selected)
    mismatches = journal._mismatches(selected, data, events)
    acknowledge(selected, sorted({m['event_sha256'] for m in mismatches}))
    payload = journal._override(selected, data, {m['event_sha256'] for m in mismatches})
    payload['discrepancies'] = mismatches
    # Reproduce A's pre-D56 behavior: it recorded this ineffective override
    # before refusing. Upgrading that history must still refuse at startup.
    event = journal._event(selected, data, events, 'override', payload)
    journal._append(selected, events, event)
    data['latch_journal'] = journal._checkpoint(selected, event)
    data['latch_overrides'] = journal._acknowledgements(events)
    ledger._write_unlatched(selected, data)
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    message = 'historical terminal failure' if kind == 'terminal' else 'control-state discrepancy'
    with pytest.raises(ledger.UsageLedgerError, match=message):
        journal.check(selected, startup=True)
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())


@pytest.mark.parametrize('damage', ['delete', 'pending', 'in_flight'])
def test_validator_refresh_cannot_be_rewound(tmp_path, damage):
    selected = start(tmp_path)
    data = ledger._read(selected)
    checkpoint = {'full_sha256': 'a' * 64}
    data['validator_repair_refresh'] = {'state': 'pending', 'checkpoint': checkpoint}
    ledger._write(selected, data)
    data['validator_repair_refresh'].update(state='in_flight', usage_id='refresh-1')
    ledger._write(selected, data)
    data['validator_repair_refresh'].update(state='accepted', report_sha256='b' * 64)
    ledger._write(selected, data)
    def mutate(d):
        if damage == 'delete':
            d.pop('validator_repair_refresh')
        else:
            d['validator_repair_refresh']['state'] = damage
    disk_edit(selected, mutate)
    with pytest.raises(ledger.UsageLedgerError):
        ledger.begin_call(selected, 'report_after_repair', 2, '2026-10-28T07:03:00Z')


def test_validator_refresh_new_checkpoint_is_allowed_but_same_one_cannot_repeat(tmp_path):
    selected = start(tmp_path)
    data = ledger._read(selected)
    data['validator_repair_refresh'] = {'state': 'accepted', 'checkpoint': {'sha256': 'a' * 64},
                                       'usage_id': 'refresh', 'report_sha256': 'b' * 64}
    ledger._write(selected, data)
    data['validator_repair_refresh'] = {'state': 'pending', 'checkpoint': {'sha256': 'a' * 64}}
    with pytest.raises(ledger.UsageLedgerError):
        ledger._write(selected, data)
    data['validator_repair_refresh']['checkpoint'] = {'sha256': 'c' * 64}
    ledger._write(selected, data)
    journal.check(selected)


@pytest.mark.parametrize('damage', ['delete', 'truncate', 'payload', 'checkpoint'])
def test_structural_refusal_names_expected_and_found(tmp_path, damage):
    selected = start(tmp_path)
    path = journal.journal_path(selected)
    if damage == 'delete':
        path.unlink()
    elif damage == 'truncate':
        path.write_bytes(path.read_bytes()[:-1])
    elif damage == 'payload':
        path.write_bytes(path.read_bytes().replace(b'"value":null', b'"value":true'))
    else:
        disk_edit(selected, lambda d: d['latch_journal'].update(head_sha256='f' * 64))
    with pytest.raises(ledger.UsageLedgerError) as caught:
        journal.check(selected)
    assert 'expected' in str(caught.value) and 'found' in str(caught.value)


@pytest.mark.parametrize('expected', [None, 'f' * 64])
def test_resume_needs_external_head_before_recovery_or_dispatch(tmp_path, monkeypatch, capsys, expected):
    selected = start(tmp_path)
    monkeypatch.setattr(api, '_execute', lambda *a, **kw: pytest.fail('recovery/dispatch reached'))
    with pytest.raises(ledger.UsageLedgerError, match='expected.*found'):
        api.execute(selected, client=SimpleNamespace(), expect_journal_head_sha256=expected)
    output = capsys.readouterr().err
    assert 'latch journal refused:' in output and 'not a resume anchor' in output
    assert 'latch journal start:' not in output and 'latch journal stop:' not in output
    head = raw_events(selected)[-1]['sha256']
    assert head not in output
    assert head[:8] + '…(unverified, not a resume anchor)' in output


def test_resume_accepts_recorded_head_and_fresh_launch_needs_none(tmp_path, monkeypatch, capsys):
    from tests.test_download.test_api_runner import spec
    selected = spec(out_dir=tmp_path)
    def accepted(run, *, resume, client):
        # Like the real executor, initialize accounting while its new locks
        # are held. A stub leaving only released locks is now refused by D69.
        ledger.prepare_usage(run, resume=resume)
        return {'accepted': True}
    monkeypatch.setattr(api, '_execute', accepted)
    assert api.execute(selected)['accepted']
    ledger.prepare_usage(selected, resume=False)
    head = raw_events(selected)[-1]['sha256']
    assert api.execute(selected, expect_journal_head_sha256=head)['accepted']
    assert capsys.readouterr().err.count('latch journal stop') == 2
