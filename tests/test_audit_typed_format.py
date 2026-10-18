"""Selected v2 contracts execute through real batching, including multiple workers."""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator
import pytest

from data_sheets_schema import audit_batches as batches, audit_batch_format as output
from data_sheets_schema import audit_grammar as grammar


@pytest.mark.parametrize("stage", ["worker", "integration"])
def test_full_v2_contract_example_matches_schema_real_parser_and_assembly(stage):
    contract = output.contract(stage, version=2)
    assert contract["format"] == "audit_batch_output_format_v2"
    assert Draft202012Validator(contract["json_schema"]).is_valid(contract["synthetic_example"]["proposal"])
    rendered = output.render(stage, version=2)
    assert json.loads(rendered.split("\n\n", 2)[2]) == contract
    example = output.synthetic_examples(version=2)
    plan = example["plan"]
    worker_id = plan["workers"][0]["id"]
    proposals = {worker_id: batches.canonical_bytes(example["worker"])}
    assert batches.check_worker(proposals[worker_id], plan, worker_id, version=2)["passed"]
    assert batches.check_integration(batches.canonical_bytes(example["integration"]), plan, proposals, version=2)["passed"]
    raw, lineage = batches.assemble(plan, proposals, batches.canonical_bytes(example["integration"]), version=2)
    assert grammar.check(raw, version=2)["passed"]
    assert not grammar.check(raw)["passed"]
    assert lineage["kind"] == "audit_batch_lineage_v2"
    assert json.loads(raw)["findings"][-1]["omission_candidates"] == ["example-candidate-1"]
    if stage == "integration":
        assert "omission_dispositions" in contract["json_schema"]["required"]
        exact_keys = next(r for r in contract["additional_rules"] if r.startswith("Return an integration delta"))
        assert "summary and omission_dispositions" in exact_keys
        assert "audit_integration_v2" in rendered


def multiworker():
    example = output.synthetic_examples(version=2)
    plan = batches.make_plan(example["original_full"], max_paths=1, version=2)
    assert len(plan["workers"]) == 3
    proposals = {}
    for worker in plan["workers"]:
        candidate = deepcopy(example["worker"])
        candidate["source_review"]["values"] = [r for r in candidate["source_review"]["values"] if r["path"] in worker["paths"]]
        candidate["findings"] = [f for f in candidate["findings"] if f["review_paths"][0] in worker["paths"]]
        proposals[worker["id"]] = batches.canonical_bytes(candidate)
    index = batches.build_index(plan, proposals, version=2)
    delta = deepcopy(example["integration"])
    delta.update(proposal_index_sha256=index["sha256"], retain_other_rows_from_index_sha256=index["sha256"])
    for decision, finding in zip(delta["finding_decisions"], index["findings"]):
        decision.update(id=finding["id"], previous_sha256=finding["sha256"])
    delta["new_findings"][0]["omission_candidates"] = ["candidate-a", "candidate-b"]
    delta["omission_dispositions"] = [{"candidate_id": identity, "action": "retain",
        "reason": "Two candidates merge into one finding.", "evidence": []}
        for identity in ("candidate-a", "candidate-b")]
    return plan, proposals, delta


def test_multiple_workers_keep_typed_findings_and_merged_omission_references_exact():
    plan, proposals, delta = multiworker()
    raw, lineage = batches.assemble(plan, proposals, batches.canonical_bytes(delta), version=2)
    audit = json.loads(raw)
    assert [f.get("kind") for f in audit["findings"]] == ["status_scope", "attribution", "omission"]
    assert audit["findings"][-1]["omission_candidates"] == ["candidate-a", "candidate-b"]
    assert [d["candidate_id"] for d in lineage["omission_dispositions"]] == ["candidate-a", "candidate-b"]
    for finding, row in zip(audit["findings"], lineage["findings"]):
        assert row["finding_sha256"] == batches.object_sha256(finding)


def test_multiworker_type_mutation_cannot_keep_old_index_authority():
    plan, proposals, delta = multiworker()
    first = next(iter(proposals))
    changed = json.loads(proposals[first])
    changed["findings"][0]["kind"] = "other"
    proposals[first] = batches.canonical_bytes(changed)
    result = batches.check_integration(batches.canonical_bytes(delta), plan, proposals, version=2)
    assert not result["passed"]
    assert any("index" in error["code"] or "predecessor" in error["code"] for error in result["errors"])


@pytest.mark.parametrize("stage", ["worker", "integration"])
def test_v2_contracts_are_fresh_without_changing_v1(stage):
    old = output.render(stage)
    contract = output.contract(stage, version=2)
    contract["json_schema"]["$defs"]["finding"]["properties"].clear()
    contract["additional_rules"].clear()
    contract["synthetic_example"]["proposal"].clear()
    fresh = output.contract(stage, version=2)
    assert fresh["json_schema"]["$defs"]["finding"]["properties"]["kind"]
    assert fresh["additional_rules"] and fresh["synthetic_example"]["proposal"]
    assert output.render(stage) == old
