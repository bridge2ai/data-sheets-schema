"""Generic source, relationship and original-artifact controls."""
import copy
import hashlib
import json

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
