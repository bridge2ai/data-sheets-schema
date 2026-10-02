"""Historical mailto rewrite attribution uses the run's Person slots (#4063)."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from data_sheets_schema import removals as rm, run_schema as rs

RID = "https://example.org/dataset"
MAIL = "mailto:jane@example.org"
PERSON = f"{RID}#person-jane"


def schema_bytes(persons=()):
    """A complete neutral schema with a nested object and enum rewrite."""
    return yaml.safe_dump({
        "id": "https://example.org/removals-schema", "name": "removals_schema",
        "default_range": "string",
        "prefixes": {"linkml": "https://w3id.org/linkml/", "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "types": {"string": {"uri": "xsd:string", "base": "str"},
                  "uriorcurie": {"uri": "xsd:anyURI", "base": "URIorCURIE"}},
        "enums": {"Relationship": {"permissible_values": {"bar": {"aliases": ["Foo"]}}}},
        "classes": {
            "Dataset": {"attributes": {"id": {"range": "uriorcurie", "identifier": True},
                                         "data_governance": {"range": "Governance"},
                                         "relationship_type": {"range": "Relationship"}}},
            "Governance": {"attributes": {
                slot: {"range": "Person" if slot in persons else "string",
                       "multivalued": slot == "committee_members"}
                for slot in ("committee_contact", "committee_members")}},
            "Person": {"attributes": {"id": {"range": "uriorcurie", "identifier": True}, "name": {}}},
        },
    }).encode()


def documents():
    person = {"id": MAIL, "name": "Jane"}
    original = {"id": RID, "data_governance": {"committee_contact": person,
                "committee_members": [copy.deepcopy(person)]}, "relationship_type": "Foo"}
    final = copy.deepcopy(original)
    final["data_governance"]["committee_contact"]["id"] = PERSON
    final["data_governance"]["committee_members"][0]["id"] = PERSON
    final["relationship_type"] = "bar"
    return original, final


def disk_run(tmp_path, raw):
    core = tmp_path / "claudecode_api_core" / "L"
    full = tmp_path / "claudecode_api" / "L" / "EXAMPLE_d4d.yaml"
    inter = core / "intermediate"
    inter.mkdir(parents=True)
    full.parent.mkdir(parents=True)
    original, final = documents()
    (inter / "EXAMPLE_full.yaml").write_text(yaml.safe_dump(original))
    (inter / "EXAMPLE_reconcile_full.yaml").write_text(yaml.safe_dump(final))
    (inter / "EXAMPLE_audit.json").write_text(json.dumps({"findings": []}))
    full.write_text(yaml.safe_dump(final))
    schema = tmp_path / "schema.yaml"
    schema.write_bytes(raw)
    record = {"run": {"project": "EXAMPLE", "label": "L"},
              "schema": {"full_path": str(schema), "full_sha256": hashlib.sha256(raw).hexdigest()}}
    provenance = core / "EXAMPLE_provenance.yaml"
    provenance.write_text(yaml.safe_dump(record))
    return provenance, record


def tree_bytes(root):
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("person_slots", [frozenset(), set(), frozenset({"committee_contact"}),
                                          frozenset({"committee_members"})])
def test_explicit_person_slots_flow_through_classifier_without_current_reads(person_slots):
    original, final = documents()
    with patch("data_sheets_schema.api_runner._person_slots", side_effect=AssertionError("current Person slots reread")):
        block = rm.classify(original, final, {"findings": []}, person_slots=person_slots, enum_aliases={})
        for slot, path in (("committee_contact", "data_governance.committee_contact.id"),
                           ("committee_members", "data_governance.committee_members[0].id")):
            expected = "mailto_id" if slot in person_slots else None
            assert rm.normaliser_form(path, MAIL, PERSON, frozenset({RID}), person_slots=person_slots) == expected
    assert block["rewritten_normaliser_by"]["mailto_id"] == len(person_slots)
    rows = {row["path"]: row.get("normaliser") for row in block["rewritten_paths"]}
    assert rows["data_governance.committee_contact.id"] == ("mailto_id" if "committee_contact" in person_slots else None)
    assert rows["data_governance.committee_members[0].id"] == ("mailto_id" if "committee_members" in person_slots else None)


def test_low_level_none_preserves_current_tables_and_other_normalisers():
    with patch("data_sheets_schema.api_runner._person_slots", return_value=frozenset({"committee_contact"})) as current:
        assert rm.normaliser_form("committee_contact.id", MAIL, PERSON, frozenset({RID})) == "mailto_id"
        assert rm.normaliser_form("committee_members[0].id", MAIL, PERSON, frozenset({RID}), person_slots=None) is None
    assert current.call_count == 2
    assert rm.normaliser_form("issued", "2024-05-01", "2024-05-01T00:00:00Z", person_slots=set()) == "temporal"
    assert rm.normaliser_form("relationship_type", "Foo", "bar", enum_aliases={"relationship_type": {"Foo": "bar"}},
                              person_slots=set()) == "enum_alias"
    # A Person ancestor is not enough: the mapping immediately owns the id.
    assert rm.normaliser_form("committee_contact.affiliation.id", MAIL, PERSON, frozenset({RID}),
                              person_slots={"committee_contact"}) is None


@pytest.mark.parametrize("historical,current", [
    ({"committee_contact"}, {"committee_members"}),
    ({"committee_members"}, {"committee_contact"}),
    (set(), {"committee_contact", "committee_members"}),
])
def test_disk_uses_opposite_pinned_person_rules_and_preserves_files(tmp_path, historical, current):
    provenance, record = disk_run(tmp_path, schema_bytes(historical))
    before = tree_bytes(tmp_path)
    with patch("data_sheets_schema.api_runner._person_slots", return_value=frozenset(current)) as current_read, \
            patch.object(rs, "todays_identifier_rules", side_effect=AssertionError("historical rules must not fall back")):
        block = rm.for_record(provenance)
    current_read.assert_not_called()
    assert tree_bytes(tmp_path) == before
    assert block["checked"]
    assert block["rewritten_normaliser_by"] == {"enum_alias": 1, "temporal": 0, "mailto_id": len(historical)}
    for key in ("person_slot_rules", "enum_alias_tables"):
        assert block["artifacts"][key]["source"] == "the run's schema, on disk"
        assert block["artifacts"][key]["sha256"] == record["schema"]["full_sha256"]
    rows = {row["path"]: row.get("normaliser") for row in block["rewritten_paths"]}
    assert rows["data_governance.committee_contact.id"] == ("mailto_id" if "committee_contact" in historical else None)
    assert rows["data_governance.committee_members[0].id"] == ("mailto_id" if "committee_members" in historical else None)


def test_unusable_recovered_person_schema_reports_independent_fallback(tmp_path):
    document = yaml.safe_load(schema_bytes())
    document["classes"]["Governance"]["is_a"] = "MissingAncestor"
    provenance, record = disk_run(tmp_path, yaml.safe_dump(document).encode())
    current = rs._derive_rules(schema_bytes({"committee_contact"}))
    with patch.object(rs, "todays_identifier_rules", return_value=current), \
            patch("data_sheets_schema.api_runner._person_slots", side_effect=AssertionError("selected fallback must stay explicit")):
        block = rm.for_record(provenance)
    person = block["artifacts"]["person_slot_rules"]
    assert person["source"] == rs.TODAY
    assert "could not be loaded as a schema" in person["reason"]
    assert person["sha256"] == record["schema"]["full_sha256"]
    assert block["artifacts"]["enum_alias_tables"]["source"] == "the run's schema, on disk"
    assert block["rewritten_normaliser_by"]["mailto_id"] == 1


def test_unrecoverable_person_schema_uses_stated_current_fallback(tmp_path):
    provenance, record = disk_run(tmp_path, schema_bytes())
    Path(record["schema"]["full_path"]).unlink()
    before = tree_bytes(tmp_path)
    current = rs._derive_rules(schema_bytes({"committee_members"}))
    with patch("data_sheets_schema.reconstructed_bytes.reconstructed_bytes_for", return_value=None), \
            patch("data_sheets_schema.provenance.committed_bytes_for", return_value=None), \
            patch.object(rs, "todays_identifier_rules", return_value=current):
        block = rm.for_record(provenance)
    assert tree_bytes(tmp_path) == before
    assert block["rewritten_normaliser_by"]["mailto_id"] == 1
    assert block["artifacts"]["person_slot_rules"]["source"] == rs.TODAY
    assert "no committed version" in block["artifacts"]["person_slot_rules"]["reason"]


def test_independent_selector_drift_is_not_reported_as_one_shared_capture(tmp_path):
    raw = schema_bytes({"committee_members"})
    provenance, record = disk_run(tmp_path, raw)
    enum_basis = {"source": "the run's schema, a git blob", "sha256": record["schema"]["full_sha256"]}
    person_basis = {"source": rs.TODAY, "reason": "historical authority became unavailable"}
    current = rs._derive_rules(schema_bytes({"committee_contact"}))
    with patch.object(rs, "run_schema_bytes", side_effect=[(raw, enum_basis), (None, person_basis)]) as selected, \
            patch.object(rs, "todays_identifier_rules", return_value=current), \
            patch("data_sheets_schema.api_runner._person_slots", side_effect=AssertionError("explicit rules must stay explicit")):
        block = rm.for_record(provenance)
    assert selected.call_count == 2
    assert block["artifacts"]["enum_alias_tables"] == enum_basis
    assert block["artifacts"]["person_slot_rules"] == person_basis
    assert block["rewritten_normaliser_by"]["mailto_id"] == 1
    rows = {row["path"]: row.get("normaliser") for row in block["rewritten_paths"]}
    assert rows["data_governance.committee_contact.id"] == "mailto_id"
    assert rows["data_governance.committee_members[0].id"] is None
