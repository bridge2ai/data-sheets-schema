"""Portable snapshot ownership and unrecorded paid attempts (#1415–1417)."""
from dataclasses import replace
import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, receipts, snapshot_store as store
from data_sheets_schema import usage_ledger as ledger
from data_sheets_schema.cli import cli
from data_sheets_schema.report_claims import phase1_snapshot_with_pin_for
from tests.test_download.test_api_runner import FakeClient
from tests.test_download.test_receipt_readdress import _ReceiptFake
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.mark.parametrize("index_state", ["foreign", "missing"])
@pytest.mark.parametrize("journals", [True, False])
def test_portable_checks_use_only_the_matching_records_phase_evidence(external, index_state, journals):
    old = external
    ledger.prepare_usage(old, resume=True)
    store.activate(old, fresh=True, completed=False, prior_record={})
    api._snapshot(old, "EXTERNAL_full.yaml", "id: x\ntitle: OLD_GENERATION\n")
    old_index = store.index_path(old.metadata_dir, old.project).read_bytes()
    current = replace(old, label="new_generation")
    ledger.prepare_usage(current, resume=False)
    store.activate(current, fresh=True, completed=False, prior_record={})
    actual = api._snapshot(current, "EXTERNAL_full.yaml", "id: x\ntitle: EXPECTED_GENERATION\n")
    record = {"run": {**ledger.run_identity(current), "generation_id": ledger.generation_id(current)},
              "inputs": {}, "intermediates": store.entries(current)}
    current.provenance_path.write_text(yaml.safe_dump(record))
    index = store.index_path(current.metadata_dir, current.project)
    if index_state == "foreign":
        index.write_bytes(old_index)
    else:
        index.unlink()
    if not journals:
        ledger.ledger_path(old).unlink()
        ledger.ledger_path(current).unlink()
    # Neither a prior index nor a numerically newer unregistered file is evidence.
    stray = current.metadata_dir / "intermediate" / "EXTERNAL_full_999.yaml"
    stray.write_text("id: x\ntitle: UNREGISTERED_GENERATION\n")
    before = {str(p): p.read_bytes() for p in current.metadata_dir.rglob("*") if p.is_file()}
    state, path, body, why = receipts.phase1_snapshot_state(api._receipt_path(current))
    assert state == "usable", why
    assert path == actual and body["title"] == "EXPECTED_GENERATION"
    report_body, pin = phase1_snapshot_with_pin_for(current.core_path)
    assert report_body == body and pin["path"] == str(actual)
    assert {str(p): p.read_bytes() for p in current.metadata_dir.rglob("*") if p.is_file()} == before


def test_completed_shortcut_cannot_discard_a_delivered_paid_attempt(external, monkeypatch):
    spec = replace(external, condition="generic_v7")
    monkeypatch.setattr(api, "_validator_lines", lambda *args: ([], None))
    old = FakeClient()
    old.messages = _ReceiptFake(bad_slot="keywords[0]")
    api.execute(spec, client=old)
    prior = spec.provenance_path.read_bytes()
    old_generation = ledger.generation_id(spec)
    attempt = FakeClient()
    attempt.messages = _ReceiptFake(bad_slot="keywords[0]")
    def crash(*args, **kwargs):
        raise OSError("crash before reasoning persistence")
    with monkeypatch.context() as failing:
        failing.setattr(api.reasoning, "append", crash)
        with pytest.raises(OSError, match="crash before reasoning"):
            api.execute(spec, resume=False, client=attempt)
    index = store.index_path(spec.metadata_dir, spec.project)
    saved = json.loads(index.read_text())
    assert saved["generation_id"] != old_generation
    rows = ledger.merge_usage(spec, [])
    assert len(rows) == 1 and rows[0]["phase"] == "full"
    response = next(e for e in saved["snapshots"] if e.get("usage_id") == rows[0]["usage_id"])
    assert Path(response["path"]).is_file()
    assert spec.provenance_path.read_bytes() == prior
    ledger.ledger_path(spec).unlink()  # a portable recovery omitted the journal
    before = {str(p): p.read_bytes() for p in spec.metadata_dir.rglob("*") if p.is_file()}
    recovered = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="snapshot|accounting|generation"):
        api.execute(spec, client=recovered)
    assert recovered.messages.calls == []
    assert {str(p): p.read_bytes() for p in spec.metadata_dir.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("selection", ["bundle", "project"])
def test_strict_chunk_check_refuses_missing_selected_input(tmp_path, selection):
    missing = tmp_path / "missing.txt"
    if selection == "bundle":
        args = ["--bundle", str(missing)]
    else:
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(yaml.safe_dump({"projects": {"EXTERNAL": {"bundle": str(missing), "sources": []}}}))
        args = ["--manifest", str(manifest), "--project", "EXTERNAL"]
    result = CliRunner().invoke(cli, ["bundle", "chunk", *args, "--check", "--strict"])
    assert result.exit_code == 1, result.output
    assert "no_bundle" in result.output
    assert not missing.exists()


def test_owned_checks_pin_and_parse_the_same_read(external, monkeypatch):
    ledger.prepare_usage(external, resume=True)
    store.activate(external, fresh=True, completed=False, prior_record={})
    before = b'id: before\ntitle: Before replacement\n'
    snapshot = api._snapshot(external, 'EXTERNAL_full.yaml', before.decode())
    record = {'run': {**ledger.run_identity(external), 'generation_id': ledger.generation_id(external)},
              'intermediates': store.entries(external)}
    external.provenance_path.write_text(yaml.safe_dump(record))
    original = Path.read_bytes
    def replacing(path):
        raw = original(path)
        if path == snapshot:
            path.write_text('id: after\n')
        return raw
    with monkeypatch.context() as race:
        race.setattr(Path, 'read_bytes', replacing)
        doc, pin = phase1_snapshot_with_pin_for(external.core_path)
    import hashlib
    assert doc['id'] == 'before'
    assert pin['sha256'] == hashlib.sha256(before).hexdigest()
    assert snapshot.read_text() == 'id: after\n'
    assert receipts.phase1_snapshot_state(api._receipt_path(external))[0] == 'unusable'


def test_portable_phase_evidence_refuses_ambiguous_or_foreign_ownership(external):
    first = api._snapshot(external, 'EXTERNAL_full.yaml', 'id: first\n')
    second = api._snapshot(external, 'EXTERNAL_full.yaml', 'id: second\n')
    import hashlib
    entries = [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
               for path in (first, second)]
    record = {'run': {**ledger.run_identity(external), 'generation_id': 'owner'}, 'intermediates': entries}
    state, _, _, why = receipts.phase1_snapshot_state(api._receipt_path(external), record=record)
    assert state == 'unusable' and 'ambiguous' in why
    record['intermediates'] = [{**entries[-1], 'phase': 'EXTERNAL_full.yaml', 'generation_id': 'someone-else'}]
    state, _, _, why = receipts.phase1_snapshot_state(api._receipt_path(external), record=record)
    assert state == 'unusable' and 'different generation' in why


def test_surviving_index_requires_an_expected_owner_and_current_inputs(external):
    ledger.prepare_usage(external, resume=True)
    store.activate(external, fresh=True, completed=False, prior_record={})
    api._snapshot(external, 'EXTERNAL_full.yaml', 'id: x\n')
    state, _, _, why = receipts.phase1_snapshot_state(api._receipt_path(external))
    assert state == 'unusable' and 'matching run' in why
    assert receipts.phase1_snapshot_state(api._receipt_path(external), spec=external)[0] == 'usable'
    external.bundle.write_text(external.bundle.read_text() + '\nchanged input\n')
    state, _, _, why = receipts.phase1_snapshot_state(api._receipt_path(external), spec=external)
    assert state == 'unusable' and 'input identity' in why


def test_archived_newer_attempt_cannot_hide_behind_a_restored_old_index(external):
    old_generation = ledger.prepare_usage(external, resume=True)
    store.activate(external, fresh=True, completed=False, prior_record={})
    index = store.index_path(external.metadata_dir, external.project)
    old_index = index.read_bytes()
    ledger.prepare_usage(external, resume=False)
    store.activate(external, fresh=True, completed=False, prior_record={})
    api._snapshot(external, 'EXTERNAL_full_response_new-call.txt', 'delivered', usage_id='new-call')
    index.with_name('EXTERNAL_snapshot_index.previous-restored.json').write_bytes(index.read_bytes())
    index.write_bytes(old_index)
    ledger.ledger_path(external).unlink()
    record = {'run': {**ledger.run_identity(external), 'generation_id': old_generation}, 'api_usage': []}
    with pytest.raises(ledger.UsageLedgerError, match='unaccounted attempt'):
        store.require_accounted(external, record)


def test_missing_index_recovery_preserves_all_phase_evidence_in_order(external):
    ledger.prepare_usage(external, resume=True)
    store.activate(external, fresh=True, completed=False, prior_record={})
    api._snapshot(external, 'EXTERNAL_full.yaml', 'id: first\n')
    latest = api._snapshot(external, 'EXTERNAL_full.yaml', 'id: second\n')
    api._snapshot(external, 'EXTERNAL_audit.json', '{}\n')
    record = {'run': {**ledger.run_identity(external), 'generation_id': ledger.generation_id(external)},
              'intermediates': store.entries(external)}
    store.index_path(external.metadata_dir, external.project).unlink()
    store.activate(external, fresh=False, completed=True, prior_record=record)
    assert store.entries(external) == record['intermediates']
    assert receipts.phase1_snapshot_path(api._receipt_path(external), spec=external) == latest


def test_identified_record_without_phase_attestation_is_unusable(external):
    api._snapshot(external, 'EXTERNAL_full.yaml', 'id: not_attested\n')
    record = {'run': {**ledger.run_identity(external), 'generation_id': 'owner'}, 'intermediates': []}
    state, _, _, why = receipts.phase1_snapshot_state(api._receipt_path(external), record=record)
    assert state == 'unusable' and 'no attested' in why


@pytest.mark.parametrize('damage', [None, 'hash', 'path', 'bytes'])
def test_historical_report_pin_disambiguates_only_attested_phase_bytes(external, damage):
    import hashlib
    selected = api._snapshot(external, 'EXTERNAL_full.yaml', 'id: selected\n')
    other = api._snapshot(external, 'EXTERNAL_full.yaml', 'id: other\n')
    entries = [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
               for path in (selected, other)]
    pin = {**entries[0], 'state': 'usable'}
    record = {'run': ledger.run_identity(external), 'intermediates': entries,
              'report_claims': {'artifacts': {'phase1_snapshot': pin}}}
    if damage == 'hash':
        pin['sha256'] = 'a' * 64
    elif damage == 'path':
        pin['path'] = str(other)
    elif damage == 'bytes':
        selected.write_text('id: tampered\n')
    state, path, doc, why = receipts.phase1_snapshot_state(api._receipt_path(external), record=record)
    if damage is None:
        assert state == 'usable' and path == selected and doc['id'] == 'selected'
    else:
        assert state == 'unusable' and ('pin' in why or 'bytes changed' in why)


@pytest.mark.parametrize('content', [None, 'projects: {}\n', 'projects: []\n'])
def test_strict_chunk_check_requires_a_readable_nonempty_registry(tmp_path, content):
    manifest = tmp_path / 'selected.yaml'
    if content is not None:
        manifest.write_text(content)
    before = {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    result = CliRunner().invoke(cli, ['bundle', 'chunk', '--manifest', str(manifest), '--check', '--strict'])
    assert result.exit_code == 1, result.output
    assert 'manifest' in result.output.lower() or 'no bundle' in result.output.lower()
    assert {str(path): path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()} == before


def test_completed_record_phase_wins_over_a_same_generation_old_index(external):
    ledger.prepare_usage(external, resume=True)
    store.activate(external, fresh=True, completed=False, prior_record={})
    api._snapshot(external, 'EXTERNAL_full.yaml', 'id: x\nfunders: [{id: inserted}, {id: original}]\n')
    index = store.index_path(external.metadata_dir, external.project)
    old_index = index.read_bytes()
    latest = api._snapshot(external, 'EXTERNAL_full.yaml', 'id: x\nfunders: [{id: original}, {id: inserted}]\n')
    record = {'run': {**ledger.run_identity(external), 'generation_id': ledger.generation_id(external)},
              'intermediates': store.entries(external)}
    external.provenance_path.write_text(yaml.safe_dump(record))
    index.write_bytes(old_index)
    store.require_accounted(external, record)
    state, path, doc, why = receipts.phase1_snapshot_state(api._receipt_path(external), spec=external, record=record)
    assert state == 'usable', why
    assert path == latest and doc['funders'][0]['id'] == 'original'
    report, pin = phase1_snapshot_with_pin_for(external.core_path, spec=external, record=record)
    assert report == doc and pin['path'] == str(latest)


def test_completed_api_shortcut_checks_the_portable_phase_after_rerun(external):
    from tests.test_generation_recovery_review import client_named
    api.execute(external, client=client_named('FIRST_PHASE'))
    index = store.index_path(external.metadata_dir, external.project)
    old_index = index.read_bytes()
    external.full_path.write_text('not a D4D mapping\n')
    api._save_progress(external, ['full', 'core'], None)
    api.execute(external, client=client_named('LATER_PHASE'))
    prior_bytes = external.provenance_path.read_bytes()
    prior = yaml.safe_load(prior_bytes)
    snapshot = next(e for e in reversed(prior['intermediates']) if e.get('phase') == 'EXTERNAL_full.yaml')
    assert 'LATER_PHASE' in Path(snapshot['path']).read_text()
    index.write_bytes(old_index)
    client = client_named('MUST_NOT_CALL')
    resumed = api.execute(external, client=client)
    assert resumed['already_complete'] and client.messages.calls == []
    assert resumed['usage'] == prior['api_usage']
    assert resumed['checks']['report']['artifacts']['phase1_snapshot']['path'] == snapshot['path']
    assert external.provenance_path.read_bytes() == prior_bytes


def test_live_phase_check_uses_current_index_over_an_older_portable_record(external):
    ledger.prepare_usage(external, resume=True)
    store.activate(external, fresh=True, completed=False, prior_record={})
    api._snapshot(external, 'EXTERNAL_full.yaml', 'id: old\n')
    record = {'run': {**ledger.run_identity(external), 'generation_id': ledger.generation_id(external)},
              'intermediates': store.entries(external)}
    external.provenance_path.write_text(yaml.safe_dump(record))
    latest = api._snapshot(external, 'EXTERNAL_full.yaml', 'id: live\n')
    state, path, doc, _ = receipts.phase1_snapshot_state(api._receipt_path(external), spec=external)
    assert state == 'usable' and path == latest and doc['id'] == 'live'
