"""The provenance CLI carries the resolved corpus through reads and writes."""
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


def artifacts(owner, bundle, manifest=None):
    concat = owner / "data/d4d_concatenated"
    full = concat / "external/run/CLINICAL_X_d4d.yaml"
    core = concat / "external_core/run/CLINICAL_X_d4d_core.yaml"
    report = core.with_name("CLINICAL_X_reconciliation.md")
    full.parent.mkdir(parents=True, exist_ok=True)
    core.parent.mkdir(parents=True, exist_ok=True)
    header = f"# Source bundle: {bundle}\n"
    if manifest is not None:
        header += f"# Source manifest: {manifest}\n"
    full.write_text(header + "id: https://example.org/synthetic\n")
    core.write_text("id: https://example.org/synthetic\n")
    report.write_text("Synthetic reconciliation.\n")
    return full, core, report, core.with_name("CLINICAL_X_provenance.yaml")


@pytest.mark.parametrize("selection", ["auto", "none", "explicit"])
def test_live_record_reads_and_writes_the_selected_owner(project_tree, monkeypatch, selection):
    ancestor, manifest, ancestor_bundle = project_tree
    caller = ancestor / "analysis"
    caller.mkdir()
    monkeypatch.chdir(caller)
    bundle = Path("external.txt")
    bundle.write_text("Caller-owned synthetic evidence.\n")
    ancestor_paths = artifacts(ancestor, ancestor_bundle, manifest)
    caller_paths = artifacts(caller, bundle, "not used (external bundle)")
    selected = ancestor_paths if selection == "explicit" else caller_paths
    untouched = caller_paths if selection == "explicit" else ancestor_paths
    untouched[-1].write_text("original: keep these bytes\n")
    args = ["provenance", "record", "--project", "CLINICAL_X", "--method", "external",
            "--label", "run", "--input-bundle", str(bundle)]
    if selection != "auto":
        args += ["--manifest", str(manifest) if selection == "explicit" else "none"]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, (result.output, result.exception)
    data = yaml.safe_load(selected[-1].read_text())
    for variant, path in zip(("full", "core", "report"), selected):
        assert Path(data["outputs"][variant]["path"]).resolve() == path
    assert data["inputs"]["bundle_md5"] is not None
    assert untouched[-1].read_text() == "original: keep these bytes\n"


def test_nested_backfill_preserves_discovered_artifacts_and_inputs(project_tree, monkeypatch):
    owner, manifest, bundle = project_tree
    paths = artifacts(owner, bundle.relative_to(owner), manifest.relative_to(owner))
    caller = owner / "analysis"
    caller.mkdir()
    monkeypatch.chdir(caller)
    result = CliRunner().invoke(cli, ["provenance", "backfill", "--verified-label", "run"])
    assert result.exit_code == 0, (result.output, result.exception)
    data = yaml.safe_load(paths[-1].read_text())
    for variant, path in zip(("full", "core", "report"), paths):
        assert Path(data["outputs"][variant]["path"]).resolve() == path
    assert Path(data["inputs"]["bundle_path"]).resolve() == bundle
    assert data["inputs"]["bundle_md5"] is not None
    assert Path(data["inputs"]["source_manifest"]["path"]).resolve() == manifest
    assert data["inputs"]["source_manifest"]["md5"] is not None
    assert not (caller / "data/d4d_concatenated").exists()
