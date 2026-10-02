"""The released evidence contract gates exact outputs without revising history."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation.validate import classify, load_schema, validate_outputs
from data_sheets_schema.semantic_evidence import check_evidence, EvidenceValidationError
from data_sheets_schema.semantic_evidence_authority import authority_digest, load_authority
from data_sheets_schema.semantic_scope import validate_scope
from tests.test_evaluation.test_semantic_evidence import (
    CONTEXT, INPUT, ROOT, _accepted_by_scope, _groups, _item, _rating, _row,
    source,  # noqa: F401 -- the pinned 39-creator fixture
)


def current(rubric, source):
    result = _rating(rubric, source)
    result["version"] = "3.0"
    definition = ROOT / f".claude/agents/d4d-{rubric}-semantic.md"
    result["metadata"].update(
        instrument_sha256=hashlib.sha256(definition.read_bytes()).hexdigest(),
        evidence_authority_sha256=authority_digest())
    for _, items in _groups(result):
        for item in items:
            for row in item["unit_scores"]:
                row.update(cited=[], absent=[], counts=[], considered=[])
    return result


def accept(result, tmp_path):
    output = tmp_path / "rating.json"
    output.write_text(json.dumps(result))
    context = tmp_path / "context.yaml"
    context.write_text(yaml.safe_dump(CONTEXT))
    rubric = result["rubric"].removesuffix("-semantic")
    definition = ROOT / f".claude/agents/d4d-{rubric}-semantic.md"
    before = output.read_bytes(), INPUT.read_bytes(), definition.read_bytes(), context.read_bytes()
    status = validate_outputs([output], rubric=result["rubric"], input_path=INPUT,
                              definition_path=definition, context_path=context)
    assert before == (output.read_bytes(), INPUT.read_bytes(), definition.read_bytes(), context.read_bytes())
    return status


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_complete_new_contract_accepts_both_rubrics(source, tmp_path, rubric):
    assert accept(current(rubric, source), tmp_path) == 0


@pytest.mark.parametrize("path", [
    "was_generated_by", "version_acess.version_details", "/version_acess/version_details",
    "/version_access.version_details", "errata.misspeled", "/errata/misspeled", "/0",
])
def test_unknown_absence_names_fail_even_after_a_missing_parent(source, tmp_path, capsys, path):
    result = current("rubric20", source)
    _row(result, "Q19", absent=[{"path": path}])
    assert accept(result, tmp_path) == 1
    output = capsys.readouterr().out
    assert "unknown_absence_name" in output and "Q19" in output and path in output


@pytest.mark.parametrize("path", ["errata", "/errata", "/creators/100/name"])
def test_declared_true_absence_replaces_the_undeclared_provenance_example(source, tmp_path, path):
    result = current("rubric20", source)
    _row(result, "Q19", absent=[{"path": path}])
    assert accept(result, tmp_path) == 0


@pytest.mark.parametrize("evidence, code", [
    ({"counts": [{"path": "creators", "claimed": 38}]}, "count_mismatch"),
    ({"absent": [{"path": "version_access.version_details"}]}, "absent_path_populated"),
    ({"cited": [{"path": "errata"}]}, "cited_path_unresolved"),
    ({"cited": [{"path": "version_access", "quote": "this quote was never recorded"}]}, "quote_not_found"),
    ({"counts": [{"path": "creators", "claimed": True}]}, "Validation error"),
])
def test_exact_file_acceptance_checks_input_claims_not_just_shape(source, tmp_path, capsys, evidence, code):
    result = current("rubric20", source)
    _row(result, "Q1", **evidence)
    assert accept(result, tmp_path) == 1
    assert code in capsys.readouterr().out


def test_warnings_survive_acceptance_and_scores_are_not_rewritten(source, tmp_path, capsys):
    result = current("rubric20", source)
    _row(result, "Q13", score=3, cited=[{"path": "id"}])
    before = copy.deepcopy(result)
    assert accept(result, tmp_path) == 0
    output = capsys.readouterr().out
    assert "WARNING" in output and "uncovered_populated_field" in output
    assert "version_access" in output and "deduction_without_linked_issue" in output
    assert result == before


def test_scope_returns_warnings_and_retains_structured_errors(source):
    result = current("rubric20", source)
    _row(result, "Q13", score=3, cited=[{"path": "id"}])
    report = validate_scope(result, document=source[0], input_sha256=source[1], expected_context=CONTEXT)
    assert report.passed and report.warnings
    _row(result, "Q1", counts=[{"path": "creators", "claimed": 38}])
    with pytest.raises(EvidenceValidationError) as error:
        validate_scope(result, document=source[0], input_sha256=source[1], expected_context=CONTEXT)
    assert error.value.report.errors[0].code == "count_mismatch"
    assert error.value.report.warnings


def test_a_deduction_cannot_use_four_empty_evidence_lists(source, tmp_path, capsys):
    result = current("rubric20", source)
    _row(result, "Q13", score=3)
    assert accept(result, tmp_path) == 1
    assert "missing_structured_evidence" in capsys.readouterr().out


@pytest.mark.parametrize("mutation", ["missing_array", "wrong_array_type", "missing_authority", "forged_authority"])
def test_new_structure_and_authority_are_required(source, tmp_path, mutation):
    result = current("rubric20", source)
    row = _item(result, "Q1")["unit_scores"][0]
    if mutation == "missing_array":
        row.pop("counts")
    elif mutation == "wrong_array_type":
        row["counts"] = {}
    elif mutation == "missing_authority":
        result["metadata"].pop("evidence_authority_sha256")
    else:
        result["metadata"]["evidence_authority_sha256"] = "0" * 64
    assert accept(result, tmp_path) == 1


def issue(**updates):
    return {"type": "completeness", "category": "temporal_version", "severity": "high",
            "description": "Test issue", "recommendation": "Test recommendation",
            "fields_involved": ["version_access"], "item_ids": ["Q13"], "score_effect": "lowered",
            **updates}


@pytest.mark.parametrize("updates", [
    {"item_ids": ["Q999"]}, {"item_ids": ["Q15"]}, {"item_ids": ["Q1"]},
    {"item_ids": ["Q13", "Q13"]}, {"item_ids": []}, {"type": "invented"},
    {"category": "invented"}, {"score_effect": "noted_only"},
])
def test_new_taxonomy_and_links_are_checked(source, tmp_path, updates):
    result = current("rubric20", source)
    _row(result, "Q13", score=3, cited=[{"path": "version_access"}])
    result["semantic_analysis"]["issues_detected"] = [issue(**updates)]
    assert accept(result, tmp_path) == 1


def test_a_linked_issue_and_noted_only_issue_accept(source, tmp_path, capsys):
    result = current("rubric20", source)
    _row(result, "Q13", score=3, cited=[{"path": "version_access"}])
    result["semantic_analysis"]["issues_detected"] = [issue(), issue(item_ids=[], score_effect="noted_only")]
    assert accept(result, tmp_path) == 0
    assert "deduction_without_linked_issue" not in capsys.readouterr().out


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_historical_v2_has_no_retroactive_evidence_or_taxonomy_gate(source, rubric):
    result = _rating(rubric, source)
    result["metadata"]["instrument_sha256"] = "a" * 64
    key = "E1.1" if rubric == "rubric10" else "Q19"
    _row(result, key, absent=[{"path": "was_generated_by"}])
    result["semantic_analysis"]["issues_detected"] = [
        {"type": "historical_free_text", "severity": "low", "description": "Old issue",
         "recommendation": "Old recommendation", "fields_involved": []}]
    schema = load_schema(ROOT / f"src/download/prompts/{rubric}_semantic_schema.json")
    assert classify(result, schema) == ("valid", [])
    assert _accepted_by_scope(result, source)
    assert check_evidence(result, source[0], rubric).passed


def test_old_semantic_output_is_classifiable_but_not_a_new_measurement(source, tmp_path, capsys):
    assert accept(_rating("rubric20", source), tmp_path) == 1
    assert "requires instrument version 3.0" in capsys.readouterr().out


def test_authority_includes_declared_rubric_names_without_special_provenance_allowlist():
    names, digest = load_authority()
    assert {"errata", "version_access", "version_details", "release_notes", "rrid",
            "software_and_tools", "vulnerable_populations"} <= names
    assert not {"was_generated_by", "version_acess", "version_access.version_details"} & names
    assert digest == authority_digest()


def frozen_authority_sources():
    artifact = json.loads((ROOT / "data/rubric/semantic_evidence_authority_v3.json").read_text())
    snapshot = ROOT / "tests/fixtures/semantic_evidence_authority_v3"
    sources = {}
    for path, digest in artifact["sources"].items():
        raw = gzip.decompress((snapshot / (path + ".gz")).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == digest, path
        sources[path] = raw
    return sources


def test_authority_rebuild_matches_its_frozen_source_bytes():
    from build_semantic_evidence_authority import build_from_sources
    artifact = ROOT / "data/rubric/semantic_evidence_authority_v3.json"
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == (
        "0605c742c61f2cc4e13de907f8e09752bde5ebd08d173b31d837c273a4bf3872")
    assert json.dumps(build_from_sources(frozen_authority_sources()), indent=2) + "\n" == artifact.read_text()


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_current_source_evolution_does_not_rotate_released_authority(source, tmp_path, monkeypatch, rubric):
    from build_semantic_evidence_authority import CONTEXT as CONTEXT_PATH, SCHEMAS, build
    from data_sheets_schema import semantic_evidence_authority as authority
    old_rating = current(rubric, source)
    old_rating["metadata"]["evidence_authority_sha256"] = (
        "0605c742c61f2cc4e13de907f8e09752bde5ebd08d173b31d837c273a4bf3872")
    snapshot = frozen_authority_sources()
    for relative, raw in snapshot.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    released = (ROOT / authority.AUTHORITY_PATH).read_bytes()
    (tmp_path / authority.AUTHORITY_PATH).write_bytes(released)
    schema = tmp_path / SCHEMAS[0]
    schema.write_bytes(schema.read_bytes() + b"\n# Ordinary maintenance after v3 release.\n")
    proposed = build(tmp_path)
    assert proposed["names"] == json.loads(released)["names"]
    assert proposed["sources"] != json.loads(released)["sources"]
    assert json.dumps(proposed, indent=2).encode() + b"\n" != released

    # A new field/alias proposal reads the supplied context bytes, not the
    # ambient imported module. Merely existing today does not grant v3 names.
    context = tmp_path / CONTEXT_PATH
    context.write_text(context.read_text().replace(
        "FIELD_ALIASES = {", 'FIELD_ALIASES = {"future_declared_field": ("future_alias",),'))
    assert {"future_declared_field", "future_alias"} <= set(build(tmp_path)["names"])
    monkeypatch.setattr(authority, "resource_path", lambda path: tmp_path / path)
    assert check_evidence(old_rating, source[0], rubric).passed
    assert accept(old_rating, tmp_path) == 0
    assert authority.authority_digest() == old_rating["metadata"]["evidence_authority_sha256"]
    _row(old_rating, "E1.1" if rubric == "rubric10" else "Q1",
         absent=[{"path": "future_declared_field"}])
    assert "unknown_absence_name" in {e.code for e in check_evidence(old_rating, source[0], rubric).errors}
    assert (tmp_path / authority.AUTHORITY_PATH).read_bytes() == released


def test_authority_builder_reads_literal_alias_bytes_without_executing_them():
    from build_semantic_evidence_authority import CONTEXT as CONTEXT_PATH, build_from_sources
    sources = frozen_authority_sources()
    sources[CONTEXT_PATH] += b'\nraise RuntimeError("recorded source must not execute")\n'
    built = build_from_sources(sources)
    assert built["names"] == json.loads((ROOT / "data/rubric/semantic_evidence_authority_v3.json").read_text())["names"]
    sources[CONTEXT_PATH] = b"FIELD_ALIASES = dict(made_up=('new_name',))\n"
    with pytest.raises(ValueError):
        build_from_sources(sources)


@pytest.mark.parametrize("rubric", ["rubric10", "rubric20"])
def test_both_schemas_and_agent_instructions_share_the_checker_taxonomy(rubric):
    from data_sheets_schema.semantic_evidence import ISSUE_CATEGORIES, ISSUE_TYPES, SCORE_EFFECTS
    schema = load_schema(ROOT / f"src/download/prompts/{rubric}_semantic_schema.json")
    conditional = next(part["then"] for part in schema["allOf"]
                       if part["if"]["properties"]["version"].get("const") == "3.0")
    properties = conditional["properties"]["semantic_analysis"]["properties"]["issues_detected"]["items"]["properties"]
    definition = (ROOT / f".claude/agents/d4d-{rubric}-semantic.md").read_text()
    for field, names in (("category", ISSUE_CATEGORIES), ("type", ISSUE_TYPES), ("score_effect", SCORE_EFFECTS)):
        assert set(properties[field]["enum"]) == names
        assert all(name in definition for name in names)
