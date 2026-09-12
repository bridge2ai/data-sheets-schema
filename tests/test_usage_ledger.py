"""Completed calls survive a process exit before final provenance (#656)."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema import api_runner as api, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient, spec


def row():
    return {"phase": "full", "attempt": 1, "started_at": "2026-09-11T00:00:00Z",
            "input_tokens": 100, "output_tokens": 20, "thinking_tokens": 5}


def test_distinct_calls_in_the_same_second_are_recovered_exactly_once(tmp_path):
    s = spec(out_dir=tmp_path)
    current = []
    first = ledger.append_usage(s, current, row())
    second = ledger.append_usage(s, current, row())
    assert first["usage_id"] != second["usage_id"]
    first.update(unusable_reason="truncated", unusable_snapshot="full-unusable.yaml")
    ledger.persist_usage(s, first)
    recovered = ledger.merge_usage(s, [])
    assert recovered == current and len(recovered) == 2
    assert ledger.merge_usage(s, recovered) == current
    # A legacy final-record row has no UUID. It is preserved, not guessed
    # to be the same call from a coarse phase/attempt/timestamp tuple.
    legacy = row()
    assert ledger.merge_usage(s, [legacy, *recovered]) == [legacy, *current]


def test_flat_output_identities_and_forced_fresh_runs_keep_accounts_separate(tmp_path):
    s = spec(out_dir=tmp_path)
    ledger.append_usage(s, [], row())
    old_bytes = ledger.ledger_path(s).read_bytes()
    for other in (replace(s, label="another_rep1"), replace(s, method="another"),
                  replace(s, condition="schema")):
        assert ledger.ledger_path(other) != ledger.ledger_path(s)
        assert ledger.merge_usage(other, []) == []
    ledger.prepare_usage(s, resume=False)
    assert not ledger.ledger_path(s).exists()
    archives = list(tmp_path.glob("*.previous-*.json"))
    assert len(archives) == 1 and archives[0].read_bytes() == old_bytes
    new = ledger.append_usage(s, [], row())
    assert ledger.merge_usage(s, []) == [new]
    assert archives[0].read_bytes() == old_bytes


def test_failed_atomic_replace_keeps_the_previous_account(tmp_path, monkeypatch):
    s = spec(out_dir=tmp_path)
    current = []
    ledger.append_usage(s, current, row())
    before = ledger.ledger_path(s).read_bytes()

    def fail(*args):
        raise OSError("disk failure")

    monkeypatch.setattr(ledger.os, "replace", fail)
    with pytest.raises(ledger.UsageLedgerError, match="disk failure"):
        ledger.append_usage(s, current, row())
    assert ledger.ledger_path(s).read_bytes() == before
    assert len(current) == 1 and not list(tmp_path.glob(".*.tmp"))


@pytest.mark.parametrize("damage", ["invalid-json", "identity", "version", "missing-id", "duplicate-id"])
def test_corrupt_accounts_fail_before_any_more_model_calls(tmp_path, damage):
    s = spec(out_dir=tmp_path)
    ledger.append_usage(s, [], row())
    path = ledger.ledger_path(s)
    data = json.loads(path.read_text())
    if damage == "identity":
        data["identity"]["label"] = "another run"
    elif damage == "version":
        data["version"] = 999
    elif damage == "missing-id":
        del data["rows"][0]["usage_id"]
    elif damage == "duplicate-id":
        data["rows"].append(data["rows"][0])
    path.write_text("{" if damage == "invalid-json" else json.dumps(data))
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError):
        api.execute(s, client=client)
    assert client.messages.calls == []


def test_usage_is_durable_before_reasoning_processing_can_fail(tmp_path, monkeypatch):
    s = spec(out_dir=tmp_path)

    def fail(*args):
        raise OSError("reasoning disk failure")

    monkeypatch.setattr(api.reasoning, "append", fail)
    client = FakeClient()
    with pytest.raises(OSError, match="reasoning disk failure"):
        api._generate_phase(s, "full", {}, client, api._model_settings(), [])
    assert len(client.messages.calls) == 1
    recovered = ledger.merge_usage(s, [])
    assert len(recovered) == 1 and recovered[0]["phase"] == "full"
    assert recovered[0]["input_tokens"] > 0


def test_ledger_failure_does_not_trigger_another_paid_attempt(tmp_path, monkeypatch):
    s = spec(out_dir=tmp_path)

    def fail(*args):
        raise OSError("disk failure")

    monkeypatch.setattr(ledger.os, "replace", fail)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="disk failure"):
        api._generate_phase(s, "full", {}, client, api._model_settings(), [])
    assert len(client.messages.calls) == 1


@pytest.mark.parametrize("phase", ["repair_full", "report_after_repair", "full_readdress"])
def test_auxiliary_calls_are_durable_before_later_processing_fails(tmp_path, monkeypatch, phase):
    s = spec(out_dir=tmp_path)
    body = "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"
    s.full_path.write_text(body)
    s.core_path.write_text(body)
    client, current, settings = FakeClient(), [], api._model_settings()

    def fail(*args):
        raise OSError("reasoning disk failure")

    monkeypatch.setattr(api.reasoning, "append", fail)
    if phase == "repair_full":
        monkeypatch.setattr(api, "_validator_lines", lambda *args: (["bad shape"], None))
        with pytest.raises(OSError, match="reasoning disk failure"):
            api._repair_invalid(s, client, settings, current)
    elif phase == "report_after_repair":
        carry = {k: body for k in api.PHASE_NEEDS["report"]}
        with pytest.raises(OSError, match="reasoning disk failure"):
            api._regenerate_report(s, client, settings, current, carry)
    else:
        from tests.test_download.test_receipt_readdress import _receipt
        receipt = yaml.safe_dump(_receipt({"slot": "unknown_slot", "snippet": "a"}))
        _, summary = api._readdress_receipt(s, api.build_phase(s, "full", carry={}), body,
                                            body, receipt, client, settings, current)
        assert summary is not None
    assert len(client.messages.calls) == 1
    recovered = ledger.merge_usage(s, [])
    assert recovered == current and len(recovered) == 1
    assert recovered[0]["phase"] == phase and recovered[0]["input_tokens"] > 0


@pytest.mark.parametrize("completed_phase", ["full", "core"])
def test_hard_exit_then_resume_preserves_completed_call_usage(tmp_path, completed_phase):
    s = spec(out_dir=tmp_path)
    root = Path(__file__).resolve().parents[1]
    code = """
import os, sys
from pathlib import Path
from data_sheets_schema import api_runner as api
from tests.test_download.test_api_runner import FakeClient, spec
save = api._save_progress
def exit_after_progress(run, completed, audit):
    save(run, completed, audit)
    if sys.argv[2] in completed:
        os._exit(23)
api._save_progress = exit_after_progress
api.execute(spec(out_dir=Path(sys.argv[1])), client=FakeClient())
"""
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)])}
    killed = subprocess.run([sys.executable, "-c", code, str(tmp_path), completed_phase],
                            cwd=root, env=environment, capture_output=True, text=True, timeout=90)
    assert killed.returncode == 23, killed.stdout + killed.stderr
    assert not s.provenance_path.exists()
    assert completed_phase in json.loads(api._progress_path(s).read_text())["completed"]
    completed = ledger.merge_usage(s, [])
    assert len(completed) == 1 and completed[0]["phase"] == "full"
    client = FakeClient()
    resumed = api.execute(s, client=client)
    assert "full" in resumed["skipped"]
    assert len(client.messages.calls) == 3
    final = yaml.safe_load(s.provenance_path.read_text())["api_usage"]
    assert final[0] == completed[0]
    assert [r["phase"] for r in final] == ["full", "audit", "reconcile_full", "report"]
    assert len({r["usage_id"] for r in final}) == 4
    assert ledger.merge_usage(s, list(final)) == final
    previous = s.provenance_path.read_bytes()
    again = api.execute(s, client=client)
    assert again["already_complete"] and again["usage"] == final
    assert len(client.messages.calls) == 3 and s.provenance_path.read_bytes() == previous


def test_explicit_fresh_execution_does_not_import_previous_usage(tmp_path):
    s = spec(out_dir=tmp_path)
    old = api.execute(s, client=FakeClient())["usage"]
    # Even a stale progress file must not defeat an explicit fresh request.
    api._save_progress(s, list(api.PHASES), None)
    new = api.execute(s, resume=False, client=FakeClient())["usage"]
    assert len(old) == len(new) == 4
    assert {r["usage_id"] for r in old}.isdisjoint(r["usage_id"] for r in new)
    archived = list(tmp_path.glob("*.previous-*.json"))
    assert len(archived) == 1 and json.loads(archived[0].read_text())["rows"] == old
