"""A recovered generation also retains phase attempts and their accounting."""
from dataclasses import replace
from pathlib import Path
import json
import pytest
import yaml

from data_sheets_schema import api_runner as api, snapshot_store as store, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient
from tests.test_download.test_receipt_readdress import _ReceiptFake
from tests.test_generation_recovery_review import client_named
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


def test_partial_resume_recovers_newer_phase_history_from_progress(external):
    api.execute(external, client=client_named('FIRST_PHASE'))
    index = store.index_path(external.metadata_dir, external.project)
    old_index = index.read_bytes()
    external.full_path.write_text('not a D4D mapping\n')
    api._save_progress(external, ['full', 'core'], None)
    with pytest.raises(RuntimeError, match='boom'):
        api.execute(external, client=client_named('LATER_PHASE', fail_on='audit'))
    index.write_bytes(old_index)
    client = client_named('MUST_KEEP_LATER_PHASE')
    result = api.execute(external, client=client)
    assert {'full', 'core'} <= set(result['skipped'])
    report_call = next(call for call in client.messages.calls
                       if any(api.PHASE_INSTRUCTIONS['report'] in part.get('text', '')
                              for part in call['messages'][0]['content']))
    assert 'FIRST_PHASE' not in json.dumps(report_call)
    assert 'LATER_PHASE' in json.dumps(report_call)
    record = yaml.safe_load(external.provenance_path.read_text())
    selected = next(e for e in reversed(record['intermediates']) if e.get('phase') == 'EXTERNAL_full.yaml')
    assert 'LATER_PHASE' in Path(selected['path']).read_text()


def test_completed_shortcut_requires_all_same_generation_charges_on_record(external, monkeypatch):
    spec = replace(external, condition='generic_v7')
    monkeypatch.setattr(api, '_validator_lines', lambda *args: ([], None))
    first = FakeClient()
    first.messages = _ReceiptFake(bad_slot='keywords[0]')
    api.execute(spec, client=first)
    original_full = spec.full_path.read_bytes()
    original_record = spec.provenance_path.read_bytes()
    spec.full_path.write_text('not a D4D mapping\n')
    api._save_progress(spec, [], None)
    attempt = FakeClient()
    attempt.messages = _ReceiptFake(bad_slot='keywords[0]')
    with monkeypatch.context() as crashing:
        def crash(*args, **kwargs):
            raise OSError('crash after delivered response')
        crashing.setattr(api.reasoning, 'append', crash)
        with pytest.raises(OSError, match='crash after delivered'):
            api.execute(spec, client=attempt)
    assert len(ledger.merge_usage(spec, [])) > len(yaml.safe_load(original_record)['api_usage'])
    # Restoring old artifacts does not undo the real additional charge.
    spec.full_path.write_bytes(original_full)
    api._progress_path(spec).unlink()
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match='account|attempt|charge'):
        api.execute(spec, client=client)
    assert client.messages.calls == []
    assert spec.provenance_path.read_bytes() == original_record
