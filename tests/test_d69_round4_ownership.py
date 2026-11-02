"""Round-4 #5212 regressions: production ownership and startup, 2026-11-01.

Reverses Codex's nine unsafe executions/two late refusals and Claude W1–W4,
W5/W7 using real writers and the externally captured launch-monitor heads.
"""
from dataclasses import replace
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api, latch_journal as journal, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient, spec
from tests.test_d68_legacy_readonly import tree
from tests.test_source_heading_runtime_api import draft_files  # noqa: F401

pytestmark = pytest.mark.usefixtures('journal_launch_monitor')


def refuses(selected, orphan, root, resume):
    before, client = tree(root), FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match='inspection only') as caught:
        api.execute(selected, resume=resume, client=client)
    assert orphan.name.casefold() in str(caught.value).casefold()
    assert client.messages.calls == []
    assert tree(root) == before


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('binding', ['input', 'hash', 'changed', 'symlink', 'phase_namespace'])
def test_foreign_reference_never_launders_residue(tmp_path, resume, binding):
    selected = spec(project='P', label='selected', out_dir=tmp_path)
    if binding == 'input':
        orphan = selected.full_path
        orphan.write_text('id: example:legacy\nname: retained legacy output\n')
        foreign = spec(project='Q', out_dir=tmp_path, bundle=orphan)
        ledger.prepare_usage(foreign, resume=True)
        assert ledger._read(foreign)['input_identity']['bundle']['path'] == str(orphan.resolve())
    elif binding == 'phase_namespace':
        foreign = replace(selected, project='P_reconcile')
        ledger.prepare_usage(foreign, resume=True)
        orphan = tmp_path / 'intermediate/P_reconcile_full.yaml'
        orphan.parent.mkdir(exist_ok=True)
        orphan.write_text('id: example:unowned-reconcile\n')
    else:
        foreign = replace(selected, project='Q' if binding == 'hash' else 'P', label='guarded')
        ledger.prepare_usage(foreign, resume=True)
        original = api._snapshot(foreign, foreign.project + '_report_context.json', 'original foreign bytes\n')
        orphan = tmp_path / 'intermediate/P_report_context.json'
        if binding == 'hash':
            orphan.write_bytes(original.read_bytes())
        elif binding == 'changed':
            orphan.write_text('unowned replacement after foreign snapshot was pinned\n')
        else:
            orphan.unlink()
            orphan.symlink_to(tmp_path / 'missing-unowned-target')
    refuses(selected, orphan, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('name', ['p_d4d.yaml', 'intermediate/p_report_context.json', '.p_unknown.tmp'])
def test_case_alias_on_real_volume_refuses(tmp_path, resume, name):
    selected = spec(project='P', out_dir=tmp_path)
    orphan = tmp_path / name
    orphan.parent.mkdir(exist_ok=True)
    orphan.write_text('unowned case alias\n')
    alias = orphan.with_name(orphan.name.upper())
    if not alias.exists():
        pytest.skip('scratch volume is case-sensitive; real filesystem alias not available')
    assert alias.samefile(orphan)
    refuses(selected, orphan, tmp_path, resume)


def test_casefold_candidates_on_every_filesystem(tmp_path):
    selected = spec(project='P', out_dir=tmp_path)
    orphan = tmp_path / '.p_unknown.tmp'
    orphan.write_text('unowned lower-case artifact\n')
    assert orphan in journal.owned_artifacts(selected)


def test_case_alias_cannot_masquerade_as_a_foreign_owner(tmp_path):
    lower = spec(project='p', out_dir=tmp_path)
    ledger.prepare_usage(lower, resume=True)
    path = api._snapshot(lower, 'P_report_context.json', 'same case-equivalent owner\n')
    selected = replace(lower, project='P')
    assert path in journal.owned_artifacts(selected)


@pytest.mark.parametrize('layout', ['flat', 'split'])
@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('sibling', [False, True])
def test_missing_key_startup_can_be_relaunched(tmp_path, monkeypatch, layout, resume, sibling):
    for key in ('ANTHROPIC_API_KEY', 'CBORG_API_KEY', 'OPENAI_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(api.RunSpec, 'output_root', property(lambda self: tmp_path / 'root'))
    kwargs = {'out_dir': tmp_path / 'outputs'} if layout == 'flat' else {}
    first = spec(project='VOICE_PEDIATRIC' if sibling else 'VOICE', **kwargs)
    before = tree(tmp_path)
    with pytest.raises(RuntimeError, match='No API key'):
        api.execute(first, client=None)
    assert tree(tmp_path) == before
    current = replace(first, project='VOICE')
    client = FakeClient()
    api.execute(current, resume=resume, client=client)
    assert len(client.messages.calls) == 4


def test_flat_label_switch_has_production_ownership(tmp_path):
    first = spec(project='P', label='first', out_dir=tmp_path)
    api.execute(first, client=FakeClient())
    for label in ('second', 'third'):
        client = FakeClient()
        api.execute(replace(first, label=label), client=client)
        assert len(client.messages.calls) == 4


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('artifact', ['full', 'report'])
def test_provenance_validation_digest_conflict_refuses(tmp_path, resume, artifact):
    first = spec(project='P', label='first', out_dir=tmp_path)
    api.execute(first, client=FakeClient())
    # A copied output bundle may omit gitignored coordination sidecars.
    for _, lock in ledger.output_locks((first.full_path, first.core_path,
                                       first.report_path, first.provenance_path)):
        lock.unlink()
    path = getattr(first, artifact + '_path')
    raw = path.read_bytes()
    path.write_bytes(b'X' + raw[1:])  # Equal length: the digest must do the work.
    refuses(replace(first, label='second'), path, tmp_path, resume)


@pytest.mark.parametrize('lock_only', [False, True])
def test_flat_refusal_remedy_and_lock_age(tmp_path, lock_only):
    selected = spec(project='P', out_dir=tmp_path)
    path = tmp_path / ('.P_d4d.yaml_api_run.lock' if lock_only else 'P_d4d.yaml')
    path.write_text('')
    with pytest.raises(ledger.UsageLedgerError) as caught:
        api.execute(selected, client=FakeClient())
    assert 'use a new output directory' in str(caught.value)
    if lock_only:
        assert 'age unestablished:' not in str(caught.value)


@pytest.mark.parametrize('sibling', [False, True])
@pytest.mark.parametrize('layout', ['flat', 'split'])
@pytest.mark.parametrize('resume', [False, True])
def test_failure_after_locks_has_a_printed_anchor_and_can_resume(tmp_path, monkeypatch, capsys, sibling, layout, resume):
    monkeypatch.setattr(api.RunSpec, 'output_root', property(lambda self: tmp_path / 'root'))
    kwargs = {'out_dir': tmp_path / 'outputs'} if layout == 'flat' else {}
    first = spec(project='VOICE_PEDIATRIC' if sibling else 'VOICE', **kwargs)
    with monkeypatch.context() as failing:
        def fail(*args, **kwargs):
            raise RuntimeError('injected failure before accounting')
        failing.setattr(api, '_execute', fail)
        with pytest.raises(RuntimeError, match='before accounting'):
            api.execute(first, client=FakeClient())
    assert not ledger.ledger_path(first).exists()
    events = journal._events(first)
    assert events and events[0]['identity'] == ledger.run_identity(first)
    assert events[-1]['sha256'] in capsys.readouterr().err
    current = replace(first, project='VOICE')
    before, client = tree(tmp_path), FakeClient()
    if not sibling:
        # Explicitly omit the monitor's retained head: D57 must still refuse.
        with pytest.raises(ledger.UsageLedgerError, match='resume journal head'):
            api.execute(current, resume=resume, client=client, expect_journal_head_sha256=None)
        assert tree(tmp_path) == before and client.messages.calls == []
    api.execute(current, resume=resume, client=client)
    assert len(client.messages.calls) == 4


@pytest.mark.parametrize('check', ['schema', 'settings', 'headers', 'shared_preflight', 'require_client'])
def test_readonly_startup_checks_precede_every_write(tmp_path, monkeypatch, check):
    from data_sheets_schema import schema_sync, shared_generation
    from tests.test_evidence_generation_gate import specification
    from tests.test_shared_generation_selection import selected_spec, registration_for
    selected = spec(project='P', out_dir=tmp_path / 'outputs')
    if check in ('shared_preflight', 'require_client'):
        base = specification(tmp_path)
        selected = selected_spec(base, registration_for(base))
    target, name = {
        'schema': (schema_sync, 'check'), 'settings': (api, '_model_settings'),
        'headers': (api.RunSpec, 'bind_api_header_values'),
        'shared_preflight': (shared_generation, 'preflight'),
        'require_client': (shared_generation, 'require_client')}[check]
    def fail(*args, **kwargs):
        raise RuntimeError('injected read-only startup failure')
    monkeypatch.setattr(target, name, fail)
    before, client = tree(tmp_path), FakeClient()
    with pytest.raises(RuntimeError, match='read-only startup failure'):
        api.execute(selected, client=client)
    assert tree(tmp_path) == before and client.messages.calls == []


@pytest.mark.parametrize('version', [1, 2])
def test_shared_no_resume_names_files(tmp_path, draft_files, version):
    from tests.test_evidence_generation_gate import specification
    from tests.test_shared_generation_selection import selected_spec, registration_for
    from tests.test_shared_generation_runtime import client as shared_client
    if version == 1:
        base = specification(tmp_path)
        selected = selected_spec(base, registration_for(base))
    else:
        from tests.test_source_heading_runtime_api import selected_spec as routing_spec
        selected = routing_spec(tmp_path, draft_files)
    ledger.prepare_usage(selected, resume=True)
    before, client = tree(tmp_path), shared_client(selected)
    with pytest.raises(ledger.UsageLedgerError, match='no-resume') as caught:
        api._execute(selected, resume=False, client=client)
    assert 'files: ' in str(caught.value)
    assert ledger.ledger_path(selected).name in str(caught.value)
    assert tree(tmp_path) == before and client.messages.calls == []


@pytest.mark.parametrize('resume', [False, True])
def test_shared_failed_launch_has_usable_production_ownership(tmp_path, monkeypatch, resume):
    from data_sheets_schema.output_ownership import require_selected_resume_owner
    from tests.test_evidence_generation_gate import specification
    from tests.test_shared_generation_selection import selected_spec, registration_for
    from tests.test_shared_generation_runtime import client as shared_client
    base = specification(tmp_path)
    selected = selected_spec(base, registration_for(base))
    def fail(*args, **kwargs):
        raise RuntimeError('injected before accounting')
    monkeypatch.setattr(api, '_execute', fail)
    for _ in range(2):
        client = shared_client(selected)
        with pytest.raises(RuntimeError, match='injected before accounting'):
            api.execute(selected, resume=resume, client=client)
        assert client.messages.calls == []
        assert journal.journal_path(selected).is_file()
        assert not ledger.ledger_path(selected).exists()
        require_selected_resume_owner(selected, resume=resume)


@pytest.mark.parametrize('destination', ['full', 'core', 'report', 'provenance', 'ledger',
                                        'journal', 'progress', 'receipt', 'reasoning', 'index'])
def test_selected_writer_addresses_survive_enumeration_aliases(tmp_path, monkeypatch, destination):
    from data_sheets_schema import snapshot_store
    selected = spec(project='P', out_dir=tmp_path)
    paths = {name: getattr(selected, name + '_path') for name in ('full', 'core', 'report', 'provenance')}
    paths.update(ledger=ledger.ledger_path(selected), journal=journal.journal_path(selected),
                 progress=api._progress_path(selected), receipt=api._receipt_path(selected),
                 reasoning=api._reasoning_path(selected), index=snapshot_store.index_path(tmp_path, 'P'))
    path = paths[destination]
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b'legacy address')
    monkeypatch.setattr(Path, 'iterdir', lambda self: iter(()))
    assert path in journal.owned_artifacts(selected)
