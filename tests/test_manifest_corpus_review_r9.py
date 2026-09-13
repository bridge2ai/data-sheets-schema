"""Historical validation writes must retain the discovered artifact identity."""
import hashlib
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import api_runner
from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree


def recorded_pair(root, *, missing_pins=False, passed=True):
    corpus = root / "data/d4d_concatenated"
    full = corpus / "external/run/CLINICAL_X_d4d.yaml"
    core = corpus / "external_core/run/CLINICAL_X_d4d_core.yaml"
    for path in (full, core):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("id: https://example.org/cohort\ntitle: Original cohort\n")
    (core.parent / "CLINICAL_X_reconciliation.md").write_text("Synthetic completed report.\n")
    block = {"passed": passed, "artifacts": {
        name: {"path": str(root / "old-location" / path.name) if missing_pins else str(path),
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for name, path in (("full", full), ("core", core))}}
    record = core.parent / "CLINICAL_X_provenance.yaml"
    record.write_text("# Historical header\n" + yaml.safe_dump({
        "run": {"project": "CLINICAL_X", "method": "external", "label": "run"},
        "record_mode": "live", "validation": block}))
    return record, full, core, block


def test_guarded_nested_recheck_keeps_the_discovered_pair(project_tree, monkeypatch):
    root, _, _ = project_tree
    record, full, core, prior = recorded_pair(root)
    caller = root / "analysis"
    caller.mkdir()
    for path in (full, core):
        duplicate = caller / path.relative_to(root)
        duplicate.parent.mkdir(parents=True, exist_ok=True)
        duplicate.write_text("id: https://example.org/other\ntitle: Different valid cohort\n")
    monkeypatch.chdir(caller)
    result = CliRunner().invoke(cli, ["provenance", "recheck-validation", "--all",
                                     "--method", "external", "--execute"])
    assert result.exit_code == 0, (result.output, result.exception)
    fresh = yaml.safe_load(record.read_text())["validation"]
    assert "duplicate_keys" in fresh, result.output
    assert fresh["artifacts"] == prior["artifacts"]
    assert not (caller / record.relative_to(root)).exists()


@pytest.mark.parametrize("passed", [False, True])
@pytest.mark.parametrize("old_schema", [False, True])
def test_default_validation_preserves_an_unavailable_historical_verdict(project_tree, monkeypatch, passed, old_schema):
    root, _, _ = project_tree
    record, full, core, prior = recorded_pair(root, missing_pins=True, passed=passed)
    if old_schema:
        prior["schema"] = {"full_sha256": "historical schema"}
        data = yaml.safe_load(record.read_text()); data["validation"] = prior
        record.write_text("# Historical header\n" + yaml.safe_dump(data))
    before = record.read_bytes()
    monkeypatch.chdir(root)
    calls = []
    monkeypatch.setattr(api_runner, "validate_outputs", lambda spec: calls.append(spec) or [])
    args = ["runs", "validate", "--method", "external", "--label", "run", "--project", "CLINICAL_X"]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, (result.output, result.exception)
    assert not calls, "an existing verdict requires explicit --recheck"
    assert record.read_bytes() == before
    result = CliRunner().invoke(cli, [*args, "--recheck"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert len(calls) == 1
    fresh = yaml.safe_load(record.read_text())["validation"]
    assert fresh["artifacts"]["full"]["sha256"] == hashlib.sha256(full.read_bytes()).hexdigest()


def test_guarded_recheck_compares_replacement_hashes_with_prior_pins(project_tree, monkeypatch):
    root, _, _ = project_tree
    record, _, _, _ = recorded_pair(root)
    before = record.read_bytes()
    monkeypatch.chdir(root)
    monkeypatch.setattr(api_runner, "validate_outputs", lambda spec: [])
    real_block = api_runner.validation_block
    def mismatched_block(*args, **kwargs):
        block = real_block(*args, **kwargs)
        block["artifacts"]["full"]["sha256"] = "replacement did not reproduce"
        return block
    monkeypatch.setattr(api_runner, "validation_block", mismatched_block)
    result = CliRunner().invoke(cli, ["provenance", "recheck-validation", "--all",
                                     "--method", "external", "--execute"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert "held" in result.output
    assert record.read_bytes() == before


def test_guarded_recheck_holds_unavailable_prior_pins(project_tree, monkeypatch):
    root, _, _ = project_tree
    record, _, _, _ = recorded_pair(root, missing_pins=True)
    before = record.read_bytes()
    monkeypatch.chdir(root)
    monkeypatch.setattr(api_runner, "validate_outputs", lambda spec: [])
    result = CliRunner().invoke(cli, ["provenance", "recheck-validation", "--all",
                                     "--method", "external", "--execute"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert "held" in result.output
    assert record.read_bytes() == before


def test_nested_recheck_compares_equivalent_problem_path_spellings(project_tree, monkeypatch):
    root, _, _ = project_tree
    record, full, _, prior = recorded_pair(root, passed=False)
    data = yaml.safe_load(record.read_text())
    for entry in prior["artifacts"].values():
        entry["path"] = str(Path(entry["path"]).relative_to(root))
    prior["problems"] = [{"artifact": str(full.relative_to(root)), "class": "Dataset", "error": "finding in /title"}]
    data["validation"] = prior
    record.write_text(yaml.safe_dump(data))
    caller = root / "analysis"; caller.mkdir(); monkeypatch.chdir(caller)
    monkeypatch.setattr(api_runner, "validate_outputs", lambda spec: [
        {"artifact": str(spec.full_path), "class": "Dataset", "error": "finding in /title"}])
    result = CliRunner().invoke(cli, ["provenance", "recheck-validation", "--all",
                                     "--method", "external", "--execute"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert "duplicate_keys" in yaml.safe_load(record.read_text())["validation"], result.output
