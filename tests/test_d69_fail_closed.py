"""D69/D73(c): complete residue inventory and refusal before helper writes."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, latch_journal as journal, usage_ledger as ledger
from tests.test_d68_legacy_readonly import fixture, tree
from tests.test_download.test_api_runner import FakeClient, spec


# These are the reviewer's concrete missed writers, not the ownership contract.
# The controller census below discovers the emitted set without a name list.
@pytest.mark.parametrize("name", [
    "intermediate/.P_snapshot_index.abcdefgh",
    "intermediate/P_report_context.json", "intermediate/P_report_context_refused.json",
    "intermediate/P_reconcile_full_context.json", "intermediate/P_report_regate_context.json",
    "intermediate/P_report_after_repair_context.json",
    "intermediate/P_routing_request_" + "a" * 32 + ".json",
    "intermediate/P_routing_response.json",
    "intermediate/P_full_receipt_completion_incomplete_attempt1_1.txt",
    "P_routing_completed.json", ".P_routing_completed.abcdef.tmp",
    "P_future_writer_never_enumerated.bin", ".P_future_writer.temporary",
])
@pytest.mark.parametrize("resume", [True, False])
def test_review_finding_one_single_artifact_refuses(tmp_path, name, resume):
    selected = spec(project="P", out_dir=tmp_path)
    path = tmp_path / name
    path.parent.mkdir(exist_ok=True)
    path.write_text('{"previous_attempt": true}\n')
    before, client = tree(tmp_path), FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="inspection only"):
        api.execute(selected, resume=resume, client=client)
    assert client.messages.calls == []
    assert tree(tmp_path) == before


@pytest.mark.parametrize("archive", [False, True])
@pytest.mark.parametrize("resume", [True, False])
def test_foreign_guarded_record_never_hides_an_unrelated_account(tmp_path, archive, resume):
    selected = spec(project="P", out_dir=tmp_path, label="selected")
    foreign = replace(selected, label="guarded")
    legacy = selected if archive else replace(selected, label="legacy")
    ledger.prepare_usage(foreign, resume=True)
    foreign.provenance_path.write_text(yaml.safe_dump({"run": ledger.run_identity(foreign)}))
    path = ledger.ledger_path(legacy)
    if archive:
        path = path.with_name(path.stem + ".previous-" + "a" * 32 + ".json")
    path.write_text(json.dumps(ledger._empty(legacy, accept_legacy=True)))
    before, client = tree(tmp_path), FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="inspection only") as caught:
        api.execute(selected, resume=resume, client=client)
    assert path.name in str(caught.value)
    assert client.messages.calls == []
    assert tree(tmp_path) == before


@pytest.mark.parametrize("boundary", ["repair", "readdress", "call", "completion", "typed", "recovery", "publish"])
def test_authentic_legacy_refuses_at_each_callable_boundary(tmp_path, boundary, monkeypatch):
    from data_sheets_schema import receipt_completion as rc, typed_audit_runtime as typed
    root, _, selected = fixture("c7", tmp_path)
    client = FakeClient()
    settings = api._model_settings()
    body = "id: example:dataset\nname: Example\n"
    from tests.test_download.test_receipt_readdress import _receipt
    receipt = yaml.safe_dump(_receipt({"slot": "unknown_slot", "snippet": "a"}))
    if boundary == "call":
        source = api._reasoning_path(selected)
        data = ledger._read(selected)
        data["pending_reasoning_archive"] = {
            "name": selected.project + "_reasoning.previous-" + "a" * 32 + ".jsonl",
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        ledger._write_unlatched(selected, data)
    before = tree(root)
    with pytest.raises(ledger.UsageLedgerError, match="inspection only"):
        if boundary == "repair":
            api._repair_invalid(selected, client, settings, [])
        elif boundary == "readdress":
            api._readdress_receipt(selected, api.build_phase(selected, "full", carry={}),
                                   body, body, receipt, client, settings, [])
        elif boundary == "call":
            api._call_with_usage(selected, "report_regate", 1, "2026-10-31T00:00:00Z", client)
        elif boundary == "completion":
            rc.run(selected, client, settings, [])
        elif boundary == "typed":
            typed.run(selected, carry={}, client=client, settings=settings, usage=[])
        elif boundary == "recovery":
            rc.recover(selected)
        else:
            rc._receipt_publish(selected, {}, {})
    assert client.messages.calls == []
    assert tree(root) == before


def test_batch_preflights_every_selection_before_lock(tmp_path, monkeypatch):
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli, api as command, provenance
    from data_sheets_schema import run_lock
    fresh = spec(project="P", out_dir=tmp_path / "fresh", label="legacy_rep1")
    root, _, legacy = fixture("c7", tmp_path)
    selected = iter([fresh, legacy])
    monkeypatch.setattr(provenance, "_require_repo_root_cwd", lambda *a: None)
    monkeypatch.setattr(command, "_spec", lambda *a, **k: next(selected))
    for name in ("_require_bundle", "_require_canonical_prompts", "_refuse_condition_mismatch"):
        monkeypatch.setattr(command, name, lambda *a, **k: None)
    monkeypatch.setattr(command, "_plan_or_refuse", lambda *a: {
        "approx_total_input_tokens": 0, "model": {"name": "offline"}})
    monkeypatch.setattr(api, "execute", lambda *a, **k: pytest.fail("batch dispatch"))
    monkeypatch.setattr(run_lock, "acquire", lambda *a, **k: pytest.fail("batch wrote lock"))
    before = tree(tmp_path)
    result = CliRunner().invoke(cli, ["api", "batch", "--projects", "P,Q", "--replicates", "1",
        "--label-prefix", "legacy", "--yes", "--no-branch-guard"])
    assert "inspection only" in result.output + str(result.exception)
    assert tree(tmp_path) == before


@pytest.mark.parametrize("symlink", [False, True])
def test_unattributed_prefix_sibling_is_residue(tmp_path, symlink):
    selected = spec(project="P", out_dir=tmp_path)
    path = tmp_path / "P_reconcile_full.yaml"
    if symlink:
        path.symlink_to(tmp_path / "missing-target")
    else:
        path.write_text("unattributed sibling or reconcile artifact")
    before = tree(tmp_path)
    with pytest.raises(ledger.UsageLedgerError, match="new label") as caught:
        journal.refuse_legacy_execution(selected)
    assert path.name in str(caught.value)
    assert tree(tmp_path) == before


def test_only_new_still_held_empty_locks_are_current_startup_writes(tmp_path):
    selected = spec(project="P", out_dir=tmp_path)
    journal.refuse_legacy_execution(selected)
    with ledger.exclusive_run(selected):
        files = journal.owned_artifacts(selected)
        assert len(files) == 4 and all(ledger.is_new_held_lock(p) for p in files)
        journal.refuse_legacy_execution(selected)
        files[0].write_text("previous attempt")
        with pytest.raises(ledger.UsageLedgerError, match="inspection only"):
            journal.refuse_legacy_execution(selected)
    before = tree(tmp_path)
    assert not any(ledger.is_new_held_lock(p) for p in files)
    with pytest.raises(ledger.UsageLedgerError, match="inspection only"):
        journal.refuse_legacy_execution(selected)
    assert tree(tmp_path) == before
