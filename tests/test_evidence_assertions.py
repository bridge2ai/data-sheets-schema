"""Generic source, relationship and original-artifact controls."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import chunking
from data_sheets_schema.evidence_assertions import (
    check_assertions, check_audit, check_files, check_relationship_removals,
    main, report_assertions,
)


def artifact(name="original_full", path="/privacy/details", op="contains", quote="in process"):
    return {"artifact": name, "path": path, "op": op, "quote": quote}


def test_quote_in_another_document_does_not_support_attribution():
    chunks = {
        "c001": {"source": "protocol.txt", "text": "We will sequester a holdout for validation."},
        "c002": {"source": "overview.txt", "text": "The repository contains analysis tools."},
    }
    wrong = {"source": "overview.txt", "chunk": "c002", "quote": "sequester a holdout"}
    assert check_assertions([wrong], artifacts={}, chunks=chunks)[0]["kind"] == "source_quote_not_found"
    assert check_assertions([{**wrong, "chunk": "c001"}], artifacts={}, chunks=chunks)[0]["kind"] == "evidence_contract"
    assert check_assertions([{**wrong, "chunk": "c001", "source": "protocol.txt"}],
                            artifacts={}, chunks=chunks) == []


def test_qualifier_already_present_cannot_be_reported_lost():
    texts = {"original_full": "privacy:\n  details: >-\n    De-identification is in\n    process. The project will transform data.\n"}
    assert check_assertions([artifact()], artifacts=texts, chunks={}) == []
    findings = check_assertions([artifact(op="lacks"), artifact(op="lacks", quote="will")],
                                artifacts=texts, chunks={})
    assert [f["kind"] for f in findings] == ["artifact_assertion_contradicted"] * 2
    assert check_assertions([artifact(op="lacks", quote="completed")], artifacts=texts, chunks={}) == []


def test_final_header_does_not_establish_original_header():
    marker = "# Phase 4 reconciliation: completed"
    texts = {"original_core": "# Phase: derived\nid: x\nnotes: " + json.dumps(marker) + "\n",
             "final_core": marker + "\nid: x\n"}
    claims = [artifact("original_core", "@header", quote=marker)]
    assert check_assertions(claims, artifacts=texts, chunks={})[0]["kind"] == "artifact_assertion_contradicted"
    claims += [artifact("final_core", "@header", quote=marker)]
    assert len(check_assertions(claims, artifacts=texts, chunks={})) == 1
    assert check_assertions([artifact("original_core", "@header", "lacks", marker)],
                            artifacts=texts, chunks={}) == []


@pytest.mark.parametrize("path", ["/absent", "/privacy/9", "/privacy/~2bad"])
def test_unusable_locations_do_not_count_as_verified_absence(path):
    assert check_assertions([artifact(path=path, op="lacks")],
        artifacts={"original_full": "privacy: {}\n"}, chunks={})[0]["kind"] == "evidence_contract"


def test_missing_original_cannot_be_substituted_by_final():
    assert check_assertions([artifact()], artifacts={"final_full": "privacy: {}"}, chunks={})[0]["kind"] == "evidence_contract"


def test_scalar_assertions_check_the_whole_value():
    texts = {"original_full": "count: 12\npresent: true\nunknown: null\n"}
    for path, quote in (("/count", "12"), ("/present", "true"), ("/unknown", "null")):
        assert check_assertions([artifact(path=path, quote=quote)], artifacts=texts, chunks={}) == []
    assert check_assertions([artifact(path="/count", quote="2")], artifacts=texts, chunks={})


def test_each_grouped_audit_assertion_is_checked_independently():
    audit = {"findings": [{"evidence": [artifact(), artifact(op="lacks")]}]}
    result = check_audit(audit, artifacts={"original_full": "privacy: {details: 'in process'}"}, chunks={})
    assert result["assertions_checked"] == 2
    assert len(result["findings"]) == 1
    assert result["findings"][0]["assertion"] == 1
    assert check_audit({"findings": [{"issue": "unsupported"}]}, artifacts={}, chunks={})["findings"]


def test_rejected_role_cannot_survive_by_disclaimer_or_reordering():
    original = {"creators": [{"name": "Established Creator"}, {"name": "Team Member"}]}
    audit = {"findings": [{"remove_relationship": {"path": "/creators/1", "identity": "/name"}}]}
    final = {"creators": [{"name": "Team Member", "notes": "Creation role is not stated"},
                          {"name": "Established Creator"}]}
    assert check_relationship_removals(audit, original, final)[0]["kind"] == "unsupported_relationship_retained"
    repaired = {"creators": [{"name": "Established Creator"}],
                "description": "Team Member belongs to the leadership team."}
    assert check_relationship_removals(audit, original, repaired) == []
    assert check_relationship_removals({"findings": []}, original, original) == []


def test_nonlist_role_must_be_removed_not_qualified():
    original = {"governance": {"contact": {"name": "Project Contact"}}}
    audit = {"findings": [{"remove_relationship": {"path": "/governance/contact"}}]}
    final = copy.deepcopy(original)
    final["governance"]["contact"]["notes"] = "No governance responsibility is stated."
    assert check_relationship_removals(audit, original, final)
    assert check_relationship_removals(audit, original, {"governance": {}}) == []


@pytest.mark.parametrize("member", [
    {"id": "rejected"}, {"id": "rejected", "name": "Renamed"},
    {"id": "rejected", "name": "Established Creator"}, {"notes": "identity deleted"},
    {"id": "invented", "name": "New identity"},
])
def test_losing_or_changing_identity_cannot_prove_removal(member):
    original = {"creators": [{"id": "rejected", "name": "Team Member"},
                             {"name": "Established Creator"}]}
    audit = {"findings": [{"remove_relationship": {"path": "/creators/0", "identity": "/name"}}]}
    final = {"creators": [member]}
    assert check_relationship_removals(audit, original, final)[0]["kind"] == "evidence_contract"
    assert check_relationship_removals(audit, original,
        {"creators": [{"name": "Established Creator"}]}) == []


def test_nested_relationship_follows_every_indexed_ancestor():
    original = {"groups": [{"id": "g1", "creators": [{"id": "supported"}]},
                           {"id": "g2", "creators": [{"id": "other"},
                               {"id": "rejected", "principal_investigator": {"name": "Member"}}]}]}
    audit = {"findings": [{"remove_relationship": {
        "path": "/groups/1/creators/1/principal_investigator"}}]}
    final = copy.deepcopy(original)
    final["groups"].reverse()
    final["groups"][0]["creators"].reverse()
    assert check_relationship_removals(audit, original, final)[0]["kind"] == "unsupported_relationship_retained"
    final["groups"][0]["creators"][0].pop("principal_investigator")
    assert check_relationship_removals(audit, original, final) == []
    final["groups"][0].pop("id")
    assert check_relationship_removals(audit, original, final)[0]["kind"] == "evidence_contract"


@pytest.mark.parametrize("key", ["name", "id"])
@pytest.mark.parametrize("survivor", [
    {"id": "https://example.org/rejected", "name": "Supported"},
    {"id": "https://example.org/supported", "name": "Rejected"},
    {"name": "Supported"}, {"id": "https://example.org/supported"},
])
def test_nested_person_identity_cannot_ignore_a_sibling_identifier(key, survivor):
    rejected = {"id": "https://example.org/rejected", "name": "Rejected"}
    supported = {"id": "https://example.org/supported", "name": "Supported"}
    original = {"creators": [{"principal_investigator": rejected}, {"principal_investigator": supported}]}
    audit = {"findings": [{"remove_relationship": {
        "path": "/creators/0", "identity": "/principal_investigator/" + key}}]}
    final = {"creators": [{"principal_investigator": survivor}]}
    assert check_relationship_removals(audit, original, final)[0]["kind"] == "evidence_contract"
    assert check_relationship_removals(audit, original,
        {"creators": [{"principal_investigator": supported}]}) == []
    assert check_relationship_removals(audit, original,
        {"creators": [{"principal_investigator": rejected}]})[0]["kind"] == "unsupported_relationship_retained"


@pytest.mark.parametrize("key", ["id", "name"])
@pytest.mark.parametrize("level", ["wrapper", "owner", "owner_new", "middle"])
def test_added_identity_fields_cannot_relocate_a_rejected_person(key, level):
    rejected = {"id": "https://example.org/rejected", "name": "Rejected"}
    supported = {"id": "https://example.org/supported", "name": "Supported"}
    if level.startswith("owner"):
        # A supported entity may originally expose only the declared field;
        # adding the rejected entity's other identifier must not be ignored.
        supported.pop("name" if key == "id" else "id")
    def wrapper(person):
        value = {"principal_investigator": person}
        return {"role": value} if level == "middle" else value
    original = {"creators": [wrapper(rejected), wrapper(supported)]}
    pointer = ("/role" if level == "middle" else "") + "/principal_investigator/" + key
    audit = {"findings": [{"remove_relationship": {"path": "/creators/0", "identity": pointer}}]}
    survivor = copy.deepcopy(wrapper(supported))
    if level.startswith("owner"):
        added = "name" if key == "id" else "id"
        survivor["principal_investigator"][added] = ("https://example.org/new-identity"
            if level == "owner_new" else rejected[added])
    elif level == "middle":
        survivor["role"].update(rejected)
    else:
        survivor.update(rejected)
    assert check_relationship_removals(audit, original,
        {"creators": [survivor]})[0]["kind"] == "evidence_contract"
    assert check_relationship_removals(audit, original,
        {"creators": [wrapper(supported)]}) == []


def test_an_identity_cannot_select_an_arbitrary_person_from_an_indexed_list():
    original = {"creators": [{"people": [{"name": "First"}, {"name": "Second"}]}]}
    audit = {"findings": [{"remove_relationship": {
        "path": "/creators/0", "identity": "/people/0/name"}}]}
    assert check_relationship_removals(audit, original, {"creators": []})[0]["kind"] == "evidence_contract"


@pytest.mark.parametrize("layout", ["person", "collection", "new_object"])
def test_wrapper_identity_cannot_hide_a_rejected_descendant_identity(layout):
    rejected_person = {"id": "https://example.org/rejected", "name": "Rejected"}
    supported_person = {"id": "https://example.org/supported", "name": "Supported"}
    def wrapper(person, identifier):
        return {"id": identifier, "principal_investigator":
                ([person] if layout == "collection" else person)}
    rejected = wrapper(rejected_person, "https://example.org/role-rejected")
    supported = wrapper(supported_person, "https://example.org/role-supported")
    original = {"creators": [rejected, supported]}
    audit = {"findings": [{"remove_relationship": {"path": "/creators/0", "identity": "/id"}}]}
    survivor = copy.deepcopy(supported)
    if layout == "new_object":
        survivor["new_role"] = {"person": rejected_person}
    else:
        survivor["principal_investigator"] = rejected["principal_investigator"]
    assert check_relationship_removals(audit, original,
        {"creators": [survivor]})[0]["kind"] == "evidence_contract"
    assert check_relationship_removals(audit, original, {"creators": [supported]}) == []


def test_distinct_people_can_share_an_unchanged_affiliation_after_removal():
    affiliation = {"id": "https://example.org/institution", "name": "Institution"}
    original = {"creators": [
        {"principal_investigator": {"id": "https://example.org/rejected", "affiliation": affiliation}},
        {"principal_investigator": {"id": "https://example.org/supported", "affiliation": affiliation}},
    ]}
    audit = {"findings": [{"remove_relationship": {
        "path": "/creators/0", "identity": "/principal_investigator/id"}}]}
    assert check_relationship_removals(audit, original, {"creators": original["creators"][1:]}) == []


def test_cyclic_descendants_cannot_establish_removal():
    member = {"id": "https://example.org/rejected"}
    member["recursive"] = member
    audit = {"findings": [{"remove_relationship": {"path": "/members/0", "identity": "/id"}}]}
    problems = check_relationship_removals(audit, {"members": [member]}, {"members": []})
    assert problems[0]["kind"] == "evidence_contract"
    assert "cyclic" in problems[0]["detail"]


@pytest.mark.parametrize("mode", ["retained", "added", "changed", "removed"])
def test_person_orcid_is_bound_with_its_id_and_name(mode):
    rejected = {"id": "https://example.org/rejected", "name": "Rejected", "orcid": "0000-0002-1825-0097"}
    supported = {"id": "https://example.org/supported", "name": "Supported"}
    if mode in {"changed", "removed"}:
        supported["orcid"] = "0000-0001-5109-3700"
    original = {"creators": [{"principal_investigator": rejected}, {"principal_investigator": supported}]}
    audit = {"findings": [{"remove_relationship": {
        "path": "/creators/0", "identity": "/principal_investigator/name"}}]}
    survivor = copy.deepcopy(rejected if mode == "retained" else supported)
    if mode in {"added", "changed"}:
        survivor["orcid"] = rejected["orcid"]
    elif mode == "removed":
        survivor.pop("orcid")
    problems = check_relationship_removals(audit, original, {"creators": [{"principal_investigator": survivor}]})
    assert problems[0]["kind"] == ("unsupported_relationship_retained" if mode == "retained" else "evidence_contract")
    assert check_relationship_removals(audit, original,
        {"creators": [{"principal_investigator": supported}]}) == []


@pytest.mark.parametrize("field", ["orcid", "doi", "grant_number", "variable_name", "hash", "md5"])
def test_schema_identifier_alias_cannot_be_borrowed_by_a_survivor(field):
    original = {"members": [{"name": "Rejected", field: "rejected-identity"}, {"name": "Supported"}]}
    audit = {"findings": [{"remove_relationship": {"path": "/members/0", "identity": "/name"}}]}
    final = {"members": [{"name": "Supported", field: "rejected-identity"}]}
    assert check_relationship_removals(audit, original, final)[0]["kind"] == "evidence_contract"
    assert check_relationship_removals(audit, original, {"members": [{"name": "Supported"}]}) == []


def test_identity_signatures_cover_the_schema_declared_identifiers():
    from data_sheets_schema.evidence_assertions import IDENTITY_FIELDS
    schema = yaml.safe_load((Path(__file__).resolve().parents[1] /
        "src/data_sheets_schema/schema/data_sheets_schema_all.yaml").read_bytes())
    concepts = {"schema:identifier", "dcterms:identifier", "schema:sha256", "spdx:checksum"}
    declared = set()
    sections = [schema.get("slots", {}), *(body.get("attributes", {}) for body in schema["classes"].values())]
    for slots in sections:
        for name, slot in slots.items():
            mappings = {slot.get("slot_uri"), *(slot.get("exact_mappings") or []),
                        *(slot.get("broad_mappings") or []), *(slot.get("close_mappings") or [])}
            if slot.get("identifier") or concepts & mappings:
                declared.add(name)
    assert declared <= IDENTITY_FIELDS, "New schema identifiers need explicit removal-check coverage"
    assert "email" not in IDENTITY_FIELDS  # schema declares contact information, not a persistent identifier


@pytest.mark.parametrize("field,container,path", [
    ("sha256", "file_collections", "/file_collections/0/resources/0"),
    ("checksum", "distribution_formats", "/distribution_formats/0"),
])
@pytest.mark.parametrize("mode", ["retained", "added", "changed", "removed"])
def test_content_digest_cannot_be_moved_to_a_surviving_resource(field, container, path, mode):
    rejected = {"id": "https://example.org/rejected", "name": "Rejected", field: "a" * 64}
    supported = {"id": "https://example.org/supported", "name": "Supported"}
    if mode in {"changed", "removed"}:
        supported[field] = "b" * 64
    if field == "checksum":
        rejected[field] = "sha256:" + rejected[field]
        if field in supported:
            supported[field] = "sha256:" + supported[field]

    def record(members):
        return {container: ([{"id": "https://example.org/files", "resources": members}]
                            if container == "file_collections" else members)}

    original = record([rejected, supported])
    audit = {"findings": [{"remove_relationship": {"path": path, "identity": "/id"}}]}
    survivor = copy.deepcopy(rejected if mode == "retained" else supported)
    if mode in {"added", "changed"}:
        survivor[field] = rejected[field]
    elif mode == "removed":
        survivor.pop(field)
    problems = check_relationship_removals(audit, original, record([survivor]))
    assert problems[0]["kind"] == ("unsupported_relationship_retained" if mode == "retained" else "evidence_contract")
    assert check_relationship_removals(audit, original, record([supported])) == []


@pytest.mark.parametrize("field", ["orcid", "doi", "grant_number", "variable_name", "hash", "md5", "sha256", "checksum"])
def test_declared_identifier_can_bind_members_without_an_id_or_name(field):
    original = {"members": [{field: "rejected-identity"}, {field: "supported-identity"}]}
    audit = {"findings": [{"remove_relationship": {"path": "/members/0", "identity": "/" + field}}]}
    assert check_relationship_removals(audit, original, original)[0]["kind"] == "unsupported_relationship_retained"
    assert check_relationship_removals(audit, original, {"members": [{field: "supported-identity"}]}) == []


def test_relationship_identity_must_be_evidenced_in_original():
    audit = {"findings": [{"remove_relationship": {"path": "/creators/0", "identity": "/notes"}}]}
    assert check_relationship_removals(audit, {"creators": [{"notes": "not an identity"}]}, {})[0]["kind"] == "evidence_contract"


def appendix(claims):
    fence = chr(96) * 3
    return "## Evidence assertions\n" + fence + "json\n" + json.dumps({"claims": claims}) + "\n" + fence + "\n"


def test_report_requires_its_own_explicit_appendix():
    text = appendix([artifact()]) + "\n## Dispositions\nA separate table.\n"
    assert report_assertions(text) == [artifact()]
    for malformed in ("No assertions", appendix([]) + appendix([]), appendix([]) + "unparsed prose"):
        with pytest.raises(ValueError):
            report_assertions(malformed)
    with pytest.raises(ValueError, match="duplicate"):
        report_assertions(appendix([]).replace('{"claims": []}', '{"claims": [1], "claims": []}'))


def test_duplicate_original_fields_are_not_last_wins_evidence():
    original = "privacy: {details: in process}\nprivacy: {details: completed}\n"
    problems = check_assertions([artifact(op="lacks")], artifacts={"original_full": original}, chunks={})
    assert problems[0]["kind"] == "evidence_contract"
    assert "duplicate" in problems[0]["detail"]


def test_null_relationship_removal_is_invalid_not_ignored():
    assert check_relationship_removals({"findings": [{"remove_relationship": None}]}, {}, {})


def test_file_check_pins_exact_inputs_and_refuses_changed_document_mapping(tmp_path):
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("FILE: protocol.txt\nPATH: protocol.txt\nWe will release a holdout.\n")
    manifest = tmp_path / "chunks.yaml"
    mapping = chunking.build_manifest(bundle)
    manifest.write_text(chunking.dump_manifest(mapping))
    original = tmp_path / "original.yaml"
    original.write_text("privacy:\n  details: in process\n")
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"summary": "One check", "findings": [
        {"severity": "low", "record": "full", "slot": "privacy",
         "issue": "Fixture finding", "evidence": [artifact()]}]}))
    report = tmp_path / "report.md"
    report.write_text(appendix([artifact()]))
    paths = [bundle, manifest, original, audit, report]
    hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    result = check_files(audit=audit, bundle=bundle, manifest=manifest,
                         artifacts={"original_full": original}, report=report)
    assert result["findings"] == []
    assert result["artifact_sha256"]["original_full"] == hashes[original]
    assert hashes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    mapping["chunks"][0]["source"] = "overview.txt"
    manifest.write_text(yaml.safe_dump(mapping))
    assert main(["--audit", str(audit), "--bundle", str(bundle), "--manifest", str(manifest),
                 "--original-full", str(original)]) == 1
