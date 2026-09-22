"""Output documentation agrees with source-blind grammar on invented inputs."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from data_sheets_schema import audit_batches as batches, audit_grammar as grammar
from data_sheets_schema import audit_batch_format as output


@pytest.fixture
def example():
    return output.synthetic_examples()


def proposals(example):
    return {example["plan"]["workers"][0]["id"]: batches.canonical_bytes(example["worker"])}


def accepts(stage, value):
    return Draft202012Validator(output.schema(stage)).is_valid(value)


def worker_report(example, value):
    return batches.check_worker(batches.canonical_bytes(value), example["plan"],
                                example["plan"]["workers"][0]["id"])


def integration_report(example, value):
    return batches.check_integration(batches.canonical_bytes(value), example["plan"], proposals(example))


@pytest.mark.parametrize("stage", ["worker", "integration"])
def test_every_rendered_example_is_a_valid_schema_and_parser_fixture(example, stage):
    contract = output.contract(stage)
    Draft202012Validator.check_schema(contract["json_schema"])
    assert accepts(stage, contract["synthetic_example"]["proposal"])
    assert worker_report(example, example["worker"])["passed"]
    assert integration_report(example, example["integration"])["passed"]
    assembled, lineage = batches.assemble(example["plan"], proposals(example),
                                        batches.canonical_bytes(example["integration"]))
    assert grammar.check(assembled)["passed"]
    assert [d["action"] for d in lineage["finding_dispositions"]] == ["retain", "replace", "drop"]
    assert json.loads(assembled)["source_review"]["values"][2]["claims"][0]["verdict"] == "supported"
    rendered = output.render(stage)
    decoded = json.loads(rendered.split("\n\n", 2)[2])
    assert decoded == contract
    assert "Invented grammar fixture only" in rendered


@pytest.mark.parametrize("stage", ["worker", "integration"])
def test_contract_freshness_determinism_and_stage_specific_keys(stage):
    first = output.contract(stage)
    first["json_schema"]["properties"].clear()
    first["additional_rules"].clear()
    assert output.contract(stage)["json_schema"]["properties"]
    assert output.contract(stage)["additional_rules"]
    assert output.render(stage) == output.render(stage)
    keys = set(output.schema(stage)["required"])
    expected = ({"findings", "summary", "source_review"} if stage == "worker" else {
        "kind", "proposal_index_sha256", "retain_other_rows_from_index_sha256",
        "row_replacements", "finding_decisions", "new_findings", "summary"})
    assert keys == expected


@pytest.mark.parametrize("stage", ["", "audit", "report", "WORKER"])
def test_unknown_stage_is_not_silently_rendered(stage):
    for call in (output.schema, output.contract, output.render):
        with pytest.raises(ValueError, match="unknown audit batch"):
            call(stage)


@pytest.mark.parametrize("damage", ["missing_claim_reason", "extra_claim_key", "artifact_claim_evidence",
    "mixed_provenance", "wrong_status", "wrong_record", "wrong_severity", "summary_object",
    "claims_mapping", "row_both_variants", "finding_empty_evidence", "digest_newline",
    "bad_pointer_after_newline", "extra_document_key", "attribution_string", "duplicate_attribution"])
def test_worker_local_shape_defects_rejected_by_documented_schema_and_real_parser(example, damage):
    value = deepcopy(example["worker"])
    claim = value["source_review"]["values"][0]["claims"][0]
    if damage == "missing_claim_reason": claim.pop("reason")
    elif damage == "extra_claim_key": claim["explanation"] = "No extra fields."
    elif damage == "artifact_claim_evidence":
        claim["evidence"] = [{"artifact": "original_full", "path": "/alpha", "op": "contains", "quote": "Example alpha."}]
    elif damage == "mixed_provenance":
        claim["evidence"] = [{"source": "example.txt", "chunk": "c001", "quote": "Example."}, provenance()]
    elif damage == "wrong_status": claim["source_status"] = "unknown"
    elif damage == "wrong_record": value["findings"][0]["record"] = "original_full"
    elif damage == "wrong_severity": value["findings"][0]["severity"] = "warning"
    elif damage == "summary_object": value["summary"] = {"count": 3}
    elif damage == "claims_mapping": value["source_review"]["values"][0]["claims"] = {"one": claim}
    elif damage == "row_both_variants": value["source_review"]["values"][0]["metadata_reason"] = "Structural."
    elif damage == "finding_empty_evidence": value["findings"][0]["evidence"] = []
    elif damage == "digest_newline": value["source_review"]["sha256"] += "\n"
    elif damage == "bad_pointer_after_newline": value["source_review"]["values"][0]["path"] = "/a\nb~3"
    elif damage == "extra_document_key": value["findings"][0]["evidence"][0]["extra"] = "No."
    elif damage == "attribution_string": claim["attributed_to"] = "example.txt"
    elif damage == "duplicate_attribution": claim["attributed_to"] = ["example.txt", "example.txt"]
    assert not accepts("worker", value)
    assert not worker_report(example, value)["passed"]


def provenance(field="effective_priority", value=2):
    return {"provenance": "source_manifest", "sha256": "a" * 64, "source_id": "example",
            "source": "example.txt", "field": field, "value": value}


@pytest.mark.parametrize("field,value,valid", [("effective_priority", 2, True),
    ("effective_priority", True, False), ("effective_priority", "2", False),
    ("effective_priority", 0, False), ("priority_basis", "source_override", True),
    ("priority_basis", "custom", False), ("source_type", "manual", True),
    ("captured_at", "2020-01-01", True), ("superseded_by", "example-later", True)])
def test_all_provenance_field_variants_match_grammar(example, field, value, valid):
    candidate = deepcopy(example["worker"])
    claim = candidate["source_review"]["values"][0]["claims"][0]
    claim.update(claim_status="fact", source_status="fact", attributed_to=[], evidence=[provenance(field, value)])
    assert accepts("worker", candidate) is valid
    assert worker_report(example, candidate)["passed"] is valid


@pytest.mark.parametrize("status", sorted(grammar.STATUSES))
def test_supported_status_pair_and_nonempty_document_evidence(example, status):
    candidate = deepcopy(example["worker"])
    claim = candidate["source_review"]["values"][0]["claims"][0]
    claim.update(verdict="supported", claim_status=status, source_status=status,
                 evidence=[{"source": "example.txt", "chunk": "c001", "quote": "Example."}])
    candidate["findings"].pop(0)
    assert accepts("worker", candidate) and worker_report(example, candidate)["passed"]
    claim["source_status"] = "unstated"
    assert not accepts("worker", candidate) and not worker_report(example, candidate)["passed"]


@pytest.mark.parametrize("damage", ["missing_replace_findings", "retain_findings", "drop_findings",
    "empty_replace_findings", "replace_empty_evidence", "drop_empty_evidence", "replacement_missing_reason",
    "replacement_empty_evidence", "extra_top_key", "unknown_action", "new_finding_artifact_name"])
def test_integration_local_shapes_are_explicit_and_match_parser(example, damage):
    value = deepcopy(example["integration"])
    keep, replace, drop = value["finding_decisions"]
    if damage == "missing_replace_findings": replace.pop("findings")
    elif damage == "retain_findings": keep["findings"] = []
    elif damage == "drop_findings": drop["findings"] = []
    elif damage == "empty_replace_findings": replace["findings"] = []
    elif damage == "replace_empty_evidence": replace["evidence"] = []
    elif damage == "drop_empty_evidence": drop["evidence"] = []
    elif damage == "replacement_missing_reason": value["row_replacements"][0].pop("reason")
    elif damage == "replacement_empty_evidence": value["row_replacements"][0]["evidence"] = []
    elif damage == "extra_top_key": value["findings"] = []
    elif damage == "unknown_action": keep["action"] = "keep"
    elif damage == "new_finding_artifact_name":
        value["new_findings"] = [deepcopy(example["worker"]["findings"][0])]
        value["new_findings"][0]["record"] = "original_full"
    assert not accepts("integration", value)
    assert not integration_report(example, value)["passed"]


@pytest.mark.parametrize("damage", ["wrong_index", "missing_decision", "duplicate_decision", "wrong_predecessor",
    "row_path_mismatch", "duplicate_row", "drop_orphans_revise"])
def test_additional_binding_rules_are_not_misrepresented_as_local_schema_checks(example, damage):
    value = deepcopy(example["integration"])
    if damage == "wrong_index": value["proposal_index_sha256"] = "0" * 64
    elif damage == "missing_decision": value["finding_decisions"].pop()
    elif damage == "duplicate_decision": value["finding_decisions"].append(deepcopy(value["finding_decisions"][0]))
    elif damage == "wrong_predecessor": value["finding_decisions"][0]["previous_sha256"] = "0" * 64
    elif damage == "row_path_mismatch": value["row_replacements"][0]["row"]["path"] = "/alpha"
    elif damage == "duplicate_row": value["row_replacements"].append(deepcopy(value["row_replacements"][0]))
    elif damage == "drop_orphans_revise": value["row_replacements"] = []
    assert accepts("integration", value)
    assert not integration_report(example, value)["passed"]
    text = output.render("integration")
    for requirement in ("canonical-object sha256", "exactly one entry", "not the plan hash",
                        "never add/delete a row", "orphan a revised row"):
        assert requirement.lower() in text.lower()


@pytest.mark.parametrize("removal", [{"path": "/alpha"}, {"path": "/alpha", "identity": "/name"},
    {"path": "/alpha", "match": "anonymous_structure_v1", "original_full_sha256": "a" * 64}])
def test_all_structural_removal_variants_disclosed(example, removal):
    value = deepcopy(example["worker"])
    value["findings"][0]["remove_relationship"] = removal
    assert accepts("worker", value) and worker_report(example, value)["passed"]
    removal["identity"] = "/name\n"
    assert not accepts("worker", value) and not worker_report(example, value)["passed"]


def test_raw_json_and_literal_numeric_rules_are_disclosed(example):
    text = output.render("worker")
    for requirement in ("raw UTF-8 bytes", "no inserted comma", "one complete JSON object",
                        "duplicate keys", "nonfinite numbers", "2.0", "not a pointer-keyed mapping"):
        assert requirement in text
    # JSON Schema's mathematical integer accepts 2.0, while the actual JSON
    # grammar requires an integer token. The explicit additional rule covers it.
    candidate = deepcopy(example["worker"])
    candidate["source_review"]["values"][0]["claims"][0].update(
        source_status="fact", evidence=[provenance(value=2.0)])
    assert accepts("worker", candidate)
    assert not worker_report(example, candidate)["passed"]


def test_empty_worker_and_empty_finding_decisions_remain_valid():
    plan = batches.make_plan("{}\n")
    worker = {"findings": [], "summary": "Empty invented inventory.", "source_review": {
        "artifact": "original_full", "sha256": plan["original_full_sha256"], "values": []}}
    assert accepts("worker", worker)
    workers = {plan["workers"][0]["id"]: batches.canonical_bytes(worker)}
    index = batches.build_index(plan, workers)
    integration = {"kind": "audit_integration_v1", "proposal_index_sha256": index["sha256"],
        "retain_other_rows_from_index_sha256": index["sha256"], "row_replacements": [],
        "finding_decisions": [], "new_findings": [], "summary": "Empty invented integration."}
    assert accepts("integration", integration)
    assert batches.check_integration(batches.canonical_bytes(integration), plan, workers)["passed"]
