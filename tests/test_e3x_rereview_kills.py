"""E3x re-review (2026-10-29): one targeted input per new guard that no shipped test kills.

Purpose: show the six surviving new guards fire on 9f6d1583f (these are the missing tests).
Inputs: the 9f6d1583f tree on PYTHONPATH; repository fixtures and evaluator mock.
Outputs: pass/fail only. No provider call.
"""
import hashlib
import json
import shutil

import pytest
import yaml

from tests.test_audit_evaluation_comparability import (  # noqa: F401  (fixtures)
    audit, isolated_execution_locks, no_network, no_unmocked_runtime,
    registered_audit, registered_case, registered_generation_inputs, registered_prepared,
    registered_problem, rewrite_plan, save, anchor_synthetic_receipt,
)
from tests import test_registered_eval_runner as support


def test_kill_N6_extra_file_in_validated_rating_directory(registered_case):
    _, output, _ = registered_case
    (output / "rating-001" / "notes.txt").write_text("added after execution")
    assert registered_problem(registered_audit(registered_case)) == ["registered_attempt_files_mismatch"]


def test_kill_N6b_extra_file_in_failed_attempt_directory(registered_case):
    _, output, _ = registered_case
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt.update(status="incomplete", ratings=receipt["ratings"][:1], attempts=receipt["attempts"][:2])
    receipt["attempts"][1].update(status="failed", exit_code=1, files=["stderr.txt", "transcript.jsonl"])
    save(output / "receipt.json", receipt)
    shutil.rmtree(output / "rating-003")
    (output / "rating-002" / "evaluation.json").unlink()
    (output / "rating-002" / "notes.txt").write_text("added after execution")
    anchor_synthetic_receipt(output)
    assert registered_problem(registered_audit(registered_case)) == ["registered_attempt_files_mismatch"]


def test_kill_N10_dumper_class_drift_is_named(registered_case):
    _, output, _ = registered_case
    rewrite_plan(output, lambda plan: plan["blinding"].update(dumper_class="yaml.cyaml.CSafeDumper"))
    assert registered_problem(registered_audit(registered_case)) == ["registered_yaml_dumper_class_mismatch"]


def test_kill_N24_unknown_receipt_format(registered_case):
    _, output, _ = registered_case
    receipt = json.loads((output / "receipt.json").read_bytes())
    receipt["format"] = "registered_evaluation_receipt_v99"
    save(output / "receipt.json", receipt)
    assert registered_problem(registered_audit(registered_case)) == ["registered_receipt_format_unsupported"]


def test_kill_N18_campaign_refuses_declared_method_token(tmp_path):
    from tests.test_blind_review_pack import campaign, build
    records = campaign(tmp_path)
    record = records[0]
    raw = record.source_path.read_bytes() + b"description: produced by claudecode_api\n"
    record.source_path.write_bytes(raw)
    provenance = (record.source_path.parent.parent.parent / "claudecode_api_core" /
                  record.label / (record.project + "_provenance.yaml"))
    doc = yaml.safe_load(provenance.read_bytes())
    doc["validation"]["artifacts"]["full"]["sha256"] = hashlib.sha256(raw).hexdigest()
    provenance.write_text(yaml.safe_dump(doc))
    with pytest.raises(ValueError, match="^generation identity remains in reviewer content; explicit blinding review required$"):
        build(tmp_path, records, cohort="campaign")


def test_kill_N19_input_arm_header_does_not_refuse_scientific_mention(registered_generation_inputs, tmp_path):
    raw = (b"# Arm: BASELINE (input documents only)\n"
           b"id: example:data\ndescription: 'BASELINE (input documents only) analysis is scientific content.'\n")
    inputs = support.rebind_record(dict(registered_generation_inputs), tmp_path, raw)
    prepared = support.runner.prepare(**inputs)
    assert b"BASELINE (input documents only) analysis" in prepared.blinded
