"""Invented offline controls exercise bookkeeping, never scientific accuracy."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema import support_calibration as calibration
from data_sheets_schema.support_plan import canonical, sha256
from tests.test_evaluation.test_nested_support_execution import declaration, reply
from tests.test_evaluation.test_nested_support_results import plan  # noqa: F401
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401


@pytest.fixture
def controls(plan, tmp_path, monkeypatch):
    _, plan_path, manifest, selections = plan
    kinds = {row["id"]: row["kind"] for row in manifest["targets"] if row["axis"] == "grounding_v3"}
    chosen = [next(row for row in selections if kinds[row["target_id"]] == kind)
              for kind in ("relationship_edge", "attribute_value")]
    descriptor = tmp_path / "descriptor"
    description = saved.prepare(plan_path, descriptor, selections=chosen, protocol=saved.FORMAT)
    registration, run = tmp_path / "registered", tmp_path / "run"
    declared = declaration({"url": "http://127.0.0.1:9/v1/messages"}, run)
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_bytes(canonical(declared))
    execution.prepare(descriptor, declaration_path, registration)
    value = {"format": calibration.CONTROLS_FORMAT, "calibration_id": "invented-software-controls",
             "registration_sha256": sha256((registration / "registration.json").read_bytes()),
             "controls": []}
    for i, selection in enumerate(description["selections"]):
        value["controls"].append({"control_id": f"invented-{i}", "target_id": selection["target_id"],
                                 "attempt_id": selection["attempt_id"], "kind": selection["binding"]["kind"],
                                 "pointer": selection["binding"]["pointer"],
                                 "binding_sha256": sha256(canonical(selection["binding"])),
                                 "review_status": "synthetic", "expected_verdict": "supported",
                                 "defect_class": "invented supported negative", "review": None,
                                 "finding": {"reference": f"synthetic://finding/{i}", "sha256": sha256(str(i).encode())}})
    path = tmp_path / "controls.json"
    destination = tmp_path / "calibration"

    def prepare(changed=None):
        path.write_bytes(canonical(value if changed is None else changed))
        return calibration.prepare(registration, path, destination)

    def execute():
        def dispatch(*args):
            return {"status_code": 200, "request_id": "invented-response", "body_complete": True,
                    "failure": None, "duration_seconds": 0, "stage": "complete"}, canonical(reply())
        monkeypatch.setattr(execution, "_dispatch", dispatch)
        return execution.run(registration)

    return SimpleNamespace(value=value, path=path, destination=destination, registration=registration,
                           run=run, prepare=prepare, execute=execute, tmp=tmp_path)


def test_no_run_is_missing_evidence_not_a_successful_negative(controls):
    manifest = controls.prepare()
    result = calibration.report(controls.destination, output=controls.tmp / "missing-report")
    assert result["totals"]["dispatch_status"]["missing"] == 2
    assert result["totals"]["dispatch_status"]["not_started"] == 0
    assert result["totals"]["unresolved_controls"] == 2
    assert result["original_readiness"] == manifest["original_readiness"]
    assert all(row["observed_verdict"] is None and not row["scored"] for row in result["rows"])
    assert all(group["false_positive_rate"] is None and group["observed_negative_controls"] == 0
               for group in result["groups"])
    assert calibration.recheck(controls.tmp / "missing-report") == result
    assert calibration.recheck(controls.destination) == manifest


def test_caller_classes_are_separate_strata_and_all_source_binding_is_preserved(controls):
    manifest = controls.prepare()
    controls.execute()
    result = calibration.report(controls.destination, controls.run)
    assert result["totals"]["unresolved_controls"] == 0
    assert result["scientific_eligibility"] is False
    assert result["evidence_scope"] == "software_only"
    assert {g["kind"] for g in result["groups"]} == {"relationship_edge", "attribute_value"}
    assert all(g["false_positive_rate"] == 0 and g["verdict_agreement_rate"] == 1 for g in result["groups"])
    assert all(g["recall"] is None for g in result["groups"])
    assert {g["defect_class"] for g in result["groups"]} == {None, "invented supported negative"}
    for control in manifest["resolved_controls"]:
        assert sha256(canonical(control["binding"])) == control["binding_sha256"]
        assert {"record", "bundle", "model", "request", "specification_sha256"} <= set(control["binding"])


@pytest.mark.parametrize("change", ["unknown_root", "unknown_control", "missing_finding", "bad_finding_digest",
                                     "reviewed_without_review", "synthetic_with_review", "pending_with_review",
                                     "unknown_verdict", "blank_class"])
def test_unreviewable_or_ambiguous_labels_refused_before_writing(controls, change):
    value = deepcopy(controls.value)
    row = value["controls"][0]
    if change == "unknown_root":
        value["approved"] = True
    elif change == "unknown_control":
        row["approved"] = True
    elif change == "missing_finding":
        row["finding"] = None
    elif change == "bad_finding_digest":
        row["finding"]["sha256"] = "unknown"
    elif change == "reviewed_without_review":
        row["review_status"] = "reviewed"
    elif change in {"synthetic_with_review", "pending_with_review"}:
        row["review_status"] = change.split("_")[0]
        row["review"] = {"reference": "invented-review", "sha256": "1" * 64}
    elif change == "unknown_verdict":
        row["expected_verdict"] = "probably supported"
    elif change == "blank_class":
        row["defect_class"] = " "
    with pytest.raises(ValueError):
        controls.prepare(value)
    assert not controls.destination.exists()
    assert not controls.run.exists()


def test_duplicate_json_keys_cannot_change_review_status(controls):
    raw = canonical(controls.value).replace(b'"review_status":"synthetic"',
                                           b'"review_status":"pending","review_status":"synthetic"', 1)
    controls.path.write_bytes(raw)
    with pytest.raises(ValueError):
        calibration.prepare(controls.registration, controls.path, controls.destination)
    assert not controls.destination.exists()


def test_recheck_refuses_changed_readable_binding_even_with_all_raw_artifacts(controls):
    controls.prepare()
    path = controls.destination / "calibration.json"
    value = json.loads(path.read_bytes())
    value["resolved_controls"][0]["binding"]["pointer"] = "/different/facet"
    path.write_bytes(canonical(value) + b"\n")
    with pytest.raises(ValueError):
        calibration.recheck(controls.destination)


def test_report_refuses_cached_execution_success_not_supported_by_captured_bytes(controls):
    controls.prepare()
    controls.execute()
    report = controls.run / "report.json"
    value = json.loads(report.read_bytes())
    value["scientific_eligibility"] = True
    report.write_bytes(canonical(value))
    with pytest.raises(ValueError):
        calibration.report(controls.destination, controls.run, output=controls.tmp / "altered-report")
    assert not (controls.tmp / "altered-report").exists()


def test_returned_objects_cannot_mutate_future_calibration_authority(controls):
    manifest = controls.prepare()
    expected_manifest = deepcopy(manifest)
    manifest["limitations"].clear()
    manifest["original_readiness"].clear()
    manifest["resolved_controls"][0]["binding"].clear()
    assert calibration.recheck(controls.destination) == expected_manifest
    controls.execute()
    report_path = controls.tmp / "portable"
    result = calibration.report(controls.destination, controls.run, output=report_path)
    expected_result = deepcopy(result)
    result["limitations"].clear()
    result["rows"].clear()
    result["original_readiness"].clear()
    nested = result["execution_accounting"]["rows"][0]["saved_result"]
    nested["limitations"].clear()
    nested["contract"]["verdicts"].clear()
    assert calibration.recheck(report_path) == expected_result
    assert calibration.report(controls.destination, controls.run) == expected_result
