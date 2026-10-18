"""Offline SourceID/filename confusion, with the terminal contract unchanged."""
import copy
import hashlib
import json
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import chunking, evidence_assertions as evidence, source_review
from data_sheets_schema import source_attribution_preflight as preflight
from data_sheets_schema.cli.review import review as review_cli


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def report(review):
    payload = {"claims": [], "source_review": review}
    return ("# Reconciliation draft\n\n## Evidence assertions\n```json\n"
            + json.dumps(payload, ensure_ascii=False) + "\n```\n").encode()


@pytest.fixture
def inputs():
    bundle = (b"FILE: protocol.txt\nPATH: protocol.txt\nThe deployment is planned.\n"
              b"FILE: overview.txt\nPATH: overview.txt\nThe overview describes the study.\n")
    manifest = yaml.safe_dump(chunking.manifest_from_bytes(bundle, "bundle.txt")).encode()
    chunks, _ = evidence.source_chunks_from_bytes(bundle, manifest)
    chunk = next(k for k, v in chunks.items() if v["source"] == "protocol.txt")
    record = b"description: The deployment is planned.\n"
    claim = {"text": "The deployment is planned.", "verdict": "supported",
             "attributed_to": ["protocol.txt"], "claim_status": "planned", "source_status": "planned",
             "evidence": [{"source": "protocol.txt", "chunk": chunk, "quote": "The deployment is planned."}],
             "reason": "The named document describes the deployment as planned."}
    review = {"artifact": "final_full", "sha256": sha(record),
              "values": [{"path": "/description", "claims": [claim]}]}
    sources = yaml.safe_dump({"projects": {"EXAMPLE": {"sources": [
        {"id": "project_documentation", "processed_file": "protocol.txt", "source_type": "documentation"},
        {"id": "overview_id", "processed_file": "overview.txt", "source_type": "documentation"},
        {"id": "external_id", "processed_file": "outside.txt", "source_type": "documentation"},
    ]}}}).encode()
    return {"report_raw": report(review), "record_raw": record, "bundle_raw": bundle,
            "chunk_manifest_raw": manifest, "source_manifest_raw": sources,
            "project": "EXAMPLE", "protocol_version": 5}


def edited(inputs, mutate):
    out = dict(inputs)
    review = evidence.report_payload(inputs["report_raw"].decode(), protocol_version=5)["source_review"]
    mutate(review)
    out["report_raw"] = report(review)
    return out


def claim(review):
    return review["values"][0]["claims"][0]


@pytest.mark.parametrize("protocol", [5, 6, 7])
def test_all_confused_claims_are_diagnosed_without_translating(inputs, protocol):
    def confuse(r):
        claim(r)["attributed_to"] = ["project_documentation"]
        r["values"][0]["claims"].append(copy.deepcopy(claim(r)))
    values = edited(inputs, confuse)
    values["protocol_version"] = protocol
    before = copy.deepcopy(values)
    out = preflight.check_bytes(**values)
    assert out["checked"] and not out["passed"] and out["terminal_evidence_required"]
    assert len(out["source_review"]["findings"]) == 1  # Historical row-level behavior.
    assert [d["claim"] for d in out["attribution_diagnostics"]] == [0, 1]
    for d in out["attribution_diagnostics"]:
        assert d["code"] == "source_id_used_as_filename"
        assert d["received"] == "project_documentation" and d["expected"] == "protocol.txt"
        assert d["registered_filename_in_bundle"]
    assert values == before


def test_pass_preserves_terminal_checker_result_and_exact_input_pins(inputs):
    out = preflight.check_bytes(**inputs)
    assert out["checked"] and out["passed"] and out["attribution_diagnostics"] == []
    assert out["expected_filenames"] == ["overview.txt", "protocol.txt"]
    assert "semantic support requires independent review" in out["scope"]
    assert out["input_sha256"] == {name.removesuffix("_raw").replace("record", "final_full"): sha(raw)
                                   for name, raw in inputs.items() if name.endswith("_raw")}
    chunks, _ = evidence.source_chunks_from_bytes(inputs["bundle_raw"], inputs["chunk_manifest_raw"])
    parsed = evidence.report_payload(inputs["report_raw"].decode(), protocol_version=5)["source_review"]
    assert out["source_review"] == source_review.check(parsed, raw=inputs["record_raw"].decode(),
        artifact="final_full", chunks=chunks, protocol_version=5,
        source_manifest_raw=inputs["source_manifest_raw"], project="EXAMPLE")


@pytest.mark.parametrize("protocol", [3, 4, 5, 6, 7])
def test_no_authority_is_discovered_for_document_only_review(inputs, protocol, monkeypatch):
    inputs.pop("source_manifest_raw"); inputs.pop("project"); inputs["protocol_version"] = protocol
    monkeypatch.setattr(Path, "read_bytes", lambda *_: pytest.fail("ambient file read"))
    assert preflight.check_bytes(**inputs)["passed"]
    empty = edited(inputs, lambda r: claim(r).update(attributed_to=[]))
    assert preflight.check_bytes(**empty)["passed"]


@pytest.mark.parametrize("attributed,code", [
    (["not_declared"], "unknown_source_filename"),
    (["<preamble>"], "unknown_source_filename"),
    (["protocol.txt", "protocol.txt"], "duplicate_attribution"),
    ([{"source": "protocol.txt"}], "attribution_filename_required"),
    (None, "attribution_array_required"),
    ("protocol.txt", "attribution_array_required"),
])
def test_bad_attribution_forms_fail_in_both_checks(inputs, attributed, code):
    values = edited(inputs, lambda r: claim(r).update(attributed_to=attributed))
    out = preflight.check_bytes(**values)
    assert not out["passed"] and out["source_review"]["findings"]
    assert code in {d["code"] for d in out["attribution_diagnostics"]}


def test_registered_id_outside_bundle_does_not_suggest_eligible_replacement(inputs):
    values = edited(inputs, lambda r: claim(r).update(attributed_to=["external_id"]))
    out = preflight.check_bytes(**values)
    detail = out["attribution_diagnostics"][0]
    assert detail["registered_filename"] == "outside.txt"
    assert detail["expected"] is None and not detail["registered_filename_in_bundle"]
    assert "outside.txt" not in out["expected_filenames"]


def test_a_real_filename_is_not_reinterpreted_as_an_id(inputs):
    inputs["source_manifest_raw"] = inputs["source_manifest_raw"].replace(b"id: overview_id", b"id: protocol.txt")
    assert preflight.check_bytes(**inputs)["passed"]
    assert preflight.check_bytes(**inputs)["attribution_diagnostics"] == []


def test_provenance_only_attribution_must_stay_empty(inputs):
    def metadata(r):
        c = claim(r)
        c.update(attributed_to=[], claim_status="fact", source_status="fact", evidence=[{
            "provenance": "source_manifest", "sha256": sha(inputs["source_manifest_raw"]),
            "source_id": "project_documentation", "source": "protocol.txt",
            "field": "source_type", "value": "documentation"}])
    valid = edited(inputs, metadata)
    assert preflight.check_bytes(**valid)["passed"]
    bad = edited(valid, lambda r: claim(r).update(attributed_to=["protocol.txt"]))
    out = preflight.check_bytes(**bad)
    assert not out["passed"]
    assert out["attribution_diagnostics"][0]["code"] == "provenance_attribution_must_be_empty"


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(sha256="0" * 64),
    lambda r: r.update(artifact="original_full"),
    lambda r: r.update(values=[]),
    lambda r: claim(r).update(evidence=[]),
    lambda r: claim(r).update(source_status="applied"),
    lambda r: claim(r)["evidence"][0].update(quote="Words not found in this document."),
])
def test_vocabulary_pass_does_not_waive_other_source_review_failures(inputs, mutation):
    out = preflight.check_bytes(**edited(inputs, mutation))
    assert out["checked"] and not out["passed"]
    assert out["source_review"]["findings"]


@pytest.mark.parametrize("payload", [None, [], {}, {"artifact": "final_full", "sha256": "bad", "values": [None]}])
def test_malformed_review_is_a_failed_preflight_not_a_crash(inputs, payload):
    inputs["report_raw"] = report(payload)
    out = preflight.check_bytes(**inputs)
    assert out["checked"] and not out["passed"]


@pytest.mark.parametrize("change", ["bundle", "chunk_duplicate", "json_duplicate", "source_duplicate", "project_missing"])
def test_ambiguous_or_mismatched_inputs_are_refused(inputs, change):
    if change == "bundle": inputs["bundle_raw"] += b"changed\n"
    elif change == "chunk_duplicate": inputs["chunk_manifest_raw"] += b"chunk_count: 1\n"
    elif change == "json_duplicate": inputs["report_raw"] = inputs["report_raw"].replace(b'"claims": []', b'"claims": [], "claims": []', 1)
    elif change == "source_duplicate": inputs["source_manifest_raw"] += b"projects: {}\n"
    else: inputs["project"] = "ABSENT"
    with pytest.raises((ValueError, KeyError)):
        preflight.check_bytes(**inputs)


@pytest.mark.parametrize("protocol", [True, 2, 8, "5"])
def test_explicit_protocol_and_authority_pair_are_required(inputs, protocol):
    inputs["protocol_version"] = protocol
    with pytest.raises(ValueError, match="protocol"):
        preflight.check_bytes(**inputs)


def test_authority_pair_cannot_be_silently_ignored(inputs):
    for absent in ("project", "source_manifest_raw"):
        changed = dict(inputs); changed.pop(absent)
        with pytest.raises(ValueError, match="together"):
            preflight.check_bytes(**changed)
    inputs["protocol_version"] = 3
    with pytest.raises(ValueError, match="protocol 5"):
        preflight.check_bytes(**inputs)


def paths_for(tmp_path, inputs):
    out = {"protocol_version": inputs["protocol_version"], "project": inputs["project"]}
    for name, raw in inputs.items():
        if name.endswith("_raw"):
            p = tmp_path / name
            p.write_bytes(raw)
            out[name.removesuffix("_raw")] = p
    return out


def test_file_checks_read_each_snapshot_once_and_leave_inputs_untouched(tmp_path, inputs, monkeypatch):
    paths = paths_for(tmp_path, inputs)
    before = {p: p.read_bytes() for p in paths.values() if isinstance(p, Path)}
    read = Path.read_bytes; seen = []
    def once(path):
        assert path not in seen
        seen.append(path)
        return read(path)
    monkeypatch.setattr(Path, "read_bytes", once)
    assert preflight.check_files(**paths)["passed"]
    assert set(seen) == set(before)
    assert before == {p: read(p) for p in before}


def test_module_and_click_cli_statuses_and_no_writes(tmp_path, inputs, capsys):
    paths = paths_for(tmp_path, inputs)
    args = [value for k, v in paths.items() for value in ("--" + k.replace("_", "-"), str(v))]
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    assert preflight.main(args) == 0
    assert json.loads(capsys.readouterr().out)["passed"]
    runner = CliRunner()
    result = runner.invoke(review_cli, ["source-attribution-preflight", *args])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["terminal_evidence_required"]
    assert before == {p: p.read_bytes() for p in tmp_path.iterdir()}
    changed = edited(inputs, lambda r: claim(r).update(attributed_to=["project_documentation"]))
    paths["report"].write_bytes(changed["report_raw"])
    result = runner.invoke(review_cli, ["source-attribution-preflight", *args])
    assert result.exit_code == 1
    assert not json.loads(result.output)["passed"]
    paths["record"].unlink()
    result = runner.invoke(review_cli, ["source-attribution-preflight", *args])
    assert result.exit_code == 2
    assert not json.loads(result.output)["checked"]
