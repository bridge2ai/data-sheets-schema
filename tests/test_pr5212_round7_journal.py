"""#5212 round 7: journal failures preserve owner order and redact diagnostics."""
import json
from pathlib import Path
import re

import pytest

from data_sheets_schema import api_runner as api, usage_ledger as ledger, run_lock
from tests.test_download.test_api_runner import FakeClient
from tests.test_d68_legacy_readonly import tree
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_cli import registered, roster, batch, stub_plan
from tests.test_shared_generation_selection import selected_spec
from data_sheets_schema import latch_journal as journal, output_ownership
from tests.test_download.test_api_runner import spec


def assert_no_unverified_hashes(*messages):
    """Refused diagnostics cannot supply a full, unverified resume anchor."""
    for message in messages:
        assert not re.search(r'[0-9a-fA-F]{64}', str(message)), str(message)


@pytest.mark.parametrize('damage', ['truncated', 'bad-hash'])
@pytest.mark.parametrize('resume', [True, False])
@pytest.mark.parametrize('entry', ['execute', 'batch'])
def test_journal_error_does_not_preempt_owner(registered, tmp_path, monkeypatch,
                                             capsys, damage, resume, entry):
    base, reg = registered
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, 'provider_identity', lambda: {
        'provider': None, 'base_url': None, 'key_env': None})
    monkeypatch.setattr(api.RunSpec, 'output_root', property(lambda self: tmp_path / 'root'))
    before = {}

    def plant(current):
        current.full_path.parent.mkdir(parents=True, exist_ok=True)
        current.full_path.write_text('unowned final output\n')
        current.metadata_dir.mkdir(parents=True, exist_ok=True)
        path = current.metadata_dir / f'{current.project}_latch_journal.jsonl'
        if damage == 'truncated':
            path.write_bytes(b'{')
        else:
            event = {'version': 1, 'line': 1, 'previous_sha256': None,
                     'identity': ledger.run_identity(current), 'generation_id': 'synthetic',
                     'kind': 'generation', 'payload': {}, 'sha256': 'a' * 64}
            path.write_text(json.dumps(event) + '\n')
        before.update(tree(tmp_path))

    reached, client = [], FakeClient()
    def forbidden(boundary):
        reached.append(boundary)
        pytest.fail(boundary + ' reached')
    monkeypatch.setattr(api, '_client', lambda: forbidden('client'))
    monkeypatch.setattr(api, '_exclusive_run', lambda *a: forbidden('run lock'))
    monkeypatch.setattr(run_lock, 'acquire', lambda *a, **kw: forbidden('coordination lock'))
    if entry == 'execute':
        current = selected_spec(base, reg)
        plant(current)
        with pytest.raises(Exception) as caught:
            api.execute(current, resume=resume, client=client)
        message = str(caught.value)
    else:
        path, _ = roster(base, reg, count=1)
        def plan(current):
            result = stub_plan(current)
            plant(current)
            return result
        monkeypatch.setattr(api, 'plan', plan)
        real_prelock = api._prelock_checks
        monkeypatch.setattr(api, '_prelock_checks', lambda specs, **kw:
                            real_prelock(specs, **{**kw, 'resume': resume}))
        execute = api.execute
        monkeypatch.setattr(api, 'execute', lambda current, **kw:
                            execute(current, **{**kw, 'resume': resume, 'client': client}))
        result = batch(reg, path, count=1)
        message = result.output + str(result.exception)
        assert result.exit_code != 0
    assert not reached and client.messages.calls == []
    assert tree(tmp_path) == before
    expected = 'no usable live ownership' if resume else 'already spent'
    assert expected in message, message
    assert_no_unverified_hashes(message, capsys.readouterr().err)


@pytest.mark.parametrize('reader', ['_events', '_read_events', 'head_sha256'])
@pytest.mark.parametrize('damage', ['bad-hash', 'duplicate-key', 'unreadable'])
def test_decoder_redacts_every_reader(tmp_path, monkeypatch, capsys, reader, damage):
    current = spec(project='P', out_dir=tmp_path)
    path = journal.journal_path(current)
    if damage == 'duplicate-key':
        key = 'A' * 64
        path.write_text('{"' + key + '":1,"' + key + '":2}\n')
    else:
        event = {'version': 1, 'line': 1, 'previous_sha256': None,
                 'identity': ledger.run_identity(current), 'generation_id': 'synthetic',
                 'kind': 'generation', 'payload': {}, 'sha256': 'a' * 64}
        path.write_text(json.dumps(event) + '\n')
    if damage == 'unreadable':
        original = Path.read_bytes
        def unreadable(target):
            if target == path:
                raise PermissionError('unreadable journal ' + 'b' * 64)
            return original(target)
        monkeypatch.setattr(Path, 'read_bytes', unreadable)
    before = tree(tmp_path) if damage != 'unreadable' else path.stat()
    with pytest.raises(ledger.UsageLedgerError) as caught:
        getattr(journal, reader)(path if reader == '_read_events' else current)
    assert_no_unverified_hashes(caught.value, capsys.readouterr().err)
    assert 'not a resume anchor' in str(caught.value)
    assert (tree(tmp_path) if damage != 'unreadable' else path.stat()) == before


@pytest.mark.parametrize('resume', [True, False])
def test_owner_passes_then_d69_refuses_sanitized_journal(tmp_path, capsys, resume):
    current = spec(project='P', out_dir=tmp_path)
    path = journal.journal_path(current)
    event = {'version': 1, 'line': 1, 'previous_sha256': None,
             'identity': ledger.run_identity(current), 'generation_id': 'synthetic',
             'kind': 'generation', 'payload': {}, 'sha256': 'c' * 64}
    path.write_text(json.dumps(event) + '\n')
    output_ownership.require_selected_resume_owner(current, resume=resume)
    before, client = tree(tmp_path), FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match='broken chain') as caught:
        api.execute(current, resume=resume, client=client)
    assert_no_unverified_hashes(caught.value, capsys.readouterr().err)
    assert tree(tmp_path) == before and client.messages.calls == []


@pytest.mark.parametrize('resume', [True, False])
def test_valid_pending_shared_launch_still_recovers(tmp_path, monkeypatch, resume):
    from tests.test_shared_generation_runtime import client as shared_client
    from tests.test_evidence_generation_gate import specification
    from tests.test_shared_generation_selection import registration_for
    base = specification(tmp_path)
    current = selected_spec(base, registration_for(base))
    with api._exclusive_run(current):
        journal.start_launch(current)
    retained_head = journal.head_sha256(current)
    assert not ledger.ledger_path(current).exists()
    pending = journal.pending_launch_paths(current)
    assert journal.journal_path(current) in pending
    assert all(path in pending for _, path in ledger.output_locks(
        (current.full_path, current.core_path, current.report_path, current.provenance_path)))
    output_ownership.require_selected_resume_owner(current, resume=resume)
    client = shared_client(current)
    result = api.execute(current, resume=resume, client=client,
                         expect_journal_head_sha256=retained_head)
    assert client.messages.calls and not result['validation_problems']
    assert current.full_path.read_bytes() and ledger.ledger_path(current).read_bytes()


def test_existing_accounting_rules_out_pending_without_journal_read(tmp_path, monkeypatch):
    current = spec(project='P', out_dir=tmp_path)
    ledger.ledger_path(current).write_text('{}\n')
    def forbidden(*args):
        pytest.fail('existing accounting must rule out a pending launch before decoding')
    monkeypatch.setattr(journal, '_events', forbidden)
    assert journal.pending_launch_paths(current) == set()


@pytest.mark.parametrize('resume', [True, False])
def test_valid_chain_does_not_make_embedded_refusal_values_anchors(tmp_path, capsys, resume):
    current = spec(project='P', out_dir=tmp_path)
    event = journal._event(current, {'generation_id': 'D' * 64}, [], 'generation', {})
    journal.journal_path(current).write_bytes(journal._canonical(event) + b'\n')
    before, client = tree(tmp_path), FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match='usage ledger deleted') as caught:
        api.execute(current, resume=resume, client=client)
    assert_no_unverified_hashes(caught.value, capsys.readouterr().err)
    assert client.messages.calls == [] and tree(tmp_path) == before
