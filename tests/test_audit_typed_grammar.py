"""Version isolation and source-blind typed shapes; no scientific annotations."""
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from data_sheets_schema import audit_batch_format as output, audit_batches as batches
from data_sheets_schema import audit_grammar as grammar, audit_protocol as protocol


@pytest.fixture
def baseline():
    return json.loads((Path(__file__).parent / "fixtures/typed_audit_v1_baseline.json").read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


def test_v1_outputs_equal_pre_edit_captured_baseline(baseline):
    assert baseline["baseline_commit"] == "a8ada66534f9e05b58efce5685e79648aa723023"
    example = output.synthetic_examples()
    assert example == baseline["examples"]
    proposals = {example["plan"]["workers"][0]["id"]: batches.canonical_bytes(example["worker"])}
    assert batches.build_index(example["plan"], proposals) == baseline["index"]
    raw, lineage = batches.assemble(example["plan"], proposals, batches.canonical_bytes(example["integration"]))
    assert raw == baseline["assembled_utf8"].encode()
    assert lineage == baseline["lineage"]
    assert grammar.check(raw) == baseline["grammar_good"]
    assert grammar.check(b'{"findings":null}') == baseline["grammar_bad"]
    for stage in ("worker", "integration"):
        assert output.contract(stage) == baseline["contracts"][stage]
        assert output.render(stage) == baseline["rendered"][stage]


@pytest.mark.parametrize("kind", sorted(protocol.KINDS))
def test_each_closed_kind_requires_explicit_v2_and_preserves_bytes(baseline, kind):
    candidate = deepcopy(baseline["examples"]["worker"])
    candidate["findings"][0]["kind"] = kind
    raw = encoded(candidate)
    before = raw[:]
    assert not grammar.check(raw)["passed"]
    report = grammar.check(raw, version=2)
    assert report == {"instrument": "audit_grammar v2", "schema_version": 2,
        "passed": True, "error_count": 0, "errors": [], "truncated": False}
    assert raw == before
    assert Draft202012Validator(output.schema("worker", version=2)).is_valid(candidate)
    assert not Draft202012Validator(output.schema("worker")).is_valid(candidate)


@pytest.mark.parametrize("kind", [None, "", " ", "Other", "unknown", 1, True, [], {}, ["omission"]])
def test_malformed_kind_is_rejected_by_both_grammar_and_schema(baseline, kind):
    candidate = deepcopy(baseline["examples"]["worker"])
    candidate["findings"][0]["kind"] = kind
    assert not grammar.check(encoded(candidate), version=2)["passed"]
    assert not Draft202012Validator(output.schema("worker", version=2)).is_valid(candidate)


def test_untyped_is_not_coerced_and_shared_kind_list_matches_released_vocabulary(baseline):
    from data_sheets_schema.audit_recall import KINDS
    candidate = baseline["examples"]["worker"]
    assert grammar.check(encoded(candidate), version=2)["passed"]
    assert all("kind" not in finding for finding in candidate["findings"])
    assert protocol.KINDS == frozenset(KINDS)


@pytest.mark.parametrize("refs,kind,record,valid", [
    (["c1"], "omission", "full", True),
    (["c1", "c2"], "omission", "full", True),
    ([], "omission", "full", False),
    (["c1", "c1"], "omission", "full", False),
    ([""], "omission", "full", False),
    (["  "], "omission", "full", False),
    ([{}], "omission", "full", False),
    ("c1", "omission", "full", False),
    (None, "omission", "full", False),
    (["c1"], "attribution", "full", False),
    (["c1"], None, "full", False),
    (["c1"], "omission", "core", False),
    (["c1"], "omission", "both", False),
])
def test_omission_reference_shape_and_full_only_boundary(baseline, refs, kind, record, valid):
    candidate = deepcopy(baseline["examples"]["worker"])
    finding = candidate["findings"][0]
    finding.update(omission_candidates=refs, record=record)
    if kind is not None:
        finding["kind"] = kind
    assert grammar.check(encoded(candidate), version=2)["passed"] is valid
    assert Draft202012Validator(output.schema("worker", version=2)).is_valid(candidate) is valid


def test_reusable_finding_check_has_no_ambient_revised_row_requirement(baseline):
    finding = baseline["examples"]["worker"]["findings"][0]
    g = grammar._Grammar(version=2)
    g.finding(finding, "/finding")
    assert g.result()["passed"]
    candidate = deepcopy(baseline["examples"]["worker"])
    candidate["source_review"]["values"][0]["claims"][0]["verdict"] = "supported"
    assert not grammar.check(encoded(candidate), version=2)["passed"]


@pytest.mark.parametrize("damage", ["claim_extra", "finding_extra", "missing_evidence", "orphan_revise", "bad_removal"])
def test_typed_version_preserves_other_strict_rules(baseline, damage):
    candidate = deepcopy(baseline["examples"]["worker"])
    candidate["findings"][0]["kind"] = "status_scope"
    if damage == "claim_extra": candidate["source_review"]["values"][0]["claims"][0]["kind"] = "other"
    elif damage == "finding_extra": candidate["findings"][0]["candidate_id"] = "c1"
    elif damage == "missing_evidence": candidate["findings"][0]["evidence"] = []
    elif damage == "orphan_revise": candidate["findings"].pop(0)
    elif damage == "bad_removal": candidate["findings"][0]["remove_relationship"] = {"path": "not-pointer"}
    assert not grammar.check(encoded(candidate), version=2)["passed"]


@pytest.mark.parametrize("version", [True, False, None, "2", 2.0, [], {}, 0, 3])
def test_numeric_version_selection_is_strict(version):
    for call in (lambda: grammar.check(b"{}", version=version),
                 lambda: grammar._Grammar(version=version),
                 lambda: output.schema("worker", version=version),
                 lambda: output.contract("worker", version=version),
                 lambda: output.render("worker", version=version),
                 lambda: output.synthetic_examples(version=version)):
        with pytest.raises(ValueError, match="exactly 1 or 2"):
            call()


@pytest.mark.parametrize("name", [None, True, 1, [], {}, "", "typed_audit_protocol_v2"])
def test_protocol_names_are_explicit(name):
    with pytest.raises(ValueError, match="unknown audit protocol"):
        protocol.select(name)


def test_protocol_descriptor_is_fresh_and_does_not_invent_evidence_v8():
    expected = {"protocol": protocol.TYPED, "grammar_version": 2, "batch_version": 2,
        "output_format_version": 2, "evidence_protocol": 7, "omission_inventory_version": 1}
    assert protocol.select(protocol.TYPED) == expected
    changed = protocol.select(protocol.TYPED)
    changed["evidence_protocol"] = 99
    assert protocol.select(protocol.TYPED) == expected
    assert protocol.select(protocol.LEGACY)["omission_inventory_version"] is None


@pytest.mark.parametrize("stage", ["worker", "integration"])
def test_v2_format_schema_is_well_formed(stage):
    Draft202012Validator.check_schema(output.schema(stage, version=2))


@pytest.mark.parametrize("action,evidence,valid", [("retain", [], True), ("drop", [], False),
    ("drop", [{"source": "example.txt", "chunk": "c1", "quote": "Example"}], True),
    ("unknown", [], False)])
def test_v2_integration_disposition_documentation(baseline, action, evidence, valid):
    candidate = deepcopy(baseline["examples"]["integration"])
    candidate.update(kind="audit_integration_v2", omission_dispositions=[{
        "candidate_id": "c1", "action": action, "reason": "An invented disposition.", "evidence": evidence}])
    assert Draft202012Validator(output.schema("integration", version=2)).is_valid(candidate) is valid
    assert not Draft202012Validator(output.schema("integration")).is_valid(candidate)
