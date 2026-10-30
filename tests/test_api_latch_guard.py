"""D41/#5138/#5142 causal controller and eligibility checks, 2026-10-26.

All clients are local fakes. No provider, scientific approval or launch.
"""
from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx
import pytest
import yaml

from data_sheets_schema import api_runner as api, canary, latch_journal, snapshot_store, usage_ledger as ledger
from tests.test_download.test_api_runner import spec
from tests.test_canary_gate import GOOD


def clean_integrity():
    return {"format": "d4d_latch_guard_v1", "verified": True, "assisted": False,
            "evidence_only": False, "overrides": [],
            "journal": {"path": "CHORUS_latch_journal.jsonl", "sha256": "a" * 64,
                        "head_sha256": "b" * 64, "line_count": 1},
            "authentication": "not_cryptographically_authenticated"}


class Transport:
    def __init__(self, transient=False, text="ok", stop_reason="end_turn"):
        self.calls = []
        self.transient = transient
        self.text = text
        self.stop_reason = stop_reason

    @contextmanager
    def stream(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        if self.transient and len(self.calls) == 1:
            raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://offline.invalid"))
        response = SimpleNamespace(content=[SimpleNamespace(type="text", text=self.text)],
            stop_reason=self.stop_reason, usage=SimpleNamespace(input_tokens=3, output_tokens=2))
        yield SimpleNamespace(get_final_message=lambda: response)


def retry(transport, check, sleep=lambda _: None):
    return api._call_with_retry(SimpleNamespace(messages=transport),
        model="claude-opus-5", max_tokens=100, temperature=None,
        system="offline fixture", messages=[{"role": "user", "content": "fixture"}],
        transport_attempts=2, wall_clock=5, sleep=sleep, before_attempt=check)


def test_retry_rechecks_edited_history_before_second_physical_dispatch(tmp_path):
    selected = spec(out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=False)
    ledger.record_report_rejection(selected, stage="fixture", report_sha256="c" * 64,
                                   reading={"checked": True, "findings": ["synthetic rejection"]})
    transport = Transport(transient=True)

    def edit_after_transport_failure(_):
        path = ledger.ledger_path(selected)
        data = json.loads(path.read_bytes())
        data.pop("report_rejections")
        path.write_text(json.dumps(data))

    with pytest.raises(ledger.UsageLedgerError):
        retry(transport, lambda: latch_journal.check(selected), sleep=edit_after_transport_failure)
    assert len(transport.calls) == 1


def test_permitted_transport_retry_and_wire_are_unchanged(tmp_path):
    selected = spec(out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=False)
    transport = Transport(transient=True)
    observations = []

    def check():
        observations.append(latch_journal.check(selected))

    assert retry(transport, check).stop_reason == "end_turn"
    assert len(observations) == len(transport.calls) == 2
    assert transport.calls[0] == transport.calls[1]
    assert "before_attempt" not in transport.calls[0]


REPAIR_RECORD = "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [original]\n"


def repair_fixture(tmp_path, monkeypatch, *, text=None, stop_reason="end_turn"):
    selected = spec(out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=False)
    selected.full_path.write_text(REPAIR_RECORD)
    monkeypatch.setattr(api, "REPAIR_ROUNDS", 1)
    monkeypatch.setattr(api, "_validator_lines", lambda *a: (["synthetic shape finding"], None))
    transport = Transport(text=text if text is not None else
        "```yaml\n" + REPAIR_RECORD.replace("original", "repaired") + "```\n", stop_reason=stop_reason)
    return selected, transport, {"name": "claude-opus-5", "temperature": 0.0}


def pinned_entries(selected, usage_id):
    entries = [entry for entry in snapshot_store.entries(selected) if entry.get("usage_id") == usage_id]
    pins = ledger._read(selected)["latch_snapshots"]
    for entry in entries:
        pin = next(pin for pin in pins if pin["path"] == entry["path"])
        assert pin["usage_id"] == usage_id
        assert pin["sha256"] == entry["sha256"] == hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest()
    return entries


def test_repair_raw_delivery_and_applied_snapshot_share_actual_usage_id(tmp_path, monkeypatch):
    selected, transport, settings = repair_fixture(tmp_path, monkeypatch)
    usage = []
    log = api._repair_invalid(selected, SimpleNamespace(messages=transport), settings, usage)
    assert len(transport.calls) == len(usage) == 1
    assert log[0]["outcome"] == "applied"
    row = usage[0]
    entries = pinned_entries(selected, row["usage_id"])
    assert {entry["phase"] for entry in entries} == {
        f"{selected.project}_repair_full_response_{row['usage_id']}.txt",
        f"{selected.project}_repair_full_r1.yaml"}
    raw = next(entry for entry in entries if entry["phase"].endswith(".txt"))
    assert Path(raw["path"]).read_text() == transport.text
    assert "repaired" in selected.full_path.read_text()
    assert latch_journal.check(selected)["verified"]


@pytest.mark.parametrize("failure", ["truncated", "unusable", "reasoning"])
def test_rejected_repair_keeps_raw_delivery_before_reasoning_or_parsing(tmp_path, monkeypatch, failure):
    selected, transport, settings = repair_fixture(tmp_path, monkeypatch,
        text="delivered repair body, retained exactly",
        stop_reason="max_tokens" if failure == "truncated" else "end_turn")
    usage = []
    if failure == "reasoning":
        def fail_reasoning(*args, **kwargs):
            raise OSError("synthetic reasoning write failure")
        monkeypatch.setattr(api.reasoning, "append", fail_reasoning)
        with pytest.raises(OSError, match="synthetic reasoning write failure"):
            api._repair_invalid(selected, SimpleNamespace(messages=transport), settings, usage)
    else:
        log = api._repair_invalid(selected, SimpleNamespace(messages=transport), settings, usage)
        assert ("truncated" if failure == "truncated" else "unusable") in log[0]["outcome"]
    assert selected.full_path.read_text() == REPAIR_RECORD
    assert len(usage) == len(transport.calls) == 1
    entries = pinned_entries(selected, usage[0]["usage_id"])
    assert len(entries) == 1
    assert entries[0]["phase"].endswith(".txt")
    assert Path(entries[0]["path"]).read_text() == transport.text
    assert latch_journal.check(selected)["verified"]


@pytest.mark.parametrize("repin", [False, True])
def test_edited_repair_delivery_refuses_dispatch_even_with_rewritten_mutable_pins(tmp_path, monkeypatch, repin):
    selected, transport, settings = repair_fixture(tmp_path, monkeypatch)
    usage = []
    api._repair_invalid(selected, SimpleNamespace(messages=transport), settings, usage)
    raw = next(entry for entry in pinned_entries(selected, usage[0]["usage_id"])
               if entry["phase"].endswith(".txt"))
    journal_before = latch_journal.journal_path(selected).read_bytes()
    path = Path(raw["path"])
    path.write_text("replacement for the actual billed delivery")
    if repin:
        replacement = hashlib.sha256(path.read_bytes()).hexdigest()
        index = snapshot_store.index_path(selected.metadata_dir, selected.project)
        for filename, key in ((index, "snapshots"), (ledger.ledger_path(selected), "latch_snapshots")):
            data = json.loads(filename.read_bytes())
            next(entry for entry in data[key] if entry["path"] == str(path))["sha256"] = replacement
            filename.write_text(json.dumps(data))
    attempted = Transport()
    with pytest.raises(ledger.UsageLedgerError):
        api._call_with_usage(selected, "repair_full", 2, "fixture", SimpleNamespace(messages=attempted),
            model="claude-opus-5", max_tokens=100, temperature=None,
            system="offline fixture", messages=[{"role": "user", "content": "fixture"}])
    assert attempted.calls == []
    assert latch_journal.journal_path(selected).read_bytes() == journal_before


@pytest.mark.parametrize("edit_partial", [False, True])
def test_partial_delivery_has_one_abandoned_id_and_only_intact_retry_dispatches(tmp_path, monkeypatch, edit_partial):
    selected = spec(out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=False)
    usage, calls = [], []
    complete = SimpleNamespace(content=[SimpleNamespace(type="text", text="completed")],
        stop_reason="end_turn", usage=SimpleNamespace(input_tokens=3, output_tokens=2))

    class Cut:
        current_message_snapshot = SimpleNamespace(content=[SimpleNamespace(type="text", text="partial body")],
            usage={"input_tokens": 3, "output_tokens": 1})
        def __iter__(self):
            return iter([SimpleNamespace(type="message_start")])

    @contextmanager
    def stream(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        yield Cut() if len(calls) == 1 else SimpleNamespace(get_final_message=lambda: complete)

    original_append = api.reasoning.append
    append_checks = []

    def assert_pinned_before_abandoned_append(path, row):
        if path == api._abandoned_ledger(selected):
            entry, = pinned_entries(selected, row["usage_id"])
            assert entry["path"] == row["snapshot"]
            assert ledger._read(selected)["rows"] == []
            append_checks.append(row["usage_id"])
        return original_append(path, row)

    monkeypatch.setattr(api.reasoning, "append", assert_pinned_before_abandoned_append)
    journal_after_partial = []

    def after_partial(_):
        row, = usage
        assert "partial body" in Path(row["snapshot"]).read_text()
        journal_after_partial.append(latch_journal.journal_path(selected).read_bytes())
        if edit_partial:
            Path(row["snapshot"]).write_text("edited partial delivery")

    def call():
        return api._call_with_usage(selected, "full", 1, "fixture", SimpleNamespace(messages=SimpleNamespace(stream=stream)),
            model="claude-opus-5", max_tokens=100, temperature=None,
            system="offline fixture", messages=[{"role": "user", "content": "fixture"}],
            transport_attempts=2, wall_clock=5, sleep=after_partial,
            on_incomplete=lambda info: api._record_incomplete_stream(selected, "full", 1, "fixture", info, usage))

    if edit_partial:
        with pytest.raises(ledger.UsageLedgerError):
            call()
        assert len(calls) == 1
        assert latch_journal.journal_path(selected).read_bytes() == journal_after_partial[0]
    else:
        response, completed_id = call()
        assert response is complete
        assert len(calls) == 2 and calls[0] == calls[1]
        assert completed_id != usage[0]["usage_id"]
        assert latch_journal.check(selected)["verified"]
    row, = usage
    assert append_checks == [row["usage_id"]]
    assert api._abandoned_rows(selected) == [row]
    # The callback did not invent a completed charge or clear the enclosing
    # logical call's pending intent; its completed caller will settle that ID.
    assert ledger._read(selected)["rows"] == []
    assert ledger._read(selected)["pending_call"]["usage_id"] != row["usage_id"]


@pytest.mark.parametrize("damage", [None, "journal_deleted", "journal_usage_id_changed", "partial_edited"])
def test_unfinished_run_resumes_only_with_intact_partial_delivery_accounting(tmp_path, monkeypatch, damage):
    from data_sheets_schema import schema_sync
    selected = spec(out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=False)
    pending = ledger.begin_call(selected, "full", 1, "fixture")
    usage = []
    api._record_incomplete_stream(selected, "full", 1, "fixture", {
        "incomplete": 1, "tail": "partial response", "usage": {"output_tokens": 1}}, usage)
    ledger.cancel_call(selected, pending)
    row, = usage
    assert not selected.provenance_path.exists()
    partial = Path(row["snapshot"])
    partial_before = partial.read_bytes()
    abandoned = api._abandoned_ledger(selected)
    abandoned_before = abandoned.read_bytes()
    if damage == "journal_deleted":
        abandoned.unlink()
    elif damage == "journal_usage_id_changed":
        changed = {**row, "usage_id": "replacement-unaccounted-id"}
        abandoned.write_text(json.dumps(changed) + "\n")
    elif damage == "partial_edited":
        partial.write_text("changed partial delivery")
    reached = []

    class ReachedGeneration(Exception):
        pass

    def stop_before_generation(spec_, phase, *args, **kwargs):
        reached.append(phase)
        raise ReachedGeneration

    # This case isolates resume accounting; schema synchronization is covered
    # elsewhere. Stop after the genuine resume path, before any generation.
    monkeypatch.setattr(schema_sync, "check", lambda **kwargs: [])
    monkeypatch.setattr(api, "_generate_phase", stop_before_generation)
    transport = Transport()
    if damage is None:
        with pytest.raises(ReachedGeneration):
            api.execute(selected, client=SimpleNamespace(messages=transport))
        assert reached == ["full"]
        assert abandoned.read_bytes() == abandoned_before
        assert partial.read_bytes() == partial_before
        assert api._abandoned_rows(selected) == [row]
        assert ledger._read(selected)["rows"] == []
    else:
        with pytest.raises(ledger.UsageLedgerError):
            api.execute(selected, client=SimpleNamespace(messages=transport))
        assert reached == []
    assert transport.calls == []


def test_startup_refuses_before_schema_or_recovery(tmp_path, monkeypatch):
    from data_sheets_schema import schema_sync
    selected = spec(out_dir=tmp_path)

    def reject(_, **kwargs):
        raise ledger.UsageLedgerError("synthetic journal mismatch")

    monkeypatch.setattr(latch_journal, "check", reject)
    monkeypatch.setattr(schema_sync, "check", lambda **kw: pytest.fail("startup guard was bypassed"))
    with pytest.raises(ledger.UsageLedgerError, match="synthetic journal mismatch"):
        api._execute(selected, resume=True, client=SimpleNamespace())


def test_report_rejections_survive_worse_regeneration_without_refunding_it(tmp_path, monkeypatch):
    selected = spec(out_dir=tmp_path, render_version=8)
    ledger.prepare_usage(selected, resume=False)
    selected.report_path.write_text("original rejected report")
    readings = iter([
        {"checked": True, "disposition_rows": 1, "claims_checked": 1, "findings": [{"kind": "first"}]},
        {"checked": True, "disposition_rows": 0, "claims_checked": 1,
         "findings": [{"kind": "first"}, {"kind": "second"}]},
    ])
    monkeypatch.setattr(api, "report_claims_block", lambda *a, **kw: next(readings))
    monkeypatch.setattr(api, "report_audit_totals_block", lambda *a, **kw: {})
    monkeypatch.setattr(api, "require_source_reviews", lambda *a, **kw: None)

    def regenerate(*args, **kwargs):
        call = ledger.begin_call(selected, "report_regate", 1, "2026-10-26T00:00:00Z")
        ledger.cancel_call(selected, call)
        selected.report_path.write_text("worse rejected report")
        return True

    monkeypatch.setattr(api, "_regenerate_report", regenerate)
    result = api._gate_report(selected, None, {}, [], {})
    assert result["regenerated"] is False
    assert selected.report_path.read_text() == "original rejected report"
    data = ledger._read(selected)
    assert len(data["report_rejections"]) == 2
    assert {r["report_sha256"] for r in data["report_rejections"]} == {
        hashlib.sha256(text.encode()).hexdigest() for text in
        ("original rejected report", "worse rejected report")}
    assert ledger.report_regate_attempted(selected)
    with pytest.raises(ledger.UsageLedgerError, match="already attempted"):
        ledger.begin_call(selected, "report_regate", 1, "2026-10-26T00:00:00Z")


def record_with(block):
    return {"pair_consistency": copy.deepcopy(GOOD["pair"]),
            "report_claims": copy.deepcopy(GOOD["report"]),
            "grounding": copy.deepcopy(GOOD["grounding"]), "form": copy.deepcopy(GOOD["form"]),
            "model": {"runtime_integrity": block}}


@pytest.mark.parametrize("change", [{"assisted": True, "evidence_only": True},
    {"verified": False}, {"assisted": "false"}, {"evidence_only": True}])
def test_assisted_or_malformed_integrity_blocks_live_and_offline_canary_without_changing_quality(change):
    block = {**clean_integrity(), **change}
    offline = canary.checks_from_record(record_with(block))
    live = {**copy.deepcopy(GOOD), "runtime_integrity": block}
    counts = canary.counts_from(GOOD)
    for checks in (offline, live):
        assert canary.counts_from(checks) == counts
        verdict = canary.verdict(checks, {}, baseline_requested=False)
        assert verdict["status"] != canary.OK
        assert "runtime integrity" in verdict["blind"]


def test_clean_or_legacy_integrity_does_not_fabricate_a_new_quality_measurement():
    record = record_with(clean_integrity())
    assert canary.verdict(canary.checks_from_record(record), {}, baseline_requested=False)["status"] == canary.OK
    record.pop("model")
    assert "runtime_integrity" not in canary.checks_from_record(record)
    assert canary.verdict(canary.checks_from_record(record), {}, baseline_requested=False)["status"] != canary.OK
    record["record_generated_at"] = "2026-09-12T12:00:00Z"
    assert canary.verdict(canary.checks_from_record(record), {}, baseline_requested=False)["status"] == canary.OK


def test_assisted_record_cannot_supply_baseline_metrics(tmp_path):
    directory = tmp_path / "claudecode_api_core" / "baseline-rep1"
    directory.mkdir(parents=True)
    (directory / "CHORUS_provenance.yaml").write_text(yaml.safe_dump(record_with({
        **clean_integrity(), "assisted": True, "evidence_only": True})))
    for reader in (canary.baseline_for, canary.report_basis):
        with pytest.raises(LookupError, match="runtime integrity is ineligible"):
            reader("CHORUS", "baseline", "claudecode_api", tmp_path)


# D57: retain externally observed journal heads across fixture resumes.
pytestmark = pytest.mark.usefixtures("journal_launch_monitor")
