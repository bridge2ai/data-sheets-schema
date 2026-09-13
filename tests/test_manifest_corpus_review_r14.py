"""Inline evidence must follow a moved or copied corpus, not its old address."""
from pathlib import Path
import shutil

from click.testing import CliRunner
import pytest

from data_sheets_schema import runs
from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from tests.test_manifest_corpus_review_r13 import artifacts


@pytest.mark.parametrize("copy_original", [False, True])
@pytest.mark.parametrize("kind", ["pair", "report"])
def test_inline_verdict_follows_the_corpus_after_relocation(project_tree, monkeypatch, copy_original, kind):
    owner, manifest, bundle = project_tree
    monkeypatch.chdir(owner)
    full, _, report, _ = artifacts(owner, bundle.relative_to(owner), manifest.relative_to(owner))
    result = CliRunner().invoke(cli, ["provenance", "record", "--project", "CLINICAL_X",
        "--method", "external", "--label", "run", "--input-bundle", str(bundle.relative_to(owner))])
    assert result.exit_code == 0, (result.output, result.exception)
    status = runs.pair_status if kind == "pair" else runs.report_claim_status
    clean = runs.PAIR_CONSISTENT if kind == "pair" else runs.CLAIMS_CLEAN
    stale = runs.PAIR_STALE if kind == "pair" else runs.CLAIMS_STALE
    assert status("external", "run", "CLINICAL_X")[0] == clean
    destination = owner.with_name("relocated")
    if copy_original:
        shutil.copytree(owner, destination)
    else:
        owner.rename(destination)
    monkeypatch.chdir(destination)
    # Unchanged evidence stays valid even after the original directory is gone.
    assert status("external", "run", "CLINICAL_X")[0] == clean
    changed = full if kind == "pair" else report
    moved_artifact = destination / changed.relative_to(owner)
    moved_artifact.write_text(moved_artifact.read_text() + "\n# Modified in the relocated corpus.\n")
    # Keeping the original cannot hide a change made only in the copy.
    assert status("external", "run", "CLINICAL_X")[0] == stale
