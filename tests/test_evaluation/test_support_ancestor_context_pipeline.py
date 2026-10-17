"""Captured ancestor-context request authority; invented replies are not labels."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
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
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401
from tests.test_evaluation.test_nested_support_plan import build, change_record
from tests.test_evaluation.test_nested_support_results import native, replace_artifact, save_manifest
from tests.test_evaluation.test_nested_support_execution import peer, declaration  # noqa: F401
from tests.test_evaluation.test_support_scalar_reference_pipeline import artifact, target_row, select, pending_controls

LEGACY = "nearest_owner_and_ancestor_identity_v1"
ANCESTORS = "ancestor_scalar_qualifiers_v1"
SCALAR = "relationship_edge_and_attribute_value_inline_class_strings_v1"
POINTER = "/creators/0/affiliations/0/name"
_CONNECT = socket.socket.connect


@pytest.fixture
def context_case(fixture):
    root, directory = fixture
    schema = yaml.safe_load((root / "schema.yaml").read_bytes())
    schema["classes"]["Creator"]["attributes"].update({
        "source_caveats": {"range": "string"},
        "affiliations": {"range": "Organization", "multivalued": True, "inlined_as_list": True},
    })
    schema["classes"]["Organization"] = {"attributes": {"name": {"range": "string"}}}
    (root / "schema.yaml").write_text(yaml.safe_dump(schema, sort_keys=False))
    change_record(root, {"notes": "Collection context is not inherited evidence.", "creators": [
        {"name": "Dana", "source_caveats": "The organization name is attributed to Document A.",
         "affiliations": [{"name": "Harbor Institute"}]}, "Original scalar role"]})
    return root, directory


def plan_case(pair, *, relationship=targets.POLICY, context=ANCESTORS):
    return build(pair, relationship_policy=relationship, context_policy=context, max_tokens=417)


def describe(directory, manifest, destination):
    row = target_row(manifest, POINTER)
    value = saved.prepare(directory, destination, selections=select(row), protocol=saved.FORMAT)
    return row, value


@pytest.mark.parametrize("relationship,relationship_cli", [(targets.POLICY, "strict"), (SCALAR, "inline-class-strings")])
@pytest.mark.parametrize("context,context_cli", [(LEGACY, "nearest-owner"), (ANCESTORS, "ancestor-qualifiers")])
def test_cli_materializes_all_four_bound_contracts(context_case, monkeypatch, relationship,
                                                  relationship_cli, context, context_cli):
    root, directory = context_case
    original = support_plan.build_plan
    monkeypatch.setattr(support_plan, "build_plan", lambda *args, **kw: original(*args, root=root, **kw))
    result = CliRunner().invoke(evaluate, ["support-plan", "--roster", str(root / "roster.json"),
        "--output", str(directory), "--profile", "neutral", "--schema", str(root / "schema.yaml"),
        "--model", "judge", "--max-tokens", "417", "--plan-version", "2", "--artifact-kind", "full",
        "--relationship-policy", relationship_cli, "--context-policy", context_cli])
    assert result.exit_code == 0, result.output
    manifest = json.loads((directory / "manifest.json").read_bytes())
    instrument = manifest["instruments"][targets.AXIS]
    assert instrument["policy"] == relationship
    assert instrument.get("context_policy") == (ANCESTORS if context == ANCESTORS else None)
    row = target_row(manifest, POINTER)
    request = support_plan.materialize_request(directory, row["id"])
    sent = json.loads(request["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    if context == ANCESTORS:
        assert "Document A" in sent["context"]["ancestors"][1]["value_yaml"]
        assert sent["context_policy"] == ANCESTORS
    else:
        assert "context_policy" not in sent and "value_yaml" not in sent["context"]["ancestors"][1]
    assert request["system"].encode() == (directory / "artifacts" / instrument["system"]["sha256"]).read_bytes()
    assert manifest["readiness"]["ready_for_paid_run"] is False
    assert {"context_projection_review_3342", "independent_empirical_calibration_3343", "paid_run_authorization"} <= set(manifest["readiness"]["blockers"])
    assert ("representation_issues" in manifest) == (relationship == SCALAR)


def test_cli_version_one_refuses_nondefault_context_before_publication(context_case, monkeypatch):
    root, directory = context_case
    original = support_plan.build_plan
    monkeypatch.setattr(support_plan, "build_plan", lambda *args, **kw: original(*args, root=root, **kw))
    result = CliRunner().invoke(evaluate, ["support-plan", "--roster", str(root / "roster.json"),
        "--output", str(directory), "--profile", "neutral", "--schema", str(root / "schema.yaml"),
        "--model", "judge", "--plan-version", "1", "--context-policy", "ancestor-qualifiers"])
    assert result.exit_code != 0 and "context" in result.output.lower()
    assert not directory.exists()


@pytest.mark.parametrize("relationship", [targets.POLICY, SCALAR])
def test_same_ids_reject_cross_context_responses_fitness_and_controls_both_directions(context_case, tmp_path, relationship):
    root, old_dir = context_case
    new_dir = tmp_path / "expanded-plan"
    old = plan_case(context_case, relationship=relationship, context=LEGACY)
    new = plan_case((root, new_dir), relationship=relationship)
    assert old["records"][0]["id"] == new["records"][0]["id"]
    old_row, new_row = target_row(old, POINTER), target_row(new, POINTER)
    assert old_row["id"] == new_row["id"] and old_row["request_sha256"] != new_row["request_sha256"]
    cases = []
    for name, directory, manifest in [("legacy", old_dir, old), ("expanded", new_dir, new)]:
        descriptor = tmp_path / (name + "-descriptor")
        _, desc = describe(directory, manifest, descriptor)
        response = tmp_path / (name + "-response.json")
        response.write_bytes(saved.package_response((descriptor / "descriptor.json").read_bytes(),
            attempt_id="one", native_message=support_plan.canonical(native())))
        accepted = tmp_path / (name + "-accepted")
        assert saved.accept(descriptor, response, accepted, attempt_id="one")["assessment"]["status"] == "accepted"
        fit = tmp_path / (name + "-fitness")
        fitness.prepare(directory, fit, selections=select(target_row(manifest, "/creators", "fitness")), protocol=fitness.FORMAT)
        reg, run = tmp_path / (name + "-registration"), tmp_path / (name + "-run")
        declaration_path = tmp_path / (name + "-declaration.json")
        declaration_path.write_bytes(support_plan.canonical(declaration({"url": "http://127.0.0.1:9/v1/messages"}, run)))
        execution.prepare(descriptor, declaration_path, reg)
        cases.append((descriptor, desc, response, accepted, fit, reg, run))
    for index, (a, b) in enumerate([(cases[0], cases[1]), (cases[1], cases[0])]):
        refused = saved.accept(b[0], a[2], tmp_path / f"cross-{index}", attempt_id="one")
        assert refused["assessment"]["status"] == "rejected"
        assert "response_envelope_descriptor_sha256_conflicts" in refused["assessment"]["problems"]
        with pytest.raises(ValueError, match="another descriptor"):
            saved.report(b[0], [a[3]])
        destination = tmp_path / f"cross-index-{index}"
        with pytest.raises(ValueError, match="same plan"):
            fitness.build_index(b[4], [], destination, support_results=[a[3]])
        assert not destination.exists()
        controls = pending_controls(b[5], b[1])
        controls["controls"][0]["binding_sha256"] = support_plan.sha256(support_plan.canonical(a[1]["selections"][0]["binding"]))
        control_path = tmp_path / f"wrong-controls-{index}.json"
        control_path.write_bytes(support_plan.canonical(controls))
        destination = tmp_path / f"cross-calibration-{index}"
        with pytest.raises(ValueError, match="binding"):
            calibration.prepare(b[5], control_path, destination)
        assert not destination.exists() and not a[6].exists() and not b[6].exists()
    for row in (r for r in old["targets"] if r["axis"] == "fitness"):
        counterpart = target_row(new, row["pointer"], "fitness")
        assert counterpart["id"] == row["id"]
        assert support_plan.materialize_request(old_dir, row["id"]) == support_plan.materialize_request(new_dir, counterpart["id"])


@pytest.mark.parametrize("change", ["policy", "system", "origin", "projection", "branch", "omission", "qualifier"])
def test_rehashed_context_artifacts_are_reconstructed_from_captured_record(context_case, tmp_path, change):
    _root, directory = context_case
    manifest = plan_case(context_case)
    row = target_row(manifest, POINTER)
    if change == "policy":
        manifest["instruments"][targets.AXIS]["context_policy"] = "invented-context"
    elif change == "system":
        instrument = manifest["instruments"][targets.AXIS]
        instrument["system"] = replace_artifact(directory, instrument["system"], targets.SYSTEM.encode())
        row["request_recipe"]["system"]["$text"] = instrument["system"]
        raw = support_plan.canonical(support_plan._expand(row["request_recipe"], directory))
        row["request_sha256"], row["request_bytes"] = support_plan.sha256(raw), len(raw)
    else:
        payload = artifact(directory, row["target_artifact"])
        ancestor = payload["context"]["ancestors"][1]
        if change == "origin":
            ancestor["field_origins"]["source_caveats"] = "/creators/1/source_caveats"
        elif change == "projection":
            ancestor["projection"] = "unreviewed-full-record"
        elif change == "branch":
            ancestor["path_branch"]["selected_entity_pointer"] = "/creators/1/affiliations/0"
        elif change == "omission":
            ancestor["omitted_containers"].append({"pointer": "/creators/0/nonexistent",
                "sha256": "0" * 64, "size": 1, "reason": "other_container_not_selected_assertion"})
        else:
            ancestor["value"]["source_caveats"] = "Forged Document B attribution"
            ancestor["value_yaml"] = yaml.safe_dump(ancestor["value"], sort_keys=True)
            ancestor["value_sha256"] = targets._digest(ancestor["value"])
        payload["context_sha256"] = targets._digest(payload["context"])
        row["context_sha256"] = payload["context_sha256"]
        row["target_artifact"] = replace_artifact(directory, row["target_artifact"], support_plan.canonical(payload))
        # Also rewrite and rehash the inventory; this must fail semantic reconstruction,
        # not merely because an old content-addressed pin was left behind.
        record = manifest["records"][0]
        captured = artifact(directory, record["inventory"])
        item = next(t for t in captured["targets"] if t["pointer"] == POINTER and t["kind"] == "attribute_value")
        item.update(context=copy.deepcopy(payload["context"]), context_sha256=payload["context_sha256"])
        record["inventory"] = replace_artifact(directory, record["inventory"], support_plan.canonical(captured))
        for planned in manifest["targets"]:
            if planned["axis"] == targets.AXIS:
                planned["inventory_artifact"] = record["inventory"]
    save_manifest(directory, manifest)
    destination = tmp_path / "forged-descriptor"
    with pytest.raises(ValueError):
        describe(directory, manifest, destination)
    assert not destination.exists()


@pytest.mark.parametrize("relationship", [targets.POLICY, SCALAR])
@pytest.mark.parametrize("context", [LEGACY, ANCESTORS])
def test_real_transport_and_pending_calibration_bind_the_exact_context(context_case, peer, tmp_path,
                                                                      monkeypatch, relationship, context):
    root, directory = context_case
    manifest = plan_case(context_case, relationship=relationship, context=context)
    descriptor, reg_dir, run = tmp_path / "descriptor", tmp_path / "registered", tmp_path / "run"
    _, desc = describe(directory, manifest, descriptor)
    endpoint = urlsplit(peer["url"])
    def connect(sock, address):
        assert address == ("127.0.0.1", endpoint.port), "non-fixture network access"
        return _CONNECT(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)
    decl = tmp_path / "declaration.json"
    decl.write_bytes(support_plan.canonical(declaration(peer, run)))
    reg = execution.prepare(descriptor, decl, reg_dir)
    controls = tmp_path / "controls.json"
    controls.write_bytes(support_plan.canonical(pending_controls(reg_dir, desc)))
    cal_dir = tmp_path / "pending-calibration"
    cal = calibration.prepare(reg_dir, controls, cal_dir)
    missing = calibration.report(cal_dir)
    assert peer["requests"] == [] and missing["totals"]["unresolved_controls"] == 1
    outcome = execution.run(reg_dir)
    assert outcome["admitted_calls"] == 1 and outcome["all_selected_accepted"] is True
    expected = (reg_dir / "artifacts" / reg["requests"][0]["effective_request"]["sha256"]).read_bytes()
    assert len(peer["requests"]) == 1 and peer["requests"][0]["raw"] == expected
    sent = json.loads(json.loads(expected)["messages"][0]["content"][1]["text"].split("\n\n", 1)[1])
    if context == ANCESTORS:
        assert "Document A" in sent["context"]["ancestors"][1]["value_yaml"]
        assert sent["context"]["ancestors"][1]["field_origins"]["source_caveats"] == "/creators/0/source_caveats"
    report_dir = tmp_path / "calibration-report"
    result = calibration.report(cal_dir, run, output=report_dir)
    for value in (desc, desc["selections"][0]["binding"], reg, outcome, cal, result, result["rows"][0]):
        assert value.get("context_policy") == (ANCESTORS if context == ANCESTORS else None)
        if context == LEGACY:
            assert "context_policy" not in value
    assert result["totals"]["unresolved_controls"] == 1 and result["scientific_eligibility"] is False
    assert result["rows"][0]["expected_verdict"] is None and result["rows"][0]["scored"] is False
    assert result["rows"][0]["verdict_agreement"] is None
    if relationship == targets.POLICY:
        for value in (desc, reg, outcome, cal, result):
            assert "representation_accounting" not in value
        assert "policy" not in result["rows"][0] and "representation" not in result["rows"][0]
        assert "representation_counts" not in result and "representation_groups" not in result
    else:
        assert result["rows"][0]["policy"] == SCALAR
        assert result["representation_counts"] == {"basis": "selected_relationship_controls",
            "schema_invalid_inline_class_string": 0, "other_relationship_edges": 0}
        assert result["representation_groups"] == []
    # An actual completed ledger cannot be pooled into controls registered for
    # the other context, even though its target and attempt IDs are identical.
    opposite = LEGACY if context == ANCESTORS else ANCESTORS
    other_plan = tmp_path / "other-context-plan"
    other_manifest = plan_case((root, other_plan), relationship=relationship, context=opposite)
    other_descriptor = tmp_path / "other-context-descriptor"
    _, other_desc = describe(other_plan, other_manifest, other_descriptor)
    other_registered, other_run = tmp_path / "other-context-registered", tmp_path / "other-context-never-run"
    other_declaration = tmp_path / "other-context-declaration.json"
    other_declaration.write_bytes(support_plan.canonical(declaration(peer, other_run)))
    execution.prepare(other_descriptor, other_declaration, other_registered)
    other_controls = tmp_path / "other-context-controls.json"
    other_controls.write_bytes(support_plan.canonical(pending_controls(other_registered, other_desc)))
    other_calibration = tmp_path / "other-context-calibration"
    calibration.prepare(other_registered, other_controls, other_calibration)
    cross_report = tmp_path / "cross-context-calibration-report"
    with pytest.raises(ValueError, match="registration"):
        calibration.report(other_calibration, run, output=cross_report)
    assert not cross_report.exists() and not other_run.exists() and len(peer["requests"]) == 1
    # Offline readback uses captured authority after all original paths disappear.
    for path in (root, directory, descriptor):
        path.rename(path.with_name(path.name + "-unavailable"))
    monkeypatch.setattr(execution, "_dispatch", lambda *_: pytest.fail("offline recheck dispatched"))
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("offline recheck connected"))
    assert execution.recheck(run) == outcome
    assert calibration.recheck(cal_dir) == cal
    assert calibration.recheck(report_dir) == result
    assert len(peer["requests"]) == 1


@pytest.mark.parametrize("case_name", ["ordinary", "mixed_inline_string"])
@pytest.mark.parametrize("explicit", [False, True])
def test_scalar_legacy_bytes_match_genuine_precontext_capture(case_name, explicit):
    from data_sheets_schema import evidence_score
    directory = Path(__file__).parents[1] / "fixtures/support_context_legacy_scalar"
    golden = json.loads((directory / "semantic.json").read_bytes())
    assert golden["source_commit"] == "3d256fccd8e37124cc78e4d56ef93b9481b34473"
    assert golden["original_receipt_sha256"] == "adddcf33331aa86b069604e28f70027673d400b435cf895e1e2eec8d4695b592"
    common = golden["common"]
    case = next(c for c in golden["cases"] if c["name"] == case_name)
    specification = targets.NestedSupportSchema(common["captured_specification_json"])
    options = {"context_policy": LEGACY} if explicit else {}
    inventory = targets.inventory_targets(case["record_yaml"].encode(), specification,
        artifact_kind="full", relationship_policy=SCALAR, **options)
    assert support_plan.canonical(inventory.to_dict()) == case["inventory_json"].encode()
    assert len(inventory.targets) == len(case["targets"])
    for current, old in zip(inventory.targets, case["targets"]):
        assert current.payload_json.encode() == old["payload_json"].encode()
        assert current.specification_json.encode() == old["specification_json"].encode()
    document = yaml.safe_load(case["record_yaml"])
    fitness_specifications = json.loads(common["fitness_specifications_json"])["slots"]
    for old in case["requests"]:
        if old["axis"] == targets.AXIS:
            kind = old["target_id"].split(":", 3)[2]
            current = targets.render_request(inventory.target(old["pointer"], kind=kind),
                bundle=common["bundle"], model=common["model"], max_tokens=common["max_tokens"])
        else:
            slot = targets.pointer_tokens(old["pointer"])[0]
            current = evidence_score.fitness_request_arguments(model=common["model"],
                max_tokens=common["max_tokens"], slot=slot, value=document[slot], specification=fitness_specifications[slot])
        assert support_plan.canonical(current) == old["request_json"].encode()


@pytest.mark.parametrize("case_name", ["ordinary", "mixed_inline_string"])
def test_explicit_legacy_context_matches_genuine_old_strict_bytes(case_name):
    golden = json.loads((Path(__file__).parents[1] / "fixtures/support_strict_v2/semantic.json").read_bytes())
    case = next(c for c in golden["cases"] if c["name"] == case_name)
    common = golden["common"]
    specification = targets.NestedSupportSchema(common["captured_specification_json"])
    inventory = targets.inventory_targets(case["record_yaml"].encode(), specification,
        artifact_kind="full", context_policy=LEGACY)
    assert support_plan.canonical(inventory.to_dict()) == case["inventory_json"].encode()
    assert [t.payload_json for t in inventory.targets] == [t["payload_json"] for t in case["targets"]]
    for request in case["requests"]:
        if request["axis"] != targets.AXIS:
            continue
        kind = request["target_id"].split(":", 3)[2]
        current = targets.render_request(inventory.target(request["pointer"], kind=kind),
            bundle=common["bundle"], model=common["model"], max_tokens=common["max_tokens"])
        assert support_plan.canonical(current) == request["request_json"].encode()


def test_genuine_old_scalar_saved_and_pending_artifacts_reconstruct_offline(tmp_path, monkeypatch):
    directory = Path(__file__).parents[1] / "fixtures/support_context_legacy_scalar"
    provenance = json.loads((directory / "provenance.json").read_bytes())
    assert provenance["receipt"]["sha256"] == "adddcf33331aa86b069604e28f70027673d400b435cf895e1e2eec8d4695b592"
    for row in provenance["copied_files"]:
        raw = (directory / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    pending = tmp_path / "historical-pending"
    shutil.copytree(directory / "pending-report", pending)
    expected = json.loads((pending / "calibration.json").read_bytes())["result"]
    descriptor = tmp_path / "historical-descriptor"
    descriptor.mkdir()
    shutil.copytree(pending / "artifacts", descriptor / "artifacts")
    shutil.copyfile(directory / "descriptor.json", descriptor / "descriptor.json")
    expected_saved = json.loads((directory / "saved-missing-report.json").read_bytes())
    original = Path.read_bytes
    original_file = saved._file
    def captured_only(path):
        assert path.is_relative_to(tmp_path), "readback reached a historical source path"
        return original(path)
    def captured_file(path, limit):
        assert Path(path).is_relative_to(tmp_path), "readback opened a historical source path"
        return original_file(path, limit)
    monkeypatch.setattr(Path, "read_bytes", captured_only)
    monkeypatch.setattr(saved, "_file", captured_file)
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("old readback connected"))
    monkeypatch.setattr(execution, "_dispatch", lambda *_: pytest.fail("old readback dispatched"))
    assert calibration.recheck(pending) == expected
    assert saved.report(descriptor, []) == expected_saved
    assert expected["totals"]["unresolved_controls"] == 2
    assert expected["representation_counts"] == {"basis": "selected_relationship_controls",
        "schema_invalid_inline_class_string": 1, "other_relationship_edges": 0}
    assert expected["representation_groups"] == []
    assert all(row["expected_verdict"] is None and not row["scored"] for row in expected["rows"])
    assert "context_policy" not in expected and "context_policy" not in expected_saved
