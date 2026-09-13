"""Run validation must retain the corpus discovered from a nested directory."""
import hashlib
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree


@pytest.mark.parametrize("recheck", [False, True])
@pytest.mark.parametrize("caller_duplicate", [False, True])
def test_nested_validation_uses_the_discovered_pair(project_tree, monkeypatch, recheck, caller_duplicate):
    root, _, _ = project_tree
    relative = Path("data/d4d_concatenated")
    full_rel = relative / "external/run/CLINICAL_X_d4d.yaml"
    core_rel = relative / "external_core/run/CLINICAL_X_d4d_core.yaml"
    record_rel = core_rel.parent / "CLINICAL_X_provenance.yaml"
    full, core, record = (root / p for p in (full_rel, core_rel, record_rel))
    for path in (full, core):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("id: https://example.org/clinical\ntitle: Synthetic cohort\n")
    (core.parent / "CLINICAL_X_reconciliation.md").write_text("Synthetic completed report.\n")
    data = {"run": {"project": "CLINICAL_X", "method": "external", "label": "run"},
            "record_mode": "live"}
    if recheck:
        data["validation"] = {"passed": False, "artifacts": {
            name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in (("full", full), ("core", core))}}
    record.write_text(yaml.safe_dump(data))
    caller = root / "analysis"
    caller.mkdir()
    if caller_duplicate:
        for relative_path in (full_rel, core_rel):
            path = caller / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("not_a_schema_slot: wrong corpus\n")
    monkeypatch.chdir(caller)
    result = CliRunner().invoke(cli, ["runs", "validate", "--method", "external",
        "--project", "CLINICAL_X", "--label", "run", *(["--recheck"] if recheck else [])])
    assert result.exit_code == 0, (result.output, result.exception)
    block = yaml.safe_load(record.read_text())["validation"]
    assert block["passed"], (result.output, block)
    for name, path in (("full", full), ("core", core)):
        entry = block["artifacts"][name]
        assert Path(entry["path"]).resolve() == path
        algorithm = "sha256" if recheck else "md5"
        assert entry[algorithm] == hashlib.new(algorithm, path.read_bytes()).hexdigest()
    assert not (caller / record_rel).exists()
