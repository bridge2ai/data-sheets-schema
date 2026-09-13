"""Completed calls survive a process exit before final provenance (#656)."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

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
    fresh = json.loads(ledger.ledger_path(s).read_text())
    assert fresh["rows"] == []
    assert fresh["generation_id"] != json.loads(old_bytes)["generation_id"]
    assert fresh["accept_legacy"] is False
    archives = list(tmp_path.glob("*.previous-*.json"))
    assert len(archives) == 1 and archives[0].read_bytes() == old_bytes
    new = ledger.append_usage(s, [], row())
    assert ledger.merge_usage(s, []) == [new]
    assert archives[0].read_bytes() == old_bytes
    assert ledger.prior_generation_ids(s) == [json.loads(old_bytes)["generation_id"]]


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
    # Starting fresh must not remove the active ledger before the replacement
    # succeeds; an interruption at that boundary still belongs to the old run.
    with pytest.raises(ledger.UsageLedgerError, match="disk failure"):
        ledger.prepare_usage(s, resume=False)
    assert ledger.ledger_path(s).read_bytes() == before


@pytest.mark.parametrize("damage", ["invalid-json", "identity", "version", "missing-id", "duplicate-id",
                                   "generation", "legacy-policy"])
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
    elif damage == "generation":
        data["generation_id"] = None
    elif damage == "legacy-policy":
        data["accept_legacy"] = "false"
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


def test_intent_persistence_failure_prevents_the_paid_call(tmp_path, monkeypatch):
    s = spec(out_dir=tmp_path)

    def fail(*args):
        raise OSError("disk failure")

    monkeypatch.setattr(ledger.os, "replace", fail)
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="disk failure"):
        api._generate_phase(s, "full", {}, client, api._model_settings(), [])
    assert client.messages.calls == []


@pytest.mark.parametrize("phase", ["full", "repair_full", "report_after_repair", "full_readdress"])
def test_response_persistence_failure_blocks_the_next_invocation(tmp_path, monkeypatch, phase):
    s = spec(out_dir=tmp_path)
    body = "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"
    s.full_path.write_text(body)
    s.core_path.write_text(body)
    client, usage, settings = FakeClient(), [], api._model_settings()
    original_replace = ledger.os.replace

    def fail_after_response(source, destination):
        if client.messages.calls:
            raise OSError("response storage failed")
        return original_replace(source, destination)

    with monkeypatch.context() as failing:
        failing.setattr(ledger.os, "replace", fail_after_response)
        with pytest.raises(ledger.UsageLedgerError, match="response storage failed"):
            if phase == "full":
                api._generate_phase(s, phase, {}, client, settings, usage)
            elif phase == "repair_full":
                failing.setattr(api, "_validator_lines", lambda *args: (["bad shape"], None))
                api._repair_invalid(s, client, settings, usage)
            elif phase == "report_after_repair":
                carry = {key: body for key in api.PHASE_NEEDS["report"]}
                api._regenerate_report(s, client, settings, usage, carry)
            else:
                from tests.test_download.test_receipt_readdress import _receipt
                receipt = yaml.safe_dump(_receipt({"slot": "unknown_slot", "snippet": "a"}))
                api._readdress_receipt(s, api.build_phase(s, "full", carry={}), body,
                                      body, receipt, client, settings, usage)
    before = ledger.ledger_path(s).read_bytes()
    pending = json.loads(before)["pending_call"]
    assert pending["phase"] == phase and pending["usage_id"]
    assert len(client.messages.calls) == 1 and usage == []
    # Restoring storage cannot turn the unresolved completed response into a
    # new run with a silently smaller total, or permit a no-call success exit.
    with pytest.raises(ledger.UsageLedgerError, match="unresolved accounting"):
        api.execute(s, client=client)
    assert len(client.messages.calls) == 1
    assert ledger.ledger_path(s).read_bytes() == before
    # Explicit fresh is allowed, with the uncertain historical bytes retained.
    ledger.prepare_usage(s, resume=False)
    ledger.require_resolved(s)
    assert any(path.read_bytes() == before for path in tmp_path.glob("*.previous-*.json"))


def test_interrupt_before_response_accounting_remains_unresolved(tmp_path, monkeypatch):
    s, client = spec(out_dir=tmp_path), FakeClient()

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    with monkeypatch.context() as interrupted:
        interrupted.setattr(api, "_append_usage", interrupt)
        with pytest.raises(KeyboardInterrupt):
            api._generate_phase(s, "full", {}, client, api._model_settings(), [])
    with pytest.raises(ledger.UsageLedgerError, match="unresolved accounting"):
        api.execute(s, client=client)
    assert len(client.messages.calls) == 1


def test_recovered_counters_resolve_the_same_pending_call(tmp_path):
    s = spec(out_dir=tmp_path)
    identifier = ledger.begin_call(s, "full", 1, "2026-09-11T00:00:00Z")
    with pytest.raises(ledger.UsageLedgerError, match="unresolved accounting"):
        ledger.begin_call(s, "audit", 1, "2026-09-11T00:00:01Z")
    recovered = {**row(), "usage_id": identifier}
    ledger.persist_usage(s, recovered)
    ledger.require_resolved(s)
    assert ledger.merge_usage(s, []) == [recovered]


def test_reported_transport_failure_does_not_leave_a_completed_call_pending(tmp_path):
    s = spec(out_dir=tmp_path)
    client = FakeClient()
    client.messages.fail_on = "full"
    with pytest.raises(RuntimeError, match="boom"):
        api._generate_phase(s, "full", {}, client, api._model_settings(), [])
    ledger.require_resolved(s)
    assert ledger.merge_usage(s, []) == []


def test_shared_outputs_reject_overlapping_resume_fresh_and_other_labels(tmp_path, monkeypatch):
    s = spec(out_dir=tmp_path)
    entered, release = threading.Event(), threading.Event()
    original = api._begin_usage_call

    def pause_before_intent(run, *args):
        if not entered.is_set():
            entered.set()
            assert release.wait(60), "concurrency test did not release the first run"
        return original(run, *args)

    monkeypatch.setattr(api, "_begin_usage_call", pause_before_intent)
    active = FakeClient()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(api.execute, s, client=active)
        try:
            assert entered.wait(60), "first run never reached the request boundary"
            before = ledger.ledger_path(s).read_bytes()
            for contender, resume in ((s, True), (s, False),
                                      (replace(s, label="another_rep1"), True)):
                client = FakeClient()
                with pytest.raises(ledger.UsageLedgerError, match="already active"):
                    api.execute(contender, resume=resume, client=client)
                assert client.messages.calls == []
                assert ledger.ledger_path(s).read_bytes() == before
            assert not ledger.ledger_path(replace(s, label="another_rep1")).exists()
            # Different output files do not share the exclusion.
            other = spec(out_dir=tmp_path / "independent")
            with ledger.exclusive_run(other):
                pass
        finally:
            release.set()
        result = future.result(timeout=60)
    assert len(active.messages.calls) == len(result["usage"]) == 4
    assert api.execute(s, client=active)["already_complete"]
    assert len(active.messages.calls) == 4


def test_hard_process_exit_releases_output_exclusion(tmp_path):
    child = """
import os, sys
from pathlib import Path
from data_sheets_schema.usage_ledger import exclusive_run
from tests.test_download.test_api_runner import spec
with exclusive_run(spec(out_dir=Path(sys.argv[1]))):
    os._exit(23)
"""
    result = subprocess.run([sys.executable, "-c", child, str(tmp_path)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 23, result.stderr
    with ledger.exclusive_run(spec(out_dir=tmp_path)):
        pass


@pytest.mark.parametrize("shared_directory", ["full", "core"])
def test_split_and_flat_layouts_cannot_overlap_in_either_direction(tmp_path, monkeypatch, shared_directory):
    monkeypatch.setattr(api, "CONCAT_DIR", tmp_path)
    split = spec(out_dir=None)
    directory = split.full_path.parent if shared_directory == "full" else split.core_path.parent
    flat = replace(split, out_dir=directory)
    assert (split.full_path == flat.full_path if shared_directory == "full"
            else split.core_path == flat.core_path)
    for owner, contender in ((split, flat), (flat, split)):
        with ledger.exclusive_run(owner):
            client = FakeClient()
            with pytest.raises(ledger.UsageLedgerError, match="already active"):
                api.execute(contender, client=client)
            assert client.messages.calls == []
            assert not ledger.ledger_path(contender).exists()
        # Failed acquisition must release files taken before the overlap.
        with ledger.exclusive_run(contender):
            pass


def test_output_aliases_share_the_physical_file_lock(tmp_path):
    owner = spec(out_dir=tmp_path / "original")
    alias = spec(out_dir=tmp_path / "alias")
    owner.out_dir.mkdir()
    alias.out_dir.mkdir()
    owner.full_path.write_text("record")
    alias.full_path.symlink_to(owner.full_path)
    with ledger.exclusive_run(owner):
        client = FakeClient()
        with pytest.raises(ledger.UsageLedgerError, match="already active"):
            api.execute(alias, client=client)
        assert client.messages.calls == []
    with ledger.exclusive_run(alias):
        pass


@pytest.mark.parametrize("phase", ["repair_full", "report_after_repair", "full_readdress"])
def test_auxiliary_calls_are_durable_before_later_processing_fails(tmp_path, monkeypatch, phase):
    s = spec(out_dir=tmp_path)
    body = "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"
    s.full_path.write_text(body)
    s.core_path.write_text(body)
    client, current, settings = FakeClient(), [], api._model_settings()
    attempted_reasoning = []

    def fail(path, entry):
        attempted_reasoning.append(entry)
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
    assert attempted_reasoning[0]["usage_id"] == recovered[0]["usage_id"]
    assert attempted_reasoning[0]["generation_id"] == ledger.generation_id(s)
    assert attempted_reasoning[0]["run_identity"] == ledger.run_identity(s)


def test_resume_after_reasoning_failure_does_not_misattribute_the_retry(tmp_path, monkeypatch):
    from data_sheets_schema.run_telemetry import run_telemetry
    s, client = spec(out_dir=tmp_path), FakeClient()
    create = client.messages.create

    def response(**kw):
        result = create(**kw)
        if "# full\n" in result.content[0].text:
            result.usage.output_tokens = 1000 if len(client.messages.calls) == 1 else 2000
        return result

    monkeypatch.setattr(client.messages, "create", response)

    def fail(*args):
        raise OSError("reasoning disk failure")

    with monkeypatch.context() as failing:
        failing.setattr(api.reasoning, "append", fail)
        with pytest.raises(OSError, match="reasoning disk failure"):
            api.execute(s, client=client)
    interrupted = ledger.merge_usage(s, [])[0]
    assert interrupted["output_tokens"] == 1000
    assert not s.provenance_path.exists() and not api._reasoning_path(s).exists()
    resumed = api.execute(s, client=client)
    assert len(resumed["usage"]) == 5
    entries = [json.loads(line) for line in api._reasoning_path(s).read_text().splitlines()]
    assert {r["usage_id"] for r in entries} == {r["usage_id"] for r in resumed["usage"][1:]}
    telemetry = run_telemetry(tmp_path, s.project)
    full = next(p for p in telemetry["phases"] if p["phase"] == "full")["attempts"]
    assert [r["output_tokens"] for r in full] == [1000, 2000]
    assert "reasoning_tokens_estimate" not in full[0]
    accepted_reasoning = next(e for e in entries if e["phase"] == "full")
    assert full[1]["reasoning_tokens_estimate"] == accepted_reasoning["reasoning_tokens_estimate"]
    assert full[1]["reasoning_tokens_estimate"] > 1800


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
    saved_ledger = ledger.ledger_path(s).read_bytes()
    ledger.ledger_path(s).unlink()
    blocked = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="ledger is missing"):
        api.execute(s, client=blocked)
    assert blocked.messages.calls == []
    ledger.ledger_path(s).write_bytes(saved_ledger)
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


@pytest.mark.parametrize("portable_prior", [False, True])
def test_explicit_fresh_execution_does_not_import_previous_usage(tmp_path, portable_prior):
    from data_sheets_schema.run_telemetry import run_telemetry
    s = spec(out_dir=tmp_path)
    old = api.execute(s, client=FakeClient())["usage"]
    previous_generation = ledger.generation_id(s)
    # Even a stale progress file must not defeat an explicit fresh request.
    api._save_progress(s, list(api.PHASES), None)
    if portable_prior:
        ledger.ledger_path(s).unlink()
    new = api.execute(s, resume=False, client=FakeClient())["usage"]
    assert len(old) == len(new) == 4
    assert {r["usage_id"] for r in old}.isdisjoint(r["usage_id"] for r in new)
    archived = list(tmp_path.glob("*.previous-*.json"))
    if portable_prior:
        assert archived == []
    else:
        assert len(archived) == 1 and json.loads(archived[0].read_text())["rows"] == old
    assert yaml.safe_load(s.provenance_path.read_text())["run"]["prior_generation_ids"] == [previous_generation]
    entries = [json.loads(line) for line in api._reasoning_path(s).read_text().splitlines()]
    current_ids = {r["usage_id"] for r in new}
    expected = sum(e["reasoning_tokens_estimate"] or 0 for e in entries if e["usage_id"] in current_ids)
    assert expected > 0
    assert run_telemetry(tmp_path, s.project)["total_reasoning_tokens_estimate"] == expected
    # A finished portable record is sufficient for the no-call exit even if
    # its recovery ledger is not copied alongside it.
    ledger.ledger_path(s).unlink()
    complete = FakeClient()
    assert api.execute(s, client=complete)["already_complete"]
    assert complete.messages.calls == [] and not ledger.ledger_path(s).exists()
    api._save_progress(s, list(api.PHASES), None)
    # Even legacy-shaped progress must not erase an identity retained in
    # provenance and turn a missing journal into a new generation.
    assert "generation_id" not in json.loads(api._progress_path(s).read_text())
    with pytest.raises(ledger.UsageLedgerError, match="ledger is missing"):
        api.execute(s, client=complete)
    assert complete.messages.calls == []


@pytest.mark.parametrize("stage,legacy_prior", [
    ("before_progress", False), ("full", False), ("core", False), ("full", True),
])
def test_interrupted_fresh_generation_cannot_recover_previous_charges(tmp_path, stage, legacy_prior):
    s = spec(out_dir=tmp_path)
    old = api.execute(s, client=FakeClient())["usage"]
    old_ids = {r["usage_id"] for r in old}
    old_generation = ledger.generation_id(s)
    api._save_progress(s, list(api.PHASES), None)
    if legacy_prior:
        prior = yaml.safe_load(s.provenance_path.read_text())
        del prior["run"]["generation_id"]
        s.provenance_path.write_text(yaml.safe_dump(prior))
        progress = json.loads(api._progress_path(s).read_text())
        del progress["generation_id"]
        api._progress_path(s).write_text(json.dumps(progress))
        reasoning = [json.loads(line) for line in api._reasoning_path(s).read_text().splitlines()]
        for entry in reasoning:
            entry.pop("usage_id")
        api._reasoning_path(s).write_text("\n".join(json.dumps(e) for e in reasoning) + "\n")
    old_provenance = s.provenance_path.read_bytes()
    root = Path(__file__).resolve().parents[1]
    code = """
import os, sys
from pathlib import Path
from data_sheets_schema import api_runner as api
from tests.test_download.test_api_runner import FakeClient, spec
save, generate = api._save_progress, api._generate_phase
def exit_after_progress(run, completed, audit):
    save(run, completed, audit)
    if sys.argv[2] in completed:
        os._exit(23)
def exit_before_progress(*args, **kwargs):
    if sys.argv[2] == 'before_progress':
        os._exit(23)
    return generate(*args, **kwargs)
api._save_progress = exit_after_progress
api._generate_phase = exit_before_progress
api.execute(spec(out_dir=Path(sys.argv[1])), resume=False, client=FakeClient())
"""
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root)])}
    killed = subprocess.run([sys.executable, "-c", code, str(tmp_path), stage],
                            cwd=root, env=environment, capture_output=True, text=True, timeout=90)
    assert killed.returncode == 23, killed.stdout + killed.stderr
    assert s.provenance_path.read_bytes() == old_provenance
    generation = ledger.generation_id(s)
    assert generation != old_generation
    if stage != "before_progress":
        assert json.loads(api._progress_path(s).read_text())["generation_id"] == generation
    client = FakeClient()
    resumed = api.execute(s, client=client)
    assert len(resumed["usage"]) == 4
    assert old_ids.isdisjoint(r["usage_id"] for r in resumed["usage"])
    assert len(client.messages.calls) == (4 if stage == "before_progress" else 3)
    assert yaml.safe_load(s.provenance_path.read_text())["run"]["generation_id"] == generation
    archives = list(tmp_path.glob("*.previous-*.json"))
    assert len(archives) == 1 and json.loads(archives[0].read_text())["rows"] == old
    from data_sheets_schema.run_telemetry import run_telemetry
    current_ids = {r["usage_id"] for r in resumed["usage"]}
    reasoning = [json.loads(line) for line in api._reasoning_path(s).read_text().splitlines()]
    expected = sum(e["reasoning_tokens_estimate"] or 0 for e in reasoning if e.get("usage_id") in current_ids)
    assert run_telemetry(tmp_path, s.project)["total_reasoning_tokens_estimate"] == expected


def test_legacy_partial_run_adopts_a_generation_without_losing_recorded_usage(tmp_path):
    s = spec(out_dir=tmp_path)
    api.execute(s, client=FakeClient())
    prior = yaml.safe_load(s.provenance_path.read_text())
    del prior["run"]["generation_id"]
    for entry in prior["intermediates"]:
        for key in ("generation_id", "phase", "usage_id"):
            entry.pop(key, None)
    for entry in prior["api_usage"]:
        entry.pop("usage_id")
    reasoning = [json.loads(line) for line in api._reasoning_path(s).read_text().splitlines()]
    for entry in reasoning:
        for key in ("usage_id", "generation_id", "run_identity"):
            entry.pop(key, None)
    api._reasoning_path(s).write_text("\n".join(json.dumps(e) for e in reasoning) + "\n")
    old = prior["api_usage"]
    s.provenance_path.write_text(yaml.safe_dump(prior))
    ledger.ledger_path(s).unlink()
    # This fixture simulates a run from before generation identities and
    # snapshot indices existed; retaining the new index would contradict it.
    from data_sheets_schema.snapshot_store import index_path
    index_path(s.metadata_dir, s.project).unlink()
    api._save_progress(s, list(api.PHASES), None)
    assert "generation_id" not in json.loads(api._progress_path(s).read_text())
    client = FakeClient()
    resumed = api.execute(s, client=client)
    assert client.messages.calls == [] and resumed["usage"] == old
    final = yaml.safe_load(s.provenance_path.read_text())
    assert final["run"]["generation_id"] == ledger.generation_id(s)


def test_fresh_generation_does_not_import_old_abandoned_stream_charges(tmp_path):
    s = spec(out_dir=tmp_path)
    old_generation = ledger.prepare_usage(s, resume=True)
    old = []
    api._record_incomplete_stream(s, "full", 1, "2026-09-11T00:00:00Z", {}, old)
    assert old[0]["generation_id"] == old_generation
    assert api.merge_abandoned_rows(s, []) == old
    before = api._abandoned_ledger(s).read_bytes()
    ledger.prepare_usage(s, resume=False)
    assert api.merge_abandoned_rows(s, []) == []
    assert api._abandoned_ledger(s).read_bytes() == before
    current = []
    api._record_incomplete_stream(s, "full", 1, "2026-09-11T00:01:00Z", {}, current)
    assert current[0]["generation_id"] != old_generation
    assert api.merge_abandoned_rows(s, []) == current


@pytest.mark.parametrize("change,stale_progress", [
    ({"label": "another_rep1"}, False), ({"label": "another_rep1"}, True),
    ({"method": "another_method"}, False),
    ({"condition": "tuned", "condition_mismatch_allowed": True}, False),
])
def test_new_identity_in_a_shared_directory_starts_its_own_generation(tmp_path, monkeypatch, change, stale_progress):
    old = spec(out_dir=tmp_path)
    generation = ledger.prepare_usage(old, resume=True)
    prior_usage = []
    ledger.append_usage(old, prior_usage, row())
    prior = {"run": {**ledger.run_identity(old), "generation_id": generation}, "api_usage": prior_usage}
    old.provenance_path.write_text(yaml.safe_dump(prior))
    body = "id: x\ntitle: T\nname: n\ndescription: d\nkeywords: [a]\n"
    old.full_path.write_text(body)
    old.core_path.write_text(body)
    old.report_path.write_text("# Report\n")
    api._record_incomplete_stream(old, "full", 1, "2026-09-11T00:00:00Z", {}, [])
    journal = api._abandoned_ledger(old).read_bytes()
    old_ledger = ledger.ledger_path(old).read_bytes()
    if stale_progress:
        api._save_progress(old, list(api.PHASES), None)
        # Older progress carries the label/generation but no full identity.
        data = json.loads(api._progress_path(old).read_text())
        data.pop("run_identity", None)
        api._progress_path(old).write_text(json.dumps(data))
    current = replace(old, **change)

    class Started(Exception):
        pass

    def start(run, phase, needed, client, settings, usage):
        assert run == current and phase == "full" and usage == []
        raise Started

    monkeypatch.setattr(api, "_generate_phase", start)
    with pytest.raises(Started):
        api.execute(current, client=FakeClient())
    assert ledger.generation_id(current) != generation
    assert ledger.prior_generation_ids(current) == []
    assert json.loads(ledger.ledger_path(current).read_text())["accept_legacy"] is False
    assert ledger.ledger_path(old).read_bytes() == old_ledger
    assert api._abandoned_ledger(old).read_bytes() == journal
    assert api.merge_abandoned_rows(current, []) == []


def test_fresh_boundary_combines_matching_record_and_ledger_history(tmp_path):
    s = spec(out_dir=tmp_path)
    generation = ledger.prepare_usage(s, resume=True)
    prior = {"run": {**ledger.run_identity(s), "generation_id": "parent",
                     "prior_generation_ids": ["ancestor"]}}
    s.provenance_path.write_text(yaml.safe_dump(prior))
    ledger.prepare_usage(s, resume=False)
    assert ledger.prior_generation_ids(s) == ["ancestor", "parent", generation]
    # Repeating fresh execution while provenance remains stale preserves the
    # whole history without duplicating the IDs present in both sources.
    current = ledger.generation_id(s)
    ledger.prepare_usage(s, resume=False)
    assert ledger.prior_generation_ids(s) == ["ancestor", "parent", generation, current]


@pytest.mark.parametrize("known_owner", [True, False])
def test_abandoned_only_state_with_no_ledger_cannot_silently_start_over(tmp_path, known_owner):
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    rows = []
    api._record_incomplete_stream(s, "full", 1, "2026-09-11T00:00:00Z", {}, rows)
    if not known_owner:
        rows[0].pop("run_identity")
        api._abandoned_ledger(s).write_text(json.dumps(rows[0]) + "\n")
    ledger.ledger_path(s).unlink()
    before = api._abandoned_ledger(s).read_bytes()
    assert not s.provenance_path.exists() and not api._progress_path(s).exists()
    client = FakeClient()
    with pytest.raises(ledger.UsageLedgerError, match="abandoned.*ledger is missing"):
        api.execute(s, client=client)
    assert client.messages.calls == [] and not ledger.ledger_path(s).exists()
    assert api._abandoned_ledger(s).read_bytes() == before


def test_completed_record_covers_its_abandoned_rows_but_not_later_charges(tmp_path):
    s = spec(out_dir=tmp_path)
    ledger.prepare_usage(s, resume=True)
    abandoned = []
    # Same snapshot name and timestamp are not a call identity.
    for _ in range(2):
        api._record_incomplete_stream(s, "full", 1, "2026-09-11T00:00:00Z", {}, abandoned)
    assert abandoned[0]["usage_id"] != abandoned[1]["usage_id"]
    assert api.merge_abandoned_rows(s, []) == abandoned
    result = api.execute(s, client=FakeClient())
    assert all(result["usage"].count(entry) == 1 for entry in abandoned)
    ledger.ledger_path(s).unlink()
    # A portable completed record covers these exact charges. Foreign
    # progress in the shared directory must survive this read-only exit.
    other = {"label": "another_rep1", "generation_id": "other-generation", "completed": ["full"]}
    api._progress_path(s).write_text(json.dumps(other))
    progress_bytes = api._progress_path(s).read_bytes()
    client = FakeClient()
    assert api.execute(s, client=client)["already_complete"]
    assert client.messages.calls == []
    assert api._progress_path(s).read_bytes() == progress_bytes
    api._progress_path(s).unlink()
    # A later fresh invocation can fail before writing any progress or
    # provenance. Its surviving charges must prevent returning the old record.
    ledger.prepare_usage(s, resume=False)
    later = []
    api._record_incomplete_stream(s, "full", 1, "2026-09-11T00:01:00Z", {}, later)
    ledger.ledger_path(s).unlink()
    with pytest.raises(ledger.UsageLedgerError, match="abandoned.*ledger is missing"):
        api.execute(s, client=client)
    assert client.messages.calls == [] and not ledger.ledger_path(s).exists()


def test_reasoning_only_state_requires_its_missing_usage_ledger(tmp_path, monkeypatch):
    s, client = spec(out_dir=tmp_path), FakeClient()

    def fail(*args):
        raise OSError("snapshot failure")

    with monkeypatch.context() as failing:
        failing.setattr(api, "_snapshot", fail)
        with pytest.raises(OSError, match="snapshot failure"):
            api.execute(s, client=client)
    saved = ledger.ledger_path(s).read_bytes()
    reasoning_bytes = api._reasoning_path(s).read_bytes()
    assert not api._progress_path(s).exists() and not s.provenance_path.exists()
    ledger.ledger_path(s).unlink()
    with pytest.raises(ledger.UsageLedgerError, match="reasoning.*ledger is missing"):
        api.execute(s, client=client)
    assert len(client.messages.calls) == 1
    assert api._reasoning_path(s).read_bytes() == reasoning_bytes
    assert not ledger.ledger_path(s).exists()
    ledger.ledger_path(s).write_bytes(saved)
    resumed = api.execute(s, client=client)
    assert len(resumed["usage"]) == len(client.messages.calls) == 5
    ledger.ledger_path(s).unlink()
    assert api.execute(s, client=client)["already_complete"]
    assert len(client.messages.calls) == 5


@pytest.mark.parametrize("snippet", ["2026-09-11", "2026-09-11T01:02:03Z", "{2026-09-11: x}"])
def test_yaml_native_receipt_diagnostics_do_not_abort_a_paid_phase(tmp_path, snippet):
    from tests.test_download.test_receipt_readdress import _ReceiptFake

    class NativeSnippet(_ReceiptFake):
        def create(self, **kw):
            result = super().create(**kw)
            result.content[0].text = result.content[0].text.replace(
                'snippet: "Medicine, Health and Life Sciences"', f"snippet: {snippet}")
            return result

    client = FakeClient()
    client.messages = NativeSnippet()
    s, current = spec(out_dir=tmp_path, condition="generic_v7"), []
    body = api._generate_phase(s, "full", {}, client, api._model_settings(), current)
    assert yaml.safe_load(body)["id"] == "x"
    assert [r["phase"] for r in current] == ["full", "full_readdress"]
    assert ledger.merge_usage(s, []) == current
    diagnostic = current[1]["readdress"]
    if snippet.startswith("{"):
        assert "diagnostics_unavailable" in diagnostic
    else:
        assert diagnostic["unresolved_before"][0]["snippet"] == str(yaml.safe_load(snippet))


def test_mixed_logs_match_ids_without_shifting_legacy_entries(tmp_path):
    from data_sheets_schema.run_telemetry import run_telemetry
    rows = [row(), {**row(), "usage_id": "missing"},
            {**row(), "usage_id": "accepted"}, row(),
            {**row(), "phase": "audit", "usage_id": "wrong-phase"}]
    (tmp_path / "P_provenance.yaml").write_text(yaml.safe_dump({"api_usage": rows}))
    entries = [{"phase": "full", "reasoning_tokens_estimate": 1},
               {"phase": "full", "usage_id": "old-run", "reasoning_tokens_estimate": 900},
               {"phase": "full", "usage_id": "accepted", "reasoning_tokens_estimate": 30},
               {"phase": "full", "usage_id": "wrong-phase", "reasoning_tokens_estimate": 800},
               {"phase": "full", "reasoning_tokens_estimate": 2}]
    (tmp_path / "P_reasoning.jsonl").write_text("\n".join(json.dumps(e) for e in entries))
    result = run_telemetry(tmp_path, "P")
    full = next(p for p in result["phases"] if p["phase"] == "full")["attempts"]
    assert [r.get("reasoning_tokens_estimate") for r in full] == [1, None, 30, 2]
    audit = next(p for p in result["phases"] if p["phase"] == "audit")["attempts"]
    assert "reasoning_tokens_estimate" not in audit[0]
    assert result["total_reasoning_tokens_estimate"] == 33
