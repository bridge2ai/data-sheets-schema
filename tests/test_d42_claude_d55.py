# Preserved D42 fixture, adapted for D55/D56/D57 on 2026-10-28.
# Original SHA256: 7ec301d4e9a812f3f3e5f71c3703ca1994af3eb9b253de8e3d9fe0c5f40a5efa
"""D42 independent tamper fixtures (claude reviewer, 2026-10-27).

Offline only: scripted fake clients, no provider. The same file is copied
byte-identically into each candidate tree. Each scenario first runs the real
runner to the incident's pre-edit state, applies the edit an operator made,
then resumes with a fresh scripted client and records whether the run was
refused and how many fake dispatches (and token counts) it made first.

Outcomes go to the JSON-lines file named by D42_RESULTS. Assertions state the
D41 requirement, so a candidate that misses it fails the test.
"""
from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
from types import SimpleNamespace

import httpx
import pytest
import yaml

from data_sheets_schema import api_runner as api, snapshot_store, usage_ledger as ledger
from data_sheets_schema import receipt_completion as rc, typed_audit_runtime as runtime
from tests.test_download.test_api_runner import FakeMessages, FakeResponse, spec as plain_spec
from tests.test_evidence_generation_gate import specification
from tests.test_shared_generation_selection import registration_for, selected_spec
from tests.test_shared_generation_runtime import Script

TREE = os.environ.get("D42_TREE", "?")
HAS_JOURNAL = importlib.util.find_spec("data_sheets_schema.latch_journal") is not None


def record(name, **fields):
    path = os.environ.get("D42_RESULTS")
    for key in ("detail", "resume_detail", "fresh_detail", "first_refusal"):
        if isinstance(fields.get(key), str) and len(fields[key]) > 400:
            fields[key] = fields[key][:400] + "..."
    if path:
        with open(path, "a", encoding="utf-8") as out:
            out.write(json.dumps({"tree": TREE, "scenario": name, **fields}, sort_keys=True, default=str) + "\n")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.setattr(api, "provider_identity", lambda: {"provider": None, "base_url": None, "key_env": None})
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)
    monkeypatch.setattr(api, "BACKOFF_BASE_SECONDS", 0)
    assert Path(api.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[1])


@pytest.fixture
def selected(tmp_path):
    base = specification(tmp_path)
    return selected_spec(base, registration_for(base))


def scripted(messages):
    result = SimpleNamespace(messages=messages, base_url="https://example.invalid", max_retries=2)
    result.with_options = lambda **options: SimpleNamespace(messages=messages,
        base_url=result.base_url, max_retries=options["max_retries"])
    return result


def resume(spec, messages):
    """Resume with a fresh client; return (outcome, detail, dispatches, counts)."""
    client = scripted(messages)
    try:
        result = api.execute(replace(spec), client=client)
    except Exception as exc:                         # noqa: BLE001 - the outcome is the data
        return "refused", f"{type(exc).__name__}: {exc}", len(messages.calls), \
            len(getattr(messages, "count_calls", []))
    return ("completed" if not result.get("already_complete") else "already_complete"), \
        None, len(messages.calls), len(getattr(messages, "count_calls", []))


def read_ledger(spec):
    return json.loads(ledger.ledger_path(spec).read_bytes())


def write_ledger(spec, data):
    # The operator's edit_file rewrote the JSON in place; formatting is immaterial.
    ledger.ledger_path(spec).write_text(json.dumps(data, indent=2) + "\n")


def index_file(spec):
    return snapshot_store.index_path(spec.metadata_dir, spec.project)


def edit_index(spec, mutate):
    path = index_file(spec)
    data = json.loads(path.read_bytes())
    mutate(data)
    path.write_text(json.dumps(data, indent=2) + "\n")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# --------------------------------------------------------------------------
# Scripted deliveries for the incidents
# --------------------------------------------------------------------------

class TimeoutScript(Script):
    """The named phase is dispatched, then the read times out (10-22a)."""
    def __init__(self, spec, *, timeout_phase=None, **kwargs):
        super().__init__(spec, **kwargs)
        self.timeout_phase = timeout_phase

    def create(self, **kwargs):
        result = super().create(**kwargs)
        if self.phases[-1] == self.timeout_phase:
            raise httpx.ReadTimeout("scripted ReadTimeout after dispatch")
        return result


class BadIntegrationScript(Script):
    """Integration answer that fails acceptance (10-20a, before edit 3)."""
    correct = None

    def create(self, **kwargs):
        result = super().create(**kwargs)
        if self.phases[-1] == runtime.INTEGRATION_PHASE:
            value = json.loads(result.content[0].text)
            BadIntegrationScript.correct = value["proposal_index_sha256"]
            value["proposal_index_sha256"] = "0" * 64
            result.content[0].text = json.dumps(value)
        return result


class ContractReportScript(Script):
    """Report whose final source review declares a status that does not
    support its claim (10-20a's four source_review_contract findings)."""
    def create(self, **kwargs):
        result = super().create(**kwargs)
        if self.phases[-1] == "report":
            result.content[0].text = flip_status(result.content[0].text, "planned")
        return result


def flip_status(text, status):
    head, rest = text.split("```json\n", 1)
    body, tail = rest.split("\n```", 1)
    payload = json.loads(body)
    claim = next(row["claims"][0] for row in payload["source_review"]["values"] if "claims" in row)
    claim["source_status"] = status
    return head + "```json\n" + json.dumps(payload) + "\n```" + tail


def fail_first(spec, script):
    try:
        api.execute(spec, client=scripted(script))
    except Exception as exc:                         # noqa: BLE001
        return f"{type(exc).__name__}: {str(exc)[:200]}"
    raise AssertionError("the scripted incident did not stop the run")


# --------------------------------------------------------------------------
# (a) 10-22a: typed audit failed terminally on ReadTimeout; ledger reset
# --------------------------------------------------------------------------

def run_to_10_22a(selected):
    stop = fail_first(selected, TimeoutScript(selected, timeout_phase=runtime.INTEGRATION_PHASE))
    data = read_ledger(selected)
    ta = data["typed_audit"]
    assert ta["state"] == "failed" and ta["failure_type"] == "ReadTimeout", (stop, ta.get("state"))
    assert ta["stages"][-1]["state"] == "admitted" and ta["stages"][-1].get("usage_id")
    abandoned = ledger.abandoned_journal_path(selected).read_text().splitlines()
    assert any(json.loads(line)["phase"] == runtime.INTEGRATION_PHASE for line in abandoned)
    return stop


def edit_10_22a(selected, *, thorough=False):
    data = read_ledger(selected)
    ta = data["typed_audit"]
    ta["state"] = "running"
    ta.pop("failure_type", None)
    ta.pop("failure_detail", None)
    stage = ta["stages"][-1]
    stage["state"] = "prepared"
    stage.pop("usage_id", None)
    write_ledger(selected, data)
    if thorough:
        # Beyond the incident: also remove the corroborating traces B reads.
        path = ledger.abandoned_journal_path(selected)
        kept = [line for line in path.read_text().splitlines()
                if json.loads(line)["phase"] != runtime.INTEGRATION_PHASE]
        path.write_text("".join(line + "\n" for line in kept))
        edit_index(selected, lambda d: d.__setitem__("snapshots", [
            e for e in d["snapshots"] if "_incomplete_attempt" not in e["name"]]))


def test_a_untampered_10_22a_failure_stays_refused(selected):
    run_to_10_22a(selected)
    outcome = resume(selected, Script(selected))
    record("a0_untampered_failed_typed_audit", outcome=outcome[0], detail=outcome[1],
           dispatches=outcome[2], counts=outcome[3])
    assert outcome[0] == "refused" and outcome[2] == outcome[3] == 0


@pytest.mark.parametrize("thorough", [False, True], ids=["as_in_incident", "plus_traces_removed"])
def test_a_10_22a_ledger_reset_is_refused_before_dispatch(selected, thorough):
    run_to_10_22a(selected)
    edit_10_22a(selected, thorough=thorough)
    messages = Script(selected)
    outcome = resume(selected, messages)
    record("a_10_22a_reset" + ("_plus_traces" if thorough else ""), outcome=outcome[0],
           detail=outcome[1], dispatches=outcome[2], counts=outcome[3], phases=messages.phases)
    assert outcome[0] == "refused", outcome
    assert outcome[2] == 0 and outcome[3] == 0, outcome


# --------------------------------------------------------------------------
# (b) 10-20a edit 3: model response patched and re-pinned; failure deleted
# --------------------------------------------------------------------------

def run_to_10_20a_edit3(selected):
    stop = fail_first(selected, BadIntegrationScript(selected))
    ta = read_ledger(selected)["typed_audit"]
    assert ta["state"] == "failed" and "failure_detail" in ta, (stop, ta.get("state"), ta.get("failure_type"))
    assert ta["stages"][-1]["state"] == "response_saved"
    return stop


def edit_10_20a_edit3(selected):
    data = read_ledger(selected)
    ta = data["typed_audit"]
    pin = ta["stages"][-1]["response"]
    saved = json.loads(Path(pin["path"]).read_bytes())
    saved["text"] = saved["text"].replace("0" * 64, BadIntegrationScript.correct)
    raw = runtime.receipts.canonical(saved)
    Path(pin["path"]).write_bytes(raw)
    new = sha(raw)
    old = pin["sha256"]
    pin["sha256"] = new
    # "Re-pinned it in the snapshot index and ledger": every pin the operator
    # can see in the ledger, including a candidate's own mutable copies.
    for entry in data.get("latch_snapshots", []):
        if entry.get("sha256") == old:
            entry["sha256"] = new
    ta["state"] = "running"
    ta.pop("failure_type", None)
    ta.pop("failure_detail", None)
    write_ledger(selected, data)
    edit_index(selected, lambda d: [e.__setitem__("sha256", new) for e in d["snapshots"]
                                    if e["path"] == pin["path"]])


def test_b_10_20a_edit3_patched_repinned_response_is_refused_before_dispatch(selected):
    run_to_10_20a_edit3(selected)
    edit_10_20a_edit3(selected)
    messages = Script(selected)
    outcome = resume(selected, messages)
    record("b_10_20a_edit3", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2],
           counts=outcome[3], phases=messages.phases)
    assert outcome[0] == "refused", outcome
    assert outcome[2] == 0 and outcome[3] == 0, outcome


# --------------------------------------------------------------------------
# (c) 10-20a edit 4: admission flipped, evidence_refusal deleted
# --------------------------------------------------------------------------

def run_to_10_20a_edit4(selected):
    stop = fail_first(selected, ContractReportScript(selected))
    data = read_ledger(selected)
    assert data.get("evidence_refusal", {}).get("stage") == "report", stop
    row = next(r for r in data["rows"] if r["phase"] == "report")
    assert row["source_review_admission"]["state"] == "pending"
    return stop, row["usage_id"]


def edit_10_20a_edit4(selected, usage_id, *, progress_too=True):
    rejected = next(e for e in json.loads(index_file(selected).read_bytes())["snapshots"]
                    if e["name"] == f"{selected.project}_report_rejected_response_{usage_id}.txt")
    normalized = flip_status(Path(rejected["path"]).read_text(), "fact")   # the "4 flips"
    body = api._extract(normalized, "md")
    selected.report_path.write_text(body, encoding="utf-8")               # edit 5
    copy_path = Path(rejected["path"]).with_name(f"{selected.project}_report.md")
    copy_path.write_text(body, encoding="utf-8")
    digest = sha(body.encode())
    data = read_ledger(selected)
    row = next(r for r in data["rows"] if r["usage_id"] == usage_id)
    row["source_review_admission"] = {"state": "accepted", "response_sha256": digest}
    data.pop("evidence_refusal", None)
    write_ledger(selected, data)

    def repoint(index):
        for entry in index["snapshots"]:
            if entry["path"] == rejected["path"]:
                entry.update(name=f"{selected.project}_report.md", path=str(copy_path), sha256=digest)
    edit_index(selected, repoint)
    if progress_too:
        path = api._progress_path(selected)
        progress = json.loads(path.read_bytes())
        if "report" not in progress["completed"]:
            progress["completed"].append("report")
        path.write_text(json.dumps(progress, indent=2) + "\n")


@pytest.mark.parametrize("progress_too", [False, True], ids=["ledger_and_index", "plus_progress"])
def test_c_10_20a_edit4_admission_flip_is_refused_before_dispatch(selected, progress_too):
    _, usage_id = run_to_10_20a_edit4(selected)
    control = resume(selected, Script(selected))
    assert control[0] == "refused" and control[2] == 0, control       # untampered: terminal
    edit_10_20a_edit4(selected, usage_id, progress_too=progress_too)
    messages = Script(selected)
    outcome = resume(selected, messages)
    record("c_10_20a_edit4" + ("_plus_progress" if progress_too else ""), outcome=outcome[0],
           detail=outcome[1], dispatches=outcome[2], counts=outcome[3], phases=messages.phases)
    assert outcome[0] == "refused", outcome
    assert outcome[2] == 0 and outcome[3] == 0, outcome


# --------------------------------------------------------------------------
# (d) journal truncated or edited (candidate A only; B has no journal)
# --------------------------------------------------------------------------

def journal(spec):
    return spec.metadata_dir / f"{spec.project}_latch_journal.jsonl"


@pytest.mark.parametrize("edit", ["truncate_last_line", "truncate_mid_line", "edit_payload",
                                  "delete_journal", "delete_journal_and_checkpoint"])
def test_d_journal_truncated_or_edited_is_refused(selected, edit):
    if not HAS_JOURNAL:
        record("d_" + edit, outcome="not_applicable", detail="no latch journal in this candidate")
        pytest.fail("candidate has no latch journal (spec item 1 missing)")
    run_to_10_22a(selected)          # untampered failure: the journal holds terminal latches
    path = journal(selected)
    lines = path.read_bytes().splitlines(keepends=True)
    if edit == "truncate_last_line":
        path.write_bytes(b"".join(lines[:-1]))
    elif edit == "truncate_mid_line":
        path.write_bytes(b"".join(lines[:-1]) + lines[-1][: len(lines[-1]) // 2])
    elif edit == "edit_payload":
        event = json.loads(lines[-2])
        event["payload"]["value"] = "edited"
        lines[-2] = json.dumps(event, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        path.write_bytes(b"".join(lines))
    elif edit == "delete_journal":
        path.unlink()
    else:
        path.unlink()
        data = read_ledger(selected)
        data.pop("latch_journal", None)
        data.pop("latch_overrides", None)
        write_ledger(selected, data)
    edit_10_22a(selected)
    messages = Script(selected)
    outcome = resume(selected, messages)
    record("d_" + edit, outcome=outcome[0], detail=outcome[1], dispatches=outcome[2], counts=outcome[3])
    assert outcome[0] == "refused" and outcome[2] == outcome[3] == 0, outcome


def rechain(spec, mutate_events):
    """Forge: rewrite events, recompute every hash, move the ledger checkpoint."""
    from data_sheets_schema import latch_journal as lj
    events = [json.loads(line) for line in journal(spec).read_bytes().splitlines()]
    events = mutate_events(events)
    previous = None
    for number, event in enumerate(events, 1):
        event["line"], event["previous_sha256"] = number, previous
        body = {k: v for k, v in event.items() if k != "sha256"}
        event["sha256"] = lj._sha(lj._canonical(body))
        previous = event["sha256"]
    journal(spec).write_bytes(b"".join(lj._canonical(e) + b"\n" for e in events))
    data = read_ledger(spec)
    data["latch_journal"] = {"path": str(journal(spec)), "head_sha256": previous, "line_count": len(events)}
    write_ledger(spec, data)


def test_d_forged_rechained_journal_documented_limit(selected):
    """D57: a re-forged local chain differs from the retained launch head."""
    if not HAS_JOURNAL:
        record("d_forged_rechain", outcome="not_applicable")
        pytest.skip("no journal")
    from data_sheets_schema import latch_journal as lj
    run_to_10_22a(selected)
    edit_10_22a(selected)
    observed = lj._observations(read_ledger(selected))

    def relatch(events):
        kept = []
        for event in events:
            if event["kind"] == "latch":
                key = event["payload"]["key"]
                if key not in observed:
                    continue
                event["payload"]["value"] = observed[key]
            kept.append(event)
        return kept
    rechain(selected, relatch)
    messages = Script(selected)
    outcome = resume(selected, messages)
    record("d_forged_rechain", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2], counts=outcome[3])
    assert outcome[0] == "refused" and outcome[2] == outcome[3] == 0, outcome
    assert "expected=" in outcome[1] and "found=" in outcome[1]


# --------------------------------------------------------------------------
# (e)/(f) overrides (candidate A only; B has none)
# --------------------------------------------------------------------------

def required_events(message):
    found = re.search(r"required event_sha256s=([0-9a-f,]+)", message or "")
    return found.group(1).split(",") if found else None


def write_override(spec, events, *, generation=None):
    data = read_ledger(spec)
    value = {"format": "d4d_latch_override_v1", "identity": data["identity"],
             "generation_id": generation or data["generation_id"], "event_sha256s": events,
             "authorization": "D42 fixture: owner authorized continuing after the named edit",
             "authorized_by": "fixture owner", "authorized_at": "2026-10-27T12:00:00-07:00"}
    (spec.metadata_dir / f"{spec.project}_latch_override.json").write_text(json.dumps(value))


def test_e_valid_override_on_the_10_22a_edit(selected):
    if not HAS_JOURNAL:
        record("e_override_10_22a", outcome="not_applicable", detail="no override mechanism")
        pytest.fail("candidate has no override mechanism (spec item 3 missing)")
    run_to_10_22a(selected)
    edit_10_22a(selected)
    first = resume(selected, Script(selected))
    events = required_events(first[1])
    assert events, first
    write_override(selected, events)
    messages = Script(selected)
    outcome = resume(selected, messages)
    data = read_ledger(selected)
    record("e_override_10_22a", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2],
           counts=outcome[3], override_recorded=bool(data.get("latch_overrides")))
    # D56: a terminal override is ineffective and must remain unrecorded.
    assert outcome[0] == "refused" and outcome[2] == outcome[3] == 0, outcome
    assert not data.get("latch_overrides")


class FailAudit(FakeMessages):
    """Non-shared run: the audit phase fails without delivery, first client only."""
    def __init__(self, fail=True):
        super().__init__(fail_on="audit" if fail else None, exc=RuntimeError("scripted audit failure"))


def plain_client(messages):
    return SimpleNamespace(messages=messages)


def plain_resume(spec, messages):
    try:
        result = api.execute(replace(spec), client=plain_client(messages))
    except Exception as exc:                     # noqa: BLE001
        return "refused", f"{type(exc).__name__}: {exc}", len(messages.calls), None
    return "completed", None, len(messages.calls), result


def plain_run_with_patched_snapshot(tmp_path):
    spec = plain_spec(out_dir=tmp_path / "out")
    try:
        api.execute(spec, client=plain_client(FailAudit()))
    except Exception:                              # noqa: BLE001
        pass
    entries = [e for e in json.loads(index_file(spec).read_bytes())["snapshots"] if e.get("usage_id")]
    assert entries, "no usage-bound snapshot after the full phase"
    target = entries[0]
    path = Path(target["path"])
    path.write_text(path.read_text() + "\n# operator edit\n")
    new = sha(path.read_bytes())
    data = read_ledger(spec)
    for entry in data.get("latch_snapshots", []):
        if entry["path"] == target["path"]:
            entry["sha256"] = new
    write_ledger(spec, data)
    edit_index(spec, lambda d: [e.__setitem__("sha256", new) for e in d["snapshots"]
                                if e["path"] == target["path"]])
    # As 10-20a edit 6 did: re-pin the progress file's copy too.
    progress_path = api._progress_path(spec)
    if progress_path.exists():
        progress = json.loads(progress_path.read_bytes())
        for entry in progress.get("intermediates", []):
            if entry.get("path") == target["path"]:
                entry["sha256"] = new
        progress_path.write_text(json.dumps(progress, indent=2) + "\n")
    return spec, target


def test_e_valid_override_on_a_patched_saved_response(tmp_path):
    if not HAS_JOURNAL:
        record("e_override_patched_response", outcome="not_applicable")
        pytest.fail("candidate has no override mechanism (spec item 3 missing)")
    spec, target = plain_run_with_patched_snapshot(tmp_path)
    first = plain_resume(spec, FailAudit(fail=False))
    assert first[0] == "refused" and first[2] == 0, first
    events = required_events(first[1])
    write_override(spec, events)
    outcome = plain_resume(spec, FailAudit(fail=False))
    prov = yaml.safe_load(spec.provenance_path.read_text()) if spec.provenance_path.exists() else {}
    integrity = (prov.get("model") or {}).get("runtime_integrity")
    record("e_override_patched_response", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2],
           first_refusal=first[1][:200], integrity=integrity)
    assert outcome[0] == "completed", outcome
    assert integrity["assisted"] is True and integrity["evidence_only"] is True
    assert integrity["overrides"] and integrity["overrides"][0]["acknowledgement"]["authorized_by"] == "fixture owner"


@pytest.mark.parametrize("wrong", ["other_event", "extra_event", "wrong_generation"])
def test_f_override_naming_the_wrong_lines_is_refused(tmp_path, wrong):
    if not HAS_JOURNAL:
        record("f_override_" + wrong, outcome="not_applicable")
        pytest.fail("candidate has no override mechanism (spec item 3 missing)")
    spec, _ = plain_run_with_patched_snapshot(tmp_path)
    first = plain_resume(spec, FailAudit(fail=False))
    events = required_events(first[1])
    others = [json.loads(line)["sha256"] for line in journal(spec).read_bytes().splitlines()]
    other = next(e for e in others if e not in events)
    if wrong == "other_event":
        write_override(spec, [other])
    elif wrong == "extra_event":
        write_override(spec, [*events, other])
    else:
        write_override(spec, events, generation="f" * 32)
    messages = FailAudit(fail=False)
    outcome = plain_resume(spec, messages)
    record("f_override_" + wrong, outcome=outcome[0], detail=outcome[1], dispatches=outcome[2])
    assert outcome[0] == "refused" and outcome[2] == 0, outcome


# --------------------------------------------------------------------------
# (g) permitted transport retry; resume after one
# --------------------------------------------------------------------------

class TransientOnce(FakeMessages):
    def __init__(self, phase="full", then_fail=None):
        super().__init__()
        self.phase, self.then_fail, self.raised = phase, then_fail, False

    def create(self, **kw):
        result = super().create(**kw)
        blob = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        phase = next((ph for ph, instr in api.PHASE_INSTRUCTIONS.items() if instr in blob), None)
        if phase == self.phase and not self.raised:
            self.raised = True
            raise httpx.ReadTimeout("scripted transient read timeout")
        if phase == self.then_fail:
            raise RuntimeError("scripted later failure")
        return result


def test_g_permitted_transport_retry_is_not_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 3)
    spec = plain_spec(out_dir=tmp_path / "out")
    messages = TransientOnce()
    outcome = plain_resume(spec, messages)
    abandoned = ledger.abandoned_journal_path(spec)
    record("g_permitted_retry", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2],
           abandoned_rows=len(abandoned.read_text().splitlines()) if abandoned.exists() else 0)
    assert outcome[0] == "completed" and outcome[2] == 5, outcome


def test_g_resume_after_a_permitted_retry_is_not_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 3)
    spec = plain_spec(out_dir=tmp_path / "out")
    first = plain_resume(spec, TransientOnce(then_fail="audit"))
    assert first[0] == "refused" and "scripted later failure" in first[1], first
    outcome = plain_resume(spec, FakeMessages())
    record("g_resume_after_retry", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2])
    assert outcome[0] == "completed" and outcome[2] == 3, outcome


def test_g_shared_full_phase_retry_then_interrupted_resume(selected, monkeypatch):
    """A permitted retry on a shared run's full phase, then an interruption
    after a durable typed worker response (the runner's own recoverable case)."""
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 2)

    class FullRetry(Script):
        raised = False

        def create(self, **kwargs):
            result = super().create(**kwargs)
            if self.phases[-1] == "full" and not FullRetry.raised:
                FullRetry.raised = True
                raise httpx.ReadTimeout("scripted transient read timeout")
            return result
    original_append = api._append_usage
    interrupted = []

    def append(spec, usage, row):
        if row["phase"] == runtime.WORKER_PHASE and not interrupted:
            interrupted.append(row["usage_id"])
            raise OSError("simulated interruption after durable complete response")
        return original_append(spec, usage, row)
    monkeypatch.setattr(api, "_append_usage", append)
    first_messages = FullRetry(selected)
    with pytest.raises(OSError, match="durable complete response"):
        api.execute(selected, client=scripted(first_messages))
    monkeypatch.setattr(api, "_append_usage", original_append)
    messages = Script(selected)
    outcome = resume(selected, messages)
    again = Script(selected)
    rerun = resume(selected, again)
    record("g_shared_retry_then_resume", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2],
           counts=outcome[3], first_phases=first_messages.phases, phases=messages.phases,
           rerun=rerun[0], rerun_detail=rerun[1], rerun_dispatches=rerun[2])
    assert outcome[0] == "completed", outcome
    assert messages.phases.count(runtime.WORKER_PHASE) == 0
    assert rerun[0] == "already_complete" and rerun[2] == 0, rerun


# --------------------------------------------------------------------------
# (h) normal completion pins the journal in provenance
# --------------------------------------------------------------------------

def test_h_normal_completion_pins_the_journal(selected):
    messages = Script(selected)
    result = api.execute(selected, client=scripted(messages))
    prov = yaml.safe_load(selected.provenance_path.read_text())
    integrity = (prov.get("model") or {}).get("runtime_integrity")
    pinned = integrity and integrity.get("journal")
    actual = sha(journal(selected).read_bytes()) if journal(selected).exists() else None
    again = Script(selected)
    rerun = resume(selected, again)
    record("h_normal_completion", outcome="completed", phases=messages.phases,
           validation_problems=result["validation_problems"], integrity=integrity,
           journal_sha_matches=bool(pinned) and pinned["sha256"] == actual,
           rerun=rerun[0], rerun_dispatches=rerun[2])
    assert result["validation_problems"] == []
    assert rerun[0] == "already_complete" and rerun[2] == 0
    assert pinned and pinned["sha256"] == actual and integrity["verified"] and not integrity["assisted"]


def test_h_first_regate_is_not_refused(selected):
    messages = Script(selected, bad_report=True)
    try:
        result = api.execute(selected, client=scripted(messages))
        outcome, detail = "completed", None
    except Exception as exc:                         # noqa: BLE001
        outcome, detail = "refused", f"{type(exc).__name__}: {str(exc)[:200]}"
    record("h_first_regate", outcome=outcome, detail=detail, phases=messages.phases)
    assert outcome == "completed" and messages.phases[-1] == "report_regate"


# --------------------------------------------------------------------------
# False positives: a crash between the journal append and the ledger write
# --------------------------------------------------------------------------

def test_fp_crash_between_journal_append_and_ledger_write(tmp_path, monkeypatch):
    if not HAS_JOURNAL:
        record("fp_crash_window", outcome="not_applicable")
        pytest.skip("no journal")
    spec = plain_spec(out_dir=tmp_path / "out")
    original = ledger._write_unlatched
    fired = []

    def crash(s, data):
        if (data.get("pending_call") or {}).get("phase") == "audit" and not fired:
            fired.append(True)
            raise KeyboardInterrupt("SIGINT after the journal append, before the ledger replace")
        return original(s, data)
    monkeypatch.setattr(ledger, "_write_unlatched", crash)
    with pytest.raises(KeyboardInterrupt):
        api.execute(spec, client=plain_client(FakeMessages()))
    monkeypatch.setattr(ledger, "_write_unlatched", original)
    refused = plain_resume(spec, FakeMessages())
    assert refused[0] == "refused" and refused[2] == 0, refused
    events = required_events(refused[1])
    assert events, refused
    write_override(spec, events)
    resumed = plain_resume(spec, FakeMessages())
    record("fp_crash_window", resume=resumed[0], resume_detail=resumed[1],
           resume_dispatches=resumed[2], acknowledgement_required=True)
    assert resumed[0] == "completed", resumed
    assert resumed[3]["usage"]
    prov = yaml.safe_load(spec.provenance_path.read_text())
    assert prov["model"]["runtime_integrity"]["assisted"] is True


# D57: independent test launch monitor retains heads at durable appends.
pytestmark = pytest.mark.usefixtures("journal_launch_monitor")
