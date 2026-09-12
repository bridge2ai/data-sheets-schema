"""The semantic instrument must retain each source item's evidence scope (#158).

A field mentioned elsewhere in the definition cannot stand in for evidence
under the item being scored. Source leaf names are mapped explicitly to the
current schema; accepting any occurrence in the file hid four missing scopes.
"""

from functools import lru_cache
from pathlib import Path
import re

import pytest
import yaml

from data_sheets_schema.schema_view import shared_view

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / ".claude/agents/d4d-rubric10-semantic.md"
SOURCE = yaml.safe_load((ROOT / "data/rubric/rubric10.txt").read_text())[
    "d4d_complex_proxy_rubric"]["rubric"]

# These are concept-preserving schema mappings, not waivers for missing items.
# RRIDs use Dataset.id; release notes must describe the release in updates or
# notes, including the dedicated update_details slot. Software is attached to
# a processing property, never Dataset itself.
ALIASES = {
    "rrid": {"id"},
    "confidentiality_level": {"regulatory_restrictions.confidentiality_level"},
    "hipaa_compliant": {"regulatory_restrictions.hipaa_compliant"},
    "other_compliance": {"regulatory_restrictions.other_compliance"},
    "governance_committee_contact": {"data_governance.committee_contact"},
    "format": {"distribution_formats.format", "file_collections.resources.format"},
    "media_type": {"distribution_formats.media_type", "file_collections.resources.media_type"},
    "encoding": {"file_collections.resources.encoding"},
    "reidentification_risk": {"participant_privacy.reidentification_risk"},
    "vulnerable_populations": {"at_risk_populations"},
    "is_data_split": {"subsets.is_data_split"},
    "is_subpopulation": {"subsets.is_subpopulation"},
    "release_notes": {"updates.update_details", "updates.description", "notes"},
    "software_and_tools": {"preprocessing_strategies.used_software",
                           "cleaning_strategies.used_software",
                           "labeling_strategies.used_software",
                           "imputation_protocols.used_software"},
}


def items(text):
    """Parse only the scored specification, preserving IDs and field locality."""
    spec = text.split("## Rubric10 Specification\n", 1)[1].split("\n## Output Format", 1)[0]
    elements = re.split(r"^### Element (\d+): [^\n]+\n", spec, flags=re.M)
    result = {}
    assert [int(n) for n in elements[1::2]] == list(range(1, 11))
    for number, block in zip(elements[1::2], elements[2::2]):
        subs = re.split(r"^(\d+)\. \*\*([^\n]+)\*\*\n", block, flags=re.M)
        assert [int(n) for n in subs[1::3]] == list(range(1, 6))
        for sub, name, body in zip(subs[1::3], subs[2::3], subs[3::3]):
            fields = re.findall(r"^   - Fields: (.+)$", body, flags=re.M)
            assert len(fields) == 1, f"E{number}.{sub}: needs one Fields declaration"
            result[int(number), int(sub)] = {
                "name": name, "fields": set(re.findall(r"`([^`]+)`", fields[0])),
                "body": body,
            }
    return result


def missing_fields(source, declared):
    return {field for field in source
            if not (ALIASES.get(field, {field}) & declared)}


@lru_cache
def slots(class_name):
    view = shared_view(ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
    return {slot.name: slot for slot in view.class_induced_slots(class_name)}


def resolves(path):
    cls = "Dataset"
    for part in path.split("."):
        found = slots(cls).get(part)
        if found is None:
            return False
        cls = found.range
    return True


@pytest.mark.parametrize("element,sub,source", [
    (element["id"], index, source)
    for element in SOURCE
    for index, source in enumerate(element["sub_elements"], 1)
])
def test_each_item_preserves_its_source_name_and_evidence(element, sub, source):
    actual = items(AGENT.read_text())[element, sub]
    assert actual["name"] == source["name"]
    assert not missing_fields(source["field"], actual["fields"])
    assert actual["fields"]
    assert all(resolves(path) for path in actual["fields"]), actual["fields"]


@pytest.mark.parametrize("item,field,elsewhere", [
    ((2, 2), "data_governance.committee_contact", (4, 1)),
    ((5, 3), "subsets.is_data_split", (5, 2)),
    ((5, 3), "subsets.is_subpopulation", (5, 1)),
    ((8, 5), "imputation_protocols", (8, 3)),
    ((9, 5), "future_use_impacts", (9, 2)),
])
def test_evidence_in_a_different_item_does_not_cover_the_source(item, field, elsewhere):
    """Recreate the original defect even when a whole-file grep would pass."""
    parsed = items(AGENT.read_text())
    assert field in parsed[elsewhere]["fields"]
    source = SOURCE[item[0] - 1]["sub_elements"][item[1] - 1]
    incomplete = parsed[item]["fields"] - {field}
    assert missing_fields(source["field"], incomplete)


def test_examples_and_field_names_inside_prose_do_not_count_as_declared_evidence():
    text = AGENT.read_text().replace(
        "   - Fields: `ethical_reviews`, `future_use_impacts`",
        "   - Fields: `ethical_reviews`\n   - Unrelated example: `future_use_impacts`")
    parsed = items(text)
    assert "future_use_impacts" not in parsed[9, 5]["fields"]
    assert missing_fields(SOURCE[8]["sub_elements"][4]["field"], parsed[9, 5]["fields"])


def test_path_resolution_does_not_accept_bare_leaves_or_class_names():
    for path in ("rrid", "confidentiality_level", "DataSubset.is_data_split",
                 "used_software", "software_and_tools", "release_notes"):
        assert not resolves(path)


def test_cross_field_rules_use_reachable_paths():
    criteria = AGENT.read_text().split("## Evaluation Criteria", 1)[1].split(
        "## Rubric10 Specification", 1)[0]
    paths = {token.split("=", 1)[0] for token in re.findall(r"`([^`]+)`", criteria)
             if re.fullmatch(r"[a-z_]+(?:\.[a-z_]+)+(?:=True)?", token)}
    assert paths
    assert all(resolves(path) for path in paths), paths


def test_release_history_only_in_the_dedicated_update_field_is_located():
    """#1283: aliases must find real evidence, not merely resolve in a schema."""
    record = {"updates": {"update_details": "Version 2 adds 400 participants to the version 1 release."}}
    fields = items(AGENT.read_text())[6, 5]["fields"]
    found = []
    for path in fields:
        value = record
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if value is not None:
            found.append(value)
    assert found == [record["updates"]["update_details"]]


def test_funding_rule_accepts_prose_awards_and_non_grant_support():
    """#1284: test the prompt contract; this is not a model-scoring result."""
    rule = AGENT.read_text().split("**Funding Logic:**", 1)[1].split("**'Applies to' Logic:**", 1)[0]
    assert "IF `funders` describes grant funding" in rule
    assert "structured awards and prose awards are alternative representations" in rule
    for path in ("funders.grants", "funders.description", "funders.notes"):
        assert f"`{path}`" in rule and resolves(path)
    assert "Non-grant support" in rule
    assert "does not require a grant number" in rule
    assert "donated cloud services or device loans" in rule
    assert "IF `funders` present" not in rule


def test_rubric20_question_names_still_match_the_source():
    source = yaml.safe_load((ROOT / "data/rubric/rubric20.txt").read_text())[
        "d4d_evaluation_rubric"]["rubric"]
    agent = (ROOT / ".claude/agents/d4d-rubric20-semantic.md").read_text()
    actual = re.findall(r"^#### Question (\d+): (.+)$", agent, flags=re.M)
    assert actual == [(str(q["id"]), q["name"]) for q in source]
