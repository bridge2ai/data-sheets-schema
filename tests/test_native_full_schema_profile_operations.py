"""Operation/catalog controls use fictional reports, never native reconstruction."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from .test_native_full_schema_profile_runtime import profile, parent_case, synthetic_pair


OPERATIONS = (
    ("_load_live", "returned"),
    ("CallbackAdapter._run_fresh_owner", "returned"),
    ("decision_fresh_loaded_run", "returned"),
    ("current_effect_view_fresh_loaded_run", "returned"),
    ("refusal_stale_worker_read_in_memory", "refused"),
    ("refusal_changed_selected_authority_in_memory", "refused"),
)


@pytest.mark.parametrize("operation,expected", OPERATIONS)
def test_fixed_catalog_requires_all_four_returns_and_both_refusals(profile, operation, expected):
    assert profile.OPERATIONS == OPERATIONS
    assert profile.operation_catalog() == {"format": "native_full_schema_operations_v1",
        "operations": [{"operation": name, "expected_status": status} for name, status in OPERATIONS]}
    pair = synthetic_pair(profile, operation)
    assert pair["plain"]["status"] == expected
    assert profile.validate_pair(pair, operation) is True


@pytest.mark.parametrize("fault", ["wrong_operation", "missing_arm", "extra_arm_field", "unearned_parity",
    "different_digest", "failed_positive", "returned_negative", "negative_without_graph", "forged_refusal_digest",
    "cause_mismatch", "negative_time", "boolean_time", "setup_time_type", "fingerprint_missing",
    "boolean_count", "unknown_counter", "plain_instrumentation"])
def test_invalid_or_incomplete_pair_cannot_be_certified_by_parity_flag(profile, fault):
    operation = OPERATIONS[4][0] if fault in {
        "returned_negative", "negative_without_graph", "forged_refusal_digest", "cause_mismatch"} else OPERATIONS[0][0]
    pair = synthetic_pair(profile, operation)
    arm = pair["instrumented"]
    if fault == "wrong_operation":
        pair["operation"] = OPERATIONS[1][0]
    elif fault == "missing_arm":
        del pair["instrumented"]
    elif fault == "extra_arm_field":
        arm["assumed_ok"] = True
    elif fault == "unearned_parity":
        pair["parity"] = 1
    elif fault == "different_digest":
        arm["semantic_sha256"] = "0" * 64
    elif fault == "failed_positive":
        pair["plain"]["status"] = arm["status"] = "refused"
    elif fault == "returned_negative":
        pair["plain"]["status"] = arm["status"] = "returned"
    elif fault == "negative_without_graph":
        pair["plain"]["refusal"] = arm["refusal"] = None
    elif fault == "forged_refusal_digest":
        pair["plain"]["semantic_sha256"] = arm["semantic_sha256"] = "0" * 64
    elif fault == "cause_mismatch":
        arm["refusal"]["cause"] = deepcopy(arm["refusal"])
        arm["refusal"]["cause"]["node"] = 1
        arm["semantic_sha256"] = profile.sha(profile.canonical(arm["refusal"]))
    elif fault == "negative_time":
        arm["wall_ns"] = -1
    elif fault == "boolean_time":
        arm["process_cpu_ns"] = True
    elif fault == "setup_time_type":
        arm["setup"]["wall_ns"] = "20"
    elif fault == "fingerprint_missing":
        del arm["fingerprint"]
    elif fault == "boolean_count":
        arm["reconstruction_counts"]["_load_live"] = True
    elif fault == "unknown_counter":
        arm["reconstruction_counts"]["assumed_fast_path"] = 1
    else:
        pair["plain"]["reconstruction_counts"] = {"_load_live": 1}
    with pytest.raises(ValueError):
        profile.validate_pair(pair, operation)


def test_complete_refusal_graph_retains_cycles_context_and_notes(profile):
    pair = synthetic_pair(profile, OPERATIONS[4][0])
    refusal = pair["plain"]["refusal"]
    refusal["context"] = {"reference": 0}
    refusal["notes"] = ["list", [["str", "retained explanatory note"]]]
    for arm in ("plain", "instrumented"):
        pair[arm]["refusal"] = deepcopy(refusal)
        pair[arm]["semantic_sha256"] = profile.sha(profile.canonical(refusal))
    assert profile.validate_pair(pair, OPERATIONS[4][0]) is True
    bad = deepcopy(pair)
    for arm in ("plain", "instrumented"):
        bad[arm]["refusal"]["context"] = {"reference": 99}
        bad[arm]["semantic_sha256"] = profile.sha(profile.canonical(bad[arm]["refusal"]))
    with pytest.raises(ValueError, match="reference"):
        profile.validate_pair(bad, OPERATIONS[4][0])


def test_missing_and_failed_parent_measurements_remain_in_fixed_denominator(profile):
    states = {name: "completed" for name, _ in OPERATIONS}
    assert profile.operation_set(states) == {"required": 6, "completed": [name for name, _ in OPERATIONS],
        "failed": [], "missing": [], "complete": True}
    states.pop(OPERATIONS[-1][0])
    states[OPERATIONS[0][0]] = "diagnostic_timeout"
    states[OPERATIONS[4][0]] = "diagnostic_refused"
    value = profile.operation_set(states)
    assert value == {"required": 6, "completed": [name for name, _ in OPERATIONS[1:4]],
        "failed": [OPERATIONS[0][0], OPERATIONS[4][0]],
        "missing": [OPERATIONS[-1][0]], "complete": False}


@pytest.mark.parametrize("operation,_expected", OPERATIONS)
def test_dispatch_selects_one_pair_without_running_other_operations(profile, parent_case, operation, _expected):
    case = parent_case
    case.args.command, case.args.operation = "measure", operation
    case.install()
    assert profile.dispatch(case.args) == 0
    assert len(case.invocations) == len(case.communications) == 1
    config = json.loads(case.communications[0][0])
    value = json.loads((case.args.output / "report.json").read_bytes())
    assert config["operation"] == value["operation"] == operation
    assert case.communications[0][1] == 600
    assert [row["operation"] for row in value["result"]["operations"]] == [operation]
    assert value["operation_set"] == profile.operation_set({operation: "completed"})


@pytest.mark.parametrize("operation", [None, "all", "_run", 0, True])
def test_unknown_operation_refuses_before_dispatch_or_output(profile, parent_case, operation):
    case = parent_case
    case.args.command, case.args.operation = "measure", operation
    with pytest.raises(ValueError, match="unknown selected operation"):
        profile.dispatch(case.args)
    assert case.invocations == [] and not case.args.output.exists()


@pytest.fixture
def collection_case(profile, parent_case, tmp_path):
    """Create declarations, not real execution evidence; no native imports/calls."""
    case = parent_case
    prepared_raw = (case.checkpoint / "report.json").read_bytes()
    selected = {"driver_sha256": profile.sha(case.driver.read_bytes()), "python_identity": case.selected,
        "git_identity": case.result["git"]["identity"], "recovered_provenance": case.result["recovered_provenance"]}
    binding = profile.measurement_binding(prepared_raw, case.result, selected)
    documents, paths = [], []
    for index, (operation, _) in enumerate(OPERATIONS):
        child = deepcopy(case.result)
        for key in ("selection_relative", "declared_deadline_seconds", "preparation_stages", "checkpoint",
                    "synthetic_parameters"):
            child.pop(key)
        child.update(mode="measure", operation=operation, operations=[synthetic_pair(profile, operation)],
            projection=profile.projection_contract(), checkpoint_verification={"process_cpu_ns": 30, "wall_ns": 40})
        stdout = profile.canonical(child)
        document = {"format": profile.FORMAT, "mode": "measure", "scope": profile.SCOPE,
            "status": "completed", "report_role": "measured_operation_pair", "operation": operation,
            "operation_catalog": profile.operation_catalog(), "measurement_binding": deepcopy(binding),
            "operation_set": profile.operation_set({operation: "completed"}),
            "scientific_eligibility": False, "execution_authorized": False,
            "historical_capture_complete": False, "native_acceptance_evaluated": False,
            "declared_acceptance_deadline_seconds": 900, "diagnostic_wall_bound_seconds": 600,
            "parent_wall_seconds": 0.125, "child_exit_code": 0,
            "driver_sha256": selected["driver_sha256"], "utility_sha256": profile.UTILITY_SHA256,
            "python_identity": deepcopy(case.selected), "stderr_bytes": 0, "stderr_sha256": profile.sha(b""),
            "stdout_bytes": len(stdout), "stdout_sha256": profile.sha(stdout), "result": child,
            "limitations": list(profile.LIMITATIONS)}
        assert set(document) == profile.PARENT_REPORT_FIELDS
        path = tmp_path / f"fictional-operation-{index}.json"
        path.write_bytes(profile.canonical(document) + b"\n")
        paths.append(path)
        documents.append(document)
    return SimpleNamespace(case=case, paths=paths, documents=documents, binding=binding,
                           output=tmp_path / "collection-output")


def retain_inputs(fixture):
    return {path: path.read_bytes() for path in [fixture.case.driver, fixture.case.checkpoint / "report.json",
        fixture.case.case / "retained.txt", *fixture.paths]}


def assert_inputs(retained):
    assert {path: path.read_bytes() for path in retained} == retained


def rewrite(profile, fixture, index, *, rehash_child=False):
    document = fixture.documents[index]
    if rehash_child:
        stdout = profile.canonical(document["result"])
        document.update(stdout_sha256=profile.sha(stdout), stdout_bytes=len(stdout))
    fixture.paths[index].write_bytes(profile.canonical(document) + b"\n")


def test_collector_recomputes_complete_catalog_in_order_and_preserves_evidence(profile, collection_case):
    fixture = collection_case
    before = retain_inputs(fixture)
    result = profile.collect_reports(fixture.case.checkpoint, list(reversed(fixture.paths)), fixture.output)
    assert result == json.loads((fixture.output / "report.json").read_bytes())
    assert result["format"] == profile.COLLECTION_FORMAT and result["status"] == "complete"
    assert result["measurement_binding"] == fixture.binding
    assert result["operation_set"] == profile.operation_set({name: "completed" for name, _ in OPERATIONS})
    assert [row["operation"] for row in result["reports"]] == [name for name, _ in OPERATIONS]
    for row, path in zip(result["reports"], fixture.paths):
        assert row["report"] == {"sha256": profile.sha(before[path]), "bytes": len(before[path])}
        assert row["pair"]["plain"]["status"] == dict(OPERATIONS)[row["operation"]]
        assert row["checkpoint_verification"] == {"process_cpu_ns": 30, "wall_ns": 40}
        assert set(row["phase_overhead"]) == {"preflight", "final_verification"}
    assert all(result[key] is False for key in ("scientific_eligibility", "execution_authorized",
        "historical_capture_complete", "native_acceptance_evaluated"))
    assert_inputs(before)


@pytest.mark.parametrize("selected_count", [0, 4, 5])
def test_missing_refusal_controls_are_never_imputed_as_success(profile, collection_case, selected_count):
    fixture = collection_case
    result = profile.collect_reports(fixture.case.checkpoint, fixture.paths[:selected_count], fixture.output)
    assert result["status"] == "incomplete"
    assert result["operation_set"] == {"required": 6,
        "completed": [name for name, _ in OPERATIONS[:selected_count]], "failed": [],
        "missing": [name for name, _ in OPERATIONS[selected_count:]], "complete": False}
    assert len(result["reports"]) == selected_count


@pytest.mark.parametrize("status,exit_code", [("diagnostic_timeout", -9), ("diagnostic_timeout", 0),
                                             ("diagnostic_refused", 2)])
def test_failed_negative_measurement_is_not_a_passing_refusal(profile, collection_case, status, exit_code):
    fixture = collection_case
    document = fixture.documents[-1]
    operation = document["operation"]
    document.update(status=status, child_exit_code=exit_code, result=None,
        stdout_bytes=0, stdout_sha256=profile.sha(b""), operation_set=profile.operation_set({operation: status}))
    rewrite(profile, fixture, -1)
    result = profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert result["status"] == "incomplete" and result["operation_set"]["complete"] is False
    assert result["operation_set"]["failed"] == [operation] and result["operation_set"]["missing"] == []
    row = result["reports"][-1]
    assert row["status"] == status
    assert row["pair"] is row["checkpoint_verification"] is row["phase_overhead"] is None


@pytest.mark.parametrize("fault", ["preparation_bytes", "case_binding", "closure_binding", "driver_binding",
    "python_binding", "git_binding", "source_binding", "catalog_binding", "limit_binding", "parent_identity",
    "wrong_format", "wrong_role", "extra_field", "invented_operation", "catalog", "eligibility", "limit",
    "denominator", "boolean_denominator", "child_operation", "child_denominator", "projection", "pair_digest",
    "child_case", "stdout_pin", "failed_with_result", "refused_exit_zero", "boolean_parent_wall"])
def test_mixed_or_rehashed_reports_refuse_before_publication(profile, collection_case, fault):
    fixture = collection_case
    document = fixture.documents[0]
    binding = document["measurement_binding"]
    if fault == "preparation_bytes":
        binding["preparation_report"]["sha256"] = "0" * 64
    elif fault == "case_binding":
        binding["case_inventory"]["sha256"] = "0" * 64
    elif fault == "closure_binding":
        binding["prepared_loaded_closure"]["entries"] += 1
    elif fault == "driver_binding":
        binding["driver_sha256"] = "0" * 64
    elif fault in {"python_binding", "git_binding"}:
        binding[fault.split("_")[0] + "_identity"]["sha256"] = "0" * 64
    elif fault == "source_binding":
        binding["recovered_provenance"]["source_commit"] = "f" * 40
    elif fault == "catalog_binding":
        binding["operation_catalog"]["operations"].pop()
    elif fault == "limit_binding":
        binding["diagnostic_wall_bound_seconds"] = 1200
    elif fault == "parent_identity":
        document["python_identity"]["sha256"] = "0" * 64
    elif fault == "wrong_format":
        document["format"] = "native_full_schema_checkpoint_v1"
    elif fault == "wrong_role":
        document["report_role"] = "checkpoint_preparation"
    elif fault == "extra_field":
        document["optional_claim"] = True
    elif fault == "invented_operation":
        document["operation"] = "all"
    elif fault == "catalog":
        document["operation_catalog"]["operations"].pop()
    elif fault == "eligibility":
        document["scientific_eligibility"] = True
    elif fault == "limit":
        document["declared_acceptance_deadline_seconds"] = 1200
    elif fault == "denominator":
        document["operation_set"]["missing"] = []
    elif fault == "boolean_denominator":
        document["operation_set"]["complete"] = 0
    elif fault == "child_operation":
        document["result"]["operation"] = OPERATIONS[1][0]
    elif fault == "child_denominator":
        document["result"]["operations"].append(synthetic_pair(profile, OPERATIONS[1][0]))
    elif fault == "projection":
        document["result"]["projection"]["scope"] = "truncated evidence"
    elif fault == "pair_digest":
        document["result"]["operations"][0]["instrumented"]["semantic_sha256"] = "0" * 64
    elif fault == "child_case":
        document["result"]["case_inventory"]["entries"]["retained.txt"]["sha256"] = "0" * 64
    elif fault == "stdout_pin":
        document["stdout_sha256"] = "0" * 64
    elif fault == "failed_with_result":
        document["status"] = "diagnostic_timeout"
    elif fault == "refused_exit_zero":
        document.update(status="diagnostic_refused", result=None)
    else:
        document["parent_wall_seconds"] = True
    rewrite(profile, fixture, 0, rehash_child=fault.startswith("child_") or fault in {"projection", "pair_digest"})
    before = retain_inputs(fixture)
    with pytest.raises(ValueError):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


def test_duplicate_reports_never_choose_or_retry_an_operation(profile, collection_case):
    fixture = collection_case
    before = retain_inputs(fixture)
    with pytest.raises(ValueError, match="duplicate selected operation"):
        profile.collect_reports(fixture.case.checkpoint, [fixture.paths[0], fixture.paths[0]], fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


@pytest.mark.parametrize("fault", ["preparation_whitespace", "case_bytes"])
def test_binding_is_to_exact_selected_preparation_and_current_case(profile, collection_case, fault):
    fixture = collection_case
    path = fixture.case.checkpoint / "report.json" if fault == "preparation_whitespace" else fixture.case.case / "retained.txt"
    path.write_bytes(path.read_bytes() + b"\n")
    before = retain_inputs(fixture)
    with pytest.raises(ValueError, match="measurement binding|current checkpoint"):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


def test_collection_does_not_reopen_original_source_dependency_or_runtime_paths(profile, collection_case, monkeypatch):
    fixture = collection_case
    case = fixture.case
    for path in (case.source, case.recovery, case.dependencies, case.interpreter, case.git):
        path.rename(path.with_name(path.name + "-unavailable-at-declared-path"))
    def forbidden(*args, **kwargs):
        pytest.fail("read-only collection attempted original-source/runtime access or execution")
    for name in ("verify_inputs", "executable_identity"):
        monkeypatch.setattr(case.tools, name, forbidden)
    monkeypatch.setattr(profile.subprocess, "Popen", forbidden)
    monkeypatch.setattr(profile, "child", forbidden)
    monkeypatch.setattr(profile, "measure_checkpoint", forbidden)
    before = retain_inputs(fixture)
    result = profile.collect_reports(case.checkpoint, fixture.paths, fixture.output)
    assert result["status"] == "complete"
    assert_inputs(before)


@pytest.mark.parametrize("fault", ["existing", "checkpoint_child", "symlink_parent"])
def test_collection_preserves_existing_and_overlapping_destinations(profile, collection_case, tmp_path, fault):
    fixture = collection_case
    if fault == "existing":
        fixture.output.mkdir()
        (fixture.output / "report.json").write_bytes(b"prior reviewed collection")
    elif fault == "checkpoint_child":
        fixture.output = fixture.case.checkpoint / "new-output"
    else:
        alias = tmp_path / "collection-alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        fixture.output = alias / "new-output"
    before = retain_inputs(fixture)
    with pytest.raises(ValueError):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    if fault == "existing":
        assert (fixture.output / "report.json").read_bytes() == b"prior reviewed collection"
    else:
        assert not fixture.output.exists()
    assert_inputs(before)


def test_collection_output_bound_is_checked_before_directory_publication(profile, collection_case, monkeypatch):
    fixture = collection_case
    reference = fixture.output.with_name("reference-collection")
    profile.collect_reports(fixture.case.checkpoint, fixture.paths, reference)
    bound = (reference / "report.json").stat().st_size - 1
    assert max(path.stat().st_size for path in [fixture.case.checkpoint / "report.json", *fixture.paths]) < bound
    monkeypatch.setattr(profile, "MAX_REPORT_BYTES", bound)
    before = retain_inputs(fixture)
    with pytest.raises(ValueError, match="publication exceeds complete report bound"):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


@pytest.mark.parametrize("fault", ["duplicate_key", "oversize", "symlink"])
def test_operation_input_requires_bounded_strict_regular_json(profile, collection_case, fault):
    fixture = collection_case
    path = fixture.paths[0]
    if fault == "duplicate_key":
        raw = path.read_bytes().rstrip()
        path.write_bytes(raw[:-1] + b',"status":"completed"}')
    elif fault == "oversize":
        path.write_bytes(b" " * (profile.MAX_REPORT_BYTES + 1))
    else:
        target = path.with_name("same-bytes-alias-target.json")
        path.rename(target)
        path.symlink_to(target)
    before = retain_inputs(fixture)
    with pytest.raises(ValueError):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


@pytest.mark.parametrize("target", ["operation", "preparation", "case", "driver"])
def test_collection_rechecks_selected_bytes_before_publication(profile, collection_case, monkeypatch, target):
    fixture = collection_case
    paths = {"operation": fixture.paths[0], "preparation": fixture.case.checkpoint / "report.json",
             "case": fixture.case.case / "retained.txt", "driver": fixture.case.driver}
    changed = paths[target]
    original_read = fixture.case.tools.read_file
    fired = []
    def read_then_drift(path, *args, **kwargs):
        raw = original_read(path, *args, **kwargs)
        if path == fixture.paths[-1] and not fired:
            fired.append(True)
            changed.write_bytes(changed.read_bytes() + b"\n")
        return raw
    monkeypatch.setattr(fixture.case.tools, "read_file", read_then_drift)
    with pytest.raises(ValueError, match="changed"):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert fired == [True] and not fixture.output.exists()


def test_cli_requires_explicit_operation_and_collect_does_not_dispatch(profile, monkeypatch):
    arguments = ["measure", "--source", "source", "--recovery", "recovery", "--dependencies", "deps",
                 "--checkpoint", "prepared", "--output", "new-output"]
    def forbidden(*args, **kwargs):
        pytest.fail("parser or collector attempted automatic operation dispatch")
    monkeypatch.setattr(profile, "dispatch", forbidden)
    with pytest.raises(SystemExit) as missing:
        profile.main(arguments)
    assert missing.value.code == 2
    with pytest.raises(SystemExit) as unknown:
        profile.main([*arguments, "--operation", "all"])
    assert unknown.value.code == 2
    calls = []
    def collect(checkpoint, reports, output):
        calls.append((checkpoint, reports, output))
        return {"operation_set": {"complete": False}}
    monkeypatch.setattr(profile, "collect_reports", collect)
    assert profile.main(["collect", "--checkpoint", "prepared", "--output", "collection"]) == 1
    assert calls == [("prepared", [], "collection")]
