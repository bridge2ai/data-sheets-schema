"""One historical resolver table governs every removal identity join (#4286)."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import receipts as rc, removals as rm, run_schema as rs

DOI = (("https://doi.org/", "doi"),)
URL = "https://doi.org/10.9999/neutral"
CURIE = "doi:10.9999/neutral"
TEXT = "Original neutral account documented thoroughly."
REPLACED = "Entirely replacement text for a different entry."
ORIGINAL = {"items": [{"id": URL, "description": TEXT}], "keywords": [URL]}
FINAL = {"items": [{"id": CURIE, "description": REPLACED}], "keywords": [CURIE]}


def classify(original, final, **kwargs):
    return rm.classify(original, final, {"findings": []}, **kwargs)


def legacy_cases(module, **kwargs):
    """Whole old blocks including phase, audit, receipt, and amend annotations."""
    old = {"items": [{"id": URL, "description": TEXT}]}
    new = {"items": [{"id": CURIE, "description": ""}]}
    receipt = {"chunks": [{"id": "c001", "status": "extracted", "extracted": [
        {"slot": "items[0].description", "snippet": TEXT}]}]}
    cases = [(ORIGINAL, FINAL, {"findings": []}, {"receipt": receipt}),
             ({"keywords": [URL, URL]}, {"keywords": [CURIE]}, None, {}),
             ({"box": {"gone": URL}}, {"box": {"source_caveats": CURIE}}, {"findings": []}, {}),
             ({"gone": URL}, {"elsewhere": CURIE}, {"findings": []}, {}),
             (None, {}, None, {}),
             (old, new, {"findings": [{"slot": "items"}]}, {
                 "intermediates": [("reconcile_full", {"items": [{"id": CURIE, "description": REPLACED}]})],
                 "amended_paths": {"items[0].description"},
                 "amended_edits": {"items[0].description": [(REPLACED, "")]}}),
             ({"box": {"count": 12345, "short": 12, "flag": True}},
              {"box": {"source_caveats": "Counts 12345 and 12 were mentioned; true."}}, None, {})]
    return [module.classify(a, b, audit, **options, **kwargs) for a, b, audit, options in cases]


def test_complete_legacy_default_and_none_bytes():
    # Whole outputs captured from the unmodified #4284 parent 612c63b54850.
    output = legacy_cases(rm)
    assert hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest() == "fb2673332c6a5d99e77d296235a4527c08d9583e5a1e20acefbc1287290f619b"
    assert legacy_cases(rm, identifier_bases=None) == output


@pytest.mark.parametrize("bases,removed,rewritten", [(None, 0, 1), ((), 3, 0), (DOI, 0, 1),
    ((("https://doi.org/", "old"),), 3, 0)])
def test_one_table_controls_entry_values_and_scalar_members(bases, removed, rewritten):
    before = copy.deepcopy((ORIGINAL, FINAL))
    block = classify(ORIGINAL, FINAL, identifier_bases=bases)
    assert (block["removed"], block["deleted"], block["rewritten"]) == (removed, removed, rewritten)
    assert (ORIGINAL, FINAL) == before


@pytest.mark.parametrize("bad", [False, "", {}, ["https://x/"], [("https://x/",)],
    [(None, "x")], [("https://x/", "")], [("https://x/", "bad:prefix")], [("relative/", "x")]])
@pytest.mark.parametrize("invoke", [
    lambda b: classify(None, {}, identifier_bases=b),
    lambda b: rm._Presence({}, {}, identifier_bases=b),
    lambda b: rm._Relocation({}, identifier_bases=b),
    lambda b: rm._flattened_into("", False, {}, {}, identifier_bases=b),
    lambda b: rm._member("plain", identifier_bases=b),
    lambda b: rm._words("plain", identifier_bases=b),
])
def test_malformed_explicit_table_refused_before_empty_shortcuts(bad, invoke):
    with pytest.raises(ValueError, match="identifier_bases"):
        invoke(bad)


def test_tables_are_immutable_cache_keys_and_never_reread_ambient(monkeypatch):
    from data_sheets_schema import api_runner
    def forbidden():
        raise AssertionError("ambient identity tables consulted")
    monkeypatch.setattr(api_runner, "_identifier_form_tables", forbidden)
    supplied = [["https://doi.org/", "doi"]]
    presence = rm._Presence(ORIGINAL, FINAL, identifier_bases=supplied)
    relocation = rm._Relocation({"new": CURIE}, identifier_bases=supplied)
    for function in (rm._member, rm._words):
        a = function(URL, identifier_bases=supplied)
        b = function(URL, identifier_bases=())
        c = function(URL, identifier_bases=(("https://doi.org/", "old"),))
        assert len({a, b, c}) == 3
        assert function(URL, identifier_bases=DOI) == a
    supplied.clear()
    assert presence.carried("items[0].description", None)
    assert presence.carried("keywords[0]", "keywords")
    assert relocation.candidate(URL)[1]["to"] == "new"
    assert classify(ORIGINAL, FINAL, identifier_bases=supplied)["deleted"] == 3
    assert classify(ORIGINAL, FINAL, identifier_bases=DOI)["deleted"] == 0
    assert rm._member(False, identifier_bases=()) != rm._member(0, identifier_bases=())


@pytest.mark.parametrize("bases,removed,flattened", [((), 2, 0), (DOI, 1, 1)])
def test_duplicated_scalar_members_consume_only_once(bases, removed, flattened):
    block = classify({"keywords": [URL, URL]}, {"keywords": [CURIE]}, identifier_bases=bases)
    assert (block["removed"], block["flattened"]) == (removed, flattened)


def test_nested_reordering_and_id_only_join():
    old = {"groups": [{"name": "outer", "items": ORIGINAL["items"]}]}
    new = {"groups": [{"name": "other"}, {"name": "outer", "items": [
        {"id": "doi:unrelated", "description": "another thing"}, FINAL["items"][0]]}]}
    explicit = classify(old, new, identifier_bases=DOI)
    empty = classify(old, new, identifier_bases=())
    assert explicit["removed"] == 0
    assert explicit["rewritten_paths"][0]["at"] == "groups[1].items[1].description"
    assert empty["deleted"] == 2


def test_containment_and_source_caveat_annotation_share_the_basis():
    old, new = {"box": {"gone": URL}}, {"box": {"source_caveats": CURIE}}
    explicit = classify(old, new, identifier_bases=DOI)
    assert explicit["flattened_paths"] == [{"path": "box.gone", "into": "box", "into_source_caveats": True}]
    assert classify(old, new, identifier_bases=())["deleted"] == 1
    assert classify({"value": URL}, {"value": CURIE}, identifier_bases=DOI)["rewritten"] == 0
    assert classify({"value": URL}, {"value": CURIE}, identifier_bases=())["rewritten"] == 1


def test_continuation_and_both_sides_of_surplus_use_same_table():
    shared = "Shared scientific account described thoroughly."
    old = {"items": [{"id": URL, "lost_detail": shared}, {"id": "other", "description": shared}]}
    new = {"items": [{"id": "other", "description": shared, "source_caveats": CURIE}]}
    assert rm._flattening("items[0].lost_detail", shared, old, new, identifier_bases=DOI) == ("items[0]", "continuation")
    assert rm._flattening("items[0].lost_detail", shared, old, new, identifier_bases=()) == (None, None)
    # The surviving sibling already accounted for the URL under this table;
    # it cannot furnish an extra copy of its CURIE to the dropped entry.
    old = {"items": [{"id": "gone", "lost_detail": CURIE}, {"id": "other", "original": URL}]}
    new = {"items": [{"id": "other", "new_detail": CURIE}]}
    assert rm._flattening("items[0].lost_detail", CURIE, old, new, identifier_bases=DOI) == (None, None)
    assert rm._flattening("items[0].lost_detail", CURIE, old, new, identifier_bases=()) == ("items", "surplus")


@pytest.mark.parametrize("old,new", [(URL, CURIE), (CURIE, URL)])
def test_relocation_reads_both_candidate_and_value_under_one_basis(old, new):
    block = classify({"gone": old}, {"new": new}, identifier_bases=DOI)
    assert block["deleted"] == 1  # A candidate does not become a retained claim.
    assert block["unfounded_paths"][0]["relocated_candidate"]["to"] == "new"
    assert classify({"gone": old}, {"new": new}, identifier_bases=())["relocated_candidate"] == 0
    assert classify({"gone": old}, {"new": new + "-different"}, identifier_bases=DOI)["relocated_candidate"] == 0


def test_phase_and_audit_amendment_attribution_follow_the_join():
    old = {"items": [{"id": URL, "description": TEXT}]}
    stage = {"items": [{"id": CURIE, "description": REPLACED}]}
    new = {"items": [{"id": CURIE, "description": ""}]}
    options = {"intermediates": [("reconcile_full", stage)],
        "amended_paths": {"items[0].description"}, "amended_edits": {"items[0].description": [(REPLACED, "")]}}
    audit = {"findings": [{"slot": "items"}]}
    explicit = rm.classify(old, new, audit, identifier_bases=DOI, **options)
    empty = rm.classify(old, new, audit, identifier_bases=(), **options)
    assert explicit["phase"] == {"write": 1}
    assert empty["phase"] == {"reconcile_full": 2}
    assert explicit["founded_paths"] == [{"path": "items[0].description", "phase": "write",
        "curator_amend": True, "by": "slot", "finding": 0}]
    row = next(r for r in empty["founded_paths"] if r["path"].endswith("description"))
    assert "curator_amend" not in row and "amended_after_model_removal" not in row


def test_pre_amend_reconstruction_joins_the_original_identity():
    old = {"items": [{"id": URL, "description": TEXT}]}
    new = {"items": [{"id": "changed", "description": REPLACED}]}
    options = {"amended_paths": {"items[0].id"}, "amended_edits": {"items[0].id": [(CURIE, "changed")]}}
    explicit = classify(old, new, identifier_bases=DOI, **options)
    empty = classify(old, new, identifier_bases=(), **options)
    row = next(r for r in explicit["unfounded_paths"] if r["path"].endswith("description"))
    assert "curator_amend" not in row and "curator_amend_ambiguous" not in row
    assert next(r for r in empty["unfounded_paths"] if r["path"].endswith("description"))["curator_amend_ambiguous"]


def test_non_identifier_text_numbers_boolean_and_boundary_semantics_stay_unchanged():
    old = {"words": ["The Organisation Centre"], "box": {"count": 12345, "flag": True}}
    new = {"words": ["the organization center"], "box": {"text": "12345 true"}}
    assert classify(old, new, identifier_bases=()) == classify(old, new, identifier_bases=DOI)
    assert rm._member("https://x.test/nameOther", identifier_bases=(("https://x.test/name", "x"),)) == rm._member("https://x.test/nameOther", identifier_bases=())


def disk_run(tmp_path, prefixes=None):
    schema = {"id": "https://example.test/schema", "name": "neutral", "default_range": "string",
        "prefixes": {"linkml": "https://w3id.org/linkml/", "xsd": "http://www.w3.org/2001/XMLSchema#", **(prefixes or {})},
        "types": {"string": {"base": "str", "uri": "xsd:string"}, "uriorcurie": {"base": "URIorCURIE", "uri": "xsd:anyURI"}},
        "classes": {"Dataset": {"attributes": {"id": {"range": "uriorcurie", "identifier": True}}}}}
    core = tmp_path / "claudecode_api_core" / "L"
    full = tmp_path / "claudecode_api" / "L" / "EXAMPLE_d4d.yaml"
    inter = core / "intermediate"
    inter.mkdir(parents=True); full.parent.mkdir(parents=True)
    for path, data in ((inter / "EXAMPLE_full.yaml", ORIGINAL), (inter / "EXAMPLE_reconcile_full.yaml", FINAL), (full, FINAL)):
        path.write_text(yaml.safe_dump(data))
    (inter / "EXAMPLE_audit.json").write_text(json.dumps({"findings": []}))
    schema_path = tmp_path / "schema.yaml"
    schema_path.write_text(yaml.safe_dump(schema))
    record = {"run": {"project": "EXAMPLE", "label": "L"}, "schema": {"full_path": str(schema_path),
        "full_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest()}}
    provenance = core / "EXAMPLE_provenance.yaml"
    provenance.write_text(yaml.safe_dump(record))
    return provenance, record


def all_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("prefixes,removed", [({}, 3), ({"doi": "https://doi.org/"}, 0), ({"old": "https://doi.org/"}, 3)])
def test_actual_disk_schema_reverses_counts_and_preserves_every_input(tmp_path, prefixes, removed, monkeypatch):
    from data_sheets_schema import api_runner
    provenance, record = disk_run(tmp_path, prefixes)
    before = all_bytes(tmp_path)
    monkeypatch.setattr(api_runner, "_identifier_form_tables", lambda: (_ for _ in ()).throw(AssertionError("ambient rules read")))
    block = rm.for_record(provenance, record=record)
    assert block["checked"]
    assert block["deleted"] == block["removed"] == removed
    assert block["phase"] == ({"reconcile_full": 3} if removed else {})
    identity = block["artifacts"]["identifier_rules"]
    assert identity["schema_basis"]["source"] == "the run's schema, on disk"
    assert identity["schema_basis"]["sha256"] == record["schema"]["full_sha256"]
    assert identity["bases_sha256"] == hashlib.sha256(json.dumps(identity["bases"], ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    assert block["artifacts"]["person_slot_rules"] == identity["schema_basis"]
    assert all_bytes(tmp_path) == before


@pytest.mark.parametrize("mode", ["unrecorded", "unrecoverable", "unusable"])
def test_current_fallback_discloses_actual_bytes_and_requested_history(tmp_path, monkeypatch, mode):
    from data_sheets_schema.identifiers import FULL_SCHEMA
    from data_sheets_schema.resources import resource_path
    provenance, record = disk_run(tmp_path)
    historical = record["schema"]["full_sha256"]
    if mode == "unrecorded":
        record.pop("schema")
    elif mode == "unrecoverable":
        Path(record["schema"]["full_path"]).unlink()
        monkeypatch.setattr("data_sheets_schema.reconstructed_bytes.reconstructed_bytes_for", lambda *a, **k: None)
        monkeypatch.setattr("data_sheets_schema.provenance.committed_bytes_for", lambda *a, **k: None)
    else:
        path = Path(record["schema"]["full_path"])
        schema = yaml.safe_load(path.read_bytes())
        schema["classes"]["Dataset"]["is_a"] = "MissingAncestor"
        path.write_text(yaml.safe_dump(schema))
        historical = record["schema"]["full_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    before = all_bytes(tmp_path)
    block = rm.for_record(provenance, record=record)
    assert block["checked"] and block["removed"] == 0
    basis = block["artifacts"]["identifier_rules"]["schema_basis"]
    assert basis["source"] == rs.TODAY and basis["reason"]
    raw = resource_path(FULL_SCHEMA).read_bytes()
    assert basis["sha256"] == hashlib.sha256(raw).hexdigest() != historical
    assert basis["md5"] == hashlib.md5(raw).hexdigest()
    if mode != "unrecorded":
        assert basis["requested_schema"]["sha256"] == historical
    if mode == "unusable":
        assert block["artifacts"]["enum_alias_tables"]["source"] == "the run's schema, on disk"
    assert all_bytes(tmp_path) == before


@pytest.mark.parametrize("bases", [None, False, (("relative", "bad"),), (("https://x/", ""),)])
def test_invalid_selected_rules_never_become_checked_counts(tmp_path, monkeypatch, bases):
    provenance, record = disk_run(tmp_path)
    rules, basis = rs.identifier_rules(record)
    monkeypatch.setattr(rs, "identifier_rules", lambda _: (rules._replace(bases=bases), basis))
    before = all_bytes(tmp_path)
    block = rm.for_record(provenance, record=record)
    assert not block["checked"] and block["removed"] is None
    assert block["artifacts"]["identifier_rules"]["state"] == "unusable"
    assert all_bytes(tmp_path) == before


def test_current_capture_disagreement_cannot_certify_a_historical_join(tmp_path, monkeypatch):
    provenance, record = disk_run(tmp_path)
    selected = rs.todays_identifier_rules()._replace(bases=())
    monkeypatch.setattr(rs, "identifier_rules", lambda _: (selected, {"source": rs.TODAY, "reason": "history missing"}))
    block = rm.for_record(provenance, record=record)
    assert not block["checked"] and block["deleted"] is None
    assert "disagree" in block["artifacts"]["identifier_rules"]["reason"]
