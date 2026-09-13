"""Resume keeps one instrument and completes only its recorded initialization."""
from dataclasses import replace
import json

import pytest

from data_sheets_schema import api_runner as api, snapshot_store, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline, snapshot  # noqa: F401


@pytest.mark.parametrize("completed", [False, True])
@pytest.mark.parametrize("change", ["renderer", "instruction"])
def test_resume_refuses_a_changed_instrument_before_spending_or_writing(external, monkeypatch, completed, change):
    original = replace(external, render_version=2)
    first = FakeClient()
    if completed:
        api.execute(original, client=first)
    else:
        first.messages.fail_on = "audit"
        with pytest.raises(RuntimeError, match="boom"):
            api.execute(original, client=first)
    before = snapshot(external.out_dir)
    if change == "renderer":
        resumed = replace(original, render_version=3)
    else:
        render = api.resolve_prompt
        monkeypatch.setattr(api, "resolve_prompt", lambda spec: render(spec) + "\nChanged instruction.\n")
        resumed = replace(original)
    second = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="input identity changed"):
        api.execute(resumed, client=second)
    assert second.messages.calls == []
    assert snapshot(external.out_dir) == before


def test_portable_record_refuses_changed_instruction_without_a_ledger(external):
    api.execute(replace(external, render_version=2), client=FakeClient())
    ledger.ledger_path(external).unlink()
    before = snapshot(external.out_dir)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="instruction identity changed"):
        api.execute(replace(external, render_version=3), client=client)
    assert client.messages.calls == []
    assert snapshot(external.out_dir) == before


@pytest.mark.parametrize("damage", [None, "changed", "removed"])
def test_label_switch_recovers_only_the_recorded_predecessor(external, monkeypatch, damage):
    api.execute(external, client=FakeClient())
    index = snapshot_store.index_path(external.metadata_dir, external.project)
    original = index.read_bytes()
    old_generation = ledger.generation_id(external)
    new = replace(external, label="another-label")
    client = FakeClient()
    with monkeypatch.context() as failing:
        def refuse(*args, **kwargs):
            raise OSError("injected snapshot activation failure")
        failing.setattr(snapshot_store, "_write", refuse)
        with pytest.raises(OSError, match="activation failure"):
            api.execute(new, client=client)
    assert client.messages.calls == []
    assert old_generation not in ledger.prior_generation_ids(new)
    assert index.read_bytes() == original
    if damage == "changed":
        index.write_bytes(original + b"\n")
    elif damage == "removed":
        index.unlink()
    before = snapshot(external.out_dir)
    if damage:
        with pytest.raises(ledger.UsageLedgerError, match="snapshot predecessor changed"):
            api.execute(new, client=client)
        assert client.messages.calls == []
        assert snapshot(external.out_dir) == before
    else:
        result = api.execute(new, client=client)
        assert len(result["usage"]) == len(client.messages.calls) == 4
        assert "pending_snapshot_activation" not in json.loads(ledger.ledger_path(new).read_text())
        archives = list(index.parent.glob(f"{index.stem}.previous-*.json"))
        assert sum(path.read_bytes() == original for path in archives) == 1
        repeat = FakeClient()
        assert api.execute(new, client=repeat)["already_complete"]
        assert repeat.messages.calls == []


def test_activation_recovers_after_index_publication_before_ledger_ack(external, monkeypatch):
    api.execute(external, client=FakeClient())
    new = replace(external, label="another-label")
    write = ledger._write
    with monkeypatch.context() as failing:
        def interrupted(spec, data):
            if spec.label == new.label and "pending_snapshot_activation" not in data:
                raise OSError("injected activation acknowledgement failure")
            return write(spec, data)
        failing.setattr(ledger, "_write", interrupted)
        with pytest.raises(OSError, match="acknowledgement failure"):
            api.execute(new, client=FakeClient())
    client = FakeClient()
    result = api.execute(new, client=client)
    assert len(result["usage"]) == len(client.messages.calls) == 4
