"""Bundle drift belongs to the recorded corpus, never a caller's copy."""
import hashlib
import shutil

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import provenance, runs
from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from tests.test_manifest_corpus_review_r13 import artifacts


@pytest.mark.parametrize("caller_kind", ["nested", "foreign", "copy"])
@pytest.mark.parametrize("changed", [None, "selected", "caller"])
def test_bundle_drift_reads_only_the_selected_corpus(project_tree, monkeypatch, caller_kind, changed):
    owner, manifest, bundle = project_tree
    monkeypatch.chdir(owner)
    artifacts(owner, bundle.relative_to(owner), manifest.relative_to(owner))
    recorded = CliRunner().invoke(cli, ["provenance", "record", "--project", "CLINICAL_X",
        "--method", "external", "--label", "run", "--input-bundle", str(bundle.relative_to(owner))])
    assert recorded.exit_code == 0, recorded.output
    caller = owner / "analysis" if caller_kind == "nested" else owner.with_name("drift_caller")
    if caller_kind == "copy":
        shutil.copytree(owner, caller)
    else:
        caller.mkdir()
    caller_bundle = caller / bundle.relative_to(owner)
    caller_bundle.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle, caller_bundle)
    if changed:
        target = bundle if changed == "selected" else caller_bundle
        target.write_text(target.read_text() + "\nChanged only here.\n")
    monkeypatch.chdir(caller)
    observed = []
    original = runs.bundle_drift_detail
    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        observed.append(result[0])
        return result
    monkeypatch.setattr(runs, "bundle_drift_detail", capture)
    args = [] if caller_kind == "nested" else ["--manifest", str(manifest)]
    result = CliRunner().invoke(cli, [*args, "runs", "check", "--method", "external"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert observed, result.output
    assert set(observed) == {runs.BUNDLE_DRIFTED if changed == "selected" else runs.BUNDLE_CURRENT}


def test_flat_record_does_not_borrow_the_callers_bundle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bundle = tmp_path / "bundle.txt"
    bundle.write_bytes(b"same bytes")
    concat = tmp_path / "flat"
    record = provenance.record_path_for("X", "external", "run", concat)
    record.parent.mkdir(parents=True)
    record.write_text(yaml.safe_dump({"inputs": {"bundle_path": "bundle.txt",
        "bundle_md5": hashlib.md5(bundle.read_bytes()).hexdigest()}}))
    status, reason, declared = runs.bundle_drift_detail("external", "run", "X", concat)
    assert status == "unresolved"
    assert "owner" in reason
    assert declared == "bundle.txt"
