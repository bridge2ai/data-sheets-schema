"""Registered provenance is an explicit, byte-bound authority, not a waiver."""
import copy
import hashlib
import json

import pytest
import yaml

from data_sheets_schema import chunking, evidence_assertions as evidence, source_metadata as metadata, source_review


MANIFEST = b"""source_priority:
  2: [documentation]
  4: [tutorial]
projects:
  EXAMPLE:
    - id: handbook
      source_type: documentation
      processed_file: handbook.txt
      captured_at: '2025-01-02'
      curation_note: Never promote this narrative to scientific authority.
    - id: lesson
      source_type: tutorial
      processed_file: lesson.txt
      superseded_by: handbook
  OTHER:
    - id: handbook
      source_type: tutorial
      processed_file: unrelated.txt
"""
RAW = "source_caveats: The registered manifest ranks the handbook as tier 2.\n"
CHUNKS = {"c001": {"source": "handbook.txt", "text": "The source describes a collection."}}


def assertion(raw=MANIFEST, **changes):
    return {"provenance": "source_manifest", "sha256": hashlib.sha256(raw).hexdigest(),
            "source_id": "handbook", "source": "handbook.txt", "field": "effective_priority", "value": 2,
            **changes}


def review(raw=RAW, *, artifact="original_full", assertions=None):
    inv = source_review.inventory(raw, artifact)
    return {"artifact": artifact, "sha256": inv["sha256"], "values": [
        {"path": item["path"], "claims": [{"text": item["text"], "verdict": "supported",
            "attributed_to": [], "claim_status": "fact", "source_status": "fact",
            "evidence": [assertion()] if assertions is None else assertions,
            "reason": "This clause reports a registered input declaration only."}]}
        for item in inv["values"]]}


def check(value=None, **kwargs):
    args = dict(raw=RAW, artifact="original_full", chunks=CHUNKS,
                protocol_version=5, source_manifest_raw=MANIFEST, project="EXAMPLE")
    args.update(kwargs)
    return source_review.check(review() if value is None else value, **args)


def test_projection_is_exact_pure_narrow_and_uses_existing_priority_rules():
    original = MANIFEST[:]
    result = metadata.projection(MANIFEST, "EXAMPLE")
    assert MANIFEST == original
    assert result == {"sha256": hashlib.sha256(MANIFEST).hexdigest(), "project": "EXAMPLE", "sources": [
        {"source_id": "handbook", "source": "handbook.txt", "source_type": "documentation",
         "effective_priority": 2, "priority_basis": "source_type", "captured_at": "2025-01-02"},
        {"source_id": "lesson", "source": "lesson.txt", "source_type": "tutorial",
         "effective_priority": 4, "priority_basis": "source_type", "superseded_by": "handbook"}]}
    assert result == metadata.projection(MANIFEST.decode(), "EXAMPLE")
    data = yaml.safe_load(MANIFEST)
    data["projects"]["EXAMPLE"][0]["priority"] = 7
    data["projects"]["EXAMPLE"][1]["source_type"] = "unranked type"
    data["projects"]["EXAMPLE"] = {"sources": data["projects"]["EXAMPLE"]}
    projected = metadata.projection(yaml.safe_dump(data), "EXAMPLE")
    assert [row["effective_priority"] for row in projected["sources"]] == [7, 99]
    assert [row["priority_basis"] for row in projected["sources"]] == ["source_override", "unranked"]
    from data_sheets_schema.source_priority import sources, priority_of, tiers
    assert [priority_of(row, tiers(data))[0] for row in sources("EXAMPLE", data)] == [7, 99]


@pytest.mark.parametrize("raw", [
    MANIFEST + b"projects: {}\n", MANIFEST.replace(b"  4: [tutorial]", b"  2: [tutorial]"),
    MANIFEST.replace(b"  4: [tutorial]", b"  true: [tutorial]"),
    MANIFEST.replace(b"  4: [tutorial]", b"  4.0: [tutorial]"),
    MANIFEST.replace(b"  4: [tutorial]", b"  -4: [tutorial]"),
    MANIFEST.replace(b"  4: [tutorial]", b"  .inf: [tutorial]"),
    MANIFEST.replace(b"  4: [tutorial]", b"  4: [documentation]"),
    MANIFEST.replace(b"  4: [tutorial]", b"  4: [tutorial, tutorial]"),
    MANIFEST.replace(b"  4: [tutorial]", b"  4: tutorial"),
    MANIFEST.replace(b"id: lesson", b"id: handbook"),
    MANIFEST.replace(b"lesson.txt", b"handbook.txt"),
    MANIFEST.replace(b"id: lesson", b"id: null"),
    MANIFEST.replace(b"source_type: tutorial", b"source_type: false"),
    MANIFEST.replace(b"superseded_by: handbook", b"superseded_by: lesson"),
    MANIFEST.replace(b"superseded_by: handbook", b"superseded_by: missing"),
    MANIFEST.replace(b"captured_at: '2025-01-02'", b"captured_at: '2025-02-30'"),
    MANIFEST.replace(b"captured_at: '2025-01-02'", b"captured_at: 'Dataset contains a million records'"),
    MANIFEST.replace(b"captured_at: '2025-01-02'", b"captured_at: 123"),
    MANIFEST.replace(b"captured_at: '2025-01-02'", b"priority: true"),
    MANIFEST.replace(b"captured_at: '2025-01-02'", b"priority: 2.0"),
    MANIFEST.replace(b"captured_at: '2025-01-02'", b"priority: null"),
    MANIFEST + b"extra: .nan\n", MANIFEST + b"extra: &loop [*loop]\n",
    MANIFEST + b"extra: {<<: {x: 1}}\n", MANIFEST + b"extra: {[one]: two}\n",
    b"projects: {EXAMPLE: []}", b"projects: {EXAMPLE: [false]}", b"projects: {EXAMPLE: {}}",
])
def test_ambiguous_or_nonfinite_manifest_cannot_be_authority(raw):
    with pytest.raises((ValueError, yaml.YAMLError)):
        metadata.projection(raw, "EXAMPLE")


@pytest.mark.parametrize("project", [None, True, [], "", "MISSING", "OTHER_ALIAS"])
def test_authority_requires_exact_selected_project(project):
    with pytest.raises(ValueError):
        metadata.projection(MANIFEST, project)


def test_supersession_cycle_and_cross_project_target_reject():
    data = yaml.safe_load(MANIFEST)
    data["projects"]["EXAMPLE"][0]["superseded_by"] = "lesson"
    with pytest.raises(ValueError, match="acyclic"):
        metadata.projection(yaml.safe_dump(data), "EXAMPLE")
    data["projects"]["EXAMPLE"][0].pop("superseded_by")
    data["projects"]["OTHER"][0]["id"] = "foreign"
    data["projects"]["EXAMPLE"][1]["superseded_by"] = "foreign"
    with pytest.raises(ValueError, match="selected-project"):
        metadata.projection(yaml.safe_dump(data), "EXAMPLE")


def test_explicit_99_and_unranked_fallback_are_distinguishable():
    data = yaml.safe_load(MANIFEST)
    sources = data["projects"]["EXAMPLE"]
    sources[0]["priority"] = 99
    sources[1]["source_type"] = "unranked type"
    raw = yaml.safe_dump(data).encode()
    authority = metadata.projection(raw, "EXAMPLE")
    assert [row["effective_priority"] for row in authority["sources"]] == [99, 99]
    assert [row["priority_basis"] for row in authority["sources"]] == ["source_override", "unranked"]
    with pytest.raises(ValueError, match="typed metadata"):
        metadata.check_assertion(assertion(raw, field="priority_basis", value="unranked"), authority=authority)


@pytest.mark.parametrize("date_value,projected", [
    ("2025-01-02", "2025-01-02"),
    ("'2025-01-02T03:04:05Z'", "2025-01-02T03:04:05Z"),
    ("'2025-01-02T03:04:05.123+01:00'", "2025-01-02T03:04:05.123+01:00"),
])
def test_capture_dates_are_structured_and_exactly_projected(date_value, projected):
    raw = MANIFEST.replace(b"'2025-01-02'", date_value.encode())
    authority = metadata.projection(raw, "EXAMPLE")
    assert authority["sources"][0]["captured_at"] == projected
    metadata.check_assertion(assertion(raw, field="captured_at", value=projected), authority=authority)


@pytest.mark.parametrize("field,value", [("source_type", "documentation"),
    ("effective_priority", 2), ("priority_basis", "source_type"), ("captured_at", "2025-01-02")])
def test_whitelisted_exact_typed_assertions(field, value):
    assert check(review(assertions=[assertion(field=field, value=value)]))["findings"] == []
    assert check()["instrument"] == "source_review v2 (#2169)"
    metadata.check_assertion(assertion(source_id="lesson", source="lesson.txt",
        field="superseded_by", value="handbook"), authority=metadata.projection(MANIFEST, "EXAMPLE"))


@pytest.mark.parametrize("change", [
    {"sha256": "0" * 64}, {"source_id": "missing"}, {"source": "lesson.txt"},
    {"value": True}, {"value": 2.0}, {"value": "2"}, {"value": float("nan")}, {"value": None},
    {"field": "curation_note", "value": "Never promote this narrative to scientific authority."},
    {"field": "/projects/EXAMPLE/0/curation_note"}, {"field": "url"}, {"field": []},
    {"provenance": "source_bundle"}, {"extra": "ambiguous"}, {"source_id": []},
    {"field": "superseded_by", "value": "lesson"},
])
def test_wrong_binding_types_or_unlisted_metadata_reject(change):
    assert check(review(assertions=[assertion(**change)]))["findings"]


@pytest.mark.parametrize("changed", [MANIFEST + b"\n", MANIFEST.replace(b"\n", b"\r\n")])
def test_exact_raw_bytes_not_parsed_equivalence(changed):
    assert yaml.safe_load(MANIFEST) == yaml.safe_load(changed)
    assert check(source_manifest_raw=changed)["findings"]


def test_other_project_cannot_reuse_the_same_id():
    assert check(project="OTHER")["findings"]


@pytest.mark.parametrize("mode", ["mixed", "attributed", "applied", "partial", "metadata_escape"])
def test_metadata_cannot_waive_coverage_or_dataset_document_evidence(mode):
    value = review()
    claim = value["values"][0]["claims"][0]
    if mode == "mixed":
        claim["evidence"].append({"source": "handbook.txt", "chunk": "c001", "quote": CHUNKS["c001"]["text"]})
    elif mode == "attributed":
        claim["attributed_to"] = ["handbook.txt"]
    elif mode == "applied":
        claim["claim_status"] = claim["source_status"] = "applied"
    elif mode == "partial":
        claim["text"] = "tier 2"
    else:
        value["values"][0] = {"path": "/source_caveats", "metadata_reason": "It is provenance."}
    assert check(value)["findings"]


def test_missing_authority_rejects_provenance_but_permits_bundle_only_v5():
    assert check(source_manifest_raw=None)["findings"]
    ordinary = review(assertions=[{"source": "handbook.txt", "chunk": "c001", "quote": CHUNKS["c001"]["text"]}])
    assert check(ordinary, source_manifest_raw=None)["findings"] == []
    # Structural evidence checks do not classify or entail the natural-language
    # clause. Independent semantic review remains necessary in every version.
    assert "independent review" in check()["scope"]
    with pytest.raises(ValueError):
        check(ordinary, project=None)


@pytest.mark.parametrize("version", [3, 4])
def test_legacy_review_does_not_enable_provenance_or_change_instrument(version):
    assert check(protocol_version=version, source_manifest_raw=None, project=None)["findings"]
    ordinary = review(assertions=[{"source": "handbook.txt", "chunk": "c001", "quote": CHUNKS["c001"]["text"]}])
    assert check(ordinary, protocol_version=version, source_manifest_raw=None, project=None)["instrument"] == source_review.INSTRUMENT
    with pytest.raises(ValueError, match="protocol 5"):
        check(protocol_version=version)


def test_metadata_form_is_not_an_unrestricted_audit_or_report_assertion():
    errors = evidence.check_assertions([assertion()], artifacts={}, chunks=CHUNKS)
    assert errors and errors[0]["kind"] == "evidence_contract"


def fixture(tmp_path):
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("FILE: handbook.txt\nPATH: handbook.txt\nThe source describes a collection.\n")
    chunks = tmp_path / "chunks.yaml"
    chunks.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    source_manifest = tmp_path / "registered.yaml"
    source_manifest.write_bytes(MANIFEST)
    original, final = tmp_path / "original.yaml", tmp_path / "final.yaml"
    original.write_text(RAW)
    final.write_text(RAW)
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"summary": "Synthetic provenance review", "findings": [], "source_review": review()}))
    report = tmp_path / "report.md"
    report.write_text("## Evidence assertions\n```json\n" + json.dumps({"claims": [],
        "source_review": review(artifact="final_full")}) + "\n```\n")
    return dict(audit=audit, bundle=bundle, manifest=chunks, source_manifest=source_manifest,
                project="EXAMPLE", artifacts={"original_full": original, "final_full": final},
                report=report, protocol_version=5)


def test_actual_file_audit_final_report_and_cli_preserve_inputs_and_bind_authority(tmp_path, capsys):
    args = fixture(tmp_path)
    files = list(tmp_path.iterdir())
    before = {p: p.read_bytes() for p in files}
    result = evidence.check_files(**args)
    assert result["findings"] == []
    assert result["source_review_original"]["claims_checked"] == result["source_review_final"]["claims_checked"] == 1
    assert result["artifact_sha256"]["source_manifest"] == hashlib.sha256(MANIFEST).hexdigest()
    argv = ["--protocol-version", "5", "--project", "EXAMPLE"]
    for key in ("audit", "bundle", "manifest", "source_manifest", "report"):
        argv.extend(["--" + key.replace("_", "-"), str(args[key])])
    for key, path in args["artifacts"].items():
        argv.extend(["--" + key.replace("_", "-"), str(path)])
    assert evidence.main(argv) == 0
    assert not json.loads(capsys.readouterr().out)["findings"]
    assert before == {p: p.read_bytes() for p in files}
    args["source_manifest"].write_bytes(MANIFEST + b"\n")
    assert evidence.main(argv) == 1
    assert "exact source-manifest bytes" in json.dumps(json.loads(capsys.readouterr().out)["findings"])


@pytest.mark.parametrize("boundary", ["audit", "report"])
def test_real_file_authority_threading_omission_mutant_fails(tmp_path, monkeypatch, boundary):
    args = fixture(tmp_path)
    original = getattr(evidence, "check_" + boundary)
    def omitted(*a, **kw):
        kw.pop("source_manifest_raw", None)
        kw.pop("project", None)
        return original(*a, **kw)
    monkeypatch.setattr(evidence, "check_" + boundary, omitted)
    result = evidence.check_files(**args)
    assert result["findings"]
    target = "source_review_original" if boundary == "audit" else "source_review_final"
    assert result[target]["findings"]


def test_legacy_file_check_rejects_new_authority_before_read(tmp_path):
    args = fixture(tmp_path)
    args.update(protocol_version=4, source_manifest=tmp_path / "does-not-exist.yaml")
    with pytest.raises(ValueError, match="protocol 5"):
        evidence.check_files(**args)


def test_version_dispatch_is_explicit():
    assert [evidence.protocol_for_renderer(v) for v in (10, 11, 12, 14, 15, 16, 17, 18, 19, 20)] == [1, 2, 3, 3, 4, 5, 5, 6, 6, 7]
    assert evidence.instrument(5) == "evidence_assertions v5 / source_review v2 (#2169)"
    assert evidence.instrument(6) == "evidence_assertions v6 / source_review v2 (#2178)"
    assert evidence.instrument(7) == "evidence_assertions v7 / source_review v2 (#2192)"
    for value in (True, 5.0, 6.0, 7.0, None, 8):
        with pytest.raises(ValueError):
            evidence.instrument(value)
