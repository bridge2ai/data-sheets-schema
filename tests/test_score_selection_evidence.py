"""Synthetic receipt/publication joins for issue 6385; no scorer calls."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema.score_selection import build_evidence_table


INSTRUMENT = "synthetic-instrument"
LABEL = "configuration_rep1"
PROJECT = "Example"
METHOD = "synthetic"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return sha(raw)


def scenario(tmp_path):
    corpus = tmp_path / "corpus"
    metadata_root = tmp_path / "receipts"
    record = corpus / "data/d4d_concatenated" / METHOD / LABEL / (PROJECT + "_d4d.yaml")
    record.parent.mkdir(parents=True)
    record.write_text("id: example:record\ntitle: Synthetic\n")
    entries = {}
    for family, maximum in (("rubric10", 50), ("rubric20", 88)):
        for number in (1, 2, 3):
            run = metadata_root / (family + "-" + str(number))
            directory = (corpus / "data/evaluation_llm" / (family + "_semantic") / "label_aware" / INSTRUMENT
                         if number == 1 else corpus / "data/evaluation_repeats" / INSTRUMENT /
                         ("scoring_rep" + str(number)) / (family + "_semantic"))
            output = directory / (PROJECT + "_" + LABEL + "_evaluation.json")
            identity = {"rubric": family + "-semantic", "version": "6.0", "project": PROJECT,
                        "method": METHOD, "label": LABEL, "instrument_id": INSTRUMENT,
                        "d4d_file": str(record.relative_to(corpus))}
            inputs = {name: {"sha256": sha((family + name).encode())} for name in
                      ("agent-definition.md", "output-schema.json", "evidence-authority.json", "rubric.txt")}
            inputs.update({"record.yaml": {"sha256": sha(record.read_bytes())},
                           "scope-context.json": {"sha256": sha(b"scope")}})
            metadata = {"input_sha256": inputs["record.yaml"]["sha256"],
                        "context_sha256": sha(b"context"),
                        "scope_context_sha256": inputs["scope-context.json"]["sha256"],
                        "rubric_sha256": inputs["rubric.txt"]["sha256"],
                        "instrument_sha256": inputs["agent-definition.md"]["sha256"],
                        "evidence_authority_sha256": inputs["evidence-authority.json"]["sha256"]}
            deterministic = {"metadata": metadata, "evaluation_scope": {"policy": "single_dataset"},
                             "applicability_context": {}}
            plan = {"instrument": INSTRUMENT, "identity": identity, "inputs": inputs,
                    "run_directory": str(run), "output": str(output), "prompt": family,
                    "prompt_sha256": sha(family.encode()), "runner_sha256": sha(b"runner"),
                    "definition_provenance": {"composed_sha256": metadata["instrument_sha256"]},
                    "deterministic_fields": deterministic}
            publication = {**{k: v for k, v in identity.items() if k != "instrument_id"},
                           **deterministic,
                           "scorer_instrument": {"id": INSTRUMENT, "prompt_sha256": plan["prompt_sha256"],
                                                 "runner_sha256": plan["runner_sha256"]},
                           "overall_score": {"total_points": 20 + number, "adjusted_max_points": maximum}}
            output_sha = write(output, publication)
            plan_sha = write(run / "plan.json", plan)
            receipt = {"status": "VALIDATED_AND_PUBLISHED", "plan_sha256": sha(json.dumps(plan, sort_keys=True).encode()),
                       "codex_exit": 0, "validator_exit": 0, "auth_copy_absent": True,
                       "output": str(output), "output_sha256": output_sha, "validator_input_sha256": output_sha}
            receipt_sha = write(run / "receipt.json", receipt)
            entry = {"plan": plan, "receipt": receipt, "publication": publication, "output": output,
                     "plan_path": run / "plan.json", "receipt_path": run / "receipt.json"}
            if number > 1:
                manifest_path = metadata_root / "export-manifests" / run.name / "manifest.json"
                manifest = {"status": "EXPORTED_VALIDATED_REPEAT", "identity": identity,
                            "scoring_replicate": number, "generation_replicate": 1,
                            "actual_plan": str(run / "plan.json"), "actual_plan_sha256": plan_sha,
                            "actual_receipt": str(run / "receipt.json"), "actual_receipt_sha256": receipt_sha,
                            "destination": str(output), "destination_sha256": output_sha,
                            "source_output_sha256": output_sha, "copy_validator_exit": 0}
                write(manifest_path, manifest)
                entry.update(manifest=manifest, manifest_path=manifest_path)
            entries[family, number] = entry
    candidates = [{"label": LABEL, "record": record, "validity": "valid", "slots": 2}]
    return corpus, metadata_root, candidates, entries


def table(case, roots=True):
    corpus, receipts, candidates, _entries = case
    return build_evidence_table(PROJECT, "configuration", INSTRUMENT, candidates=candidates,
                                corpus_root=corpus, evidence_roots=[receipts] if roots else [])


def cell(rows, family="rubric10", number=1):
    return rows[0]["rubrics"][family]["scorings"][number - 1]


def rebind(entry):
    """Bind deliberate synthetic modifications consistently for mutation tests."""
    plan_sha = write(entry["plan_path"], entry["plan"])
    receipt = entry["receipt"]
    receipt["plan_sha256"] = sha(json.dumps(entry["plan"], sort_keys=True).encode())
    output_sha = write(entry["output"], entry["publication"])
    receipt.update(output_sha256=output_sha, validator_input_sha256=output_sha)
    receipt_sha = write(entry["receipt_path"], receipt)
    if "manifest" in entry:
        entry["manifest"].update(actual_plan_sha256=plan_sha, actual_receipt_sha256=receipt_sha,
                                 destination_sha256=output_sha, source_output_sha256=output_sha)
        write(entry["manifest_path"], entry["manifest"])


def test_three_scorings_each_rubric_with_identical_measured_inputs(tmp_path):
    case = scenario(tmp_path)
    rows = table(case)
    assert len(rows) == 1
    assert rows[0]["paired"]["count"] == 3
    assert rows[0]["problems"] == []
    for family in ("rubric10", "rubric20"):
        evidence = rows[0]["rubrics"][family]
        assert evidence["count"] == 3 and evidence["spread"] > 0
        assert all(item["attempt"] == 1 for item in evidence["scorings"])
        assert len({item["measurement_identity"]["schema_sha256"] for item in evidence["scorings"]}) == 1
    assert rows[0]["receipt_coverage"] is None
    assert rows[0]["presence_evaluation"] is None
    assert rows[0]["review_verdict_counts"] is None


def test_published_scores_without_receipts_are_not_measurements(tmp_path):
    rows = table(scenario(tmp_path), roots=False)
    assert rows[0]["paired"]["mean"] is None
    assert all(item["points"] is None for family in ("rubric10", "rubric20")
               for item in rows[0]["rubrics"][family]["scorings"])


def test_missing_scoring_remains_explicit_not_zero(tmp_path):
    case = scenario(tmp_path)
    case[3]["rubric10", 3]["output"].unlink()
    row = table(case)
    assert cell(row, number=3)["status"] == "not measured"
    assert cell(row, number=3)["points"] is None
    assert row[0]["paired_numbers"] == [1, 2]


def test_other_instrument_and_changed_record_are_not_mixed(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 2]
    entry["plan"]["instrument"] = "another-instrument"
    entry["plan"]["identity"]["instrument_id"] = "another-instrument"
    rebind(entry)
    assert cell(table(case), number=2)["status"] == "not measured"
    case[2][0]["record"].write_text("id: example:changed\n")
    assert cell(table(case))["status"] == "not measured"
    assert "changed record" in cell(table(case))["reason"]


def test_schema_or_measured_input_drift_invalidates_repeated_mean(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 3]
    entry["plan"]["inputs"]["output-schema.json"]["sha256"] = sha(b"different schema")
    rebind(entry)
    rows = table(case)
    assert rows[0]["rubrics"]["rubric10"]["mean"] is None
    assert any("measured inputs differ" in problem for problem in rows[0]["problems"])


def test_refused_scoring_never_opens_its_published_or_raw_output(tmp_path, monkeypatch):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 3]
    entry["receipt"].update(status="REFUSED", failure="synthetic refusal")
    rebind(entry)
    original = Path.read_bytes
    def guarded(path):
        if path == entry["output"] or path.name in ("candidate_evaluation.json", "raw-response.json"):
            raise AssertionError("refused output was opened")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert cell(table(case), number=3)["status"] == "not measured"


def test_replacement_is_one_scoring_and_keeps_refused_receipt_provenance(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric20", 3]
    refused_path = case[1] / "refused-rubric20-3"
    old_plan = copy.deepcopy(entry["plan"])
    old_plan["run_directory"] = str(refused_path)
    old_plan_sha = write(refused_path / "plan.json", old_plan)
    refused = {"status": "REFUSED", "failure": "synthetic non-score refusal",
               "plan_sha256": sha(json.dumps(old_plan, sort_keys=True).encode())}
    refused_sha = write(refused_path / "receipt.json", refused)
    entry["manifest"].update(attempt=2, refused_attempt_receipt={"path": str(refused_path / "receipt.json"),
                                                             "sha256": refused_sha},
                             refused_attempt_plan={"path": str(refused_path / "plan.json"), "sha256": old_plan_sha})
    write(entry["manifest_path"], entry["manifest"])
    rows = table(case)
    assert rows[0]["rubrics"]["rubric20"]["count"] == 3
    replaced = cell(rows, "rubric20", 3)
    assert replaced["attempt"] == 2
    assert replaced["refused_attempt"]["sha256"] == refused_sha
    assert replaced["refused_attempt"]["reason"] == "synthetic non-score refusal"
    assert rows[0]["paired_numbers"] == [1, 2, 3]
    old_plan["inputs"]["output-schema.json"]["sha256"] = sha(b"different refused schema")
    old_plan_sha = write(refused_path / "plan.json", old_plan)
    refused["plan_sha256"] = sha(json.dumps(old_plan, sort_keys=True).encode())
    refused_sha = write(refused_path / "receipt.json", refused)
    entry["manifest"]["refused_attempt_plan"]["sha256"] = old_plan_sha
    entry["manifest"]["refused_attempt_receipt"]["sha256"] = refused_sha
    write(entry["manifest_path"], entry["manifest"])
    assert cell(table(case), "rubric20", 3)["status"] == "not measured"
    assert "refused measured inputs" in cell(table(case), "rubric20", 3)["reason"]


def test_changed_receipt_or_publication_is_not_a_measurement(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 2]
    entry["output"].write_text("{}\n")
    assert cell(table(case), number=2)["status"] == "not measured"
    entry = case[3]["rubric20", 2]
    entry["receipt"]["auth_copy_absent"] = False
    write(entry["receipt_path"], entry["receipt"])
    assert cell(table(case), "rubric20", 2)["status"] == "not measured"


def test_duplicate_export_is_reported_not_counted_twice(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 3]
    write(case[1] / "export-manifests/duplicate/manifest.json", entry["manifest"])
    assert cell(table(case), number=3)["status"] == "not measured"
    assert "ambiguous" in cell(table(case), number=3)["reason"]


def test_missing_schema_binding_cannot_be_supplied_by_published_metadata(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric10", 2]
    del entry["plan"]["inputs"]["output-schema.json"]
    rebind(entry)
    assert cell(table(case), number=2)["status"] == "not measured"


def test_unrelated_malformed_presence_is_not_measured_without_hiding_scores(tmp_path):
    case = scenario(tmp_path)
    broken = case[0] / "data/evaluation/unrelated/scores.json"
    broken.parent.mkdir(parents=True)
    broken.write_text("{broken\n")
    rows = table(case)
    assert rows[0]["presence_evaluation"] is None
    assert rows[0]["paired"]["count"] == 3


def test_missing_record_has_no_zero_coverage_and_malformed_cell_is_missing(tmp_path):
    case = scenario(tmp_path)
    entry = case[3]["rubric20", 2]
    entry["plan"]["inputs"] = []
    rebind(entry)
    assert cell(table(case), "rubric20", 2)["status"] == "not measured"
    case[2][0]["record"].unlink()
    case[2][0]["slots"] = 0
    rows = table(case)
    assert rows[0]["slots"] is None
    assert rows[0]["paired"]["mean"] is None


def test_optional_columns_require_checked_or_record_bound_evidence(tmp_path):
    case = scenario(tmp_path)
    corpus, _receipts, candidates, _entries = case
    record_sha = sha(candidates[0]["record"].read_bytes())
    provenance_path = (corpus / "data/d4d_concatenated" / (METHOD + "_core") /
                       LABEL / (PROJECT + "_provenance.yaml"))
    slots = {"with_receipt": 1, "receiptable": 2}
    verdicts = {"slot_receipted": {"supported": 1, "weak": 1}}
    provenance = {"receipts": {"checked": True, "slots": slots},
                  "review": {"checked": True, "adverse": 1, "by_kind": verdicts,
                             "findings": [], "unanswered": [], "unanswered_truncated": None}}
    # JSON is a YAML subset and retains the exact synthetic provenance shape.
    write(provenance_path, provenance)
    presence_path = corpus / "data/evaluation/synthetic-presence/scores.json"
    presence = {"project": PROJECT, "method": METHOD, "label": LABEL,
                "instrument": {"kind": "deterministic_presence", "input_sha256": record_sha},
                "rubric10": {"total": 2, "max": 4, "percentage": 50},
                "rubric20": {"total": 1, "max": 4, "percentage": 25}}
    write(presence_path, [presence])
    row = table(case)[0]
    assert row["receipt_coverage"] == slots
    assert row["review_verdict_counts"] == verdicts
    assert len(row["presence_evaluation"]) == 1
    assert row["presence_evaluation"][0]["rubric10"] == presence["rubric10"]
    assert row["presence_evaluation"][0]["rubric20"] == presence["rubric20"]
    assert row["presence_evaluation"][0]["instrument"]["input_sha256"] == record_sha

    provenance["receipts"]["checked"] = False
    provenance["review"]["checked"] = False
    write(provenance_path, provenance)
    del presence["instrument"]["input_sha256"]
    write(presence_path, [presence])
    row = table(case)[0]
    assert row["receipt_coverage"] is None
    assert row["review_verdict_counts"] is None
    assert row["presence_evaluation"] is None
    assert row["paired"]["count"] == 3
