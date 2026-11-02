"""D68: historical orphan attempts are evidence, never in-place restarts."""
import pytest
from tests.test_d68_legacy_readonly import test_authentic_legacy_refuses_without_calls_or_tree_changes as _refuse


@pytest.mark.parametrize("state", ["missing", "malformed"])
def test_fresh_restart_records_an_orphaned_partial_predecessor(tmp_path, state):
    _refuse("c3" if state == "missing" else "c2", "execute", False, tmp_path)


def test_legacy_predecessor_refuses_before_index_activation(tmp_path):
    # C4 call 3: a prepared pre-D41 ledger, without a journal.
    _refuse("c4", "execute", True, tmp_path)


def test_guarded_predecessor_survives_interrupted_index_activation(tmp_path, monkeypatch):
    from data_sheets_schema import api_runner as api, usage_ledger as ledger, snapshot_store
    from tests.test_download.test_api_runner import FakeClient, spec
    selected = spec(out_dir=tmp_path)
    first = FakeClient()
    first.messages.fail_on = "audit"
    with pytest.raises(RuntimeError, match="boom"):
        api.execute(selected, client=first)
    predecessor = ledger.generation_id(selected)
    index = snapshot_store.index_path(selected.metadata_dir, selected.project)
    original = index.read_bytes()
    client = FakeClient()
    with monkeypatch.context() as interruption:
        interruption.setattr(snapshot_store, "_write", lambda *a: (_ for _ in ()).throw(
            OSError("injected index publication failure")))
        with pytest.raises(OSError, match="index publication failure"):
            api.execute(selected, resume=False, client=client)
    assert client.messages.calls == []
    assert index.read_bytes() == original
    assert predecessor in ledger.prior_generation_ids(selected)
    result = api.execute(selected, client=client)
    assert len(result["usage"]) == len(client.messages.calls) == 4
    assert any(p.read_bytes() == original for p in index.parent.glob("*_snapshot_index.previous-*.json"))


pytestmark = pytest.mark.usefixtures("journal_launch_monitor")


def test_fresh_restart_does_not_accept_unrelated_archived_attempts(tmp_path):
    # C1 now asserts every file and directory, including sidecar lock files.
    _refuse("c1", "execute", False, tmp_path)
