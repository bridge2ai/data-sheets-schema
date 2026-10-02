"""Restore-only runtime condition: neutral offline evidence and real outcomes."""
import builtins
import copy
from dataclasses import replace
import hashlib
import json
import socket

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner as api, removal_repair as repair, snapshot_store, usage_ledger
from data_sheets_schema.cli import cli
from tests.test_download.test_api_runner import FakeClient, FakeMessages, FakeResponse
from tests.test_generation_manifest_identity import external  # noqa: F401

ORIGINAL = {"id": "urn:loom", "title": "Loom", "name": "loom", "description": "Thread settings archive",
            "keywords": ["retained thread", "missing shuttle"]}
CURRENT = {**ORIGINAL, "keywords": ["retained thread"]}
AUDIT = '{"findings": []}'


def text(doc):
    return yaml.safe_dump(doc, sort_keys=False)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.setattr(api, "MAX_ATTEMPTS", 1)


def test_restores_a_list_member_and_does_not_treat_a_disposition_as_repair():
    before = repair.reading(text(ORIGINAL), text(CURRENT), AUDIT)
    assert before["unfounded"] == 1 and before["unfounded_paths"][0]["path"] == "keywords[1]"
    assert repair.restored_candidate(text(ORIGINAL), text(CURRENT), AUDIT, text(ORIGINAL))["unfounded"] == 0
    with pytest.raises(ValueError, match="does not restore"):
        repair.restored_candidate(text(ORIGINAL), text(CURRENT), AUDIT,
                                 text(CURRENT) + "# disposition: removed as unsupported\n")


@pytest.mark.parametrize("mutation", ["novel", "rewrite", "caveat", "duplicate", "founded"])
def test_repair_cannot_add_or_destroy_facts_or_restore_a_founded_deletion(mutation):
    original, current, candidate = copy.deepcopy(ORIGINAL), copy.deepcopy(CURRENT), copy.deepcopy(ORIGINAL)
    audit = AUDIT
    if mutation == "novel":
        candidate["keywords"].append("unobserved spinning wheel")
    elif mutation == "rewrite":
        candidate["description"] = "Changed scientific meaning"
    elif mutation == "caveat":
        candidate = copy.deepcopy(CURRENT)
        candidate["source_caveats"] = ["missing shuttle"]
    elif mutation == "duplicate":
        candidate["keywords"].append("retained thread")
    else:
        original["notes"] = "Founded removal of another unique claim"
        candidate["notes"] = original["notes"]
        audit = json.dumps({"findings": [{"slot": "notes", "issue": "unsupported"}]})
    with pytest.raises(ValueError):
        repair.restored_candidate(text(original), text(current), audit, text(candidate))


def test_whole_object_restoration_preserves_identity_after_reordering():
    original = {**ORIGINAL, "creators": [{"id": "urn:person:a", "name": "Ada Loom", "conforms_to_class": "Creator"},
                                          {"id": "urn:person:b", "name": "Blake Shuttle"}]}
    current = {**ORIGINAL, "creators": [original["creators"][1]]}
    candidate = {**ORIGINAL, "creators": list(reversed(original["creators"]))}
    assert repair.restored_candidate(text(original), text(current), AUDIT, text(candidate))["unfounded"] == 0


def test_work_order_is_not_truncated_at_the_diagnostic_path_limit():
    original = {**ORIGINAL, "keywords": [f"unique original value {i:04d}" for i in range(65)]}
    current = {k: v for k, v in original.items() if k != "keywords"}
    before = repair.reading(text(original), text(current), AUDIT)
    assert before["unfounded"] == 65 and len(before["unfounded_paths"]) == 65
    envelope = json.loads(repair.request_payload(text(original), text(current), AUDIT, None, before))
    assert len(yaml.safe_load(envelope["restoration_work_order_yaml"])) == 65
    assert repair.restored_candidate(text(original), text(current), AUDIT, text(original))["unfounded"] == 0


@pytest.mark.parametrize("bad_audit", ['{}', '{"findings":null}', '{"findings":[null]}',
                                         '{"findings":[],"findings":[]}'])
def test_unusable_audit_is_not_a_clean_reading(bad_audit):
    with pytest.raises(ValueError):
        repair.reading(text(ORIGINAL), text(CURRENT), bad_audit)


def test_duplicate_yaml_keys_cannot_be_accepted_as_a_restoration():
    with pytest.raises(ValueError, match="duplicate"):
        repair.restored_candidate(text(ORIGINAL), text(CURRENT), AUDIT,
                                 text(ORIGINAL) + "keywords: [replacement]\n")


def test_cyclic_yaml_cannot_be_mistaken_for_a_clean_reading():
    with pytest.raises(ValueError, match="cyclic YAML alias"):
        repair.reading(text(ORIGINAL), text(CURRENT) + "notes: &loop [*loop]\n", AUDIT)


def test_supported_review_needs_a_linked_finding_even_in_runtime_reading():
    original_raw = text(ORIGINAL)
    audit = {"findings": [{"slot": "keywords"}], "source_review": {
        "artifact": "original_full", "sha256": hashlib.sha256(original_raw.encode()).hexdigest(),
        "values": [{"path": "/keywords/1", "claims": [{"text": "missing shuttle", "verdict": "supported"}]}]}}
    before = repair.reading(original_raw, text(CURRENT), json.dumps(audit))
    assert before["unfounded"] == 1
    assert before["source_review"]["unfounded_supported"] == 1
    audit["findings"][0]["review_paths"] = ["/keywords/1"]
    assert repair.reading(original_raw, text(CURRENT), json.dumps(audit))["unfounded"] == 0


def test_capped_diagnostics_and_complete_work_orders_have_identical_counts():
    from data_sheets_schema.removals import classify
    original = {**ORIGINAL, "keywords": [f"numbered shuttle {n}" for n in range(65)]}
    current = {k: v for k, v in original.items() if k != "keywords"}
    capped = classify(original, current, {"findings": []})
    complete = classify(original, current, {"findings": []}, path_limit=None)
    assert capped["unfounded"] == complete["unfounded"] == 65
    assert len(capped["unfounded_paths"]) == 50 and capped["unfounded_paths_truncated"] == 15
    assert len(complete["unfounded_paths"]) == 65 and complete["unfounded_paths_truncated"] is None


@pytest.mark.parametrize("value", [False, True, -1, 2, "1", None])
def test_policy_axis_is_explicitly_versioned(external, value):
    with pytest.raises(ValueError, match="removal_repair_version"):
        replace(external, removal_repair_version=value)


@pytest.mark.parametrize("renderer,runtime", [(7, api.RUNTIME), (9, api.RUNTIME), (23, api.RUNTIME), (8, "Claude Code")])
def test_policy_refuses_unregistered_runtime_combinations(external, renderer, runtime):
    with pytest.raises(ValueError, match="renderer 8"):
        replace(external, removal_repair_version=1, render_version=renderer, runtime=runtime)


def test_policy_identity_replays_and_is_independent_of_api_playbook(external):
    historical = replace(external, condition="generic")
    assert "removal_repair_version" not in historical.render_spec()
    assert replace(historical, removal_repair_version=0).instruction == historical.instruction
    spec = replace(historical, removal_repair_version=1, api_playbook_version=1)
    recorded = spec.render_spec()
    assert recorded["removal_repair_sha256"] == repair.POLICY_SHA256
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction
    assert repair.policy_text() in spec.instruction
    assert api.assembly_digest(8)["sha256"] != api.assembly_digest(8, removal_repair_version=1)["sha256"]
    old, new = api.assembly_digest(8), api.assembly_digest(8, removal_repair_version=1)
    assert api.condition_delta(spec.condition, spec.condition, old, new) == ["assembly"]
    from data_sheets_schema import runs
    facts = lambda prefix, digest: {"prefix": prefix, "values": {"assembly digest": [digest["sha256"]]}}
    assert runs.arm_confounds(facts("old", old), facts("new", new))[0]["field"] == "assembly digest"
    for change in ({"removal_repair_sha256": "0" * 64}, {"removal_repair_version": 0}):
        with pytest.raises(ValueError):
            api.RunSpec.from_render_spec(recorded | change, project=spec.project, method=spec.method, label=spec.label)


def test_historical_rendering_does_not_import_the_new_policy(external, monkeypatch):
    spec = replace(external, condition="generic")
    recorded, instruction = spec.render_spec(), spec.instruction
    real = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name == "data_sheets_schema.removal_repair":
            raise ImportError("new policy unavailable in historical replay")
        return real(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    replay = api.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert replay.instruction == instruction
    assert "removal_repair_version" not in replay.render_spec()


@pytest.fixture
def active(external, monkeypatch):
    spec = replace(external, condition="generic", removal_repair_version=1)
    api._prepare_usage(spec, resume=False)
    snapshot_store.activate(spec, fresh=True, completed=False, prior_record={})
    spec.full_path.parent.mkdir(parents=True, exist_ok=True)
    spec.full_path.write_text(text(CURRENT))
    spec.core_path.write_text(text(CURRENT))
    api._snapshot(spec, f"{spec.project}_full.yaml", text(ORIGINAL))
    api._snapshot(spec, f"{spec.project}_audit.json", AUDIT)
    monkeypatch.setattr(api, "_validator_lines", lambda *a: ([], None))
    return spec


class RepairMessages(FakeMessages):
    def __init__(self, response, *, truncated=False):
        super().__init__()
        self.response, self.truncated = response, truncated

    def create(self, **kwargs):
        self.calls.append(kwargs)
        out = FakeResponse(self.response)
        out.stop_reason = "max_tokens" if self.truncated else "end_turn"
        return out


def client_for(body, **kwargs):
    client = FakeClient()
    client.messages = RepairMessages(body, **kwargs)
    return client


def test_runtime_accepts_actual_restoration_and_records_exact_work_order(active):
    client, usage = client_for(text(ORIGINAL)), []
    out = repair.run(active, client, api._model_settings(), usage)
    assert out["changed"] and not out["findings"] and out["final"]["unfounded"] == 0
    assert yaml.safe_load(active.full_path.read_text()) == ORIGINAL
    assert len(usage) == 1 and usage[0]["phase"] == repair.PHASE
    payload = json.loads(client.messages.calls[0]["messages"][0]["content"][1]["text"])
    work = yaml.safe_load(payload["restoration_work_order_yaml"])
    assert work[0]["original_value"] == "missing shuttle"
    assert payload["unchanged_audit_json"] == AUDIT
    assert usage_ledger.removal_repair_attempted(active)
    assert usage_ledger.evidence_refusal(active) is None
    assert repair.completion_check(active)["findings"] == []


@pytest.mark.parametrize("response,truncated", [(text(CURRENT), False), (text(ORIGINAL), True),
                                                 ("I documented the deletion in the report.", False)])
def test_unsuccessful_response_preserves_records_counts_charge_and_terminal_state(active, response, truncated):
    original_bytes = active.full_path.read_bytes(), active.core_path.read_bytes()
    client, usage = client_for(response, truncated=truncated), []
    out = repair.run(active, client, api._model_settings(), usage)
    assert out["findings"] and not out["changed"]
    assert out["final"]["unfounded"] == 1
    assert original_bytes == (active.full_path.read_bytes(), active.core_path.read_bytes())
    assert len(usage) == 1 and usage[0]["output_tokens"] is not None
    assert usage_ledger.evidence_refusal(active)["reading"]["response_sha256"] == hashlib.sha256(response.encode()).hexdigest()
    with pytest.raises(usage_ledger.UsageLedgerError, match="terminal"):
        usage_ledger.begin_call(active, "report_regate", 1, "now")


def test_lost_response_does_not_refresh_the_allowance(active):
    call = usage_ledger.begin_call(active, repair.PHASE, 1, "now")
    usage_ledger.cancel_call(active, call)
    client = client_for(text(ORIGINAL))
    out = repair.run(active, client, api._model_settings(), [])
    assert out["findings"][0]["kind"] == "removal_repair_exhausted"
    assert client.messages.calls == []


def test_interrupted_delivery_stops_resume_before_generation_phases(active):
    identifier = usage_ledger.begin_call(active, repair.PHASE, 1, "now")
    usage_ledger.cancel_call(active, identifier)
    client = FakeClient()
    with pytest.raises(usage_ledger.UsageLedgerError, match="removal repair admission"):
        api.execute(active, client=client)
    assert client.messages.calls == []


def test_candidate_validation_failure_cannot_replace_records(active, monkeypatch):
    monkeypatch.setattr(api, "_validator_lines", lambda *a: (["required field missing"], None))
    before = active.full_path.read_bytes(), active.core_path.read_bytes()
    out = repair.run(active, client_for(text(ORIGINAL)), api._model_settings(), [])
    assert "does not validate" in out["findings"][0]["detail"]
    assert before == (active.full_path.read_bytes(), active.core_path.read_bytes())


def test_cli_plan_records_conditional_repair_and_payload_policy(external):
    result = CliRunner().invoke(cli, ["api", "plan", "--project", external.project,
        "--label", "new-removal-condition", "--bundle", str(external.bundle), "--manifest", "none",
        "--condition", "generic", "--removal-repair-version", "1", "--json"])
    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["removal_repair_version"] == 1
    assert any("removal_repair_full" in row for row in plan["conditional_calls"])


@pytest.mark.parametrize("value", [False, 0, "", None])
def test_false_and_zero_restoration_is_typed(value):
    original = {**ORIGINAL, "released": value}
    before = repair.reading(text(original), text(ORIGINAL), AUDIT)
    if value is None or value == "":
        assert before["unfounded"] == 0
    else:
        assert before["unfounded"] == 1
        assert repair.restored_candidate(text(original), text(ORIGINAL), AUDIT, text(original))["unfounded"] == 0
        with pytest.raises(ValueError):
            repair.restored_candidate(text(original), text(ORIGINAL), AUDIT, text({**original, "released": str(value)}))


def test_missing_or_drifted_snapshot_is_unverified_and_never_spends(active):
    _, found = snapshot_store.read_latest(active.metadata_dir, active.project, f"{active.project}_full.yaml", spec=active)
    found[0].write_text(text(CURRENT))
    client = client_for(text(ORIGINAL))
    out = repair.run(active, client, api._model_settings(), [])
    assert not out["checked"] and out["findings"][0]["kind"] == "removal_inputs_unusable"
    assert client.messages.calls == []
    assert usage_ledger.evidence_refusal(active)


def test_concurrent_record_edit_is_not_overwritten_by_restoration(active, monkeypatch):
    changed = {**CURRENT, "description": "New concurrent text"}
    client = client_for(text(ORIGINAL))
    create = client.messages.create
    def mutate(**kwargs):
        response = create(**kwargs)
        active.full_path.write_text(text(changed))
        return response
    monkeypatch.setattr(client.messages, "create", mutate)
    out = repair.run(active, client, api._model_settings(), [])
    assert out["findings"] and "changed during" in out["findings"][0]["detail"]
    assert yaml.safe_load(active.full_path.read_text()) == changed


class GeneratingMessages(FakeMessages):
    def __init__(self, restore):
        super().__init__()
        self.restore = restore

    def create(self, **kwargs):
        if kwargs["system"] == repair.policy_text():
            self.calls.append(kwargs)
            return FakeResponse(text(ORIGINAL if self.restore else CURRENT))
        response = super().create(**kwargs)
        blob = " ".join(part.get("text", "") for part in kwargs["messages"][0]["content"])
        phase = next((name for name, instruction in api.PHASE_INSTRUCTIONS.items() if instruction in blob), None)
        if phase in {"full", "reconcile_full"}:
            return FakeResponse(text(ORIGINAL if phase == "full" else CURRENT))
        return response


@pytest.mark.parametrize("restore", [True, False])
def test_execute_routes_real_removals_and_resume_preserves_outcome(external, restore):
    # Real generation driver, LinkML validation, derivation, provenance and
    # ledger paths; only transport responses are synthetic.
    spec = replace(external, condition="generic", removal_repair_version=1)
    client = FakeClient()
    client.messages = GeneratingMessages(restore)
    if restore:
        result = api.execute(spec, client=client)
        assert not result["validation_problems"]
        assert result["checks"]["removal_repair"]["changed"]
        assert yaml.safe_load(spec.full_path.read_text()) == ORIGINAL
        record = yaml.safe_load(spec.provenance_path.read_text())
        assert record["removals"]["unfounded"] == 0
        assert record["core_derivation"]["phase"] == "removal_repair_core"
        assert [row["phase"] for row in record["api_usage"]][-2:] == [repair.PHASE, "report_after_repair"]
        assert not api._progress_path(spec).exists()
        before = spec.provenance_path.read_bytes()
        second = FakeClient()
        resumed = api.execute(replace(spec), client=second)
        assert resumed["already_complete"] and not second.messages.calls
        assert resumed["checks"]["removal_repair"]["final"]["unfounded"] == 0
        assert spec.provenance_path.read_bytes() == before
    else:
        with pytest.raises(RuntimeError, match="removal_repair_rejected"):
            api.execute(spec, client=client)
        record = yaml.safe_load(spec.provenance_path.read_text())
        assert record["removals"]["unfounded"] == 1
        assert record["removal_repair"]["findings"] and api._progress_path(spec).exists()
        assert record["api_usage"][-1]["phase"] == repair.PHASE
        # Even a local 'repair' after refusal cannot erase the terminal run.
        spec.full_path.write_text(text(ORIGINAL))
        second = FakeClient()
        with pytest.raises(RuntimeError, match="removal_repair_rejected"):
            api.execute(replace(spec), client=second)
        assert not second.messages.calls


def test_final_check_catches_record_drift_during_report_refresh(external, monkeypatch):
    spec = replace(external, condition="generic", removal_repair_version=1)
    client = FakeClient()
    client.messages = GeneratingMessages(True)
    monkeypatch.setattr(api, "_validator_lines", lambda *a: ([], None))
    regenerate = api._regenerate_report
    def drifting_report(*args, **kwargs):
        result = regenerate(*args, **kwargs)
        spec.full_path.write_text(text(CURRENT))
        return result
    monkeypatch.setattr(api, "_regenerate_report", drifting_report)
    with pytest.raises(RuntimeError, match="unfounded_removals"):
        api.execute(spec, client=client)
    record = yaml.safe_load(spec.provenance_path.read_text())
    assert record["removals"]["unfounded"] == 1
    assert record["removal_repair"]["findings"] == [{"kind": "unfounded_removals", "count": 1}]
    assert usage_ledger.evidence_refusal(spec)["reading"]["final"]["unfounded"] == 1


@pytest.mark.parametrize("delivered", [False, True])
def test_interruption_after_restoration_cannot_skip_or_buy_a_second_report_refresh(external, monkeypatch, delivered):
    spec = replace(external, condition="generic", removal_repair_version=1)
    client = FakeClient()
    client.messages = GeneratingMessages(True)
    monkeypatch.setattr(api, "_validator_lines", lambda *a: ([], None))
    regenerate = api._regenerate_report
    def interrupted_report(*args, **kwargs):
        if delivered:
            assert regenerate(*args, **kwargs)
        raise KeyboardInterrupt("interrupted after accepted restoration, before refresh")
    monkeypatch.setattr(api, "_regenerate_report", interrupted_report)
    with pytest.raises(KeyboardInterrupt):
        api.execute(spec, client=client)
    assert yaml.safe_load(spec.full_path.read_text()) == ORIGINAL
    second = FakeClient()
    with pytest.raises(usage_ledger.UsageLedgerError, match="report refresh"):
        api.execute(replace(spec), client=second)
    assert second.messages.calls == []


def test_truncated_report_after_restoration_remains_terminal_with_its_charge(external, monkeypatch):
    spec = replace(external, condition="generic", removal_repair_version=1)
    client = FakeClient()
    client.messages = GeneratingMessages(True)
    monkeypatch.setattr(api, "_validator_lines", lambda *a: ([], None))
    create = client.messages.create
    restored = False
    def response(**kwargs):
        nonlocal restored
        out = create(**kwargs)
        if restored:
            out.stop_reason = "max_tokens"
        if kwargs["system"] == repair.policy_text():
            restored = True
        return out
    monkeypatch.setattr(client.messages, "create", response)
    with pytest.raises(RuntimeError, match="removal_report_refresh_failed"):
        api.execute(spec, client=client)
    record = yaml.safe_load(spec.provenance_path.read_text())
    assert record["removals"]["unfounded"] == 0
    assert record["removal_repair"]["before"]["unfounded"] == 1
    assert record["api_usage"][-1]["phase"] == "report_after_repair"
    assert record["api_usage"][-1]["stop_reason"] == "max_tokens"
    second = FakeClient()
    with pytest.raises(RuntimeError, match="removal_report_refresh_failed"):
        api.execute(replace(spec), client=second)
    assert second.messages.calls == []


def test_completed_refresh_recovers_original_outcome_without_new_spend(external, monkeypatch):
    spec = replace(external, condition="generic", removal_repair_version=1)
    client = FakeClient()
    client.messages = GeneratingMessages(True)
    monkeypatch.setattr(api, "_validator_lines", lambda *a: ([], None))
    grounding = api.grounding_block
    def interrupted_after_report(*args, **kwargs):
        raise KeyboardInterrupt("after repair and refresh, before final provenance")
    monkeypatch.setattr(api, "grounding_block", interrupted_after_report)
    with pytest.raises(KeyboardInterrupt):
        api.execute(spec, client=client)
    monkeypatch.setattr(api, "grounding_block", grounding)
    second = FakeClient()
    result = api.execute(replace(spec), client=second)
    assert second.messages.calls == []
    outcome = result["checks"]["removal_repair"]
    assert outcome["resumed"] and outcome["attempted"] and outcome["changed"]
    assert outcome["before"]["unfounded"] == 1 and outcome["final"]["unfounded"] == 0
    record = yaml.safe_load(spec.provenance_path.read_text())
    assert record["core_derivation"]["phase"] == "removal_repair_core"
    assert [row["phase"] for row in record["api_usage"]][-2:] == [repair.PHASE, "report_after_repair"]
    assert record["removal_repair"]["response_sha256"] == outcome["response_sha256"]
    with pytest.raises(usage_ledger.UsageLedgerError, match="no second refresh"):
        usage_ledger.begin_call(spec, "report_after_repair", 1, "later")
