"""An explicit restart can supersede an orphaned partial generation."""
import json
from pathlib import Path
import pytest
from data_sheets_schema import api_runner as api, usage_ledger as ledger, snapshot_store
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401

@pytest.mark.parametrize("state", ["missing", "malformed"])
def test_fresh_restart_records_an_orphaned_partial_predecessor(external, state):
    first = FakeClient()
    first.messages.fail_on = "audit"
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(external, client=first)
    previous = ledger.generation_id(external)
    original_index = snapshot_store.index_path(external.metadata_dir, external.project).read_bytes()
    index = json.loads(snapshot_store.index_path(external.metadata_dir, external.project).read_text())
    preserved = {entry["path"]: Path(entry["path"]).read_bytes() for entry in index["snapshots"]}
    assert not external.provenance_path.exists()
    if state == "missing": ledger.ledger_path(external).unlink()
    else: ledger.ledger_path(external).write_text("not JSON")
    fresh_client = FakeClient()
    fresh = api.execute(external, resume=False, client=fresh_client)
    assert len(fresh["usage"]) == len(fresh_client.messages.calls) == 4
    assert previous in ledger.prior_generation_ids(external)
    assert all(Path(path).read_bytes() == raw for path, raw in preserved.items())
    assert any(path.read_bytes() == original_index for path in
               snapshot_store.index_path(external.metadata_dir, external.project).parent.glob(
                   f"{external.project}_snapshot_index.previous-*.json"))
    repeat = FakeClient()
    assert api.execute(external, client=repeat)["already_complete"]
    assert repeat.messages.calls == []


def test_predecessor_binding_survives_interrupted_index_activation(external, monkeypatch):
    first = FakeClient()
    first.messages.fail_on = "audit"
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(external, client=first)
    previous = ledger.generation_id(external)
    path = snapshot_store.index_path(external.metadata_dir, external.project)
    original = path.read_bytes()
    ledger.ledger_path(external).unlink()
    client = FakeClient()
    with monkeypatch.context() as failing:
        def refuse(*args, **kwargs):
            raise OSError("injected index publication failure")
        failing.setattr(snapshot_store, "_write", refuse)
        with pytest.raises(OSError, match="index publication"):
            api.execute(external, resume=False, client=client)
    assert client.messages.calls == []
    assert previous in ledger.prior_generation_ids(external)
    assert path.read_bytes() == original
    resumed = api.execute(external, client=client)
    assert len(resumed["usage"]) == len(client.messages.calls) == 4
    assert any(candidate.read_bytes() == original for candidate in
               path.parent.glob(f"{external.project}_snapshot_index.previous-*.json"))


def test_fresh_restart_does_not_accept_unrelated_archived_attempts(external):
    first = FakeClient()
    first.messages.fail_on = "audit"
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(external, client=first)
    path = snapshot_store.index_path(external.metadata_dir, external.project)
    unrelated = json.loads(path.read_text())
    unrelated["generation_id"] = "unrelated-unaccounted-generation"
    archive = path.with_name(f"{path.stem}.previous-unrelated.json")
    archive.write_text(json.dumps(unrelated))
    prior = archive.read_bytes()
    ledger.ledger_path(external).unlink()
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="unaccounted attempt"):
        api.execute(external, resume=False, client=client)
    assert client.messages.calls == []
    assert unrelated["generation_id"] not in ledger.prior_generation_ids(external)
    assert archive.read_bytes() == prior
