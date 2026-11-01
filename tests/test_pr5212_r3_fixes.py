"""R1/R2/R5 regression contracts, #5212, 2026-10-28; offline only."""
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, latch_journal as journal, usage_ledger as ledger
from data_sheets_schema import run_lock, shared_generation as sg
from data_sheets_schema.cli import cli
from tests.test_latch_journal import start, raw_events
from tests.test_download.test_api_runner import FakeClient, spec
from tests.test_shared_generation_cli import registered, roster, module  # noqa: F401
from tests.test_generation_manifest_identity import external  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def retain_stop(output, previous):
    """A monitor updates its external anchor only from normal stop records."""
    heads = re.findall(r'^latch journal stop: .* head_sha256=([0-9a-f]{64}) ', output, re.M)
    return heads[-1] if heads else previous


def test_refused_forgery_cannot_supply_the_next_monitored_resume_head(tmp_path, monkeypatch, capsys, caplog):
    selected = start(tmp_path)
    retained = raw_events(selected)[-1]['sha256']
    # Forge a consistent local chain and checkpoint, as the attack in R2 did.
    events = raw_events(selected)
    events[0]['payload']['counterfeit'] = 'untrusted replacement'
    previous = None
    for event in events:
        event['previous_sha256'] = previous
        event['sha256'] = journal._sha(journal._canonical({k: v for k, v in event.items() if k != 'sha256'}))
        previous = event['sha256']
    journal.journal_path(selected).write_bytes(b''.join(journal._canonical(e) + b'\n' for e in events))
    data = ledger._read(selected)
    data['latch_journal'] = journal._checkpoint(selected, events[-1])
    ledger._write_unlatched(selected, data)
    assert journal.check(selected)['verified'] and previous != retained
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    monkeypatch.setattr(api, '_execute', lambda *a, **k: pytest.fail('refused launch reached execution'))
    for _ in range(2):
        with pytest.raises(ledger.UsageLedgerError, match='resume journal head') as caught:
            api.execute(selected, expect_journal_head_sha256=retained)
        captured = capsys.readouterr()
        output = '\n'.join((captured.out, captured.err, str(caught.value), caplog.text))
        assert 'latch journal refused:' in output and 'not a resume anchor' in output
        assert previous not in output
        for candidate in set(re.findall(r'[0-9a-fA-F]{64}', output)):
            with pytest.raises(ledger.UsageLedgerError, match='resume journal head'):
                api.execute(selected, expect_journal_head_sha256=candidate)
        capsys.readouterr()
        assert 'latch journal start:' not in output and 'latch journal stop:' not in output
        assert retain_stop(output, retained) == retained
        retained = retain_stop(output, retained)
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())


def test_sigterm_requires_reconciliation_before_a_new_launch_anchor(tmp_path, monkeypatch, capsys):
    child = subprocess.Popen([sys.executable, str(ROOT / 'scripts/adhoc/pr5212_sigterm_fixture_20261028.py'),
                              str(tmp_path)], cwd=ROOT, text=True, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with selectors.DefaultSelector() as ready:
            ready.register(child.stdout, selectors.EVENT_READ)
            assert ready.select(timeout=30), 'SIGTERM fixture never reached its checkpoint'
            line = child.stdout.readline().strip()
            assert line == 'READY', child.communicate(timeout=15)[1]
        lock = run_lock.Lock(tmp_path / 'synthetic-lock', child.pid, 'r1-sigterm', [], 'offline')
        monkeypatch.setattr(run_lock, 'live', lambda: [lock])
        result = CliRunner().invoke(cli, ['api', 'stop', '--label-prefix', lock.label_prefix])
        assert result.exit_code == 0 and '(TERM)' in result.output
        _, output = child.communicate(timeout=15)
        assert child.returncode == -signal.SIGTERM
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=15)
    start_heads = re.findall(r'^latch journal start: .* head_sha256=([0-9a-f]{64}) ', output, re.M)
    assert len(start_heads) == 1  # The initial launch now binds its four locks.
    assert 'latch journal stop:' not in output
    selected = spec(out_dir=tmp_path)
    assert start_heads[0] != journal.head_sha256(selected)
    monkeypatch.setattr(api, '_execute', lambda *a, **k: pytest.fail('unanchored execution'))
    with pytest.raises(ledger.UsageLedgerError, match='required from prior launch/monitor record'):
        api.execute(selected)
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    with pytest.raises(ledger.UsageLedgerError, match='resume journal head'):
        api.execute(selected, expect_journal_head_sha256=start_heads[0])
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())
    assert retain_stop(capsys.readouterr().err, None) is None
    # Simulate the documented read-only inspection plus explicit owner approval
    # of a NEW external launch record. This is not an automatic fallback.
    before = journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes()
    reconciled = journal.check(selected, spending=False, startup=True)
    assert reconciled['verified'] and not reconciled['assisted']
    assert ledger._read(selected).get('pending_call') is None
    assert before == (journal.journal_path(selected).read_bytes(), ledger.ledger_path(selected).read_bytes())
    owner_approved_launch = {'head': reconciled['journal']['head_sha256'],
                            'authorization': 'synthetic owner-approved reconciliation'}
    monkeypatch.setattr(api, '_execute', lambda *a, **k: {'accepted': True})
    assert api.execute(selected, client=FakeClient(),
                       expect_journal_head_sha256=owner_approved_launch['head'])['accepted']
    assert retain_stop(capsys.readouterr().err, None) == owner_approved_launch['head']


@pytest.mark.parametrize('damage', [None, 'registration', 'journal'])
def test_batch_checks_registration_hash_and_journal_head_together(registered, tmp_path, monkeypatch, damage):
    base, registration = registered
    path, rows = roster(base, registration, count=1)
    selected = start(tmp_path / 'output')
    # This is a CLI boundary test: real roster hashing and real D57 admission,
    # with unrelated registration-to-RunSpec/planning behavior stubbed.
    head = raw_events(selected)[-1]['sha256']
    digest = sg.sha(Path(rows[0]['registration_path']).read_bytes())
    monkeypatch.setattr(module, '_spec', lambda *a, **k: selected)
    for name in ('_shared_current', '_require_bundle', '_require_canonical_prompts', '_refuse_condition_mismatch', '_shared_plan_line'):
        monkeypatch.setattr(module, name, lambda *a, **k: None)
    monkeypatch.setattr(module, '_plan_or_refuse', lambda *a: {})
    monkeypatch.setattr(run_lock, 'acquire', lambda *a: tmp_path / 'batch-lock')
    monkeypatch.setattr(run_lock, 'release', lambda *a: None)
    calls = []
    def execute_body(run, **kwargs):
        calls.append(run)
        raise ValueError('offline reached execution')
    monkeypatch.setattr(api, '_execute', execute_body)
    monkeypatch.setattr(api, '_client', FakeClient)
    result = CliRunner().invoke(cli, ['api', 'batch', '--projects', registration['run']['project'],
        '--label-prefix', 'shared', '--replicates', '1', '--shared-generation-version', '1',
        '--shared-generation-registration', str(path), '--no-branch-guard', '--yes',
        '--expect-sha256', 'f' * 64 if damage == 'registration' else digest,
        '--expect-journal-head', selected.project, selected.label,
        'f' * 64 if damage == 'journal' else head])
    if damage is None:
        assert calls == [selected] and 'offline reached execution' in result.output, result.output
    else:
        assert not calls, result.output
        assert ('sha256' if damage == 'registration' else 'resume journal head') in result.output, result.output
