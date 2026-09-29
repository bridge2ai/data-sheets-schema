"""Evaluator evidence is checked against the record it scored (#2920).

The fixtures are version-2.0 ratings built over one committed input: the CM4AI
v7 rep2 record whose rubric20 rating counted 38 creators where the record has
39 (#1355). `validate_scope` accepts a rating carrying that count, and this
module reports it. The same rating lowered Q13 on a misreading of
`version_access.version_details`, a field it cited. That is beyond these
mechanical checks, as `test_a_misreading_of_a_field_the_row_cites_passes_these_checks`
shows. The Q13 deduction that warns
here is #2920's synthetic acceptance case, which never reads `version_access`.
It is not a reproduction of the #1355 rating. Every expectation below is a
fact about the bytes pinned by INPUT_SHA256, so a change to that record fails
here first rather than silently moving what these tests prove.
"""
import copy
import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation_context import context_digest, load_document
from data_sheets_schema.judge_contract import evaluation_contract
from data_sheets_schema.semantic_evidence import check_evidence
from data_sheets_schema.semantic_scope import validate_scope
from tests.test_evaluation.test_semantic_evaluation_contract import _rubric10_record, _rubric20_record

ROOT = Path(__file__).resolve().parents[2]
INPUT = (ROOT / "data/d4d_concatenated/claudecode_agent"
         / "2026-09-01_claude-opus-5-api-generic-v7_rep2/CM4AI_d4d.yaml")
INPUT_SHA256 = "af41bfae4fd0cea107b3468ad46e9a1a1599e297bfa5dd92739c48e6008f30b1"
# The record states involves_human_subjects: false. Declaring shared_dataset
# changes Q13's (and E3.2's) status from unknown to applicable; an undeclared
# predicate leaves an item applicable too, so this does not decide applicability.
CONTEXT = {"human_subjects": False, "shared_dataset": True}


@pytest.fixture(scope="module")
def source():
    document, digest = load_document(INPUT)
    assert digest == INPUT_SHA256, "the pinned CM4AI v7 rep2 input changed; re-derive these fixtures"
    return document, digest


def _groups(result):
    rubric10 = result["rubric"] == "rubric10-semantic"
    for group in result["elements" if rubric10 else "categories"]:
        yield group, group["sub_elements" if rubric10 else "questions"]


def _rescore(result):
    """Keep group and overall totals consistent with the item scores."""
    rubric10 = result["rubric"] == "rubric10-semantic"
    total = adjusted = fixed = excluded = 0
    for group, items in _groups(result):
        points = sum(item["score"] or 0 for item in items)
        tops = [1 if rubric10 else item["max_score"] for item in items]
        cap = sum(top for top, item in zip(tops, items) if item["applicable"])
        if rubric10:
            group.update(element_score=points, element_max=cap)
        else:
            group.update(category_score=points, category_max=sum(tops))
        total, adjusted, fixed = total + points, adjusted + cap, fixed + sum(tops)
        excluded += sum(not item["applicable"] for item in items)
    result["overall_score"].update(
        total_points=total, max_points=fixed, adjusted_max_points=adjusted,
        excluded_max_points=fixed - adjusted, normalized_percentage=round(100 * total / adjusted, 1),
        **{"sub_elements_not_applicable" if rubric10 else "questions_not_applicable": excluded})


def _rating(rubric, source):
    """A full-score version-2.0 rating of the pinned input, with no issues."""
    document, digest = source
    raw = (ROOT / f"data/rubric/{rubric}.txt").read_bytes()
    contract = evaluation_contract(rubric, yaml.safe_load(raw), CONTEXT, document)
    result = _rubric10_record() if rubric == "rubric10" else _rubric20_record()
    result.update(version="2.0", project="CM4AI", method="claudecode_agent",
                  d4d_file=str(INPUT.relative_to(ROOT)),
                  applicability_context=contract["context"], evaluation_scope=contract["scope"],
                  metadata={"context_sha256": context_digest(contract["context"]), "input_sha256": digest,
                            "rubric_sha256": hashlib.sha256(raw).hexdigest()})
    result["semantic_analysis"]["issues_detected"] = []
    for group, items in _groups(result):
        for index, item in enumerate(items, 1):
            key = f"E{group['id']}.{index}" if rubric == "rubric10" else f"Q{item['id']}"
            rule = contract["items"][key]
            score = rule["fixed_max_score"] if rule["applicable"] else None
            item.update(name=rule["name"], applicable=rule["applicable"], applicability_status=rule["status"],
                        applicability_evidence=rule["evidence"], score=score,
                        unit_scores=[{"path": "#", "score": score, "evidence": "Fixture evidence"}])
            if rubric == "rubric10":
                item["item_id"] = key
            else:
                item["max_score"] = rule["fixed_max_score"]
    _rescore(result)
    return result


def _item(result, key):
    for group, items in _groups(result):
        for index, item in enumerate(items, 1):
            if key in (item.get("item_id"), f"Q{item.get('id')}"):
                return item
    raise KeyError(key)


def _row(result, key, score=None, **evidence):
    """Set the item's single resource row; a score lowers the item with it."""
    item = _item(result, key)
    if score is not None:
        item["score"] = item["unit_scores"][0]["score"] = score
        _rescore(result)
    item["unit_scores"][0].update(evidence)
    return item


def _issue(result, item_ids, effect="lowered"):
    result["semantic_analysis"]["issues_detected"].append({
        "type": "completeness", "severity": "medium", "description": "Fixture issue",
        "fields_involved": [], "recommendation": "Fixture recommendation",
        "item_ids": item_ids, "score_effect": effect})


def _check(result, source):
    return check_evidence(result, source[0], result["rubric"])


def _codes(findings):
    return [(f.code, f.item_id, f.path) for f in findings]


def _accepted_by_scope(result, source):
    validate_scope(result, document=source[0], input_sha256=source[1], expected_context=CONTEXT)
    return True


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_a_full_score_rating_is_a_valid_v2_output_with_no_findings(source, rubric):
    result = _rating(rubric, source)
    assert _accepted_by_scope(result, source)
    assert _check(result, source).findings == ()


def test_the_38_creator_miscount_passes_scope_validation_and_is_an_error_here(source):
    result = _rating("rubric20", source)
    _row(result, "Q1", counts=[{"path": "/creators", "claimed": 38}])
    assert _accepted_by_scope(result, source)
    report = _check(result, source)
    assert not report.passed
    [finding] = report.errors
    assert (finding.code, finding.item_id, finding.path, finding.unit) == ("count_mismatch", "Q1", "/creators", "#")
    assert "the input has 39" in finding.message
    for path in ("/creators", "creators"):
        _row(result, "Q1", counts=[{"path": path, "claimed": 39}])
        assert _check(result, source).findings == ()


def test_a_count_needs_one_list(source):
    result = _rating("rubric20", source)
    _row(result, "Q1", counts=[{"path": "title", "claimed": 1}, {"path": "creators.affiliations", "claimed": 39},
                               {"path": "/contributors", "claimed": 0}, {"path": "/creators", "claimed": True}])
    assert _codes(_check(result, source).errors) == [
        ("count_path_not_list", "Q1", "title"), ("count_path_not_list", "Q1", "creators.affiliations"),
        ("count_path_unresolved", "Q1", "/contributors"), ("malformed_evidence", "Q1", "/creators")]


def test_an_absence_claim_is_checked_against_the_input(source):
    result = _rating("rubric20", source)
    _row(result, "Q19", absent=[{"path": "was_generated_by"}, {"path": "errata"},
                                {"path": "/missing_data_documentation"}])
    assert _check(result, source).findings == ()
    _row(result, "Q19", absent=[{"path": "version_access.version_details"},
                                {"path": "human_subject_research.involves_human_subjects"}])
    errors = _check(result, source).errors
    assert _codes(errors) == [
        ("absent_path_populated", "Q19", "version_access.version_details"),
        # A stated false is a value, not an absence.
        ("absent_path_populated", "Q19", "human_subject_research.involves_human_subjects")]
    assert "/version_access/version_details" in errors[0].message


def test_an_absence_claim_passes_on_a_null_or_empty_value(source):
    # The committed record has no null or empty value, so this half of the
    # rule is shown on a copy of it (#3075).
    document = copy.deepcopy(source[0])
    document["version_access"]["version_details"] = None
    document["errata"] = []
    document["updates"] = {}
    document["keywords"] = "  \n"
    document["maintainers"] = [{"maintainer_details": None, "role": ""}, {"maintainer_details": []}]
    paths = ("version_access.version_details", "/errata", "updates", "/keywords", "maintainers",
             "maintainers.maintainer_details", "/maintainers/0/role")
    result = _rating("rubric20", source)
    _row(result, "Q19", absent=[{"path": path} for path in paths])
    assert check_evidence(result, document, "rubric20").findings == ()
    # One populated value among them is an error that names where it is.
    document["maintainers"].append({"maintainer_details": "Fixture maintainer"})
    errors = check_evidence(result, document, "rubric20").errors
    assert _codes(errors) == [("absent_path_populated", "Q19", "maintainers"),
                              ("absent_path_populated", "Q19", "maintainers.maintainer_details")]
    assert "populates /maintainers/2/maintainer_details" in errors[1].message


def test_a_cited_path_must_resolve_to_a_populated_value(source):
    result = _rating("rubric20", source)
    _row(result, "Q13", cited=[{"path": "/creator"}, {"path": "version_access.change_log"},
                               {"path": "/creators/39"},
                               {"path": "/creators/0/name"}, {"path": "creators.affiliations.name"}])
    assert _codes(_check(result, source).errors) == [
        ("cited_path_unresolved", "Q13", "/creator"), ("cited_path_unresolved", "Q13", "version_access.change_log"),
        ("cited_path_unresolved", "Q13", "/creators/39")]
    # The committed record has no null or empty value, so emptiness is shown on a copy of it.
    document = copy.deepcopy(source[0])
    document["version_access"]["version_details"] = "  \n"
    document["errata"] = [{"description": None}]
    _row(result, "Q13", cited=[{"path": "version_access.version_details"}, {"path": "/errata"}])
    assert _codes(check_evidence(result, document, "rubric20").errors) == [
        ("cited_path_empty", "Q13", "version_access.version_details"), ("cited_path_empty", "Q13", "/errata")]


def test_a_quote_must_lie_inside_the_cited_value_up_to_whitespace(source):
    result = _rating("rubric20", source)
    _row(result, "Q13", cited=[
        {"path": "version_access.version_details",
         "quote": "Each quarterly release   is deposited\nas a distinct Dataverse dataset"},
        {"path": "/keywords", "quote": "affinity purification"},
        {"path": "/human_subject_research/involves_human_subjects", "quote": "false"}])
    assert _check(result, source).findings == ()
    _row(result, "Q13", cited=[
        {"path": "version_access.version_details", "quote": "Each monthly release is deposited"},
        {"path": "version_access.version_details", "quote": "each quarterly release is deposited"},
        {"path": "/keywords", "quote": "AI, affinity purification"},
        {"path": "/version", "quote": " "}])
    assert _codes(_check(result, source).errors) == [
        ("quote_not_found", "Q13", "version_access.version_details"),
        ("quote_not_found", "Q13", "version_access.version_details"),
        ("quote_not_found", "Q13", "/keywords"),
        ("malformed_evidence", "Q13", "/version")]
    # The value is normalised too. Every string in the committed record is
    # single-spaced, so a value written across lines, as a literal block
    # scalar is, is shown on a copy of it (#3074).
    document = copy.deepcopy(source[0])
    document["version_access"].update(yaml.safe_load(
        "version_details: |\n  Each quarterly release\n  is deposited   as a distinct\n  Dataverse dataset\n"))
    value = document["version_access"]["version_details"]
    assert "\n" in value and "   " in value
    _row(result, "Q13", cited=[
        {"path": "version_access.version_details", "quote": "release is deposited as a distinct Dataverse dataset"}])
    assert check_evidence(result, document, "rubric20").findings == ()
    _row(result, "Q13", cited=[
        {"path": "version_access.version_details", "quote": "release is deposited as a distinct Dataverse record"}])
    assert _codes(check_evidence(result, document, "rubric20").errors) == [
        ("quote_not_found", "Q13", "version_access.version_details")]


def test_a_quote_yaml_cannot_read_is_not_found_rather_than_raised(source):
    # PyYAML's constructors raise ValueError, AttributeError, KeyError or
    # RecursionError, none of them a YAMLError, for text that matches a
    # pattern but builds no value. Each is a false quote of a non-string
    # scalar, not a malformed input (#3072).
    assert source[0]["total_file_count"] == 10
    assert source[0]["human_subject_research"]["involves_human_subjects"] is False
    result = _rating("rubric20", source)
    unreadable = ("2026-02-30", "2025-09-31", "2026-13-01", "2026-01-01T25:00:00Z", "!!int abc",
                  "!!float abc", "!!timestamp x", "!!bool maybe", "[" * 1200 + "]" * 1200)
    for path in ("/total_file_count", "/human_subject_research/involves_human_subjects"):
        for quote in unreadable:
            _row(result, "Q13", cited=[{"path": path, "quote": quote}])
            assert _codes(_check(result, source).errors) == [("quote_not_found", "Q13", path)], (path, quote[:30])
    # The same dates against a datetime are not found either.
    document = copy.deepcopy(source[0])
    document.update(yaml.safe_load("issued: 2026-05-01T00:00:00Z\n"))
    for quote in unreadable[:4]:
        _row(result, "Q13", cited=[{"path": "issued", "quote": quote}])
        assert _codes(check_evidence(result, document, "rubric20").errors) == [
            ("quote_not_found", "Q13", "issued")], quote


def test_a_quote_of_a_whole_non_string_value_matches_as_yaml_reads_it(source):
    # The input is parsed, so an unquoted timestamp, a YAML 1.1 boolean or a
    # float no longer holds the text the record wrote (#3022).
    document = copy.deepcopy(source[0])
    document.update(yaml.safe_load("issued: 2026-05-01T00:00:00Z\nfixture_date: 2026-05-01\n"
                                   "fixture_flag: no\nfixture_ratio: 1.10\nfixture_count: 1\n"))
    result = _rating("rubric20", source)
    for path, quote in [
            ("issued", "2026-05-01T00:00:00Z"), ("issued", "2026-05-01T00:00:00+00:00"),
            ("issued", "2026-05-01 00:00:00+00:00"), ("issued", "2026-05-01T00:00:00"), ("issued", "2026-05-01"),
            ("fixture_date", "2026-05-01"), ("fixture_flag", "no"), ("fixture_flag", "False"),
            ("fixture_flag", "false"), ("fixture_ratio", "1.10"), ("fixture_ratio", "1.1"),
            ("fixture_count", "1")]:
        _row(result, "Q13", cited=[{"path": path, "quote": quote}])
        assert check_evidence(result, document, "rubric20").findings == (), (path, quote)
    for path, quote in [
            ("issued", "2026-04-30T19:00:00-05:00"),  # the same instant, not the offset written
            ("issued", "2026-05-02T00:00:00Z"), ("fixture_date", "2026-05-01T00:00:00Z"),
            ("fixture_flag", "yes"), ("fixture_flag", "0"), ("fixture_ratio", "1.11"), ("fixture_count", "true")]:
        _row(result, "Q13", cited=[{"path": path, "quote": quote}])
        assert _codes(check_evidence(result, document, "rubric20").errors) == [
            ("quote_not_found", "Q13", path)], (path, quote)


# Each spells a value the input populates. Read as a path that reaches
# nothing, each would pass as a true absence (#3017).
OFF_GRAMMAR = ("#/version_access/version_details", "version_access/version_details", "creators[0].name",
               "creators.0.name", "Version_Access.version_details", " version_access.version_details",
               "version_access.version_details ", "version_access..version_details",
               "/version_access/version_details/", "/version_access/ version_details",
               "/version_access/version~2details")


def test_an_absence_claim_on_a_path_outside_the_grammar_is_an_error(source):
    result = _rating("rubric20", source)
    _row(result, "Q19", absent=[{"path": path} for path in OFF_GRAMMAR])
    findings = _check(result, source).findings
    assert _codes(findings) == [("malformed_path", "Q19", path) for path in OFF_GRAMMAR]
    assert {finding.severity for finding in findings} == {"error"}
    messages = dict(zip(OFF_GRAMMAR, (finding.message for finding in findings)))
    assert "begins with #" in messages["#/version_access/version_details"]
    for path in (" version_access.version_details", "version_access.version_details "):
        assert "leading or trailing whitespace" in messages[path]
    # A dotted segment is a key name, never a list index (#3021).
    for path in ("creators[0].name", "creators.0.name"):
        assert "an index is written only in pointer form" in messages[path]
    # The same values, spelled in the grammar, are populated.
    _row(result, "Q19", absent=[{"path": "version_access.version_details"}, {"path": "/creators/0/name"}])
    assert _codes(_check(result, source).errors) == [
        ("absent_path_populated", "Q19", "version_access.version_details"),
        ("absent_path_populated", "Q19", "/creators/0/name")]


@pytest.mark.parametrize("name", ["cited", "counts", "considered"])
def test_a_path_outside_the_grammar_is_an_error_in_every_other_list(source, name):
    result = _rating("rubric20", source)
    entries = {"cited": [{"path": path} for path in OFF_GRAMMAR],
               "counts": [{"path": path, "claimed": 1} for path in OFF_GRAMMAR],
               "considered": list(OFF_GRAMMAR)}[name]
    _row(result, "Q19", **{name: entries})
    assert _codes(_check(result, source).findings) == [("malformed_path", "Q19", path) for path in OFF_GRAMMAR]


def test_a_key_that_is_not_a_snake_case_name_is_written_in_pointer_form(source):
    # A few model-written records carry keys such as DOI or "Point of Contact".
    document = copy.deepcopy(source[0])
    document.update({"DOI": "Fixture identifier", "Point of Contact": "Fixture contact"})
    result = _rating("rubric20", source)
    _row(result, "Q13", cited=[{"path": "/DOI", "quote": "Fixture"}, {"path": "/Point of Contact"},
                               {"path": "DOI"}])
    assert _codes(check_evidence(result, document, "rubric20").errors) == [("malformed_path", "Q13", "DOI")]


def test_a_q13_deduction_that_never_reads_version_access_warns(source):
    result = _rating("rubric20", source)
    _issue(result, ["Q13"])
    _row(result, "Q13", score=3, cited=[{"path": path} for path in
                                        ("version", "updates", "maintainers", "doi", "publisher")])
    assert _accepted_by_scope(result, source)
    report = _check(result, source)
    assert report.passed and report.errors == ()
    assert _codes(report.warnings) == [("uncovered_populated_field", "Q13", "version_access")]
    # A field inside it, or naming it as considered, accounts for it.
    for evidence in ({"cited": [{"path": "/version_access/version_details"}]},
                     {"considered": ["version_access"]}):
        row = _item(result, "Q13")["unit_scores"][0]
        row.update(cited=[{"path": path} for path in ("version", "updates", "maintainers", "doi", "publisher")],
                   considered=[])
        row["cited"] += evidence.get("cited", [])
        row["considered"] = evidence.get("considered", [])
        assert _check(result, source).findings == ()


@pytest.mark.parametrize("name", ["cited", "considered"])
def test_a_malformed_path_accounts_for_no_field_even_where_it_resolves(source, name):
    # A key that is not snake_case lets a malformed dotted path resolve: the
    # committed gpt5 CM4AI record holds "Point of Contact" keys inside
    # maintainers. The path is an error, and it accounts for nothing (#3073).
    document = copy.deepcopy(source[0])
    document["version_access"]["Change Log"] = "Fixture change log"
    result = _rating("rubric20", source)
    _issue(result, ["Q13"])
    five = [{"path": path} for path in ("version", "updates", "maintainers", "doi", "publisher")]
    for path, codes in [
            ("version_access.Change Log", [("malformed_path", "Q13", "version_access.Change Log")]),
            ("/version_access/Change Log", [])]:
        _row(result, "Q13", score=3, cited=five + ([{"path": path}] if name == "cited" else []),
             considered=[path] if name == "considered" else [])
        report = check_evidence(result, document, "rubric20")
        assert _codes(report.errors) == codes, path
        # Both spellings reach /version_access/Change Log; only the
        # well-formed pointer accounts for version_access.
        assert _codes(report.warnings) == (
            [("uncovered_populated_field", "Q13", "version_access")] if codes else []), path


def test_a_misreading_of_a_field_the_row_cites_passes_these_checks(source):
    """#1355's Q13 deduction named the three `version_access` fields cited
    here and misread `version_details`. It scored 4 of 5 under version 1.0,
    whose domain version 2.0 narrows to 0, 3 and 5. Coverage asks whether a
    field was named, not whether it was read correctly, so a deduction of that
    shape raises nothing."""
    result = _rating("rubric20", source)
    _issue(result, ["Q13"])
    _row(result, "Q13", score=3, cited=[{"path": path} for path in (
        "version", "updates", "maintainers", "doi", "publisher", "version_access.versions_available",
        "version_access.version_details", "version_access.latest_version_doi")])
    assert _accepted_by_scope(result, source)
    assert _check(result, source).findings == ()


def test_a_full_score_row_needs_no_field_coverage(source):
    result = _rating("rubric20", source)
    _row(result, "Q13", cited=[{"path": "version"}])
    assert _check(result, source).findings == ()


def test_declared_names_that_are_not_root_slots_follow_the_presence_rule(source):
    result = _rating("rubric10", source)
    _issue(result, ["E2.2", "E2.4"])
    _row(result, "E2.2", score=0)
    _row(result, "E2.4", score=0)
    assert _accepted_by_scope(result, source)
    # Bare confidentiality_level, hipaa_compliant, other_compliance and
    # governance_committee_contact do not resolve from the root and never warn;
    # format and media_type are populated through distribution_formats.
    assert _codes(_check(result, source).warnings) == [
        ("uncovered_populated_field", "E2.2", "regulatory_restrictions"),
        ("uncovered_populated_field", "E2.4", "distribution_formats"),
        ("uncovered_populated_field", "E2.4", "format"),
        ("uncovered_populated_field", "E2.4", "media_type")]
    _row(result, "E2.2", cited=[{"path": "regulatory_restrictions.governance_committee_contact"}])
    _row(result, "E2.4", cited=[{"path": "/distribution_formats/0"}])
    assert _check(result, source).findings == ()


def test_a_container_an_alias_passes_through_accounts_only_for_values_it_holds(source):
    # format's aliases include file_collections.resources.format, but this
    # input populates format only at /distribution_formats/{0,1}/format and no
    # file collection holds one (#3018).
    result = _rating("rubric10", source)
    _issue(result, ["E3.2"])
    _row(result, "E3.2", score=0)
    assert _accepted_by_scope(result, source)
    uncovered = [("uncovered_populated_field", "E3.2", "format")]
    assert _codes(_check(result, source).warnings) == uncovered
    _row(result, "E3.2", cited=[{"path": "/file_collections/0"}])
    assert _check(result, source).errors == () and _codes(_check(result, source).warnings) == uncovered
    for path in ("file_collections", "/file_collections/0", "file_collections.resources.format",
                 "/file_collections/0/compression", "distribution_formats.media_type"):
        _row(result, "E3.2", cited=[], considered=[path])
        assert _codes(_check(result, source).warnings) == uncovered, path
    # A location that holds a format, a container of one, or the declared name itself.
    for path in ("format", "distribution_formats", "distribution_formats.format", "/distribution_formats/1",
                 "/distribution_formats/0/format"):
        _row(result, "E3.2", cited=[], considered=[path])
        assert _check(result, source).findings == (), path


def test_an_issue_must_name_rubric_items_that_apply(source):
    result = _rating("rubric20", source)
    _issue(result, ["Q21", "E1.1", "Q8"], effect="noted_only")
    assert _codes(_check(result, source).errors) == [
        ("unknown_item_id", "Q21", None), ("unknown_item_id", "E1.1", None), ("non_applicable_item_id", "Q8", None)]
    result = _rating("rubric10", source)
    _issue(result, ["E11.1", "E4.3", "Q1"], effect="noted_only")
    errors = _check(result, source).errors
    assert _codes(errors) == [
        ("unknown_item_id", "E11.1", None), ("non_applicable_item_id", "E4.3", None), ("unknown_item_id", "Q1", None)]
    assert {finding.issue for finding in errors} == {0}


def test_a_lowered_issue_must_name_an_item_below_its_maximum(source):
    result = _rating("rubric20", source)
    _issue(result, ["Q3", "Q16"])
    _issue(result, [])
    _issue(result, ["Q3"], effect="noted_only")
    _issue(result, ["Q3"], effect="lowered_slightly")
    report = _check(result, source)
    assert [(f.code, f.item_id, f.issue) for f in report.errors] == [
        ("lowered_issue_without_deduction", "Q3", 0), ("lowered_issue_without_deduction", None, 1),
        ("malformed_issue", None, 3)]
    assert "none of Q3, Q16 is scored below its maximum" in report.errors[0].message
    _row(result, "Q16", score=0, cited=[{"path": path} for path in ("page", "doi", "id")])
    assert [(f.code, f.issue) for f in _check(result, source).errors] == [
        ("lowered_issue_without_deduction", 1), ("malformed_issue", 3)]


def test_a_deduction_with_no_linked_issue_or_reason_warns(source):
    result = _rating("rubric20", source)
    _row(result, "Q20", score=3, cited=[{"path": "known_biases"}, {"path": "future_use_impacts"}])
    _issue(result, ["Q20"], effect="noted_only")
    report = _check(result, source)
    assert report.passed
    assert _codes(report.warnings) == [("deduction_without_linked_issue", "Q20", None)]
    _item(result, "Q20")["no_issue_reason"] = "The deduction is for depth; no semantic issue applies"
    assert _check(result, source).findings == ()
    del _item(result, "Q20")["no_issue_reason"]
    _issue(result, ["Q20"])
    assert _check(result, source).findings == ()


def test_malformed_rows_and_unknown_resources_are_findings_not_exceptions(source):
    result = _rating("rubric20", source)
    _row(result, "Q2", cited="description", absent=[{"path": ""}], counts=[{"claimed": 3}], considered=[None])
    _item(result, "Q3")["unit_scores"].append({"path": "#/resources/0", "score": 5, "evidence": "Fixture"})
    assert _codes(_check(result, source).errors) == [
        ("malformed_evidence", "Q2", None), ("malformed_evidence", "Q2", None),
        ("malformed_evidence", "Q2", None), ("malformed_evidence", "Q2", None),
        ("unknown_unit", "Q3", None)]


def test_malformed_issues_and_item_ids_are_findings_not_exceptions(source):
    result = _rating("rubric20", source)
    result["semantic_analysis"]["issues_detected"] = [
        {"item_ids": ["Q1"], "score_effect": ["lowered"]}, {"item_ids": ["Q1"], "score_effect": {}},
        {"item_ids": "Q1"}, {"item_ids": [13]}, "an issue"]
    assert [(f.code, f.issue) for f in _check(result, source).findings] == [
        ("malformed_issue", index) for index in range(5)]
    result["semantic_analysis"]["issues_detected"] = "none"
    assert [(f.code, f.issue) for f in _check(result, source).findings] == [("malformed_issue", None)]
    # An item id that is not a string names no item, and its evidence is still checked.
    result = _rating("rubric10", source)
    _row(result, "E7.5", counts=[{"path": "/creators", "claimed": 38}])["item_id"] = ["E7.5"]
    assert _codes(_check(result, source).errors) == [("count_mismatch", None, "/creators")]


def test_the_checker_never_changes_a_rating_or_its_input(source):
    result = _rating("rubric20", source)
    _issue(result, ["Q1", "Q21"])
    _row(result, "Q1", score=3, counts=[{"path": "/creators", "claimed": 38}],
         cited=[{"path": "creators", "quote": "Trey Ideker"}], absent=[{"path": "version_access"}],
         considered=["keywords"])
    _row(result, "Q13", score=3)
    before, document = copy.deepcopy(result), copy.deepcopy(source[0])
    report = _check(result, source)
    assert report.errors and report.warnings
    assert result == before
    assert source[0] == document


def test_the_rubric_is_the_one_the_rating_declares(source):
    result = _rating("rubric20", source)
    with pytest.raises(ValueError, match="declares rubric20"):
        check_evidence(result, source[0], "rubric10")
    with pytest.raises(ValueError, match="unknown"):
        check_evidence(result, source[0], "rubric30")
    assert check_evidence(result, source[0], "rubric20").findings == ()
