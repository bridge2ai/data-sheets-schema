"""PR1587 review: selected ownership and path-bound integrity."""
import hashlib
from pathlib import Path

import click
import pytest
import yaml

from data_sheets_schema import api_runner, chunking, provenance, resources, runs
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree


def test_imported_registry_fallback_does_not_select_a_write_tree(project_tree, monkeypatch):
    root, manifest, bundle = project_tree
    monkeypatch.setattr(resources, "CHECKOUT_ROOT", root)
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic")
    assert spec.manifest is None
    assert spec.full_path.resolve().is_relative_to(Path.cwd())


@pytest.mark.parametrize("missing", [False, True])
def test_nested_validation_never_trusts_an_unverified_pin(project_tree, monkeypatch, missing):
    root, manifest, _ = project_tree
    relative = Path("data/d4d_concatenated/external/run/CLINICAL_X_d4d.yaml")
    full = root / relative
    full.parent.mkdir(parents=True)
    original = b"id: https://example.org/original\n"
    full.write_bytes(original)
    record = root / "data/d4d_concatenated/external_core/run/CLINICAL_X_provenance.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(yaml.safe_dump({"validation": {"passed": True, "artifacts": {"full": {
        "path": str(relative), "sha256": hashlib.sha256(original).hexdigest()}}}}))
    if missing:
        full.unlink()
    else:
        full.write_text("id: https://example.org/changed\n")
    nested = root / "analysis"
    nested.mkdir()
    monkeypatch.chdir(nested)
    expected = runs.UNVERIFIED if missing else runs.STALE
    assert runs.validation_status("external", "run", "CLINICAL_X") == expected


@pytest.mark.parametrize("runtime", ["Claude Code", "Codex CLI"])
def test_agentic_write_destinations_are_the_paths_its_checks_use(project_tree, runtime):
    root, manifest, bundle = project_tree
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v8", manifest=manifest, runtime=runtime)
    assert spec.render_version >= 5
    outputs = spec.instruction.split("OUTPUTS", 1)[1].split("HEADER BLOCK", 1)[0]
    assert all(str(path) in outputs for path in (spec.full_path, spec.core_path, spec.report_path))
    recorded = spec.render_spec()
    again = api_runner.RunSpec.from_render_spec(recorded, project=spec.project, method=spec.method, label=spec.label)
    assert again.instruction == spec.instruction


def test_explicit_caller_relative_input_keeps_its_original_location(project_tree):
    root, manifest, _ = project_tree
    own_bundle = Path("sources/input.txt")
    own_bundle.parent.mkdir()
    own_bundle.write_text("FILE: caller.txt\nThe caller's own selected input.\n")
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic", bundle=own_bundle, manifest=manifest)
    assert spec.bundle.is_absolute() and spec.bundle.read_bytes() == own_bundle.read_bytes()
    from data_sheets_schema.backfill_checks import declared_bundle
    with click.Context(cli) as ctx:
        ctx.params["manifest"] = str(manifest)
        assert declared_bundle({"inputs": {"bundle_path": str(spec.bundle)}}).resolve() == own_bundle.resolve()


@pytest.mark.parametrize("runtime", ["Claude Code", "Claude API (direct)"])
def test_programmatic_spec_discovers_chunks_with_its_selected_manifest(project_tree, runtime):
    root, manifest, bundle = project_tree
    chunks = root / "data/preprocessed/chunks/CLINICAL_X_chunks.yaml"
    chunks.parent.mkdir()
    chunks.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    spec = _spec("CLINICAL_X", "baseline", "external_run", "generic_v9", manifest=manifest, runtime=runtime)
    assert spec.chunk_manifest is not None and spec.chunk_manifest.resolve() == chunks
    assert api_runner.build_phase(spec, "full", carry={}) is not None


def test_programmatic_record_uses_manifest_outputs_and_preserves_explicit_bundle(project_tree):
    root, manifest, _ = project_tree
    own_bundle = Path("explicit.txt")
    own_bundle.write_text("The caller's explicitly selected input.\n")
    full = root / "data/d4d_concatenated/external/run/CLINICAL_X_d4d.yaml"
    full.parent.mkdir(parents=True)
    full.write_text("id: https://example.org/clinical\ntitle: Synthetic\n")
    record = provenance.build_record("CLINICAL_X", "external", "run", mode="live",
        input_bundle=own_bundle, input_verified=True, manifest=manifest)
    assert Path(record.data["inputs"]["bundle_path"]).is_absolute()
    assert Path(record.data["outputs"]["full"]["path"]).resolve() == full


@pytest.mark.parametrize("selection", ["root_option", "environment"])
def test_root_selection_governs_api_context_and_profile(project_tree, monkeypatch, selection):
    from data_sheets_schema.profiles import select_profile
    root, manifest, bundle = project_tree
    data = yaml.safe_load(manifest.read_bytes())
    data["profile"] = "bridge2ai"  # explicitly selected; never a default for this fixture
    manifest.write_text(yaml.safe_dump(data))
    if selection == "environment":
        monkeypatch.setenv("D4D_MANIFEST", str(manifest))
    with click.Context(cli) as ctx:
        if selection == "root_option":
            ctx.params["manifest"] = str(manifest)
        spec = _spec("CLINICAL_X", "baseline", "external_run", "generic", bundle=bundle)
        assert spec.manifest == manifest and spec.profile == "bridge2ai"
        assert select_profile().name == "bridge2ai"
        # A command's own explicit none takes precedence over the root.
        without = _spec("CLINICAL_X", "baseline", "without", "generic", bundle=bundle, manifest=None)
        assert without.manifest is None and without.profile == "neutral"
