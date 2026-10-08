"""Regressions for the three independent Codex plugin evidence findings.

These are synthetic local artifacts. No recovered reconstruction, process,
helper, provider, or scientific scoring runs in this module.
"""
from copy import deepcopy
from io import BytesIO
import json
from types import SimpleNamespace

import pytest

from .test_native_full_schema_profile_runtime import profile, parent_case, synthetic_pair
from .test_native_full_schema_profile_operations import collection_case, retain_inputs, assert_inputs, rewrite


@pytest.mark.parametrize("consumer", ["measure", "collect"])
@pytest.mark.parametrize("fault", ["missing_field", "extra_field", "historical_complete", "zero_flag",
    "scope", "limits_prepare", "limits_acceptance", "child_exit", "boolean_exit", "negative_time",
    "boolean_time", "wrong_stdout_hash", "wrong_stdout_size", "boolean_stdout_size", "negative_stderr_size",
    "invalid_stderr_hash", "missing_operation", "claimed_operation", "binding", "wrong_catalog",
    "wrong_denominator", "boolean_denominator", "missing_limitations"])
def test_preparation_anchor_must_be_an_exact_published_v2_envelope(
        profile, collection_case, consumer, fault):
    fixture = collection_case
    case = fixture.case
    value = deepcopy(case.preparation)
    if fault == "missing_field":
        del value["scope"]
    elif fault == "extra_field":
        value["assumed_verified"] = True
    elif fault == "historical_complete":
        value["historical_capture_complete"] = True
    elif fault == "zero_flag":
        value["execution_authorized"] = 0
    elif fault == "scope":
        value["scope"] = "completed historical native acceptance"
    elif fault == "limits_prepare":
        value["diagnostic_wall_bound_seconds"] = 600
    elif fault == "limits_acceptance":
        value["declared_acceptance_deadline_seconds"] = 1200
    elif fault == "child_exit":
        value["child_exit_code"] = 1
    elif fault == "boolean_exit":
        value["child_exit_code"] = False
    elif fault == "negative_time":
        value["parent_wall_seconds"] = -1
    elif fault == "boolean_time":
        value["parent_wall_seconds"] = True
    elif fault == "wrong_stdout_hash":
        value["stdout_sha256"] = "0" * 64
    elif fault == "wrong_stdout_size":
        value["stdout_bytes"] += 1
    elif fault == "boolean_stdout_size":
        value["stdout_bytes"] = True
    elif fault == "negative_stderr_size":
        value["stderr_bytes"] = -1
    elif fault == "invalid_stderr_hash":
        value["stderr_sha256"] = "not a sha256"
    elif fault == "missing_operation":
        del value["operation"]
    elif fault == "claimed_operation":
        value["operation"] = "_load_live"
    elif fault == "binding":
        value["measurement_binding"] = {}
    elif fault == "wrong_catalog":
        value["operation_catalog"]["operations"].pop()
    elif fault == "wrong_denominator":
        value["operation_set"]["missing"] = []
    elif fault == "boolean_denominator":
        value["operation_set"]["complete"] = 0
    else:
        value["limitations"] = []
    raw = profile.canonical(value)
    (case.checkpoint / "report.json").write_bytes(raw)
    # Rebind every fictional operation to these exact malformed preparation
    # bytes, so a raw-preparation mismatch cannot mask the envelope defect.
    for index, document in enumerate(fixture.documents):
        document["measurement_binding"]["preparation_report"] = {
            "sha256": profile.sha(raw), "bytes": len(raw)}
        rewrite(profile, fixture, index)
    before = retain_inputs(fixture)
    case.args.command = "measure"
    case.install()
    with pytest.raises(ValueError):
        if consumer == "measure":
            profile.dispatch(case.args)
        else:
            profile.collect_reports(case.checkpoint, fixture.paths, fixture.output)
    assert case.invocations == [] and not case.args.output.exists() and not fixture.output.exists()
    assert_inputs(before)


@pytest.mark.parametrize("origin", ["unknown/file.py", "/dependency/file.py", "dependency/",
    "dependency//file.py", "dependency/./file.py", "dependency/../file.py", "dependency/a/../file.py",
    "dependency\\file.py", "dependency/a\\file.py", "dependency/a/", "dependency/./", "dependency/.."])
def test_final_import_closure_requires_canonical_role_relative_origins(profile, origin):
    rows = [{"origin": origin, "sha256": "a" * 64, "bytes": 12}]
    with pytest.raises(ValueError):
        profile.validate_loaded_closure(rows)


@pytest.mark.parametrize("fault", ["empty", "nonrow", "missing_field", "extra_field", "invalid_digest",
    "uppercase_digest", "negative_bytes", "boolean_bytes", "duplicate_origin", "conflicting_duplicate"])
def test_final_import_closure_cannot_be_arbitrary_json(profile, collection_case, fault):
    fixture = collection_case
    document = fixture.documents[0]
    rows = document["result"]["loaded_closure"]
    if fault == "empty":
        rows.clear()
    elif fault == "nonrow":
        rows[0] = "assume imported code unchanged"
    elif fault == "missing_field":
        del rows[0]["sha256"]
    elif fault == "extra_field":
        rows[0]["trusted"] = True
    elif fault == "invalid_digest":
        rows[0]["sha256"] = "not a digest"
    elif fault == "uppercase_digest":
        rows[0]["sha256"] = "A" * 64
    elif fault == "negative_bytes":
        rows[0]["bytes"] = -1
    elif fault == "boolean_bytes":
        rows[0]["bytes"] = True
    else:
        rows.append(deepcopy(rows[0]))
        if fault == "conflicting_duplicate":
            rows[-1]["sha256"] = "b" * 64
    rewrite(profile, fixture, 0, rehash_child=True)
    before = retain_inputs(fixture)
    with pytest.raises(ValueError):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


@pytest.mark.parametrize("field,value", [("sha256", "f" * 64), ("bytes", 900)])
def test_final_closure_cannot_change_a_prepared_origin_pin(profile, collection_case, field, value):
    fixture = collection_case
    fixture.documents[0]["result"]["loaded_closure"][0][field] = value
    rewrite(profile, fixture, 0, rehash_child=True)
    before = retain_inputs(fixture)
    with pytest.raises(ValueError):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


def test_collection_retains_each_operations_distinct_final_import_closure(profile, collection_case):
    fixture = collection_case
    for index, document in enumerate(fixture.documents):
        document["result"]["loaded_closure"].append({"origin": f"dependency/operation_{index}.py",
            "sha256": profile.sha(f"fictional operation {index}".encode()), "bytes": index})
        rewrite(profile, fixture, index, rehash_child=True)
    before = retain_inputs(fixture)
    result = profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert result["status"] == "complete"
    for row, document in zip(result["reports"], fixture.documents):
        closure = document["result"]["loaded_closure"]
        assert row["loaded_closure"] == {"sha256": profile.sha(profile.canonical(closure)), "entries": len(closure)}
    assert len({row["loaded_closure"]["sha256"] for row in result["reports"]}) == 6
    assert_inputs(before)


def test_failed_measurement_does_not_claim_a_final_import_closure(profile, collection_case):
    fixture = collection_case
    document = fixture.documents[0]
    document.update(status="diagnostic_timeout", child_exit_code=-9, result=None,
        stdout_bytes=0, stdout_sha256=profile.sha(b""),
        operation_set=profile.operation_set({document["operation"]: "diagnostic_timeout"}))
    rewrite(profile, fixture, 0)
    result = profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert result["reports"][0]["loaded_closure"] is None
    assert result["operation_set"]["failed"] == [document["operation"]]


@pytest.mark.parametrize("fault", ["bare_hash", "both_forged_hashes", "changed_payload", "rehashed_different_payload",
    "malformed_equal_payloads", "boolean_as_int", "wrong_typed_float", "missing_none_tag", "bad_bytes_pin",
    "negative_bytes", "malformed_dict_pair", "unknown_tag"])
def test_positive_pair_is_recomputed_from_complete_typed_state(profile, collection_case, fault):
    fixture = collection_case
    pair = fixture.documents[0]["result"]["operations"][0]
    left, right = pair["plain"], pair["instrumented"]
    if fault == "bare_hash":
        del left["semantics"]
        del right["semantics"]
    elif fault == "both_forged_hashes":
        left["semantic_sha256"] = right["semantic_sha256"] = "0" * 64
    elif fault == "changed_payload":
        right["semantics"] = ["str", "different captured state"]
    elif fault == "rehashed_different_payload":
        right["semantics"] = ["str", "different captured state"]
        right["semantic_sha256"] = profile.sha(profile.canonical(right["semantics"]))
    else:
        malformed = {
            "malformed_equal_payloads": {"assertion": "same returned state"},
            "boolean_as_int": ["int", True], "wrong_typed_float": ["float", 1],
            "missing_none_tag": ["none", None], "bad_bytes_pin": ["bytes", 3, "bad hash"],
            "negative_bytes": ["bytes", -1, "a" * 64], "malformed_dict_pair": ["dict", [["str", "key"]]],
            "unknown_tag": ["object", "repr-only proof"],
        }[fault]
        for arm in (left, right):
            arm["semantics"] = deepcopy(malformed)
            arm["semantic_sha256"] = profile.sha(profile.canonical(malformed))
    rewrite(profile, fixture, 0, rehash_child=True)
    before = retain_inputs(fixture)
    with pytest.raises(ValueError):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


def test_positive_and_refusal_payload_roles_are_disjoint(profile):
    pair = synthetic_pair(profile, "refusal_stale_worker_read_in_memory")
    pair["plain"]["semantics"] = ["none"]
    with pytest.raises(ValueError):
        profile.validate_pair(pair, pair["operation"])
    pair = synthetic_pair(profile, "_load_live")
    pair["plain"]["semantics"] = pair["instrumented"]["semantics"] = None
    for arm in ("plain", "instrumented"):
        pair[arm]["semantic_sha256"] = profile.sha(profile.canonical(None))
    with pytest.raises(ValueError):
        profile.validate_pair(pair, pair["operation"])


def test_typed_state_bound_refuses_instead_of_truncating_equal_arms(profile):
    pair = synthetic_pair(profile)
    nested = ["none"]
    for _ in range(130):
        nested = ["list", [nested]]
    for arm in ("plain", "instrumented"):
        pair[arm]["semantics"] = deepcopy(nested)
        pair[arm]["semantic_sha256"] = profile.sha(profile.canonical(nested))
    with pytest.raises(ValueError, match="bound"):
        profile.validate_pair(pair, "_load_live")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_typed_state_never_accepts_nonfinite_float_evidence(profile, value):
    with pytest.raises(ValueError):
        profile.validate_typed_value(["float", value])


def test_typed_state_node_ceiling_is_not_silent_truncation(profile):
    profile.validate_typed_value(["list", [["none"]] * 99999])
    with pytest.raises(ValueError, match="bound"):
        profile.validate_typed_value(["list", [["none"]] * 100000])


@pytest.mark.parametrize("overflow", [False, True])
def test_child_checks_complete_result_bound_before_first_stdout_byte(profile, monkeypatch, overflow):
    child_result = {"fictional_test_result": "full serialized evidence"}
    raw = profile.canonical(child_result)
    stdin, stdout = BytesIO(b"{}"), BytesIO()
    fake_sys = SimpleNamespace(flags=SimpleNamespace(isolated=1, no_site=1), dont_write_bytecode=True,
        stdin=SimpleNamespace(buffer=stdin), stdout=SimpleNamespace(buffer=stdout))
    monkeypatch.setattr(profile, "sys", fake_sys)
    monkeypatch.setattr(profile, "utility", lambda: SimpleNamespace(strict_json=json.loads))
    monkeypatch.setattr(profile, "child", lambda config: child_result)
    monkeypatch.setattr(profile, "MAX_REPORT_BYTES", len(raw) - int(overflow))
    if overflow:
        with pytest.raises(ValueError, match="child.*bound|bound.*child"):
            profile.main(["_child"])
        assert stdout.getvalue() == b""
    else:
        assert profile.main(["_child"]) == 0
        assert stdout.getvalue() == raw


def test_parent_envelope_overflow_retains_failed_measurement_and_full_denominator(
        profile, collection_case, monkeypatch):
    fixture = collection_case
    case = fixture.case
    child = deepcopy(fixture.documents[0]["result"])
    child["environment"]["python"] = "fictional interpreter disclosure " + "x" * 16384
    raw = profile.canonical(child)
    monkeypatch.setattr(profile, "MAX_REPORT_BYTES", len(raw) + 1)
    case.args.command = "measure"
    case.install(body=raw)
    before = retain_inputs(fixture)
    assert profile.dispatch(case.args) == 1
    document = json.loads((case.args.output / "report.json").read_bytes())
    assert document["status"] == "diagnostic_publication_refused" and document["result"] is None
    assert document["child_exit_code"] == 0
    assert document["stdout_sha256"] == profile.sha(raw) and document["stdout_bytes"] == len(raw)
    assert document["stderr_sha256"] == profile.sha(b"") and document["stderr_bytes"] == 0
    assert document["measurement_binding"] == fixture.binding
    assert document["operation"] == "_load_live"
    assert document["operation_set"] == profile.operation_set({"_load_live": "diagnostic_publication_refused"})
    assert (case.args.output / "refusal.stderr").read_bytes() == b""
    assert len(case.invocations) == len(case.communications) == 1
    assert_inputs(before)
    paths = [case.args.output / "report.json", *fixture.paths[1:]]
    result = profile.collect_reports(case.checkpoint, paths, fixture.output)
    assert result["status"] == "incomplete" and result["operation_set"]["complete"] is False
    assert result["operation_set"]["required"] == 6
    assert result["operation_set"]["failed"] == ["_load_live"]
    assert len(result["operation_set"]["completed"]) == 5 and result["operation_set"]["missing"] == []
    assert result["reports"][0]["pair"] is result["reports"][0]["loaded_closure"] is None
    assert all(result[key] is False for key in ("scientific_eligibility", "execution_authorized",
        "historical_capture_complete", "native_acceptance_evaluated"))


@pytest.mark.parametrize("fault", ["nonzero_exit", "retained_result", "claimed_complete"])
def test_publication_refusal_cannot_disguise_child_failure_or_completed_result(profile, collection_case, fault):
    fixture = collection_case
    document = fixture.documents[0]
    completed_child = deepcopy(document["result"])
    document.update(status="diagnostic_publication_refused", result=None,
        operation_set=profile.operation_set({document["operation"]: "diagnostic_publication_refused"}))
    if fault == "nonzero_exit":
        document["child_exit_code"] = 2
    elif fault == "retained_result":
        document["result"] = completed_child
    else:
        document["operation_set"] = profile.operation_set({document["operation"]: "completed"})
    rewrite(profile, fixture, 0)
    before = retain_inputs(fixture)
    with pytest.raises(ValueError):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)


@pytest.mark.parametrize("kind", ["dict", "dataclass"])
def test_equal_rehashed_duplicate_typed_fields_are_still_malformed(profile, collection_case, kind):
    fixture = collection_case
    pair = fixture.documents[0]["result"]["operations"][0]
    payload = (["dict", [
        [["str", "same-key"], ["str", "first value"]],
        [["str", "same-key"], ["str", "second value"]],
    ]] if kind == "dict" else ["dataclass", "FictionalCapturedState", [
        ["same_field", ["str", "first value"]], ["same_field", ["str", "second value"]],
    ]])
    for arm in ("plain", "instrumented"):
        pair[arm]["semantics"] = deepcopy(payload)
        pair[arm]["semantic_sha256"] = profile.sha(profile.canonical(payload))
    rewrite(profile, fixture, 0, rehash_child=True)
    before = retain_inputs(fixture)
    with pytest.raises(ValueError, match="repeats"):
        profile.collect_reports(fixture.case.checkpoint, fixture.paths, fixture.output)
    assert not fixture.output.exists()
    assert_inputs(before)
