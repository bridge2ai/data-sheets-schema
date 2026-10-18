"""Versioned batching preserves typed evidence and released v1 wire bytes."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from data_sheets_schema import audit_batches as b, audit_batch_format as fmt


@pytest.mark.parametrize("selection", [{}, {"version": 1}])
def test_released_v1_exact_bytes(selection):
    saved = json.loads((Path(__file__).parent / "fixtures/typed_audit_legacy_v1.json").read_bytes())
    plan = b.make_plan(saved["original_full"], **selection)
    workers = {key: value.encode() for key, value in saved["worker_bytes"].items()}
    delta = saved["integration_bytes"].encode()
    worker_id = next(iter(workers))
    audit, lineage = b.assemble(plan, workers, delta, **selection)
    actual = dict(plan=plan, index=b.build_index(plan, workers, **selection),
                  audit=json.loads(audit), lineage=lineage,
                  worker_check=b.check_worker(workers[worker_id], plan, worker_id, **selection),
                  integration_check=b.check_integration(delta, plan, workers, **selection),
                  worker_bad_json=b.check_worker(b"{", plan, worker_id, **selection),
                  worker_unknown=b.check_worker(workers[worker_id], plan, "absent", **selection),
                  integration_bad_json=b.check_integration(b"{", plan, workers, **selection))
    assert {key: b.canonical_bytes(value).decode() for key, value in actual.items()} == saved["expected"]
    b.validate_plan(plan, saved["original_full"], **selection)


def example():
    ex = fmt.synthetic_examples(version=2)
    plan = ex["plan"]
    workers = {plan["workers"][0]["id"]: b.canonical_bytes(ex["worker"])}
    return ex, plan, workers, ex["integration"]


def test_typed_all_integration_routes_and_exact_lineage():
    ex, plan, workers, delta = example()
    audit, lineage = b.assemble(plan, workers, b.canonical_bytes(delta), version=2)
    value = json.loads(audit)
    assert [row.get("kind") for row in value["findings"]] == ["status_scope", "attribution", "omission"]
    assert value["findings"][-1]["omission_candidates"] == ["example-candidate-1"]
    assert [row["kind"] for row in lineage["findings"]] == ["retain", "replace", "integration_new"]
    assert [row["action"] for row in lineage["finding_dispositions"]] == ["retain", "replace", "drop"]
    for finding, trace in zip(value["findings"], lineage["findings"]):
        assert trace["finding_sha256"] == b.object_sha256(finding)
    disposition = delta["omission_dispositions"][0]
    assert lineage["omission_dispositions"] == [{**disposition, "decision_ordinal": 0,
                                                "decision_sha256": b.object_sha256(disposition)}]
    assert lineage["kind"] == "audit_batch_lineage_v2"
    assert lineage["schema_version"] == 2


@pytest.mark.parametrize("change", ["kind", "omission_candidates"])
def test_complete_finding_hash_rejects_stale_integration(change):
    ex, plan, workers, delta = example()
    original = deepcopy(ex["worker"])
    if change == "kind":
        original["findings"][0]["kind"] = "other"
    else:
        original["findings"][0].update(kind="omission", omission_candidates=["candidate-2"])
    modified = {next(iter(workers)): b.canonical_bytes(original)}
    assert b.check_worker(next(iter(modified.values())), plan, next(iter(workers)), version=2)["passed"]
    assert b.build_index(plan, modified, version=2)["sha256"] != b.build_index(plan, workers, version=2)["sha256"]
    assert not b.check_integration(b.canonical_bytes(delta), plan, modified, version=2)["passed"]


@pytest.mark.parametrize("mutation", ["absent", "duplicate", "unknown_key", "empty_reason", "drop_no_evidence", "invalid_action"])
def test_closed_complete_disposition_shape(mutation):
    _, plan, workers, delta = example()
    row = delta["omission_dispositions"][0]
    if mutation == "absent":
        del delta["omission_dispositions"]
    elif mutation == "duplicate":
        delta["omission_dispositions"].append(deepcopy(row))
    elif mutation == "unknown_key":
        row["success"] = True
    elif mutation == "empty_reason":
        row["reason"] = " "
    elif mutation == "drop_no_evidence":
        row["action"] = "drop"
    else:
        row["action"] = {}
    assert not b.check_integration(b.canonical_bytes(delta), plan, workers, version=2)["passed"]


def test_drop_evidence_preserved_but_candidate_coverage_is_consumer_responsibility():
    _, plan, workers, delta = example()
    row = delta["omission_dispositions"][0]
    row["action"] = "drop"
    row["evidence"] = deepcopy(delta["new_findings"][0]["evidence"])
    _, lineage = b.assemble(plan, workers, b.canonical_bytes(delta), version=2)
    assert lineage["decision_assertions"][-1] == row["evidence"][0]
    assert lineage["omission_dispositions"][0]["decision_sha256"] == b.object_sha256(row)
    delta["omission_dispositions"] = []
    assert b.check_integration(b.canonical_bytes(delta), plan, workers, version=2)["passed"]


@pytest.mark.parametrize("route", ["worker", "replace", "new"])
@pytest.mark.parametrize("record", ["core", "both"])
def test_full_only_omission_routes(route, record):
    ex, plan, workers, delta = example()
    if route == "worker":
        row = ex["worker"]["findings"][0]
        row.update(kind="omission", omission_candidates=["example-candidate-1"], record=record)
        assert not b.check_worker(b.canonical_bytes(ex["worker"]), plan, next(iter(workers)), version=2)["passed"]
    else:
        row = (delta["finding_decisions"][1]["findings"][0] if route == "replace" else delta["new_findings"][0])
        row.update(kind="omission", omission_candidates=["example-candidate-1"], record=record)
        assert not b.check_integration(b.canonical_bytes(delta), plan, workers, version=2)["passed"]


@pytest.mark.parametrize("version", [True, False, None, "2", 2.0, 0, 3, [], {}])
def test_all_public_entrypoints_require_exact_version(version):
    ex, plan, workers, delta = example()
    calls = [lambda: b.make_plan(ex["original_full"], version=version),
             lambda: b.validate_plan(plan, ex["original_full"], version=version),
             lambda: b.check_worker(next(iter(workers.values())), plan, next(iter(workers)), version=version),
             lambda: b.build_index(plan, workers, version=version),
             lambda: b.check_integration(b.canonical_bytes(delta), plan, workers, version=version),
             lambda: b.assemble(plan, workers, b.canonical_bytes(delta), version=version)]
    for call in calls:
        with pytest.raises(ValueError):
            call()


def test_v2_never_auto_selected_from_plan_or_responses():
    ex, plan, workers, delta = example()
    with pytest.raises(b.AuditBatchError):
        b.validate_plan(plan, ex["original_full"])
    with pytest.raises(b.AuditBatchError):
        b.build_index(plan, workers)
    with pytest.raises(b.AuditBatchError):
        b.assemble(plan, workers, b.canonical_bytes(delta))
    assert not b.check_worker(next(iter(workers.values())), plan, next(iter(workers)))["passed"]
    assert not b.check_integration(b.canonical_bytes(delta), plan, workers)["passed"]
