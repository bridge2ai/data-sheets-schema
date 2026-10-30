"""D68/D69 authentic f8 controls and stripped-current negative probes (#5212)."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import yaml

from data_sheets_schema import api_runner as api, latch_journal as journal, usage_ledger as ledger
from tests.test_download.test_api_runner import FakeClient, spec

FIXTURES = Path(__file__).parent / "fixtures/pre_d41"


def tree(root):
    # Ignore-independent whole-tree assertion, including directories and locks.
    result = {}
    for p in [root, *root.rglob("*")]:
        info = p.lstat()
        content = str(p.readlink()) if p.is_symlink() else "dir" if p.is_dir() else p.read_bytes()
        result[str(p.relative_to(root))] = (info.st_mode, info.st_size, info.st_mtime_ns,
                                          info.st_ino, content)
    return result


def fixture(case, tmp_path):
    source = FIXTURES / case
    root = tmp_path / case
    shutil.copytree(source / "before", root)
    manifest = json.loads((source / "before-manifest.json").read_text())
    assert {str(p.relative_to(root)): {"bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in root.rglob("*") if p.is_file()} == manifest
    invocation = json.loads((source / "invocation.json").read_text())
    kwargs = invocation["spec"]["kwargs"]
    old = Path(invocation["root"])
    # Only the invocation moves. The entire original before-tree is unchanged.
    for key, value in kwargs.items():
        if isinstance(value, dict) and set(value) == {"__path__"}:
            kwargs[key] = root / Path(value["__path__"]).relative_to(old)
    return root, old, api.RunSpec(**kwargs)


@pytest.mark.parametrize("case", ["i1", "i2", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"])
@pytest.mark.parametrize("entry", ["execute", "internal", "prepare", "write", "spend", "begin_call"])
@pytest.mark.parametrize("resume", [True, False])
def test_authentic_legacy_refuses_without_calls_or_tree_changes(case, entry, resume, tmp_path):
    root, _, selected = fixture(case, tmp_path)
    before = tree(root)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError):
        if entry == "execute":
            api.execute(selected, resume=resume, client=client)
        elif entry == "internal":
            api._execute(selected, resume=resume, client=client)
        elif entry == "prepare":
            ledger.prepare_usage(selected, resume=resume)
        elif entry == "write":
            ledger._write(selected, ledger._empty(selected, accept_legacy=resume))
        elif entry == "begin_call":
            ledger.begin_call(selected, "report_regate", 1, "2026-10-30T00:00:00Z")
        else:
            journal.check(selected, spending=True)
    assert client.messages.calls == []
    assert tree(root) == before


@pytest.mark.parametrize("case", ["i1", "c7"])
def test_completed_legacy_verifier_is_readonly(case, tmp_path, monkeypatch):
    root, old, selected = fixture(case, tmp_path)
    before = tree(root)
    def forbidden(*args, **kwargs):
        pytest.fail("verifier reached execution or mutation")
    for owner, names in ((api, ["execute", "_execute", "_client"]),
                         (ledger, ["prepare_usage", "_write", "_write_unlatched"]),
                         (journal, ["_append"])):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    result = journal.verify_completed_legacy(selected.provenance_path,
                    evidence_root=root, recorded_root=old)
    assert result["already_complete"] and result["evidence_only"]
    assert result["legacy_unverifiable"] and not result["campaign_eligible"]
    assert result["new_calls"] == 0 and result["accounting_completeness"] == "unknown"
    assert len(result["observed_usage"]) == 4
    assert tree(root) == before


@pytest.mark.parametrize("damage", ["output", "report", "instruction", "age", "accounting", "progress", "symlink", "ledger-input", "index-input"])
def test_verifier_rejects_incomplete_or_changed_evidence(tmp_path, damage):
    root, old, selected = fixture("i1", tmp_path)
    record = yaml.safe_load(selected.provenance_path.read_text())
    if damage == "output":
        selected.full_path.write_text("changed")
    elif damage == "report":
        selected.report_path.write_text("changed")
    elif damage == "progress":
        (selected.metadata_dir / f"{selected.project}_api_progress.json").write_text("{}")
    elif damage == "symlink":
        (root / "escape").symlink_to("/etc/passwd")
    elif damage in ("ledger-input", "index-input"):
        target = ledger.ledger_path(selected) if damage == "ledger-input" else next(root.rglob("*_snapshot_index.json"))
        data = json.loads(target.read_text())
        data["input_identity"]["instruction"]["sha256"] = "0" * 64
        target.write_text(json.dumps(data))
    else:
        if damage == "age":
            record["repo"]["commit"] = journal.D41_COMMIT
        elif damage == "instruction":
            record["prompts"]["request"]["spec"]["run_date"] = "2000-01-01"
        else:
            record["api_usage"].pop()
        selected.provenance_path.write_text(yaml.safe_dump(record))
    before = tree(root)
    with pytest.raises(ledger.UsageLedgerError):
        journal.verify_completed_legacy(selected.provenance_path, evidence_root=root, recorded_root=old)
    assert tree(root) == before


@pytest.mark.parametrize("probe", ["P3", "P4", "P5"])
@pytest.mark.parametrize("entry", ["execute", "internal", "prepare", "write", "spend", "begin_call"])
@pytest.mark.parametrize("resume", [True, False])
def test_stripped_current_state_never_spends(tmp_path, probe, entry, resume):
    selected = spec(out_dir=tmp_path)
    ledger.prepare_usage(selected, resume=True)
    if probe == "P4":
        call = ledger.begin_call(selected, "report_regate", 1, "2026-10-26T00:00:00Z")
        ledger.cancel_call(selected, call)
        assert ledger.report_regate_attempted(selected)
    data = ledger._read(selected)
    journal.journal_path(selected).unlink()
    for key in ("latch_journal", "latch_overrides", "latch_snapshots"):
        data.pop(key, None)
    if probe == "P4":
        data["report_regate_attempted"] = False
    ledger._write_unlatched(selected, data)
    if probe == "P5":
        ledger.ledger_path(selected).unlink()
        selected.full_path.write_text("id: surviving-output\n")
    else:
        # A valid acknowledgement of the inspection binding grants no spend.
        binding = journal.provenance(selected)["binding_sha256"]
        journal.override_path(selected).write_text(json.dumps({
            "format": journal.OVERRIDE_FORMAT, "identity": data["identity"],
            "generation_id": data["generation_id"], "event_sha256s": [binding],
            "authorization": "test inspection", "authorized_by": "test",
            "authorized_at": "2026-10-30T00:00:00Z"}))
    before = tree(tmp_path)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError):
        if entry == "execute": api.execute(selected, resume=resume, client=client)
        elif entry == "internal": api._execute(selected, resume=resume, client=client)
        elif entry == "prepare": ledger.prepare_usage(selected, resume=resume)
        elif entry == "write": ledger._write(selected, data)
        elif entry == "begin_call": ledger.begin_call(selected, "report_regate", 1, "2026-10-30T00:00:00Z")
        else: journal.check(selected)
    assert client.messages.calls == []
    assert tree(tmp_path) == before


@pytest.mark.parametrize("completed", [True, False])
@pytest.mark.parametrize("resume", [True, False])
def test_p3_p5_real_current_run_stripped_after_dispatch(tmp_path, completed, resume):
    from tests.test_generation_manifest_identity import external
    selected = external.__wrapped__(tmp_path)
    first = FakeClient()
    if completed:
        api.execute(selected, client=first)
    else:
        first.messages.fail_on = "audit"
        with pytest.raises(RuntimeError, match="boom"):
            api.execute(selected, client=first)
    journal.journal_path(selected).unlink()
    if completed:
        ledger.ledger_path(selected).unlink()
    else:
        data = ledger._read(selected)
        for key in ("latch_journal", "latch_overrides", "latch_snapshots"):
            data.pop(key, None)
        ledger._write_unlatched(selected, data)
    before = tree(tmp_path)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="inspection only"):
        api.execute(selected, resume=resume, client=client)
    assert not client.messages.calls and tree(tmp_path) == before


@pytest.mark.parametrize("case", ["i1", "i2", "c1", "c2", "c4", "c7", "P3", "P4", "P5"])
def test_cli_refuses_legacy_and_stripped_runs_readonly(tmp_path, monkeypatch, case):
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli, api as command
    if case.startswith("P"):
        selected = spec(out_dir=tmp_path)
        ledger.prepare_usage(selected, resume=True)
        if case == "P4":
            call = ledger.begin_call(selected, "report_regate", 1, "2026-10-26T00:00:00Z")
            ledger.cancel_call(selected, call)
        journal.journal_path(selected).unlink()
        data = ledger._read(selected)
        for key in ("latch_journal", "latch_overrides", "latch_snapshots", "report_regate_attempted"):
            data.pop(key, None)
        ledger._write_unlatched(selected, data)
        if case == "P5":
            ledger.ledger_path(selected).unlink()
            selected.full_path.write_text("id: residue\n")
        else:
            binding = journal.provenance(selected)["binding_sha256"]
            journal.override_path(selected).write_text(json.dumps({
                "format": journal.OVERRIDE_FORMAT, "identity": data["identity"],
                "generation_id": data["generation_id"], "event_sha256s": [binding],
                "authorization": "test inspection", "authorized_by": "test",
                "authorized_at": "2026-10-30T00:00:00Z"}))
        root = tmp_path
    else:
        root, _, selected = fixture(case, tmp_path)
    monkeypatch.setattr(command, "_spec", lambda *a, **k: selected)
    for name in ("_require_bundle", "_require_canonical_prompts", "_refuse_condition_mismatch"):
        monkeypatch.setattr(command, name, lambda *a, **k: None)
    monkeypatch.setattr(command, "_plan_or_refuse", lambda *a: {
        "approx_total_input_tokens": 0, "model": {"name": "offline"}})
    monkeypatch.setattr(api, "_client", lambda: pytest.fail("CLI constructed a provider client"))
    before = tree(root)
    result = CliRunner().invoke(cli, ["api", "run", "--project", selected.project,
                                     "--label", selected.label, "--yes"])
    message = result.output + str(result.exception)
    assert result.exit_code != 0 and any(reason in message for reason in (
        "inspection only", "a run label is never reused"))
    assert tree(root) == before


@pytest.mark.parametrize("case", ["i1", "i2", "c4", "c7"])
@pytest.mark.parametrize("resume", [True, False])
def test_new_label_cannot_overwrite_a_legacy_evidence_directory(tmp_path, case, resume):
    from dataclasses import replace
    root, _, selected = fixture(case, tmp_path)
    selected = replace(selected, label="independent-new-label")
    before = tree(root)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError):
        api.execute(selected, resume=resume, client=client)
    assert not client.messages.calls and tree(root) == before


@pytest.mark.parametrize("checkpoint", [True, False])
def test_previously_adopted_legacy_journal_never_reopens(tmp_path, checkpoint):
    selected = spec(out_dir=tmp_path)
    data = ledger._empty(selected, accept_legacy=True)
    ledger._write_unlatched(selected, data)
    events = []
    event = journal._legacy(selected, data, events)[0]
    journal._append(selected, events, event)
    data["latch_journal"] = journal._checkpoint(selected, event) if checkpoint else None
    ledger._write_unlatched(selected, data)
    before = tree(tmp_path)
    with pytest.raises(ledger.UsageLedgerError, match="inspection only"):
        api.execute(selected, client=FakeClient(), resume=False)
    assert tree(tmp_path) == before
