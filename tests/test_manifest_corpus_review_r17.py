"""Default manifest routing stays consistent beneath archived copies."""
import shutil

from click.testing import CliRunner
import pytest

from data_sheets_schema import chunking, resources
from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("stale", [False, True])
def test_chunk_check_uses_one_manifest_owner_under_an_archive(project_tree, monkeypatch, explicit, stale):
    root, manifest, bundle = project_tree
    monkeypatch.setattr(resources, "CHECKOUT_ROOT", root)
    monkeypatch.chdir(root)
    chunking.write_manifest_for(bundle)
    archive = root / "notes/copy"
    copied = archive / "data/preprocessed/source_manifest.yaml"
    copied.parent.mkdir(parents=True)
    shutil.copyfile(manifest, copied)
    if stale:
        bundle.write_text(bundle.read_text() + "\nChanged selected input.\n")
    monkeypatch.chdir(archive)
    args = ["--manifest", str(manifest)] if explicit else []
    result = CliRunner().invoke(cli, ["bundle", "chunk", *args,
        "--project", "CLINICAL_X", "--check", "--strict"])
    assert result.exit_code == int(stale), (result.output, result.exception)
    assert ("stale" if stale else "current") in result.output, result.output
    assert "missing" not in result.output, result.output
