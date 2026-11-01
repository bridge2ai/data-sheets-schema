"""#5212 round 5, 2026-11-01: reviewer boundary regressions with real writers.

Codex round-4 safe probes and Claude R4-2/3/4/8/9, in both resume modes.
All executions use fake clients and the externally retained launch monitor.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unicodedata

import pytest
import yaml

from data_sheets_schema import api_runner as api, latch_journal as journal
from data_sheets_schema import usage_ledger as ledger, provenance
from tests.test_download.test_api_runner import FakeClient, spec
from tests.test_d68_legacy_readonly import tree
from tests.test_generation_manifest_identity import external  # noqa: F401

pytestmark = pytest.mark.usefixtures('journal_launch_monitor')


def refuses(selected, orphan, root, resume):
    before, client = tree(root), FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match='inspection only') as caught:
        api.execute(selected, resume=resume, client=client)
    assert unicodedata.normalize('NFC', orphan.name).casefold() in unicodedata.normalize('NFC', str(caught.value)).casefold()
    assert client.messages.calls == []
    assert tree(root) == before


@pytest.mark.parametrize('resume', [False, True])
def test_absent_production_reasoning_pin_cannot_claim_a_later_file(tmp_path, resume):
    foreign = spec(project='P', label='guarded', out_dir=tmp_path)
    ledger.prepare_usage(foreign, resume=True)
    orphan = tmp_path / 'P_reasoning.jsonl'
    record = provenance.build_record(foreign.project, foreign.method, foreign.label,
        mode='reconstructed', input_bundle=foreign.bundle, concat_dir=tmp_path,
        condition=foreign.condition, manifest=None,
        outputs={'full': foreign.full_path, 'core': foreign.core_path,
                 'report': foreign.report_path, 'reasoning': orphan})
    record.write(foreign.provenance_path)
    pin = yaml.safe_load(foreign.provenance_path.read_text())['companions']['reasoning_log']
    assert pin['present'] is False and pin.get('md5') is None
    orphan.write_text('{"legacy": "unowned reasoning"}\n')
    refuses(replace(foreign, label='selected'), orphan, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('constraint', ['path', 'bytes', 'absent', 'null_sha256', 'null_md5'])
def test_canonical_digestless_or_absent_pin_is_not_ownership(tmp_path, resume, constraint):
    foreign = spec(project='P', label='guarded', out_dir=tmp_path)
    ledger.prepare_usage(foreign, resume=True)
    orphan = tmp_path / 'P_unknown_writer.bin'
    orphan.write_bytes(b'unowned output')
    pin = {'path': str(orphan)}
    if constraint == 'bytes':
        pin['bytes'] = orphan.stat().st_size
    if constraint in ('absent', 'null_sha256', 'null_md5'):
        pin['sha256'] = hashlib.sha256(orphan.read_bytes()).hexdigest()
        pin.update({'present': False} if constraint == 'absent' else {constraint[5:]: None})
    foreign.provenance_path.write_text(yaml.safe_dump({
        'run': ledger.run_identity(foreign), 'outputs': {'unknown': pin}}))
    refuses(replace(foreign, label='selected'), orphan, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('record_kind', ['provenance', 'index', 'index_archive', 'ledger', 'ledger_archive', 'routing'])
def test_residue_metadata_cannot_authorize_another_orphan(tmp_path, resume, record_kind):
    foreign = spec(project='Q', out_dir=tmp_path)
    ledger.prepare_usage(foreign, resume=True)
    selected = replace(foreign, project='P')
    orphan = tmp_path / 'P_report_context.json'
    orphan.write_bytes(b'unowned output\n')
    names = {'provenance': 'P_orphan_provenance.yaml', 'index': 'P_snapshot_index.json',
        'index_archive': 'P_snapshot_index.previous-' + 'a' * 32 + '.json',
        'ledger': ledger.ledger_path(foreign).name.replace('Q_', 'P_'),
        'ledger_archive': ledger.ledger_path(foreign).stem.replace('Q_', 'P_') + '.previous-' + 'a' * 32 + '.json',
        'routing': 'P_routing_completed.json'}
    counterfeit = tmp_path / names[record_kind]
    record = {'run': ledger.run_identity(foreign), 'outputs': {'unowned': {
        'path': str(orphan), 'sha256': hashlib.sha256(orphan.read_bytes()).hexdigest()}}}
    if record_kind == 'routing':
        record.update(format='source_heading_completed_v1', selection={'run': ledger.run_identity(foreign)})
    counterfeit.write_text(yaml.safe_dump(record))
    assert counterfeit in journal.owned_artifacts(selected)
    refuses(selected, counterfeit, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('canonical', [False, True])
def test_edited_identity_record_requires_canonical_address(tmp_path, resume, canonical):
    first = spec(project='P', label='first', out_dir=tmp_path)
    api.execute(first, client=FakeClient())
    record = yaml.safe_load(first.provenance_path.read_bytes())
    record['curator_note'] = 'unguarded edit; canonical post-run records intentionally remain mutable'
    path = first.provenance_path if canonical else tmp_path / 'P_notes_provenance.yaml'
    path.write_text(yaml.safe_dump(record))
    second = replace(first, label='second')
    if canonical:
        assert path not in journal.owned_artifacts(second)
        client = FakeClient()
        api.execute(second, resume=resume, client=client)
        assert len(client.messages.calls) == 4
    else:
        refuses(second, path, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('real_alias', [False, True])
@pytest.mark.parametrize('project,suffix', [('Café', 'report_context.json'), ('PÜ', 'full.yaml')])
def test_unicode_normalization_alias_is_residue(tmp_path, resume, real_alias, project, suffix):
    selected = spec(project=project, out_dir=tmp_path)
    orphan = tmp_path / 'intermediate' / unicodedata.normalize('NFD', project + '_' + suffix)
    orphan.parent.mkdir()
    orphan.write_text('unowned Unicode alias\n')
    alias = orphan.with_name(unicodedata.normalize('NFC', orphan.name))
    if real_alias and (not alias.exists() or not alias.samefile(orphan)):
        pytest.skip('volume does not alias composed/decomposed Unicode filenames')
    refuses(selected, orphan, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
def test_casefold_does_not_equate_distinct_real_files(tmp_path, resume):
    foreign = spec(project='P', label='guarded', out_dir=tmp_path)
    ledger.prepare_usage(foreign, resume=True)
    first = api._snapshot(foreign, 'P_Straße_context.json', 'same bytes, distinct artifact\n')
    second = first.with_name('P_STRASSE_context.json')
    if second.exists():
        pytest.skip('case-insensitive volume aliases this casefold pair; distinct-file check requires Linux/case-sensitive volume')
    second.write_bytes(first.read_bytes())
    assert not first.samefile(second) and str(first).casefold() == str(second).casefold()
    refuses(replace(foreign, label='selected'), second, tmp_path, resume)


def test_distinct_file_identity_is_required_portably(tmp_path, monkeypatch):
    first, second = tmp_path / 'P_A', tmp_path / 'P_a'
    first.write_bytes(b'equal bytes')
    original, read_bytes = Path.lstat, Path.read_bytes
    def distinct(path, *args, **kwargs):
        info = original(first if path == second else path, *args, **kwargs)
        if path == second:
            from types import SimpleNamespace
            return SimpleNamespace(st_dev=info.st_dev, st_ino=info.st_ino + 1, st_mode=info.st_mode)
        return info
    monkeypatch.setattr(Path, 'lstat', distinct)
    monkeypatch.setattr(Path, 'read_bytes', lambda path: read_bytes(first if path == second else path))
    pin = {'path': str(first), 'sha256': hashlib.sha256(first.read_bytes()).hexdigest()}
    assert not journal._output_matches(second, pin)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('sibling', [False, True])
def test_partial_lock_acquisition_does_not_burn_the_location(tmp_path, monkeypatch, capsys, resume, sibling):
    from filelock import FileLock
    first = spec(project='VOICE_PEDIATRIC' if sibling else 'VOICE', out_dir=tmp_path)
    acquire, calls = FileLock.acquire, []
    with monkeypatch.context() as failing:
        def acquire_with_failure(lock, *args, **kwargs):
            calls.append(str(lock.lock_file))
            if len(calls) == 2:
                raise OSError('injected second lock acquisition failure')
            return acquire(lock, *args, **kwargs)
        failing.setattr(FileLock, 'acquire', acquire_with_failure)
        client = FakeClient()
        with pytest.raises(OSError, match='second lock acquisition'):
            api.execute(first, resume=resume, client=client)
        assert client.messages.calls == []
    assert list(tmp_path.glob('.*_api_run.lock'))
    head = journal.head_sha256(first)
    if head:
        assert head in capsys.readouterr().err
    current, client = replace(first, project='VOICE'), FakeClient()
    api.execute(current, resume=resume, client=client)
    assert len(client.messages.calls) == 4


@pytest.mark.parametrize('resume', [False, True])
def test_existing_lock_contention_precedes_any_new_sidecar(tmp_path, monkeypatch, resume):
    monkeypatch.setattr(api.RunSpec, 'output_root', property(lambda self: tmp_path / 'root'))
    owner = spec(project='P', label='owner')
    api.execute(owner, client=FakeClient())
    contender = replace(owner, label='contender', out_dir=owner.core_path.parent)
    leftover = contender.full_path.with_name(f'.{contender.full_path.name}_api_run.lock')
    assert not leftover.exists()
    with ledger.exclusive_run(owner):
        client = FakeClient()
        with pytest.raises(ledger.UsageLedgerError, match='already active'):
            api.execute(contender, resume=resume, client=client)
        assert client.messages.calls == []
    assert not leftover.exists()
    client = FakeClient()
    api.execute(contender, resume=resume, client=client)
    assert len(client.messages.calls) == 4


@pytest.mark.parametrize('resume', [False, True])
def test_identity_bearing_unknown_writer_fails_independent_census(external, tmp_path, monkeypatch, resume):
    from tests.test_d69_artifact_completeness import assert_writer_completeness
    original = api._snapshot
    def extra_writer(selected, *args, **kwargs):
        result = original(selected, *args, **kwargs)
        path = selected.metadata_dir / 'intermediate' / (selected.project + '_new_writer.json')
        path.write_text(json.dumps({'run_identity': ledger.run_identity(selected)}))
        return result
    monkeypatch.setattr(api, '_snapshot', extra_writer)
    api.execute(external, resume=resume, client=FakeClient())
    with pytest.raises(AssertionError, match='new_writer'):
        assert_writer_completeness(external, tmp_path)


@pytest.mark.parametrize('resume', [False, True])
def test_canonical_record_requires_the_complete_embedded_identity(tmp_path, resume):
    foreign = spec(project='P', label='foreign', out_dir=tmp_path)
    ledger.prepare_usage(foreign, resume=True)
    orphan = tmp_path / 'P_orphan.bin'
    orphan.write_bytes(b'unowned')
    foreign.provenance_path.write_text(yaml.safe_dump({'run': {'project': 'P', 'label': 'foreign'},
        'outputs': {'orphan': {'path': str(orphan), 'sha256': hashlib.sha256(orphan.read_bytes()).hexdigest()}}}))
    refuses(replace(foreign, label='selected'), orphan, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
def test_pre_round4_identity_binds_sidecars_on_next_launch(tmp_path, resume):
    first = spec(project='VOICE_PEDIATRIC', out_dir=tmp_path)
    ledger.prepare_usage(first, resume=True)  # Production generation with no launch event.
    with ledger.exclusive_run(first):
        pass  # Existing pre-round-4 sidecars, still without any launch binding.
    assert not any(row['kind'] == 'launch' for row in journal._events(first))
    api.execute(first, resume=resume, client=FakeClient())
    assert any(row['kind'] == 'launch' for row in journal._events(first))
    client = FakeClient()
    api.execute(replace(first, project='VOICE'), resume=resume, client=client)
    assert len(client.messages.calls) == 4


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('operation', ['head_read', 'launch_read', 'sidecar_read', 'append'])
def test_transient_pre_event_failure_has_recoverable_ownership(tmp_path, monkeypatch, capsys, resume, operation):
    first = spec(project='VOICE_PEDIATRIC', out_dir=tmp_path)
    calls = []
    target = {'head_read': 'require_launch_head', 'launch_read': '_events',
              'sidecar_read': '_bytes', 'append': '_append'}[operation]
    original = getattr(journal, target)
    with monkeypatch.context() as failing:
        def fail_once(*args, **kwargs):
            locks = list(tmp_path.glob('.*_api_run.lock'))
            eligible = bool(locks) and (operation != 'sidecar_read' or str(args[0]).endswith('_api_run.lock'))
            if operation == 'launch_read':
                import inspect
                eligible = eligible and inspect.currentframe().f_back.f_code.co_name == 'start_launch'
            if eligible and not calls:
                calls.append(operation)
                raise OSError('transient launch ' + operation)
            return original(*args, **kwargs)
        failing.setattr(journal, target, fail_once)
        client = FakeClient()
        with pytest.raises(OSError, match='transient launch'):
            api.execute(first, resume=resume, client=client)
        assert client.messages.calls == []
    head = journal.head_sha256(first)
    assert head and head in capsys.readouterr().err
    client = FakeClient()
    api.execute(replace(first, project='VOICE'), resume=resume, client=client)
    assert len(client.messages.calls) == 4
    client = FakeClient()
    api.execute(first, resume=resume, client=client, expect_journal_head_sha256=head)
    assert len(client.messages.calls) == 4


@pytest.mark.parametrize('resume', [False, True])
def test_stray_path_only_provenance_cannot_authorize_residue(tmp_path, resume):
    first = spec(project='P', label='first', out_dir=tmp_path)
    api.execute(first, client=FakeClient())
    orphan = tmp_path / 'P_unknown_writer.bin'
    orphan.write_bytes(b'journal-less artifact')
    stray = tmp_path / 'P_notes_provenance.yaml'
    stray.write_text(yaml.safe_dump({'run': ledger.run_identity(first),
                                   'outputs': {'note': {'path': str(orphan)}}}))
    refuses(replace(first, label='second'), orphan, tmp_path, resume)


@pytest.mark.parametrize('resume', [False, True])
def test_digestless_launch_cannot_exempt_unbound_sidecars(tmp_path, resume):
    selected = spec(project='P', out_dir=tmp_path)
    with ledger.exclusive_run(selected):
        pass
    locks = [path for _, path in ledger.output_locks((selected.full_path, selected.core_path,
                                                     selected.report_path, selected.provenance_path))]
    events = []
    event = journal._event(selected, {'generation_id': 'unproved-launch'}, events,
        'launch', {'outputs': [{'path': str(path), 'bytes': 0} for path in locks]})
    journal._append(selected, events, event)
    refuses(selected, locks[0], tmp_path, resume)
