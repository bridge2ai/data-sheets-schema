"""Independent calibration boundary controls using invented offline evidence.

These are not human labels or calibration measurements. The execution writer
runs against an in-process byte supplier; the inherited plan fixture forbids
network access and provider calls throughout.
"""

from copy import deepcopy
import hashlib
import json
import shutil
from types import SimpleNamespace

import pytest

from data_sheets_schema import nested_support_execution as execution
from data_sheets_schema import nested_support_results as saved
from data_sheets_schema import support_calibration as calibration
from data_sheets_schema.support_plan import canonical
from tests.test_evaluation.test_nested_support_execution import declaration, reply
from tests.test_evaluation.test_nested_support_results import plan  # noqa: F401
from tests.test_evaluation.test_support_plan import fixture  # noqa: F401


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot(directory):
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


@pytest.fixture
def scenario(plan, tmp_path, monkeypatch):
    _, plan_path, manifest, selections = plan
    kinds = {row["id"]: row["kind"] for row in manifest["targets"]
             if row["axis"] == "grounding_v3"}
    chosen = [next(row for row in selections if kinds[row["target_id"]] == "relationship_edge")]
    chosen += [row for row in selections if kinds[row["target_id"]] == "attribute_value"][:2]

    def create(name="case", *, stop_after_first=False, declared_calibration=False):
        root = tmp_path / name
        root.mkdir()
        descriptor, registered, output = root / "descriptor", root / "registration", root / "run"
        description = saved.prepare(plan_path, descriptor, selections=chosen, protocol=saved.FORMAT)
        declared = declaration({"url": "http://127.0.0.1:9/v1/messages"}, output)
        declared["registration_id"] = f"invented-{name}"
        if declared_calibration:
            declared["purpose"] = "calibration"
            declared["transport"].update(url="https://example.invalid/v1/messages", auth="bearer")
            for key in declared["decisions"]:
                if key not in {"calibration_acceptance", "canary_acceptance"}:
                    declared["decisions"][key] = {
                        "reference": f"synthetic://non-authenticated-decision/{key}", "sha256": "d" * 64}
        declared["limits"].update(max_calls=3, total_response_bytes=150_003,
                                  input_scheduling_threshold=100 if stop_after_first else 300,
                                  output_scheduling_threshold=1251)
        declaration_path = root / "declaration.json"
        declaration_path.write_bytes(canonical(declared))
        execution.prepare(descriptor, declaration_path, registered)
        expected = ("status_shifted", "supported", "unsupported")
        controls = {
            "format": "support_calibration_controls_v1", "calibration_id": f"invented-{name}",
            "registration_sha256": digest((registered / "registration.json").read_bytes()),
            "controls": [
                {"control_id": f"invented-control-{index}", "target_id": selection["target_id"],
                 "attempt_id": selection["attempt_id"], "kind": selection["binding"]["kind"],
                 "pointer": selection["binding"]["pointer"],
                 "binding_sha256": digest(canonical(selection["binding"])),
                 "review_status": "synthetic", "expected_verdict": verdict, "defect_class": verdict,
                 "finding": {"reference": f"synthetic://fixture/{index}",
                             "sha256": digest(f"invented finding {index}".encode())},
                 "review": None}
                for index, (selection, verdict) in enumerate(zip(description["selections"], expected))],
        }
        controls_path = root / "controls.json"

        def prepare(changed=None, name="calibration"):
            controls_path.write_bytes(canonical(controls if changed is None else changed))
            destination = root / name
            calibration.prepare(registered, controls_path, destination)
            return destination

        calls = []

        def run(verdicts=expected, *, http_status=200, fail_after_admission=False):
            def dispatch(transport, request_raw, cap, credential):
                calls.append(request_raw)
                if fail_after_admission:
                    raise OSError("invented interruption after durable admission")
                verdict = verdicts[len(calls) - 1]
                body = reply()
                body["content"][-1]["text"] = json.dumps({"verdict": verdict, "reason": "Invented offline response"})
                return {"status_code": http_status, "request_id": "invented-response", "body_complete": True,
                        "failure": None, "duration_seconds": 0, "stage": "complete"}, canonical(body)
            monkeypatch.setattr(execution, "_dispatch", dispatch)
            return execution.run(registered, credential="invented-test-value" if declared_calibration else None)

        return SimpleNamespace(root=root, controls=controls, controls_path=controls_path,
                               registration=registered, descriptor=descriptor, description=description,
                               output=output, prepare=prepare, run=run, calls=calls)
    return create


@pytest.mark.parametrize("field,wrong", [
    ("target_id", "wrong-record:grounding_v3:relationship_edge:/creators/0"),
    ("attempt_id", "unselected-retry"),
    ("kind", "attribute_value"),
    ("pointer", "/creators/0/name"),
    ("binding_sha256", "0" * 64),
])
def test_control_must_match_registered_target_and_facet_before_output(scenario, field, wrong):
    case = scenario()
    changed = deepcopy(case.controls)
    changed["controls"][0][field] = wrong
    before = snapshot(case.registration)
    with pytest.raises(ValueError):
        case.prepare(changed)
    assert not (case.root / "calibration").exists()
    assert snapshot(case.registration) == before
    assert case.calls == []


@pytest.mark.parametrize("identity", ["model", "request", "record", "bundle", "specification_sha256", "context_sha256"])
def test_rehashed_alternate_binding_cannot_relabel_same_pointer(scenario, identity):
    case = scenario()
    binding = deepcopy(case.description["selections"][0]["binding"])
    if identity == "model":
        binding[identity]["name"] = "different-judge"
    elif identity in {"request", "record", "bundle"}:
        binding[identity]["sha256"] = "0" * 64
    else:
        binding[identity] = "0" * 64
    changed = deepcopy(case.controls)
    changed["controls"][0]["binding_sha256"] = digest(canonical(binding))
    with pytest.raises(ValueError):
        case.prepare(changed)
    assert not (case.root / "calibration").exists()


@pytest.mark.parametrize("change", ["same_id", "different_id", "omitted_control", "wrong_registration"])
def test_control_denominator_is_closed_and_cannot_duplicate_an_attempt(scenario, change):
    case = scenario()
    changed = deepcopy(case.controls)
    if change in {"same_id", "different_id"}:
        duplicate = deepcopy(changed["controls"][0])
        if change == "different_id":
            duplicate["control_id"] = "apparently-distinct-control"
        changed["controls"].append(duplicate)
    elif change == "omitted_control":
        changed["controls"].pop()
    else:
        changed["registration_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        case.prepare(changed)
    assert not (case.root / "calibration").exists()


def test_same_targets_from_another_registration_are_not_an_implicit_retry(scenario):
    case, other = scenario("selected"), scenario("unselected")
    calibrated = case.prepare()
    other.run()
    assert case.description["selections"] == other.description["selections"]
    before = snapshot(calibrated)
    with pytest.raises(ValueError):
        calibration.report(calibrated, other.output, output=case.root / "wrong-run-report")
    assert snapshot(calibrated) == before
    assert not (case.root / "wrong-run-report").exists()


def test_existing_destination_is_preserved_for_prepare_and_report(scenario):
    case = scenario()
    calibrated = case.prepare()
    case.run()
    destination = case.root / "sentinel"
    destination.mkdir()
    (destination / "report.json").write_bytes(b"preserved reviewed result\n")
    before = snapshot(destination)
    with pytest.raises(ValueError):
        calibration.prepare(case.registration, case.controls_path, destination)
    assert snapshot(destination) == before
    with pytest.raises(ValueError):
        calibration.report(calibrated, case.output, output=destination)
    assert snapshot(destination) == before


def test_portable_report_rechecks_without_original_sources_or_dispatch(scenario, plan, tmp_path, monkeypatch):
    case = scenario()
    calibrated = case.prepare()
    case.run()
    original = case.root / "portable-report"
    expected = calibration.report(calibrated, case.output, output=original)
    portable = tmp_path / "relocated-report"
    shutil.copytree(original, portable)
    before = snapshot(portable)
    plan[0].rename(tmp_path / "source-preserved")
    plan[1].rename(tmp_path / "plan-preserved")
    case.root.rename(tmp_path / "case-preserved")
    def forbidden(*args, **kwargs):
        pytest.fail("portable calibration replay used runtime or execution access")
    monkeypatch.setattr(execution, "_dispatch", forbidden)
    monkeypatch.setattr(execution, "_identity", forbidden)
    assert calibration.recheck(portable) == expected
    assert snapshot(portable) == before


def test_changed_captured_raw_response_cannot_keep_a_cached_score(scenario):
    case = scenario()
    calibrated = case.prepare()
    case.run()
    portable = case.root / "portable-report"
    calibration.report(calibrated, case.output, output=portable)
    outcome = json.loads((case.output / "attempts/000000/response.json").read_bytes())
    blob = portable / "artifacts" / outcome["body"]["sha256"]
    value = json.loads(blob.read_bytes())
    value["model"] = "different-judge"
    blob.write_bytes(canonical(value))
    with pytest.raises(ValueError):
        calibration.recheck(portable)


def overall_group(report, kind):
    return next(group for group in report["groups"]
                if group["scope"] == "synthetic" and group["kind"] == kind
                and group["defect_class"] is None)


def assert_no_complete_rates(report):
    for group in report["groups"]:
        assert group["recall"] is None
        assert group["false_positive_rate"] is None
        assert group["verdict_agreement_rate"] is None


def test_wrong_class_detection_is_not_exact_verdict_agreement(scenario):
    case = scenario()
    calibrated = case.prepare()
    # Relationship error detected under the wrong class; one false positive
    # and one false negative in attributes. No invented response is correct.
    case.run(("unsupported", "unsupported", "supported"))
    result = calibration.report(calibrated, case.output)
    relationship = overall_group(result, "relationship_edge")
    attributes = overall_group(result, "attribute_value")
    assert relationship["positive_controls"] == 1
    assert relationship["detected_positive_controls"] == 1
    assert relationship["recall"] == 1.0
    assert relationship["negative_controls"] == 0
    assert relationship["false_positive_rate"] is None
    assert relationship["verdict_agreement_rate"] == 0.0
    assert attributes["positive_controls"] == attributes["negative_controls"] == 1
    assert attributes["recall"] == 0.0
    assert attributes["false_positive_rate"] == 1.0
    assert attributes["verdict_agreement_rate"] == 0.0


@pytest.mark.parametrize("has_draft_label", [False, True])
def test_pending_label_with_accepted_response_cannot_complete_calibration(scenario, has_draft_label):
    case = scenario()
    controls = deepcopy(case.controls)
    controls["controls"][2].update(review_status="pending", review=None)
    if not has_draft_label:
        controls["controls"][2].update(expected_verdict=None, defect_class=None)
    calibrated = case.prepare(controls)
    case.run()
    result = calibration.report(calibrated, case.output)
    row = result["rows"][2]
    assert row["dispatch_status"] == "accepted"
    assert row["review_status"] == "pending"
    assert row["scored"] is False
    assert row["verdict_agreement"] is None
    assert row["defect_detected"] is None
    assert row["false_positive"] is None
    assert_no_complete_rates(result)
    assert result["totals"]["unresolved_controls"] == 1
    assert result["totals"]["pending"] == 1


def test_missing_negatives_do_not_turn_a_single_detected_positive_into_success(scenario):
    case = scenario(stop_after_first=True)
    calibrated = case.prepare()
    case.run()
    result = calibration.report(calibrated, case.output)
    assert [row["dispatch_status"] for row in result["rows"]] == ["accepted", "not_started", "not_started"]
    assert [row["scored"] for row in result["rows"]] == [True, False, False]
    assert_no_complete_rates(result)
    relationship = overall_group(result, "relationship_edge")
    assert relationship["observed_positive_controls"] == relationship["detected_positive_controls"] == 1
    attributes = overall_group(result, "attribute_value")
    assert attributes["negative_controls"] == 1
    assert attributes["observed_negative_controls"] == attributes["false_positive_controls"] == 0
    assert attributes["unresolved_controls"] == 2


def test_semantically_accepted_http_failure_is_not_a_calibration_observation(scenario):
    case = scenario()
    calibrated = case.prepare()
    executed = case.run(http_status=429)
    assert executed["rows"][0]["saved_result"]["assessment"]["status"] == "accepted"
    result = calibration.report(calibrated, case.output)
    assert result["rows"][0]["dispatch_status"] == "failed"
    assert result["rows"][0]["assessment_status"] == "accepted"
    assert all(row["scored"] is False for row in result["rows"])
    assert_no_complete_rates(result)
    assert overall_group(result, "relationship_edge")["observed_controls"] == 0


def test_admission_only_remains_spent_unknown_without_replacement_attempt(scenario):
    case = scenario()
    calibrated = case.prepare()
    with pytest.raises(OSError, match="invented interruption"):
        case.run(fail_after_admission=True)
    assert len(case.calls) == 1
    result = calibration.report(calibrated, case.output)
    assert [row["dispatch_status"] for row in result["rows"]] == ["spent_unknown", "not_started", "not_started"]
    assert all(row["scored"] is False for row in result["rows"])
    assert_no_complete_rates(result)
    assert len(case.calls) == 1


def test_claimed_review_reference_cannot_make_local_fixture_empirical(scenario):
    case = scenario()
    controls = deepcopy(case.controls)
    for row in controls["controls"]:
        row["review_status"] = "reviewed"
        row["review"] = {"reference": "synthetic://claimed-review-not-human-approval", "sha256": "f" * 64}
    calibrated = case.prepare(controls)
    case.run()
    result = calibration.report(calibrated, case.output)
    assert {row["metric_scope"] for row in result["rows"]} == {"synthetic"}
    assert {group["scope"] for group in result["groups"]} == {"synthetic"}
    assert result["evidence_scope"] == "software_only"
    assert result["scientific_eligibility"] is False
    assert result["original_readiness"]["ready_for_paid_run"] is False


def test_declared_reviewed_scope_still_does_not_authenticate_scientific_approval(scenario):
    # Exercise the nonlocal declaration shape with a fictional invalid-domain
    # URL and the in-process reply supplier. No HTTP client is constructed.
    case = scenario(declared_calibration=True)
    controls = deepcopy(case.controls)
    for row in controls["controls"]:
        row["review_status"] = "reviewed"
        row["review"] = {"reference": "synthetic://claimed-review", "sha256": "f" * 64}
    calibrated = case.prepare(controls)
    case.run()
    result = calibration.report(calibrated, case.output)
    assert result["evidence_scope"] == "declared_reviewed_labels"
    assert {row["metric_scope"] for row in result["rows"]} == {"reviewed"}
    assert {group["scope"] for group in result["groups"]} == {"reviewed"}
    assert result["scientific_eligibility"] is False
    assert result["original_readiness"]["ready_for_paid_run"] is False
    assert result["totals"]["unresolved_controls"] == 0
    assert any("not authenticated" in text for text in result["limitations"])


def test_missing_run_preserves_every_control_and_does_not_start_execution(scenario):
    case = scenario()
    calibrated = case.prepare()
    result = calibration.report(calibrated)
    assert result["totals"]["unresolved_controls"] == 3
    assert [row["dispatch_status"] for row in result["rows"]] == ["missing"] * 3
    assert_no_complete_rates(result)
    assert not case.output.exists()
    assert case.calls == []


@pytest.mark.parametrize("mutation", ["scientific_eligibility", "counts", "row_verdict"])
def test_cached_calibration_summary_cannot_override_reconstructed_evidence(scenario, mutation):
    case = scenario()
    calibrated = case.prepare()
    case.run()
    portable = case.root / "portable-report"
    calibration.report(calibrated, case.output, output=portable)
    path = portable / "calibration.json"
    stored = json.loads(path.read_bytes())
    if mutation == "scientific_eligibility":
        stored["result"]["scientific_eligibility"] = True
    elif mutation == "counts":
        stored["result"]["groups"][0]["detected_positive_controls"] += 1
    else:
        stored["result"]["rows"][0]["observed_verdict"] = "supported"
    path.write_bytes(canonical(stored) + b"\n")
    with pytest.raises(ValueError):
        calibration.recheck(portable)


def test_forged_execution_cache_is_refused_without_rewriting_input(scenario):
    case = scenario()
    calibrated = case.prepare()
    case.run(http_status=429)
    path = case.output / "report.json"
    cached = json.loads(path.read_bytes())
    cached["all_selected_accepted"] = True
    cached["rows"][0]["status"] = "accepted"
    path.write_bytes(canonical(cached))
    before = snapshot(case.output)
    destination = case.root / "forged-report"
    with pytest.raises(ValueError):
        calibration.report(calibrated, case.output, output=destination)
    assert snapshot(case.output) == before
    assert not destination.exists()


def test_report_size_limit_refuses_before_publishing_an_unrecheckable_result(scenario, monkeypatch):
    case = scenario()
    calibrated = case.prepare()
    case.run()
    reference = case.root / "size-reference"
    calibration.report(calibrated, case.output, output=reference)
    limit = len((reference / "calibration.json").read_bytes()) - 1
    # Keep each source document legal while the combined result is one byte
    # too large; an input-size failure would not exercise publication here.
    assert len((calibrated / "calibration.json").read_bytes()) < limit
    assert len((case.output / "report.json").read_bytes()) < limit
    before = snapshot(case.root)
    executor_bound = saved.MAX_MANIFEST_BYTES
    monkeypatch.setattr(calibration, "MAX_CALIBRATION_BYTES", limit)
    destination = case.root / "oversized-report"
    with pytest.raises(ValueError, match="calibration output exceeds manifest byte bound"):
        calibration.report(calibrated, case.output, output=destination)
    assert not destination.exists()
    assert snapshot(case.root) == before
    assert saved.MAX_MANIFEST_BYTES == executor_bound


def test_prepare_size_limit_refuses_before_publishing_an_unrecheckable_manifest(scenario, monkeypatch):
    case = scenario()
    reference = case.prepare()
    limit = len((reference / "calibration.json").read_bytes()) - 1
    before = snapshot(case.root)
    executor_bound = saved.MAX_MANIFEST_BYTES
    monkeypatch.setattr(calibration, "MAX_CALIBRATION_BYTES", limit)
    destination = case.root / "oversized-manifest"
    with pytest.raises(ValueError, match="calibration output exceeds manifest byte bound"):
        calibration.prepare(case.registration, case.controls_path, destination)
    assert not destination.exists()
    assert snapshot(case.root) == before
    assert saved.MAX_MANIFEST_BYTES == executor_bound
