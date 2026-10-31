"""NF3 backfill admits only hash-proven, owner-supported path spellings."""
import hashlib
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import agentic_runtime, api_runner as api, chunking, provenance as pv
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.provenance import _backfill_input_spellings
from tests.test_manifest_corpus_root import project_tree  # noqa: F401


@pytest.mark.parametrize("value,owner,expected", [
    (None, "/owned", (None,)),
    ("inputs/bundle.txt", None, ("inputs/bundle.txt",)),
    ("/owned/inputs/bundle.txt", None, ("/owned/inputs/bundle.txt",)),
    ("/foreign/bundle.txt", "/owned", ("/foreign/bundle.txt",)),
    ("../bundle.txt", "/owned", ("../bundle.txt",)),
    ("/owned/alias/../bundle.txt", "/owned", ("/owned/alias/../bundle.txt",)),
    ("inputs/bundle.txt", "relative-owner", ("inputs/bundle.txt",)),
    ("inputs/bundle.txt", "/owned/../other", ("inputs/bundle.txt",)),
    ("alias/bundle.txt", "/owned", ("alias/bundle.txt", "/owned/alias/bundle.txt")),
    ("/owned/alias/bundle.txt", "/owned", ("/owned/alias/bundle.txt", "alias/bundle.txt")),
])
def test_spelling_alternatives_do_not_guess_owners_or_resolve_paths(monkeypatch, value, owner, expected):
    def forbidden(*args, **kwargs):
        pytest.fail("path spelling candidates must not consult the filesystem")
    for name in ("resolve", "absolute", "exists", "is_file", "read_bytes", "stat"):
        monkeypatch.setattr(Path, name, forbidden)
    candidates = _backfill_input_spellings(
        Path(value) if value is not None else None,
        Path(owner) if owner is not None else None,
    )
    assert tuple(str(path) if path is not None else None for path in candidates) == expected


@pytest.mark.parametrize("literal_inputs,valid_hash", [(True, True), (False, True), (True, False)])
def test_flat_record_does_not_guess_its_original_owner(project_tree, monkeypatch, literal_inputs, valid_hash):
    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    spec = api.RunSpec(
        project="CLINICAL_X", arm="BASELINE (input documents only)", method="external",
        label="nf3_flat_backfill", condition="generic_v9", bundle=bundle,
        manifest=manifest, chunk_manifest=chunks, runtime="Claude Code", provider="offline",
        render_version=5, run_date="2026-09-13", profile="neutral",
    )
    instruction = spec.instruction
    assert not spec.bundle.is_absolute() and not spec.manifest.is_absolute()
    path = root / "flat_provenance.yaml"
    assert path.is_absolute() and pv.artifact_root(path) is None
    data = {
        "record_generated_at": "2026-09-13T00:00:00+00:00",
        "run": {"project": spec.project, "method": spec.method, "label": spec.label},
        "model": {"provider": spec.provider}, "schema": {"profile": "neutral"},
        "inputs": {
            "bundle_path": str(spec.bundle if literal_inputs else bundle),
            "source_manifest": {"path": str(spec.manifest if literal_inputs else manifest)},
            "chunks": {"path": str(spec.chunk_manifest)},
        },
        "outputs": {key: {"path": str(value)} for key, value in
                    (("full", spec.full_path), ("core", spec.core_path), ("report", spec.report_path))},
        "prompts": {"request": {"sha256": hashlib.sha256(instruction.encode()).hexdigest()
                                if valid_hash else "0" * 64}},
    }
    before = yaml.safe_dump(data).encode()
    path.write_bytes(before)
    monkeypatch.setattr(pv, "record_path_for", lambda *args, **kwargs: path)
    def unavailable():
        raise ValueError("current resources unavailable; renderer5 remains replayable")
    monkeypatch.setattr(agentic_runtime, "toolchain", unavailable)
    result = CliRunner().invoke(cli, ["--manifest", str(manifest), "provenance", "backfill-spec",
        "--project", spec.project, "--method", spec.method, "--label", spec.label,
        "--condition", spec.condition, "--runtime", spec.runtime, "--execute"])
    if literal_inputs and valid_hash:
        assert result.exit_code == 0, (result.output, result.exception)
        after = yaml.safe_load(path.read_bytes())
        assert after["inputs"] == data["inputs"]
        restored = api.RunSpec.from_render_spec(after["prompts"]["request"]["spec"],
            project=spec.project, method=spec.method, label=spec.label)
        assert restored.instruction == instruction
    else:
        assert result.exit_code != 0, result.output
        assert "no spec under" in result.output
        assert path.read_bytes() == before
