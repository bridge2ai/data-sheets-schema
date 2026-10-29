"""#5212 R2, 2026-10-28: refused output cannot supply a resume anchor; offline."""
import re
import traceback

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, latch_journal as journal, usage_ledger as ledger
from data_sheets_schema.cli import cli, api as command
from tests.test_latch_journal import start, raw_events
from tests.test_d42_claude_d55 import (
    Script, edit_10_22a, offline, read_ledger, rechain, run_to_10_22a,
    scripted, selected,
)  # noqa: F401 - selected and offline are fixtures; no automatic head monitor

HEX64 = re.compile(r'[0-9a-fA-F]{64}')


@pytest.mark.parametrize('damage', ['mismatch', 'missing', 'malformed', 'broken-chain'])
def test_cli_refusal_redacts_heads_in_output_exception_and_logs(tmp_path, monkeypatch, caplog, damage):
    run = start(tmp_path)
    found = raw_events(run)[-1]['sha256']
    expected = {'mismatch': 'f' * 64, 'missing': None,
                'malformed': found + 'x', 'broken-chain': found}[damage]
    if damage == 'broken-chain':
        events = raw_events(run)
        events[-1]['version'] = 2
        journal.journal_path(run).write_bytes(b''.join(journal._canonical(e) + b'\n' for e in events))
    monkeypatch.setattr(command, '_spec', lambda *a, **k: run)
    for name in ('_require_bundle', '_require_canonical_prompts', '_refuse_condition_mismatch'):
        monkeypatch.setattr(command, name, lambda *a, **k: None)
    monkeypatch.setattr(command, '_plan_or_refuse', lambda *a: {
        'approx_total_input_tokens': 0, 'model': {'name': 'offline'}})
    monkeypatch.setattr(api, '_execute', lambda *a, **k: pytest.fail('refused CLI reached execution'))
    args = ['api', 'run', '--project', run.project, '--label', run.label, '--yes']
    if expected is not None:
        args += ['--expect-journal-head-sha256', expected]
    result = CliRunner().invoke(cli, args)
    # Click 8.1 mixes stderr into stdout; newer Click also captures it separately.
    stderr = result.stderr if result.stderr_bytes is not None else ''
    output = '\n'.join((result.stdout, stderr, str(result.exception), caplog.text,
                        ''.join(traceback.format_exception(*result.exc_info))))
    assert result.exit_code != 0 and 'latch journal refused:' in output
    assert 'unverified, not a resume anchor' in output
    assert 'latch journal start:' not in output and 'latch journal stop:' not in output
    for candidate in set(HEX64.findall(output)):
        with pytest.raises(ledger.UsageLedgerError):
            api.execute(run, expect_journal_head_sha256=candidate)
    assert found not in output and not HEX64.search(output)


def test_dprime_refused_output_cannot_resume_rechained_10_22a(selected, capsys, caplog):
    """Reviewer's d′: reset terminal state, rechain latches, move checkpoint."""
    run_to_10_22a(selected)
    prior = capsys.readouterr().err
    retained = re.findall(r'latch journal stop: .* head_sha256=([0-9a-f]{64}) ', prior)[-1]
    edit_10_22a(selected)
    observed = journal._observations(read_ledger(selected))

    def relatch(events):
        kept = []
        for event in events:
            if event['kind'] == 'latch':
                key = event['payload']['key']
                if key not in observed:
                    continue
                event['payload']['value'] = observed[key]
            kept.append(event)
        return kept

    rechain(selected, relatch)
    forged = journal.head_sha256(selected)
    assert forged != retained
    capsys.readouterr()
    caplog.clear()
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    messages = Script(selected)
    with pytest.raises(ledger.UsageLedgerError, match='resume journal head') as caught:
        api.execute(selected, client=scripted(messages), expect_journal_head_sha256=retained)
    captured = capsys.readouterr()
    output = '\n'.join((captured.out, captured.err, str(caught.value), caplog.text,
                        ''.join(traceback.format_exception(caught.value))))
    assert not messages.calls and not messages.count_calls
    assert 'latch journal refused:' in output and 'latch journal stop:' not in output
    for candidate in set(HEX64.findall(output)):
        again = Script(selected)
        with pytest.raises(ledger.UsageLedgerError):
            api.execute(selected, client=scripted(again), expect_journal_head_sha256=candidate)
        assert not again.calls and not again.count_calls
    assert forged not in output and not HEX64.search(output)
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())
    # Positive control: the locally forged anchor really would unlock the run.
    # It comes from our attack setup, never from the refused invocation.
    control = Script(selected)
    result = api.execute(selected, client=scripted(control), expect_journal_head_sha256=forged)
    assert not result['validation_problems'] and len(control.calls) == 3
