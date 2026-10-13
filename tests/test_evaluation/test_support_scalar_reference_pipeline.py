"""Opt-in captured pipeline controls; invented replies are not calibration."""
import copy
import json
from pathlib import Path
import socket
from urllib.parse import urlsplit

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema import support_calibration as calibration
from data_sheets_schema import support_plan, support_targets as targets
from data_sheets_schema import top_level_fitness_results as fitness
from data_sheets_schema.cli.evaluate import evaluate
from tests.test_evaluation.test_support_plan import fixture, rewrite_roster  # noqa: F401
from tests.test_evaluation.test_nested_support_plan import build, change_record
from tests.test_evaluation.test_nested_support_results import (
    native, replace_artifact, save_manifest,
)
from tests.test_evaluation.test_nested_support_execution import peer, declaration  # noqa: F401

POLICY = "relationship_edge_and_attribute_value_inline_class_strings_v1"
INSTRUMENT = "support_targets v3 scalar-reference draft (#4902)"
_CONNECT = socket.socket.connect


def artifact(directory, pin):
    return json.loads((directory / "artifacts" / pin["sha256"]).read_bytes())


def target_row(manifest, pointer, axis=targets.AXIS):
    rows = [t for t in manifest["targets"] if t["axis"] == axis and t["pointer"] == pointer]
    assert len(rows) == 1
    return rows[0]


def select(row, attempt="one"):
    return [{"target_id": row["id"], "attempt_id": attempt}]


def prepare(directory, manifest, output, pointer="/creators/0"):
    row = target_row(manifest, pointer)
    value = saved.prepare(directory, output, selections=select(row), protocol=saved.FORMAT)
    return row, value


def pending_controls(registration, descriptor):
    selection = descriptor["selections"][0]
    binding = selection["binding"]
    return {"format": calibration.CONTROLS_FORMAT, "calibration_id": "unlabelled-software-control",
            "registration_sha256": support_plan.sha256((registration / "registration.json").read_bytes()),
            "controls": [{"control_id": "pending-1", "target_id": selection["target_id"],
                "attempt_id": selection["attempt_id"], "kind": binding["kind"], "pointer": binding["pointer"],
                "binding_sha256": support_plan.sha256(support_plan.canonical(binding)),
                "review_status": "pending", "expected_verdict": None, "defect_class": None,
                "finding": {"reference": "synthetic://unlabelled-case", "sha256": "1" * 64},
                "review": None}]}


@pytest.fixture
def scalar_plan(fixture):
    root, directory = fixture
    change_record(root, {"creators": ["  Dana and 李 / ~1  "]})
    manifest = build(fixture, relationship_policy=POLICY, max_tokens=417)
    return root, directory, manifest


def test_actual_cli_policy_materialization_and_fitness_are_bound(fixture, monkeypatch, tmp_path):
    root, directory = fixture
    change_record(root, {"creators": ["Dana and Lee"]})
    original = support_plan.build_plan
    monkeypatch.setattr(support_plan, "build_plan", lambda *a, **kw: original(*a, root=root, **kw))
    result = CliRunner().invoke(evaluate, ["support-plan", "--roster", str(root / "roster.json"),
        "--output", str(directory), "--profile", "neutral", "--schema", str(root / "schema.yaml"),
        "--model", "judge", "--max-tokens", "417", "--plan-version", "2", "--artifact-kind", "full",
        "--relationship-policy", "inline-class-strings"])
    assert result.exit_code == 0, result.output
    assert "BLOCKED for paid use" in result.output
    manifest = json.loads((directory / "manifest.json").read_bytes())
    instrument = manifest["instruments"][targets.AXIS]
    assert instrument["policy"] == POLICY and instrument["name"] == INSTRUMENT
    row = target_row(manifest, "/creators/0")
    request = support_plan.materialize_request(directory, row["id"])
    payload = json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    assert payload["policy"] == POLICY
    assert yaml.safe_load(payload["value_yaml"]) == "Dana and Lee"
    assert request["system"].encode() == (directory / "artifacts" / instrument["system"]["sha256"]).read_bytes()
    assert request["system"] != targets.SYSTEM
    assert manifest["readiness"]["ready_for_paid_run"] is False
    assert {"instrument_review_3342", "context_projection_review_3342", "paid_run_authorization",
            "independent_empirical_calibration_3343"} <= set(manifest["readiness"]["blockers"])
    assert manifest["counts"]["support_by_kind"] == {"relationship_edge": 1, "attribute_value": 4}
    assert manifest["counts"]["fitness_top_level"] == 5
    issue = {"record_id": manifest["records"][0]["id"], "pointer": "/creators/0",
             "kind": "relationship_edge", "code": "inline_class_requires_mapping", "range": "Creator"}
    assert manifest["representation_issues"] == [issue]
    assert manifest["counts"]["representation_issue_count"] == 1
    assert manifest["records"][0]["representation_issue_count"] == 1
    inv = artifact(directory, manifest["records"][0]["inventory"])
    assert inv["representation_issues"] == [{k: v for k, v in issue.items() if k != "record_id"}]
    # The separate fitness consumer must accept this exact opt-in plan too.
    fit_path = tmp_path / "fitness-descriptor"
    fit_rows = [t for t in manifest["targets"] if t["axis"] == "fitness"]
    desc = fitness.prepare(directory, fit_path,
        selections=[{"target_id": t["id"], "attempt_id": f"fit-{i}"} for i, t in enumerate(fit_rows)],
        protocol=fitness.FORMAT)
    assert len(desc["selections"]) == 5
    index = fitness.build_index(fit_path, [], tmp_path / "fitness-index")
    assert index["strata"]["fitness_top_level"] == {"selected": 5, "missing": 5, "accepted": 0, "rejected": 0}
    assert index["scientific_scoring_eligible"] is False


@pytest.mark.parametrize("version,policy", [(1, POLICY), (2, "unknown-policy")])
def test_invalid_policy_route_refuses_before_writing(fixture, version, policy):
    root, output = fixture
    options = {"artifact_kind": "full"} if version == 2 else {}
    with pytest.raises(ValueError, match="policy|version"):
        support_plan.build_plan(root / "roster.json", output, root=root, profile="neutral", model="judge",
            schema_path=root / "schema.yaml", plan_version=version, relationship_policy=policy, **options)
    assert not output.exists()


def test_strict_and_optin_common_ids_cannot_replay_or_cross_fitness_join(fixture, tmp_path):
    root, strict_dir = fixture
    change_record(root, {"creators": ["Dana"]})
    strict = build(fixture, max_tokens=417)
    opt_dir = tmp_path / "optin-plan"
    opt = build((root, opt_dir), relationship_policy=POLICY, max_tokens=417)
    assert strict["records"][0]["id"] == opt["records"][0]["id"]
    a, b = target_row(strict, "/title"), target_row(opt, "/title")
    assert a["id"] == b["id"] and a["request_sha256"] != b["request_sha256"]
    strict_desc, opt_desc = tmp_path / "strict-descriptor", tmp_path / "optin-descriptor"
    prepare(strict_dir, strict, strict_desc, "/title")
    prepare(opt_dir, opt, opt_desc, "/title")
    envelope = tmp_path / "old-response.json"
    envelope.write_bytes(saved.package_response((strict_desc / "descriptor.json").read_bytes(),
        attempt_id="one", native_message=support_plan.canonical(native())))
    accepted_path = tmp_path / "strict-accepted"
    accepted = saved.accept(strict_desc, envelope, accepted_path, attempt_id="one")
    assert accepted["assessment"]["status"] == "accepted"  # only invented response syntax
    refused = saved.accept(opt_desc, envelope, tmp_path / "optin-rejected", attempt_id="one")
    assert refused["assessment"]["status"] == "rejected"
    assert "response_envelope_descriptor_sha256_conflicts" in refused["assessment"]["problems"]
    with pytest.raises(ValueError, match="another descriptor"):
        saved.report(opt_desc, [accepted_path])
    opt_fit = tmp_path / "optin-fitness"
    fitness.prepare(opt_dir, opt_fit, selections=select(target_row(opt, "/title", "fitness")), protocol=fitness.FORMAT)
    output = tmp_path / "cross-policy-index"
    with pytest.raises(ValueError, match="same plan"):
        fitness.build_index(opt_fit, [], output, support_results=[accepted_path])
    assert not output.exists()
    # The policy isolation is symmetric even though logical IDs are unchanged.
    new_envelope = tmp_path / "new-response.json"
    new_envelope.write_bytes(saved.package_response((opt_desc / "descriptor.json").read_bytes(),
        attempt_id="one", native_message=support_plan.canonical(native())))
    opt_accepted_path = tmp_path / "optin-accepted"
    opt_accepted = saved.accept(opt_desc, new_envelope, opt_accepted_path, attempt_id="one")
    assert opt_accepted["assessment"]["status"] == "accepted"
    reverse = saved.accept(strict_desc, new_envelope, tmp_path / "strict-rejected", attempt_id="one")
    assert reverse["assessment"]["status"] == "rejected"
    assert "response_envelope_descriptor_sha256_conflicts" in reverse["assessment"]["problems"]
    with pytest.raises(ValueError, match="another descriptor"):
        saved.report(strict_desc, [opt_accepted_path])
    strict_fit = tmp_path / "strict-fitness"
    fitness.prepare(strict_dir, strict_fit, selections=select(target_row(strict, "/title", "fitness")),
        protocol=fitness.FORMAT)
    reverse_index = tmp_path / "reverse-policy-index"
    with pytest.raises(ValueError, match="same plan"):
        fitness.build_index(strict_fit, [], reverse_index, support_results=[opt_accepted_path])
    assert not reverse_index.exists()
    # Even with the same logical IDs, a strict control cannot bind the new request.
    reg_dir = tmp_path / "optin-registration"
    decl = tmp_path / "optin-declaration.json"
    decl.write_bytes(support_plan.canonical(declaration(
        {"url": "http://127.0.0.1:9/v1/messages"}, tmp_path / "never-run")))
    execution.prepare(opt_desc, decl, reg_dir)
    opt_description = json.loads((opt_desc / "descriptor.json").read_bytes())
    strict_description = json.loads((strict_desc / "descriptor.json").read_bytes())
    controls = pending_controls(reg_dir, opt_description)
    controls["controls"][0]["binding_sha256"] = support_plan.sha256(
        support_plan.canonical(strict_description["selections"][0]["binding"]))
    control_path = tmp_path / "wrong-policy-controls.json"
    control_path.write_bytes(support_plan.canonical(controls))
    bad_calibration = tmp_path / "wrong-policy-calibration"
    with pytest.raises(ValueError, match="binding"):
        calibration.prepare(reg_dir, control_path, bad_calibration)
    assert not bad_calibration.exists() and not (tmp_path / "never-run").exists()
    for old in [t for t in strict["targets"] if t["axis"] == "fitness"]:
        newer = target_row(opt, old["pointer"], "fitness")
        assert old["id"] == newer["id"] and old["request_sha256"] == newer["request_sha256"]
        assert support_plan.materialize_request(strict_dir, old["id"]) == support_plan.materialize_request(opt_dir, newer["id"])


@pytest.mark.parametrize("change", ["policy", "instrument", "system", "value", "context", "specification", "representation"])
def test_rehashed_plan_artifacts_cannot_replace_captured_semantics(scalar_plan, tmp_path, change):
    _root, directory, manifest = scalar_plan
    row = target_row(manifest, "/creators/0")
    if change == "policy":
        manifest["instruments"][targets.AXIS]["policy"] = targets.POLICY
    elif change == "instrument":
        manifest["instruments"][targets.AXIS]["name"] = targets.INSTRUMENT
    elif change == "system":
        system = manifest["instruments"][targets.AXIS]["system"]
        replacement = replace_artifact(directory, system, targets.SYSTEM.encode())
        manifest["instruments"][targets.AXIS]["system"] = replacement
        # Keep the selected request's independent pin consistent with its forged recipe.
        row["request_recipe"]["system"]["$text"] = replacement
        request = support_plan._expand(row["request_recipe"], directory)
        raw = support_plan.canonical(request)
        row["request_sha256"], row["request_bytes"] = support_plan.sha256(raw), len(raw)
    else:
        payload = artifact(directory, row["target_artifact"])
        if change == "value":
            payload["value"] = "Invented replacement"
            payload["value_yaml"] = yaml.safe_dump(payload["value"])
            payload["value_sha256"] = targets._digest(payload["value"])
            row["value_sha256"] = payload["value_sha256"]
        elif change == "context":
            payload["context"]["containing_entity"]["pointer"] = "/wrong-owner"
            payload["context_sha256"] = targets._digest(payload["context"])
            row["context_sha256"] = payload["context_sha256"]
        elif change == "representation":
            payload["representation"]["status"] = "schema_valid"
        else:
            payload["specification_ref"] = "0" * 64
            row["specification_ref"] = payload["specification_ref"]
        row["target_artifact"] = replace_artifact(directory, row["target_artifact"], support_plan.canonical(payload))
    save_manifest(directory, manifest)
    output = tmp_path / "forged-descriptor"
    with pytest.raises(ValueError):
        saved.prepare(directory, output, selections=select(row), protocol=saved.FORMAT)
    assert not output.exists()


def test_scalar_saved_result_is_portable_and_never_implies_schema_validity(scalar_plan, tmp_path, monkeypatch):
    root, directory, manifest = scalar_plan
    descriptor = tmp_path / "descriptor"
    _row, desc = prepare(directory, manifest, descriptor)
    binding = desc["selections"][0]["binding"]
    assert binding["policy"] == POLICY
    assert binding["representation"] == {"status": "schema_invalid_inline_class_string",
        "expected": "mapping", "observed": "str", "range": "Creator"}
    accounting = desc["representation_accounting"]
    assert accounting["verified_record_issue_count"] == accounting["selected_target_issue_count"] == 1
    assert accounting["selected_target_issues"] == [{**manifest["representation_issues"][0],
        "target_id": _row["id"], "attempt_id": "one"}]
    response = tmp_path / "response.json"
    response.write_bytes(saved.package_response((descriptor / "descriptor.json").read_bytes(),
        attempt_id="one", native_message=support_plan.canonical(native())))
    accepted = tmp_path / "accepted"
    value = saved.accept(descriptor, response, accepted, attempt_id="one")
    assert value["binding"] == binding
    assert value["assessment"]["status"] == "accepted"
    report = saved.report(descriptor, [accepted])
    assert report["full_record_schema_validation"] == "not_performed"
    assert report["scientific_accuracy"] == "unverified"
    assert report["all_planned_nested_targets_selected"] is False
    assert report["fitness"] == "separate_and_unscored"
    assert report["representation_accounting"] == accounting
    # Move original inputs out of their old locations; only copied evidence may be read.
    for path in (root, directory, descriptor):
        path.rename(path.with_name(path.name + "-unavailable"))
    original_read = Path.read_bytes
    def captured_only(path):
        assert path.is_relative_to(accepted), path
        return original_read(path)
    monkeypatch.setattr(Path, "read_bytes", captured_only)
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("offline readback connected"))
    assert saved.recheck(accepted) == value


def test_actual_http_and_pending_calibration_keep_bound_scalar_warning(
        scalar_plan, peer, tmp_path, monkeypatch):
    _root, directory, manifest = scalar_plan
    descriptor, registered, run = tmp_path / "descriptor", tmp_path / "registered", tmp_path / "run"
    row, desc = prepare(directory, manifest, descriptor)
    endpoint = urlsplit(peer["url"])
    def connect(sock, address):
        assert address == ("127.0.0.1", endpoint.port), "non-fixture network access"
        return _CONNECT(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_bytes(support_plan.canonical(declaration(peer, run)))
    reg = execution.prepare(descriptor, declaration_path, registered)
    controls = tmp_path / "controls.json"
    controls.write_bytes(support_plan.canonical(pending_controls(registered, desc)))
    cal_path = tmp_path / "pending-calibration"
    cal = calibration.prepare(registered, controls, cal_path)
    missing = calibration.report(cal_path)
    assert missing["rows"][0]["expected_verdict"] is None
    assert missing["rows"][0]["observed_verdict"] is None
    assert missing["rows"][0]["scored"] is False
    assert missing["rows"][0]["policy"] == POLICY
    assert missing["rows"][0]["representation"] == desc["selections"][0]["binding"]["representation"]
    assert missing["totals"]["unresolved_controls"] == 1
    assert missing["representation_counts"] == {"basis": "selected_relationship_controls",
        "schema_invalid_inline_class_string": 1, "other_relationship_edges": 0}
    assert missing["representation_groups"] == []
    assert peer["requests"] == []
    outcome = execution.run(registered)
    assert outcome["admitted_calls"] == 1 and outcome["all_selected_accepted"] is True
    assert len(peer["requests"]) == 1
    expected = (registered / "artifacts" / reg["requests"][0]["effective_request"]["sha256"]).read_bytes()
    assert peer["requests"][0]["raw"] == expected
    body = json.loads(expected)
    payload = json.loads(body["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    assert payload["policy"] == POLICY and payload["pointer"] == row["pointer"]
    warning = {"status": "schema_invalid_inline_class_string", "expected": "mapping",
               "observed": "str", "range": "Creator"}
    assert payload["representation"] == warning
    assert desc["selections"][0]["binding"]["representation"] == warning
    assert outcome["rows"][0]["saved_result"]["binding"]["representation"] == warning
    assert yaml.safe_load(payload["value_yaml"]) == "  Dana and 李 / ~1  "
    assert body["system"] != targets.SYSTEM and body["stream"] is False
    assessment = calibration.report(cal_path, run, output=tmp_path / "calibration-report")
    assert assessment["rows"][0]["scored"] is False
    assert assessment["rows"][0]["policy"] == POLICY
    assert assessment["rows"][0]["representation"] == warning
    assert assessment["rows"][0]["expected_verdict"] is None
    assert assessment["rows"][0]["verdict_agreement"] is None
    assert assessment["scientific_eligibility"] is False
    assert assessment["totals"]["unresolved_controls"] == 1
    assert assessment["representation_counts"] == missing["representation_counts"]
    assert assessment["representation_groups"] == []
    monkeypatch.setattr(execution, "_dispatch", lambda *_: pytest.fail("offline recheck dispatched"))
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("offline recheck connected"))
    assert execution.recheck(run) == outcome
    assert calibration.recheck(cal_path) == cal
    assert calibration.recheck(tmp_path / "calibration-report") == assessment
    assert len(peer["requests"]) == 1


@pytest.mark.parametrize("change", ["remove", "different_pointer", "change_range"])
def test_rehashed_inventory_representation_ledger_is_rebuilt(scalar_plan, tmp_path, change):
    _root, directory, manifest = scalar_plan
    record = manifest["records"][0]
    captured = artifact(directory, record["inventory"])
    if change == "remove":
        captured["representation_issues"] = []
    elif change == "different_pointer":
        captured["representation_issues"][0]["pointer"] = "/title"
    else:
        captured["representation_issues"][0]["range"] = "UnrelatedRange"
    replacement = replace_artifact(directory, record["inventory"], support_plan.canonical(captured))
    record["inventory"] = replacement
    for row in manifest["targets"]:
        if row["axis"] == targets.AXIS:
            row["inventory_artifact"] = replacement
    save_manifest(directory, manifest)
    output = tmp_path / "forged-inventory"
    with pytest.raises(ValueError, match="inventory"):
        prepare(directory, manifest, output)
    assert not output.exists()


@pytest.mark.parametrize("location", ["record", "global"])
def test_boolean_cannot_replace_new_representation_count(scalar_plan, tmp_path, location):
    _root, directory, manifest = scalar_plan
    if location == "record":
        manifest["records"][0]["representation_issue_count"] = True
    else:
        manifest["counts"]["representation_issue_count"] = True
    save_manifest(directory, manifest)
    output = tmp_path / "boolean-count"
    with pytest.raises(ValueError):
        prepare(directory, manifest, output)
    assert not output.exists()


def test_selected_target_record_and_declared_plan_warning_scopes_are_distinct(fixture, tmp_path):
    root, directory = fixture
    change_record(root, {"creators": ["Dana"]})
    (root / "second.yaml").write_bytes((root / "record.yaml").read_bytes())
    provenance = yaml.safe_load((root / "provenance.yaml").read_bytes())
    provenance["run"]["label"] = "second_rep1"
    (root / "second-provenance.yaml").write_text(yaml.safe_dump(provenance))
    def second_record(roster):
        jobs = copy.deepcopy(roster["jobs"])
        for job in jobs:
            job.update(id="second_" + job["id"], input="second.yaml", label="second_rep1",
                       provenance="second-provenance.yaml")
        roster["jobs"] += jobs
        roster["pinned_files"]["second.yaml"] = support_plan.sha256((root / "second.yaml").read_bytes())
    rewrite_roster(root, second_record)
    manifest = build(fixture, relationship_policy=POLICY, max_tokens=417)
    record = next(r for r in manifest["records"] if r["record"]["path"] == "record.yaml")
    row = next(t for t in manifest["targets"] if t["record_id"] == record["id"]
               and t["axis"] == targets.AXIS and t["pointer"] == "/title")
    descriptor = tmp_path / "one-title-descriptor"
    desc = saved.prepare(directory, descriptor, selections=select(row), protocol=saved.FORMAT)
    report = saved.report(descriptor, [])
    expected = {"policy": POLICY, "verified_record_ids": [record["id"]],
        "verified_record_issues": record["representation_issues"], "verified_record_issue_count": 1,
        "selected_target_issues": [], "selected_target_issue_count": 0,
        "full_plan_declared_issue_count": 2, "unselected_record_evidence": "not_reconstructed"}
    assert desc["representation_accounting"] == expected
    assert report["representation_accounting"] == expected
    assert report["full_plan_declared_counts"]["representation_issue_count"] == 2
    assert desc["selections"][0]["binding"]["representation"] is None
    assert desc["selections"][0]["binding"]["policy"] == POLICY
    assert report["all_planned_nested_targets_selected"] is False
    assert report["selected_counts"]["attribute_value"]["missing"] == 1
    assert report["selected_counts"]["relationship_edge"]["selected"] == 0


def test_actual_old_saved_descriptor_and_pending_calibration_replay_portably(tmp_path, monkeypatch):
    """Recheck true pre-edit artifacts, including their unchanged old path pins."""
    import hashlib
    import shutil
    frozen = Path(__file__).parents[1] / "fixtures/support_strict_v2"
    pins = json.loads((frozen / "saved-pins.json").read_bytes())
    assert pins["source_commit"] == "f2c050c1833c9a5c54c4373a02f6230578a27fe4"
    for row in pins["files"]:
        raw = (frozen / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    portable = tmp_path / "old-capture-relocated"
    shutil.copytree(frozen / "ordinary_saved", portable)
    old_calibration = json.loads((portable / "calibration.json").read_bytes())
    old_descriptor = json.loads((portable / "descriptor.json").read_bytes())
    original_read = Path.read_bytes
    def captured_only(path):
        assert path.is_relative_to(portable), "historical recheck read outside relocated captured evidence"
        return original_read(path)
    monkeypatch.setattr(Path, "read_bytes", captured_only)
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("historical recheck connected"))
    monkeypatch.setattr(execution, "_dispatch", lambda *_: pytest.fail("historical recheck dispatched"))
    assert calibration.recheck(portable) == old_calibration
    report = saved.report(portable, [])
    assert report["descriptor"]["sha256"] == support_plan.sha256(support_plan.canonical(old_descriptor) + b"\n")
    assert report["readiness"] == old_descriptor["readiness"]
    assert sum(row["missing"] for row in report["selected_counts"].values()) == len(old_descriptor["selections"])
    old_result = calibration.report(portable)
    assert "representation_counts" not in old_result and "representation_groups" not in old_result
    assert "representation_accounting" not in report
    assert "representation_accounting" not in old_descriptor
    assert all("representation" not in s["binding"] and "policy" not in s["binding"]
               for s in old_descriptor["selections"])


@pytest.mark.parametrize("pending_attribute", [False, True])
def test_representation_subgroups_keep_global_unresolved_denominator_and_reconstruct(
        fixture, tmp_path, monkeypatch, pending_attribute):
    """Invented responses/labels exercise arithmetic; they supply no human review."""
    from tests.test_evaluation.test_nested_support_execution import reply
    root, directory = fixture
    change_record(root, {"creators": ["Dana", {"name": "Lee"}]})
    manifest = build(fixture, relationship_policy=POLICY, max_tokens=417)
    descriptor, registration, run = tmp_path / "descriptor", tmp_path / "registration", tmp_path / "run"
    pointers = ["/creators/0", "/creators/1", "/title"]
    selections = [{"target_id": target_row(manifest, pointer)["id"], "attempt_id": f"case-{i}"}
                  for i, pointer in enumerate(pointers)]
    desc = saved.prepare(directory, descriptor, selections=selections, protocol=saved.FORMAT)
    declared = declaration({"url": "http://127.0.0.1:9/v1/messages"}, run)
    declared["limits"].update(max_calls=3, total_response_bytes=150_003,
        input_scheduling_threshold=300, output_scheduling_threshold=1251)
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_bytes(support_plan.canonical(declared))
    execution.prepare(descriptor, declaration_path, registration)
    controls = {"format": calibration.CONTROLS_FORMAT, "calibration_id": "invented-subgroups",
        "registration_sha256": support_plan.sha256((registration / "registration.json").read_bytes()),
        "controls": []}
    for i, selection in enumerate(desc["selections"]):
        binding = selection["binding"]
        pending = pending_attribute and binding["pointer"] == "/title"
        controls["controls"].append({"control_id": f"invented-{i}", "target_id": selection["target_id"],
            "attempt_id": selection["attempt_id"], "kind": binding["kind"], "pointer": binding["pointer"],
            "binding_sha256": support_plan.sha256(support_plan.canonical(binding)),
            "review_status": "pending" if pending else "synthetic",
            "expected_verdict": None if pending else "unsupported" if binding["pointer"] == "/creators/0" else "supported",
            "defect_class": None if pending else "invented scalar" if binding["pointer"] == "/creators/0" else "invented negative",
            "finding": {"reference": f"synthetic://subgroup/{i}", "sha256": "1" * 64}, "review": None})
    controls_path = tmp_path / "controls.json"
    controls_path.write_bytes(support_plan.canonical(controls))
    cal_path = tmp_path / "calibration"
    calibration.prepare(registration, controls_path, cal_path)
    dispatches = []
    def dispatch(*args):
        dispatches.append(args)
        return {"status_code": 200, "request_id": "invented-response", "body_complete": True,
                "failure": None, "duration_seconds": 0, "stage": "complete"}, support_plan.canonical(reply())
    monkeypatch.setattr(execution, "_dispatch", dispatch)
    outcome = execution.run(registration)
    assert outcome["all_selected_accepted"] is True and len(dispatches) == 3
    report_path = tmp_path / "subgroup-report"
    result = calibration.report(cal_path, run, output=report_path)
    assert result["representation_counts"] == {"basis": "selected_relationship_controls",
        "schema_invalid_inline_class_string": 1, "other_relationship_edges": 1}
    assert result["totals"]["controls"] == 3
    assert result["totals"]["unresolved_controls"] == int(pending_attribute)
    assert result["scientific_eligibility"] is False and result["evidence_scope"] == "software_only"
    grouped = {(g["representation_status"], g["defect_class"]): g
               for g in result["representation_groups"]}
    assert set(grouped) == {("schema_invalid_inline_class_string", None),
        ("schema_invalid_inline_class_string", "invented scalar"),
        ("other_relationship_edges", None), ("other_relationship_edges", "invented negative")}
    for (status, defect), group in grouped.items():
        assert group["scope"] == "synthetic" and group["kind"] == "relationship_edge"
        assert group["controls"] == group["observed_controls"] == 1
        assert group["unresolved_controls"] == 0  # pending attribute is elsewhere
        assert group["positive_controls"] == int(status == "schema_invalid_inline_class_string")
        assert group["negative_controls"] == int(status == "other_relationship_edges")
        expected_conditional = ({"recall": 0.0, "false_positive_rate": None, "verdict_agreement_rate": 0.0}
            if status == "schema_invalid_inline_class_string" else
            {"recall": None, "false_positive_rate": 0.0, "verdict_agreement_rate": 1.0})
        assert group["conditional_observed_rates"] == expected_conditional
        for metric, rate in expected_conditional.items():
            assert group[metric] == (None if pending_attribute else rate)
    all_edges = [g for g in result["groups"] if g["kind"] == "relationship_edge" and g["defect_class"] is None]
    assert len(all_edges) == 1 and all_edges[0]["controls"] == 2
    assert all_edges[0]["observed_controls"] == 2
    assert all("schema_valid" not in key for key in result["representation_counts"])
    monkeypatch.setattr(execution, "_dispatch", lambda *_: pytest.fail("subgroup readback dispatched"))
    assert calibration.recheck(report_path) == result
    raw_path = report_path / "calibration.json"
    original = raw_path.read_bytes()
    for field in ("representation_counts", "representation_groups"):
        forged = json.loads(original)
        if field == "representation_counts":
            forged["result"][field]["other_relationship_edges"] += 1
        else:
            forged["result"][field][0]["controls"] += 1
        raw_path.write_bytes(support_plan.canonical(forged) + b"\n")
        with pytest.raises(ValueError, match="reconstructed"):
            calibration.recheck(report_path)
        raw_path.write_bytes(original)
    assert calibration.recheck(report_path) == result
