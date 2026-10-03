"""Invented engineering fixtures use real typed reconstruction, never recall labels."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from data_sheets_schema import audit_batches as b, typed_audit as ta, typed_audit_report as report
from tests.test_typed_audit import supplied, packet, replies, seal  # shared neutral actual-checker fixtures


def encoded(packet, count=1, *, mixed=False):
    workers, omissions, delta, quote = replies(packet, count)
    if mixed:
        delta["new_findings"][0]["issue"] = "Do not infer a category from this unrelated prose."
        delta["new_findings"][0]["omission_candidates"].remove("candidate-2")
        delta["omission_dispositions"][2].update(action="drop", reason="Proposed drop for independent review.", evidence=[quote])
        delta["new_findings"].append({"severity": "low", "record": "full", "slot": "name",
            "issue": "Missing supported information; this finding deliberately has no kind.", "evidence": [quote]})
    return b.canonical_bytes(seal(packet, workers, omissions, delta))


@pytest.fixture
def raw(packet):
    return encoded(packet, 3, mixed=True)


@pytest.fixture
def selected(tmp_path, raw):
    path = tmp_path / "assembly.json"
    path.write_bytes(raw)
    return path


def test_actual_reconstruction_reports_kind_untyped_merge_and_drop(raw):
    original = raw
    result = report.build_report([("explicit-input.json", raw)])
    row = result["assemblies"][0]
    assert row["counts"]["findings"] == 2
    assert row["counts"]["candidates"] == 3
    assert row["counts"]["retained_candidates"] == 2
    assert row["counts"]["dropped_candidates"] == 1
    assert row["counts"]["findings_by_declared_kind"]["omission"] == 1
    assert row["counts"]["findings_by_declared_kind"]["untyped"] == 1
    assert [(f["classification_basis"], f["declared_kind"]) for f in row["findings"]] == [
        ("audit_declared_kind", "omission"), ("untyped", None)]
    assert [c["final_finding_ordinal"] for c in row["candidates"]] == [0, 0, None]
    assert row["acceptance"]["independently_reconstructed"] is True
    assert all(row["acceptance"][key] == "unverified" for key in ("scientific_support", "novelty", "exhaustive_recall"))
    assert "independent observations" in " ".join(result["limitations"])
    assert raw == original


def test_all_raw_and_authority_identities_are_retained(raw):
    saved = json.loads(raw)
    row = report.build_report([("chosen-name", raw)])["assemblies"][0]
    assert row["source"] == {"path": "chosen-name", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    identity = row["identity"]
    assert identity["assembly_sha256"] == saved["sha256"]
    assert identity["packet_sha256"] == saved["packet"]["sha256"]
    assert identity["schema_sources_sha256"] == saved["lineage"]["schema_sources_sha256"]
    assert row["lineage"] == saved["lineage"]
    for name, blob in saved["packet"]["inputs"].items():
        assert identity["inputs"][name] == {key: blob[key] for key in ("sha256", "bytes")}
    assert len(identity["schema_sources"]) == len(saved["packet"]["schema_sources"])
    for name, blob in saved["workers"].items():
        inner = json.loads(ta._unblob(blob, ta.MAX_SAVED_RESPONSE_BYTES))
        assert identity["workers"][name]["response"]["sha256"] == inner["response"]["sha256"]
        assert identity["workers"][name]["request_sha256"] == inner["request_sha256"]
    assert identity["integration_request_sha256"] == saved["index"]["integration_request"]["request_sha256"]
    assert identity["omission_contract_sha256"] == saved["packet"]["omission_request"]["payload"]["contract_sha256"]


def test_optional_core_and_source_manifest_authorities_preserved(supplied):
    supplied.update(original_core=b"name: Core Example\n", project="EXAMPLE",
        source_manifest=b"projects:\n  EXAMPLE:\n    sources:\n    - id: manual\n      processed_file: manual.txt\n      source_type: article\n")
    packet = ta.prepare(**supplied)
    result = report.build_report([("selected", encoded(packet, 0))])["assemblies"][0]
    for name in ("original_core", "source_manifest"):
        assert result["identity"]["inputs"][name]["sha256"] == hashlib.sha256(supplied[name]).hexdigest()


@pytest.mark.parametrize("kind", sorted(ta.audit_protocol.KINDS - {"omission"}))
def test_declared_taxonomy_is_not_mapped_to_old_regex_categories(packet, kind):
    workers, omissions, delta, quote = replies(packet, 0)
    delta["new_findings"] = [{"severity": "low", "record": "full", "slot": "name", "kind": kind,
        "issue": "Missing supported information.", "evidence": [quote]}]
    value = report.build_report([("selected", b.canonical_bytes(seal(packet, workers, omissions, delta)))])
    row = value["assemblies"][0]
    assert row["counts"]["findings_by_declared_kind"][kind] == 1
    assert row["findings"][0]["declared_kind"] == kind
    assert row["findings"][0]["classification_basis"] == "audit_declared_kind"


@pytest.mark.parametrize("mutation", ["passed", "counts", "lineage", "audit", "context", "missing_chunk"])
def test_tampering_rejected_even_after_outer_reseal(raw, mutation):
    value = json.loads(raw)
    if mutation == "passed":
        value["acceptance"]["passed"] = False
    elif mutation == "counts":
        value["acceptance"]["finding_counts"]["omission"] = 100
    elif mutation == "lineage":
        value["lineage"]["omission_candidates"][0]["final_finding_ordinal"] = 1
    elif mutation == "audit":
        audit = json.loads(ta._unblob(value["audit"]))
        audit["findings"][0]["kind"] = "other"
        value["audit"] = ta._blob(b.canonical_bytes(audit))
    elif mutation == "context":
        context = json.loads(ta._unblob(value["packet"]["inputs"]["context"]))
        context["scopes"][0]["scope"] = "A different release."
        value["packet"]["inputs"]["context"] = ta._blob(b.canonical_bytes(context))
    else:
        omissions = json.loads(ta._unblob(value["omission_response"]))
        omissions["chunks"].pop(0)
        value["omission_response"] = ta._blob(b.canonical_bytes(omissions))
    value = ta._seal({key: item for key, item in value.items() if key != "sha256"})
    with pytest.raises(ValueError):
        report.build_report([("tampered", b.canonical_bytes(value))])


@pytest.mark.parametrize("raw", [b'{"passed":true}', b'{"a":1,"a":2}', b'{"bad":NaN}', b'[]'])
def test_refuse_unbound_reports_or_ambiguous_json(raw):
    with pytest.raises(ValueError):
        report.build_report([("not-an-assembly", raw)])


@pytest.mark.parametrize("mode", ["same", "whitespace"])
def test_duplicate_canonical_assembly_is_not_an_independent_audit(raw, mode):
    second = raw if mode == "same" else json.dumps(json.loads(raw), indent=4).encode()
    with pytest.raises(ValueError, match="duplicate canonical assembly"):
        report.build_report([("one", raw), ("another-name", second)])


def test_order_is_explicit_no_method_or_cohort_inference(packet, raw):
    other = encoded(packet, 0)
    value = report.build_report([("arbitrary-legacy-v99", other), ("not-a-method", raw)])
    assert [r["source"]["path"] for r in value["assemblies"]] == ["arbitrary-legacy-v99", "not-a-method"]
    assert [r["selection_index"] for r in value["assemblies"]] == [0, 1]
    assert value["assemblies"][0]["counts"]["findings"] == 0
    assert value["assemblies"][0]["counts"]["candidates"] == 0
    assert not ({"method", "cohort", "project", "aggregate"} & value.keys())


def test_csv_preserves_zero_finding_merged_dropped_and_untyped_rows(packet, raw):
    result = report.build_report([("mixed", raw), ("empty", encoded(packet, 0))])
    rows = list(csv.DictReader(io.StringIO(report.csv_bytes(result).decode())))
    assemblies = [r for r in rows if r["row_type"] == "assembly"]
    assert len(rows) == 7 and len(assemblies) == 2
    assert [r["findings"] for r in assemblies] == ["2", "0"]
    assert json.loads(assemblies[0]["identity_json"]) == result["assemblies"][0]["identity"]
    assert assemblies[0]["assembly_raw_bytes"] == str(len(raw))
    assert json.loads(assemblies[0]["protocol_json"]) == result["assemblies"][0]["protocol"]
    assert json.loads(assemblies[0]["acceptance_json"]) == result["assemblies"][0]["acceptance"]
    assert json.loads(assemblies[0]["lineage_json"]) == result["assemblies"][0]["lineage"]
    candidates = [r for r in rows if r["row_type"] == "candidate"]
    assert [r["final_finding_ordinal"] for r in candidates] == ["0", "0", ""]
    assert [r["disposition"] for r in candidates] == ["retain", "retain", "drop"]
    assert all(r["findings"] == "" for r in rows if r["row_type"] != "assembly")
    assert [r["classification_basis"] for r in rows if r["row_type"] == "finding"] == ["audit_declared_kind", "untyped"]


def test_drop_only_still_has_assembly_and_candidate_rows(packet):
    workers, omissions, delta, quote = replies(packet)
    delta["new_findings"] = []
    delta["omission_dispositions"][0].update(action="drop", evidence=[quote])
    value = report.build_report([("dropped", b.canonical_bytes(seal(packet, workers, omissions, delta)))])
    rows = list(csv.DictReader(io.StringIO(report.csv_bytes(value).decode())))
    assert [r["row_type"] for r in rows] == ["assembly", "candidate"]
    assert rows[0]["findings"] == "0" and rows[0]["dropped_candidates"] == "1"


def test_file_read_once_and_embedded_schema_not_reopened(selected, supplied, monkeypatch):
    # Poison only this test's local authority after a legitimate capture.
    supplied["schema_path"].write_text("this is no longer a schema")
    calls = []
    original = report.audit_omissions._file
    def capture(path, limit):
        calls.append(path)
        return original(path, limit)
    monkeypatch.setattr(report.audit_omissions, "_file", capture)
    result = report.read_report([selected])
    assert calls == [selected]
    assert result["assemblies"][0]["acceptance"]["passed"] is True


@pytest.mark.parametrize("alias", ["input", "hardlink", "symlink", "dangling", "schema", "schema_hardlink", "existing_output"])
def test_never_overwrite_input_authority_or_destination(selected, supplied, tmp_path, alias):
    output = tmp_path / "report.json"
    if alias == "input":
        output = selected
    elif alias == "hardlink":
        os.link(selected, output)
    elif alias == "symlink":
        output.symlink_to(selected)
    elif alias == "dangling":
        output.symlink_to(tmp_path / "absent")
    elif alias == "schema":
        output = supplied["schema_path"]
    elif alias == "schema_hardlink":
        os.link(supplied["schema_path"], output)
    else:
        output.write_bytes(b"prior report")
    before = {p: p.read_bytes() for p in (selected, supplied["schema_path"])}
    with pytest.raises(ValueError, match="new"):
        report.write_report([selected], output)
    assert {p: p.read_bytes() for p in before} == before
    if alias == "existing_output":
        assert output.read_bytes() == b"prior report"


def test_captured_authority_name_protected_even_when_absent(selected, supplied):
    source = supplied["schema_path"]
    source.rename(source.with_suffix(".retained"))
    with pytest.raises(ValueError, match="authority"):
        report.write_report([selected], source)
    assert not source.exists()


def test_failed_second_input_publishes_nothing(selected, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_bytes(b'{"passed":true}')
    output = tmp_path / "report.json"
    with pytest.raises(ValueError):
        report.write_report([selected, bad], output)
    assert not output.exists()


def test_output_race_preserves_winning_file(selected, tmp_path, monkeypatch):
    output = tmp_path / "report.json"
    original = os.link
    def race(source, target):
        Path(target).write_bytes(b"concurrent writer")
        return original(source, target)
    monkeypatch.setattr(report.os, "link", race)
    with pytest.raises(FileExistsError):
        report.write_report([selected], output)
    assert output.read_bytes() == b"concurrent writer"
    assert not list(tmp_path.glob(".typed-audit-report-*"))


def test_failed_flush_leaves_no_completed_destination(selected, tmp_path, monkeypatch):
    output = tmp_path / "report.json"
    def fail(_):
        raise OSError("injected fsync failure")
    monkeypatch.setattr(report.os, "fsync", fail)
    with pytest.raises(OSError, match="injected"):
        report.write_report([selected], output)
    assert not output.exists()
    assert not list(tmp_path.glob(".typed-audit-report-*"))


@pytest.mark.parametrize("format", ["json", "csv"])
def test_actual_cli_outputs_and_refuses_existing_destination(selected, tmp_path, format):
    output = tmp_path / ("report." + format)
    command = [sys.executable, "-m", "data_sheets_schema.typed_audit_report", "--assembly", str(selected),
               "--format", format, "--output", str(output)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    raw = output.read_bytes()
    if format == "json":
        assert json.loads(raw)["assemblies"][0]["counts"]["candidates"] == 3
    else:
        assert len(list(csv.DictReader(io.StringIO(raw.decode())))) == 6
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2 and "destination must be new" in second.stderr
    assert output.read_bytes() == raw


def test_explicit_selection_and_resource_bounds(packet, monkeypatch):
    with pytest.raises(ValueError, match="at least one"):
        report.build_report([])
    raw = encoded(packet, 0)
    monkeypatch.setattr(report, "MAX_SELECTED_BYTES", len(raw) - 1)
    with pytest.raises(ValueError, match="bound"):
        report.build_report([("selected", raw)])
    monkeypatch.setattr(report, "MAX_SELECTED_BYTES", len(raw) * 3)
    monkeypatch.setattr(report, "MAX_ASSEMBLIES", 1)
    with pytest.raises(ValueError, match="too many"):
        report.build_report([("one", raw), ("two", raw)])
