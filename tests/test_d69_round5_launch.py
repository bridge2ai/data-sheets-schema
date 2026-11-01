"""#5212 round 5, 2026-11-01: durable startup failure and CLI advice controls."""
from dataclasses import replace
from contextlib import contextmanager
import os
from pathlib import Path

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, latch_journal as journal, usage_ledger as ledger
from data_sheets_schema import run_lock, shared_generation as sg
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient, spec
from tests.test_shared_generation_cli import registered, roster, module  # noqa: F401
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_d68_legacy_readonly import tree

pytestmark = pytest.mark.usefixtures('journal_launch_monitor')


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('failure', ['partial_append', 'fsync', 'create', 'after_acquire'])
def test_ordinary_partial_write_or_creation_recovers_under_locks(tmp_path, monkeypatch, capsys, resume, failure):
    from filelock import FileLock
    selected = spec(project='VOICE_PEDIATRIC', out_dir=tmp_path)
    original_append, original_sync, original_open = journal._append, os.fsync, os.open
    original_acquire = FileLock.acquire
    injected = []
    with monkeypatch.context() as failing:
        def partial_append(run, events, event):
            if not injected and event['kind'] == 'launch':
                injected.append(failure)
                journal.journal_path(run).write_bytes(journal._canonical(event)[:31])
                raise OSError('injected partial append')
            return original_append(run, events, event)
        def sync_once(fd):
            if not injected:
                injected.append(failure)
                raise OSError('injected fsync')
            return original_sync(fd)
        def create_once(path, flags, *args, **kwargs):
            if str(path).endswith('_api_run.lock') and flags & os.O_EXCL:
                injected.append(str(path))
                if len(injected) == 2:
                    raise OSError('injected create')
            return original_open(path, flags, *args, **kwargs)
        def acquire_then_fail(lock, *args, **kwargs):
            result = original_acquire(lock, *args, **kwargs)
            injected.append(str(lock.lock_file))
            if len(injected) == 2:
                raise OSError('injected after acquire')
            return result
        if failure == 'partial_append':
            failing.setattr(journal, '_append', partial_append)
        elif failure == 'fsync':
            failing.setattr(os, 'fsync', sync_once)
        elif failure == 'create':
            failing.setattr(os, 'open', create_once)
        else:
            failing.setattr(FileLock, 'acquire', acquire_then_fail)
        client = FakeClient()
        with pytest.raises(OSError, match='injected'):
            api.execute(selected, resume=resume, client=client)
        assert client.messages.calls == []
    head = journal.head_sha256(selected)
    assert head and head in capsys.readouterr().err
    before = tree(tmp_path)
    with pytest.raises(ledger.UsageLedgerError, match='resume journal head'):
        api.execute(selected, client=FakeClient(), expect_journal_head_sha256=None)
    assert tree(tmp_path) == before
    client = FakeClient()
    api.execute(selected, resume=resume, client=client, expect_journal_head_sha256=head)
    assert len(client.messages.calls) == 4
    client = FakeClient()
    api.execute(replace(selected, project='VOICE'), resume=resume, client=client)
    assert len(client.messages.calls) == 4


@pytest.mark.parametrize('resume', [False, True])
def test_persistent_durability_failure_never_prints_a_trusted_anchor(tmp_path, monkeypatch, capsys, resume):
    selected = spec(project='P', out_dir=tmp_path)
    def fail(fd):
        raise OSError('persistent fsync failure')
    client = FakeClient()
    with monkeypatch.context() as failing:
        failing.setattr(os, 'fsync', fail)
        with pytest.raises(OSError) as caught:
            api.execute(selected, resume=resume, client=client)
    output = capsys.readouterr().err
    assert 'latch journal stop:' not in output
    assert 'new output directory' in journal.failure_advice(selected, caught.value)
    assert '--expect-journal-head P ' not in journal.failure_advice(selected, caught.value)
    assert client.messages.calls == []
    assert list(tmp_path.glob('.*_api_run.lock'))  # Never remove coordination inodes.


@pytest.mark.parametrize('resume', [False, True])
def test_in_lock_stale_head_is_a_safety_refusal(tmp_path, monkeypatch, capsys, resume):
    selected = spec(project='P', out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=True)
    expected = journal.head_sha256(selected)
    initial_count = len(journal._events(selected))
    capsys.readouterr()
    acquire = api._exclusive_run
    @contextmanager
    def intervening_writer(run):
        # Simulate another writer between preflight and acquisition; this is
        # deliberately outside the selected invocation's physical exclusion.
        events = journal._events(run)
        event = journal._event(run, {'generation_id': 'other-launch'}, events, 'launch', {'outputs': []})
        journal._append(run, events, event)
        with acquire(run):
            yield
    monkeypatch.setattr(api, '_exclusive_run', intervening_writer)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match='resume journal head') as caught:
        api.execute(selected, resume=resume, client=client, expect_journal_head_sha256=expected)
    assert client.messages.calls == []
    output = capsys.readouterr().err
    assert 'latch journal stop:' not in output and journal.head_sha256(selected) not in output
    assert 'not a resume anchor' in output
    assert len(journal._events(selected)) == initial_count + 1  # Only the intervening writer's event.


@pytest.mark.parametrize('resume', [False, True])
def test_batch_post_lock_failure_prints_exact_resume_option(registered, tmp_path, monkeypatch, resume):
    base, registration = registered
    path, rows = roster(base, registration, count=1)
    selected = spec(project='P', out_dir=tmp_path / 'output')
    digest = sg.sha(Path(rows[0]['registration_path']).read_bytes())
    monkeypatch.setattr(module, '_spec', lambda *a, **k: selected)
    for name in ('_shared_current', '_require_bundle', '_require_canonical_prompts',
                 '_refuse_condition_mismatch', '_shared_plan_line'):
        monkeypatch.setattr(module, name, lambda *a, **k: None)
    monkeypatch.setattr(module, '_plan_or_refuse', lambda *a: {})
    monkeypatch.setattr(run_lock, 'acquire', lambda *a: tmp_path / 'batch-lock')
    monkeypatch.setattr(run_lock, 'release', lambda *a: None)
    monkeypatch.setattr(api, '_client', FakeClient)
    execute = api.execute  # batch imports this at invocation time
    monkeypatch.setattr(api, 'execute', lambda run, **kwargs: execute(run, resume=resume, **kwargs))
    def fail(*args, **kwargs):
        raise ValueError('post-lock failure')
    monkeypatch.setattr(api, '_execute', fail)
    result = CliRunner().invoke(cli, ['api', 'batch', '--projects', registration['run']['project'],
        '--label-prefix', 'shared', '--replicates', '1', '--shared-generation-version', '1',
        '--shared-generation-registration', str(path), '--no-branch-guard', '--yes',
        '--expect-sha256', digest])
    head = journal.head_sha256(selected)
    assert head and 'post-lock failure' in result.output, result.output
    assert f'--expect-journal-head {selected.project} {selected.label} {head}' in result.output
