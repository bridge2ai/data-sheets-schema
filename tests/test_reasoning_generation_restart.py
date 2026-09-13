"""Explicit restarts preserve opaque predecessors and isolate active reasoning."""
import json

import pytest
import yaml

from data_sheets_schema import api_runner as api, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.mark.parametrize("portable", [False, True])
def test_fresh_generation_archives_malformed_predecessor_reasoning(external, portable):
    old = api.execute(external, client=FakeClient())["usage"]
    old_generation = ledger.generation_id(external)
    path = api._reasoning_path(external)
    predecessor = path.read_bytes() + b'{"unfinished":'
    path.write_bytes(predecessor)
    if portable:
        ledger.ledger_path(external).unlink()
    fresh = api.execute(external, resume=False, client=FakeClient())
    archives = list(path.parent.glob(f"{external.project}_reasoning.previous-*.jsonl"))
    assert len(archives) == 1 and archives[0].read_bytes() == predecessor
    assert {row["usage_id"] for row in old}.isdisjoint(row["usage_id"] for row in fresh["usage"])
    record = yaml.safe_load(external.provenance_path.read_text())
    assert old_generation in record["run"]["prior_generation_ids"]
    assert all(json.loads(line)["generation_id"] == ledger.generation_id(external)
               for line in path.read_text().splitlines())
    client = FakeClient()
    assert api.execute(external, client=client)["already_complete"]
    assert client.messages.calls == []
    # Corruption in the active journal is still a refusal, not an ignored gap.
    path.write_bytes(path.read_bytes() + b'{"unfinished":')
    with pytest.raises(ledger.UsageLedgerError, match="reasoning"):
        api.execute(external, client=client)
    assert client.messages.calls == []
    assert archives[0].read_bytes() == predecessor


@pytest.mark.parametrize("failure", ["rename", "finalize"])
def test_interrupted_archive_initialization_recovers_without_losing_bytes(external, monkeypatch, failure):
    api.execute(external, client=FakeClient())
    source = api._reasoning_path(external)
    predecessor = source.read_bytes() + b"\nnot JSON\n"
    source.write_bytes(predecessor)
    client = FakeClient()
    with monkeypatch.context() as failing:
        if failure == "rename":
            original = ledger.os.replace
            def rename(src, dst):
                if src == source:
                    raise OSError("injected reasoning rename failure")
                return original(src, dst)
            failing.setattr(ledger.os, "replace", rename)
        else:
            original = ledger._write
            def write(spec, data):
                if data.get("reasoning_archives") and "pending_reasoning_archive" not in data:
                    raise OSError("injected reasoning finalize failure")
                return original(spec, data)
            failing.setattr(ledger, "_write", write)
        with pytest.raises(ledger.UsageLedgerError, match="reasoning"):
            api.execute(external, resume=False, client=client)
    assert client.messages.calls == []
    interrupted = json.loads(ledger.ledger_path(external).read_text())
    assert interrupted["pending_reasoning_archive"]
    resumed = api.execute(external, client=client)
    assert len(resumed["usage"]) == len(client.messages.calls) == 4
    final = json.loads(ledger.ledger_path(external).read_text())
    assert "pending_reasoning_archive" not in final
    assert len(final["reasoning_archives"]) == 1
    archive = source.with_name(final["reasoning_archives"][0]["name"])
    assert archive.read_bytes() == predecessor
