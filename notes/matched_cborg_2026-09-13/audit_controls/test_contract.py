"""Adversarial exact-file and once-only checks for the Phase 3 continuation."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sys

import pytest

from data_sheets_schema import api_runner, chunking, source_review
from . import contract


def audit_fixture(tmp_path):
    """Actual renderer-14 synthetic example, no provider or semantic mock."""
    example = api_runner.AUDIT_RECORD_CONTRACT_V14.split("### Synthetic audit namespace example\n\n", 1)[1]
    raw = re.search(r"```yaml\n(.*?)```", example, re.S).group(1)
    audit = json.loads(re.search(r"```json\n(.*?)```", example, re.S).group(1))
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    contents = {
        "original_full": raw, "original_core": raw,
        "bundle": "FILE: protocol.txt\nPATH: protocol.txt\nThe service is planned.\n",
        "source_manifest": "projects: {}\n", "full_schema": "name: test_full\n",
        "core_schema": "name: test_core\n", "receipt": "chunks: []\n",
        "parent_instruction": "Parent fixture instruction.\n", "protocol": "Evidence protocol v3\n",
    }
    paths = {}
    for name, text in contents.items():
        paths[name] = inputs_dir / (name + ".txt")
        paths[name].write_text(text)
    paths["chunk_manifest"] = inputs_dir / "chunks.yaml"
    paths["chunk_manifest"].write_text(chunking.dump_manifest(chunking.build_manifest(paths["bundle"])))
    paths["source_inventory"] = inputs_dir / "inventory.json"
    paths["source_inventory"].write_text(json.dumps(source_review.inventory(raw, "original_full")))
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    output = attempt / "output"
    output.mkdir()
    target = output / "audit.json"
    target.write_text(json.dumps(audit))
    manifest = {
        "protocol_version": 3, "render_version": 14, "profile": "neutral",
        "inputs": {k: str(v) for k, v in paths.items()},
        "pinned_files": {str(v): hashlib.sha256(v.read_bytes()).hexdigest() for v in paths.values()},
        "job": {"id": "EXAMPLE_audit", "attempt_dir": str(attempt), "output_dir": str(output),
                "audit_path": str(target)},
    }
    return manifest, audit


def write_audit(manifest, audit):
    Path(manifest["job"]["audit_path"]).write_text(json.dumps(audit))


def test_actual_contract_passes_without_mutating_any_file(tmp_path):
    manifest, _ = audit_fixture(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = contract.validate_audit(manifest)
    assert result["passed"] and result["checked"]
    assert result["evidence"]["assertions_checked"] == 2
    assert result["evidence"]["source_review_original"]["values_required"] == 1
    assert result["audit_sha256"] == hashlib.sha256(Path(manifest["job"]["audit_path"]).read_bytes()).hexdigest()
    assert before == {p: p.read_bytes() for p in before}
    assert not (Path(manifest["job"]["attempt_dir"]) / "validation.json").exists()


@pytest.mark.parametrize("raw", [
    "null", "[]", '"text"', '{"findings":[],"findings":[],"summary":"x"}',
    '{"findings":[],"summary":"x","extra":{"x":1,"x":2}}',
    '{"findings":[],"summary":"x","extra":NaN}',
    '{"findings":[],"summary":"x","extra":Infinity}',
    '{"findings":[],"summary":"x","extra":-Infinity}',
    '{"findings":[],"summary":"x","extra":1e999}',
    '{"findings":[],"summary":"\\ud800"}',
    '{"findings":[]}', '{"findings":[],"summary":{}}', '{"findings":[],"summary":" "}',
    '{"findings":[]', '{"findings":[]} trailing',
])
def test_malformed_audit_is_rejected_and_preserved(tmp_path, raw):
    manifest, _ = audit_fixture(tmp_path)
    path = Path(manifest["job"]["audit_path"])
    path.write_text(raw)
    result = contract.validate_audit(manifest)
    assert not result["passed"] and result["errors"]
    assert path.read_text() == raw


@pytest.mark.parametrize("damage", ["artifact_namespace", "empty_evidence", "false_quote", "wrong_artifact_hash",
                                   "missing_value", "wrong_inventory_role", "status_strengthening", "core_false_quote"])
def test_real_evidence_checker_rejects_unusable_audits(tmp_path, damage):
    manifest, audit = audit_fixture(tmp_path)
    if damage == "artifact_namespace":
        audit["findings"][0]["record"] = "original_full"
    elif damage == "empty_evidence":
        audit["findings"][0]["evidence"] = []
    elif damage == "false_quote":
        audit["findings"][0]["evidence"][1]["quote"] = "The service is already deployed."
    elif damage == "wrong_artifact_hash":
        audit["source_review"]["sha256"] = "0" * 64
    elif damage == "missing_value":
        audit["source_review"]["values"] = []
    elif damage == "wrong_inventory_role":
        audit["source_review"]["artifact"] = "final_full"
    elif damage == "status_strengthening":
        audit["source_review"]["values"][0]["claims"][0].update(verdict="supported", source_status="planned")
    else:
        audit["findings"][0]["record"] = "core"
        audit["findings"][0]["evidence"][0].update(artifact="original_core", quote="An unavailable core claim.")
    write_audit(manifest, audit)
    result = contract.validate_audit(manifest)
    assert not result["passed"]
    assert result["findings"] or result["errors"]


@pytest.mark.parametrize("role", sorted(contract.INPUTS))
def test_every_registered_input_pin_is_enforced(tmp_path, role):
    manifest, _ = audit_fixture(tmp_path)
    path = Path(manifest["inputs"][role])
    path.write_bytes(path.read_bytes() + b"\n")
    result = contract.validate_audit(manifest)
    assert not result["passed"]
    assert any("bytes changed or are not pinned" in error for error in result["errors"])


@pytest.mark.parametrize("change", ["hash", "path", "text", "typed_flag", "extra"])
def test_inventory_must_equal_recomputed_original_not_merely_a_pinned_file(tmp_path, change):
    manifest, _ = audit_fixture(tmp_path)
    path = Path(manifest["inputs"]["source_inventory"])
    inventory = json.loads(path.read_text())
    if change == "hash": inventory["sha256"] = "0" * 64
    elif change == "path": inventory["values"][0]["path"] = "/absent"
    elif change == "text": inventory["values"][0]["text"] = "Another record"
    elif change == "typed_flag": inventory["values"][0]["whole_value_required"] = 0
    else: inventory["extra"] = "not an inventory field"
    path.write_text(json.dumps(inventory))
    manifest["pinned_files"][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = contract.validate_audit(manifest)
    assert not result["passed"]
    assert any("inventory differs" in error for error in result["errors"])


@pytest.mark.parametrize("which", ["audit", "original_full", "original_core", "bundle"])
def test_midcheck_changes_cannot_receive_success(tmp_path, monkeypatch, which):
    manifest, _ = audit_fixture(tmp_path)
    original = contract.evidence_assertions.check_files
    target = Path(manifest["job"]["audit_path"] if which == "audit" else manifest["inputs"][which])
    def changing(**kwargs):
        result = original(**kwargs)
        target.write_bytes(target.read_bytes() + b"\n")
        return result
    monkeypatch.setattr(contract.evidence_assertions, "check_files", changing)
    result = contract.validate_audit(manifest)
    assert not result["passed"]
    assert any("changed during validation" in error for error in result["errors"])


@pytest.mark.parametrize("kind", ["hardlink", "symlink", "outside_output", "input_alias"])
def test_audit_cannot_alias_or_escape_its_exclusive_output(tmp_path, kind):
    manifest, _ = audit_fixture(tmp_path)
    target = Path(manifest["job"]["audit_path"])
    if kind == "hardlink":
        (tmp_path / "other.json").hardlink_to(target)
    elif kind == "symlink":
        other = tmp_path / "other.json"
        target.rename(other)
        target.symlink_to(other)
    elif kind == "outside_output":
        other = tmp_path / "other.json"
        target.rename(other)
        manifest["job"]["audit_path"] = str(other)
    else:
        manifest["inputs"]["receipt"] = str(target)
        manifest["pinned_files"][str(target)] = hashlib.sha256(target.read_bytes()).hexdigest()
    result = contract.validate_audit(manifest)
    assert not result["passed"] and result["errors"]


def test_duplicate_original_yaml_cannot_be_admitted_by_updating_its_pin(tmp_path):
    manifest, _ = audit_fixture(tmp_path)
    target = Path(manifest["inputs"]["original_core"])
    target.write_text("description: first\ndescription: second\n")
    manifest["pinned_files"][str(target)] = hashlib.sha256(target.read_bytes()).hexdigest()
    result = contract.validate_audit(manifest)
    assert not result["passed"] and result["errors"]


def cli_fixture(tmp_path, monkeypatch):
    manifest, audit = audit_fixture(tmp_path)
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(json.dumps(manifest))
    # Registration admission has its own tests; this lane executes the actual
    # evidence checker and CLI receipt machinery with an admitted fixture.
    from . import registration
    monkeypatch.setattr(registration, "validate_registration", lambda path: json.loads(Path(path).read_bytes()))
    return manifest, audit, registration_path


def test_cli_success_receipt_matches_stdout_and_pure_recheck_does_not_write(tmp_path, monkeypatch, capsys):
    manifest, _, path = cli_fixture(tmp_path, monkeypatch)
    assert contract.main(["--registration", str(path)]) == 0
    printed = capsys.readouterr().out
    receipt = Path(manifest["job"]["attempt_dir"]) / "validation.json"
    assert receipt.read_text() == printed
    record = json.loads(printed)
    assert record["passed"] is True and record["job_id"] == manifest["job"]["id"]
    assert record["registration_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert not receipt.with_name("validation_failure.json").exists()
    before = receipt.read_bytes()
    assert contract.validate_audit(manifest)["passed"]
    assert receipt.read_bytes() == before


@pytest.mark.parametrize("failure", ["audit", "registration_exception", "checker_exception"])
def test_failed_check_writes_terminal_failure_and_identical_stdout(tmp_path, monkeypatch, capsys, failure):
    manifest, audit, path = cli_fixture(tmp_path, monkeypatch)
    if failure == "audit":
        audit["findings"][0]["record"] = "original_full"
        write_audit(manifest, audit)
    elif failure == "registration_exception":
        from . import registration
        monkeypatch.setattr(registration, "validate_registration", lambda path: (_ for _ in ()).throw(ValueError("changed pin")))
    else:
        monkeypatch.setattr(contract.evidence_assertions, "check_files", lambda **kw: (_ for _ in ()).throw(RuntimeError("checker failed")))
    assert contract.main(["--registration", str(path)]) == 1
    printed = capsys.readouterr().out
    attempt = Path(manifest["job"]["attempt_dir"])
    assert (attempt / "validation.json").read_text() == printed
    assert (attempt / "validation_failure.json").read_text() == printed
    result = json.loads(printed)
    assert result["passed"] is False and result["audit_sha256"]


def test_second_cli_invocation_cannot_replace_success_and_records_terminal_failure(tmp_path, monkeypatch, capsys):
    manifest, _, path = cli_fixture(tmp_path, monkeypatch)
    assert contract.main(["--registration", str(path)]) == 0
    capsys.readouterr()
    attempt = Path(manifest["job"]["attempt_dir"])
    original = (attempt / "validation.json").read_bytes()
    assert contract.main(["--registration", str(path)]) == 1
    assert (attempt / "validation.json").read_bytes() == original
    assert json.loads((attempt / "validation_failure.json").read_bytes())["passed"] is False


def test_interrupted_claim_remains_once_only(tmp_path, monkeypatch, capsys):
    manifest, _, path = cli_fixture(tmp_path, monkeypatch)
    receipt = Path(manifest["job"]["attempt_dir"]) / "validation.json"
    receipt.write_bytes(b"")
    assert contract.main(["--registration", str(path)]) == 1
    assert receipt.read_bytes() == b""
    assert receipt.with_name("validation_failure.json").exists()


def test_receipts_cannot_be_placed_inside_model_write_directory(tmp_path, monkeypatch, capsys):
    manifest, _, path = cli_fixture(tmp_path, monkeypatch)
    manifest["job"]["attempt_dir"] = manifest["job"]["output_dir"]
    path.write_text(json.dumps(manifest))
    assert contract.main(["--registration", str(path)]) == 1
    assert not (Path(manifest["job"]["output_dir"]) / "validation.json").exists()


def rendered_fixture(tmp_path):
    from tests.test_evidence_generation_gate import specification
    manifest, audit = audit_fixture(tmp_path)
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    spec = replace(specification(parent_dir, "Claude Code"), condition="generic_v9", render_version=14)
    instruction = parent_dir / "instruction.md"
    instruction.write_bytes(spec.instruction.encode())
    parent_path = parent_dir / "registration.json"
    parent_job = {"id": "EXAMPLE_parent", "project": spec.project, "method": spec.method,
                  "label": spec.label, "render_spec": spec.render_spec(), "instruction": str(instruction)}
    parent_path.write_text(json.dumps({"repository": str(Path.cwd()), "generation": {"jobs": [parent_job]}}))
    manifest["parent"] = {"registration": str(parent_path), "repository": str(Path.cwd()), "job_id": "EXAMPLE_parent"}
    manifest["inputs"]["parent_instruction"] = str(instruction)
    manifest["inputs"]["bundle"] = str(spec.bundle)
    manifest["inputs"]["chunk_manifest"] = str(spec.chunk_manifest)
    manifest["job"]["validator_argv"] = [sys.executable, "-m", "audit_controls.contract", "--registration", str(tmp_path / "registration.json")]
    return manifest, spec


def test_renderer_replays_parent_and_embeds_actual_full_core_sources_inventory(tmp_path):
    manifest, spec = rendered_fixture(tmp_path)
    before = Path.cwd()
    text = contract.render_instruction(manifest)
    assert Path.cwd() == before
    assert text == contract.render_instruction(copy.deepcopy(manifest))
    assert spec.instruction in text
    assert api_runner.phase_instruction("audit", 14) in text
    assert api_runner.AUDIT_RECORD_CONTRACT_V14 in text
    assert "# Completed full record" in text and "# Completed core record" in text
    assert "A sample dataset is planned." in text
    assert "# Required source-review inventory" in text
    final = text.split("## Current Phase 3 execution instructions\n\n", 1)[1]
    assert "Do not begin Phase 4" in final
    assert manifest["job"]["audit_path"] in final
    assert "audit_controls.contract" in final
    assert "invoke this exact validator once" in final


def test_renderer_rejects_changed_parent_instruction_and_restores_cwd(tmp_path):
    manifest, _ = rendered_fixture(tmp_path)
    path = Path(manifest["inputs"]["parent_instruction"])
    path.write_text(path.read_text() + "Changed")
    before = Path.cwd()
    with pytest.raises(ValueError, match="does not replay exactly"):
        contract.render_instruction(manifest)
    assert Path.cwd() == before


def test_renderer_rejects_different_source_bytes(tmp_path):
    manifest, _ = rendered_fixture(tmp_path)
    other = tmp_path / "other_bundle.txt"
    other.write_text("Different sources")
    manifest["inputs"]["bundle"] = str(other)
    with pytest.raises(ValueError, match="differs from the parent source bytes"):
        contract.render_instruction(manifest)
