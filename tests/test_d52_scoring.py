"""D52 approved deterministic scoring rules, 2026-10-28.

Inputs: actual frozen rubrics, explicit synthetic context/records. Outputs:
causal offline tests; no historical scores, rubric assets or contexts edited.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import evaluate_d4d as scoring

ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER_SHA256 = "1ee3debcbd234f300115ec67885bac707c167ded1ef5256470b1c057f9812d41"
MODERN = "data_governance.committee_contact"
LEGACY = "regulatory_restrictions.governance_committee_contact"
OMITTED = ["regulatory_restrictions." + field for field in (
    "confidentiality_level", "hipaa_compliant", "other_compliance", "governance_committee_contact")]
PERSON = {"name": "Synthetic committee", "email": "committee@example.invalid"}


def evaluator(context=None):
    return scoring.D4DEvaluator(ROOT / "data/rubric/rubric10.txt", ROOT / "data/rubric/rubric20.txt", context=context)


def q9(ev):
    return next(q for q in ev.rubric20["d4d_evaluation_rubric"]["rubric"] if q["id"] == 9)


def record(*contacts):
    data = {"id": "example:synthetic", "license_and_use_terms": {"description": "Synthetic terms"},
            "ip_restrictions": {"description": "Synthetic restrictions"},
            "regulatory_restrictions": {"confidentiality_level": "restricted",
                "hipaa_compliant": "hipaa_compliant", "other_compliance": ["Synthetic framework"]}}
    for contact in contacts:
        parent, key = contact.split(".")
        data.setdefault(parent, {})[key] = copy.deepcopy(PERSON)
    return data


@pytest.mark.parametrize("contacts", [(MODERN,), (LEGACY,), (MODERN, LEGACY)])
def test_q9_approved_contacts_are_one_criterion(contacts):
    ev = evaluator({"regulated_access": True})
    result = ev._score_rubric20_question(record(*contacts), q9(ev))
    assert result.score == 5
    assert "7/7 fields populated" in result.score_label
    assert result.max_score == result.fixed_max_score == 5


@pytest.mark.parametrize("source", [MODERN, LEGACY])
@pytest.mark.parametrize("criterion", [MODERN, LEGACY])
def test_alias_presence_extraction_and_raw_values_use_actual_source(criterion, source):
    ev = evaluator()
    parent, key = source.split(".")
    data = {parent: {key: copy.deepcopy(PERSON)}}
    present, evidence = ev._is_field_present(data, [criterion])
    assert present
    assert len(evidence) == 1
    assert evidence[0].startswith("/" + source.replace(".", "/") + ": ")
    assert ev._extract_field_value(data, criterion) == PERSON
    assert ev._raw_values(data, [criterion]) == [PERSON]


def test_alias_evidence_and_raw_values_deduplicate_exact_pointers():
    ev = evaluator()
    data = record(MODERN, LEGACY)
    present, evidence = ev._is_field_present(data, [MODERN, LEGACY, MODERN])
    assert present
    assert len(evidence) == len(set(evidence)) == 2
    assert ev._raw_values(data, [MODERN, LEGACY]) == [PERSON, PERSON]


@pytest.mark.parametrize("source", [MODERN, LEGACY])
@pytest.mark.parametrize("empty", [None, "", "  ", [], {}])
def test_empty_contacts_do_not_gain_credit(source, empty):
    ev = evaluator()
    parent, key = source.split(".")
    data = {parent: {key: empty}}
    assert not ev._is_field_present(data, [MODERN, LEGACY])[0]
    result = ev._score_rubric20_question(record(), q9(ev))
    assert result.score == 3 and "6/7 fields populated" in result.score_label


def test_bare_legacy_source_does_not_satisfy_nested_q9_criterion():
    ev = evaluator()
    data = record()
    data["governance_committee_contact"] = copy.deepcopy(PERSON)
    assert ev._is_field_present(data, ["governance_committee_contact"])[0]
    assert not ev._is_field_present(data, [MODERN, LEGACY])[0]
    assert ev._extract_field_value(data, LEGACY) is None
    assert ev._raw_values(data, [LEGACY]) == []
    assert "6/7 fields populated" in ev._score_rubric20_question(data, q9(ev)).score_label


@pytest.mark.parametrize("source", [MODERN, LEGACY])
def test_frozen_rubric10_legacy_criterion_accepts_approved_nested_contact(source):
    ev = evaluator({"regulated_access": True})
    parent, key = source.split(".")
    data = {parent: {key: copy.deepcopy(PERSON)}}
    # Frozen E2.2 spells this criterion without a parent; no asset rewrite.
    element = next(e for e in ev.rubric10["d4d_complex_proxy_rubric"]["rubric"] if e["id"] == 2)
    criterion = next(s for s in element["sub_elements"] if s.get("item_id") == "E2.2")
    assert "governance_committee_contact" in criterion["field"]
    assert ev._is_field_present(data, ["governance_committee_contact"])[0]
    result = ev._score_rubric10_element(data, element)
    scored = result.sub_element_scores[element["sub_elements"].index(criterion)]
    assert scored.score == 1
    assert any(source.replace(".", "/") in value for value in scored.found_values)


@pytest.mark.parametrize("reverse", [False, True])
def test_collection_members_use_their_own_contacts_and_evidence(tmp_path, reverse):
    members = [record(LEGACY), record(MODERN)]
    if reverse:
        members.reverse()
    path = tmp_path / "collection.yaml"
    path.write_text(yaml.safe_dump({"DatasetCollection": {"resources": members}}))
    ev = evaluator()
    result = ev.evaluate_d4d_file(path, "EXAMPLE", "manual")
    scored = next(q for q in result.rubric20_scores if q.question_id == 9)
    assert scored.score == 5 and [u["score"] for u in scored.unit_scores] == [5, 5]
    for index, member in enumerate(members):
        source = MODERN if "data_governance" in member else LEGACY
        assert any(value.startswith(f"#/resources/{index}/" + source.replace(".", "/") + ": ")
                   for value in scored.found_values)
    members[1] = record()
    path.write_text(yaml.safe_dump({"DatasetCollection": {"resources": members}}))
    reduced = ev.evaluate_d4d_file(path, "EXAMPLE", "manual")
    reduced_q9 = next(q for q in reduced.rubric20_scores if q.question_id == 9)
    assert reduced_q9.score == 3 and [u["score"] for u in reduced_q9.unit_scores] == [5, 3]
    assert not any(value.startswith("#/resources/1/") and "committee_contact:" in value
                   for value in reduced_q9.found_values)


def test_explicit_dataset_does_not_borrow_child_contact(tmp_path):
    data = record()
    data["resources"] = [record(MODERN)]
    path = tmp_path / "root.yaml"
    path.write_text(yaml.safe_dump({"Dataset": data}))
    result = evaluator().evaluate_d4d_file(path, "EXAMPLE", "manual")
    scored = next(q for q in result.rubric20_scores if q.question_id == 9)
    assert scored.score == 3 and len(scored.unit_scores) == 1
    assert not any("committee_contact:" in value for value in scored.found_values)


@pytest.mark.parametrize("context,denominator,score", [
    ({"regulated_access": False}, 3, 5),
    ({"regulated_access": {"value": False, "evidence": "D52 synthetic approved declaration"}}, 3, 5),
    ({"regulated_access": True}, 7, 3), ({"regulated_access": None}, 7, 3), ({}, 7, 3),
    ({"human_subjects": False}, 7, 3),
])
def test_only_explicit_false_excludes_exactly_four_q9_fields(context, denominator, score, tmp_path):
    ev = evaluator(context)
    question = q9(ev)
    before = copy.deepcopy(question)
    data = record()
    data["regulatory_restrictions"] = {"description": "No additional source evidence"}
    result = ev._score_rubric20_question(data, question)
    assert result.score == score and f"3/{denominator} fields populated" in result.score_label
    assert result.applicable and result.max_score == result.fixed_max_score == 5
    assert question == before
    assert len(question["field"]) == 7
    assert all(field in question["field"] for field in OMITTED)
    if denominator == 3:
        assert "regulated_access" in result.applicability_evidence and "false" in result.applicability_evidence
        assert all(field in result.applicability_evidence for field in OMITTED)
    else:
        assert not any(field in result.applicability_evidence for field in OMITTED)
    path = tmp_path / "record.yaml"
    path.write_text(yaml.safe_dump(data))
    full = ev.evaluate_d4d_file(path, "EXAMPLE", "manual")
    assert full.rubric20_fixed_max == 88
    assert "Q9" not in full.excluded_items["rubric20"]
    if "human_subjects" not in context:
        assert full.rubric20_max == 88


def test_scoring_change_has_distinct_source_and_instrument_identity():
    ev = evaluator()
    actual_sha = hashlib.sha256(Path(scoring.__file__).read_bytes()).hexdigest()
    assert ev.instrument["inputs"]["runner"] == actual_sha == scoring.SOURCE_SHA256
    previous = {**ev.instrument["inputs"], "runner": BASE_RUNNER_SHA256}
    previous_identity = hashlib.sha256(json.dumps(previous, sort_keys=True).encode()).hexdigest()
    assert actual_sha != BASE_RUNNER_SHA256
    assert ev.instrument["sha256"] != previous_identity
