"""The selected manifest owns conventional corpus paths, from any directory."""
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import chunking, registry
from data_sheets_schema.cli.api import _spec


@pytest.fixture
def project_tree(tmp_path, monkeypatch):
    root = tmp_path / "caller"
    manifest = root / "data/preprocessed/source_manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(yaml.safe_dump({"projects": {"CLINICAL_X": {"sources": []}}}))
    bundle = root / "data/preprocessed/concatenated/CLINICAL_X_preprocessed.txt"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("FILE: overview.txt\nA synthetic clinical dataset.\n" * 20)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv("D4D_MANIFEST", raising=False)
    monkeypatch.delenv("D4D_PROFILE", raising=False)
    return root, manifest, bundle


def test_conventional_bundle_follows_the_explicit_manifest(project_tree):
    root, manifest, bundle = project_tree
    reg = registry.load_registry(manifest)
    assert reg.bundle("CLINICAL_X").resolve() == bundle
    assert reg.declares_bundle("CLINICAL_X", bundle)


def test_manifest_paths_share_the_manifest_corpus_root(project_tree):
    root, manifest, _ = project_tree
    manifest.write_text(yaml.safe_dump({"projects": {"CLINICAL_X": {
        "sources": [], "bundle": "bundles/clinical.txt",
        "source_dir": "processed/clinical", "raw_dir": "raw/clinical"}}}))
    reg = registry.load_registry(manifest)
    assert reg.bundle("CLINICAL_X").resolve() == root / "bundles/clinical.txt"
    assert reg.source_dir("CLINICAL_X").resolve() == root / "processed/clinical"
    assert reg.raw_dir("CLINICAL_X").resolve() == root / "raw/clinical"


def test_ancestor_discovery_keeps_context_bundles_and_chunks_in_one_tree(project_tree, monkeypatch):
    root, manifest, bundle = project_tree
    nested = root / "analysis/nested"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert registry.default_manifest_path().resolve() == manifest
    assert registry.load_registry().bundle("CLINICAL_X").resolve() == bundle
    assert chunking.bundle_path("CLINICAL_X").resolve() == bundle
    assert chunking.manifest_path("CLINICAL_X").resolve() == root / "data/preprocessed/chunks/CLINICAL_X_chunks.yaml"


def test_generation_outputs_follow_the_explicit_manifest(project_tree):
    root, manifest, bundle = project_tree
    spec = _spec("CLINICAL_X", "baseline", "test_run", "generic", manifest=manifest)
    assert spec.bundle.resolve() == bundle
    assert spec.full_path.resolve() == root / "data/d4d_concatenated/claudecode_api/test_run/CLINICAL_X_d4d.yaml"
    assert spec.core_path.resolve() == root / "data/d4d_concatenated/claudecode_api_core/test_run/CLINICAL_X_d4d_core.yaml"


def test_explicit_output_directory_remains_the_callers_override(project_tree):
    _, manifest, bundle = project_tree
    spec = _spec("CLINICAL_X", "baseline", "test_run", "generic", bundle=bundle,
                 manifest=manifest, out_dir="chosen-output")
    assert spec.full_path == Path("chosen-output/CLINICAL_X_d4d.yaml")


def test_a_standalone_manifest_uses_its_own_directory(project_tree):
    root, _, _ = project_tree
    manifest = root / "project.yaml"
    manifest.write_text(yaml.safe_dump({"projects": {"CLINICAL_X": {"sources": []}}}))
    assert registry.load_registry(manifest).bundle("CLINICAL_X").resolve() == root / "data/preprocessed/concatenated/CLINICAL_X_preprocessed.txt"


def test_generated_run_is_discoverable_and_grounded_from_a_nested_directory(project_tree, monkeypatch):
    from data_sheets_schema import api_runner, provenance, runs, verifiable
    from tests.test_download.test_api_runner import FakeClient

    root, manifest, bundle = project_tree
    nested = root / "analysis/nested"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    spec = _spec("CLINICAL_X", "baseline", "test_run", "generic")
    api_runner.execute(spec, client=FakeClient())
    found = runs.discover()
    assert len(found) == 2 and all(run.path.is_dir() for run in found)
    assert runs.full_record_path(spec.method, spec.label, spec.project) == spec.full_path
    assert runs.core_record_path(spec.method, spec.label, spec.project) == spec.core_path
    assert runs.is_complete(spec.method, spec.label, spec.project)
    assert provenance.record_path_for(spec.project, spec.method, spec.label).is_file()
    assert verifiable.declared_bundle(spec.method, spec.label, spec.project).resolve() == bundle
    assert not (nested / "data").exists()
    from click.testing import CliRunner
    from data_sheets_schema.cli import cli
    monkeypatch.chdir(root.parent / "elsewhere")
    result = CliRunner().invoke(cli, ["--manifest", str(manifest), "runs", "list"])
    assert result.exit_code == 0 and "CLINICAL_X" in result.output, result.output
    result = CliRunner().invoke(cli, ["--manifest", str(manifest), "runs", "check",
                                    "--method", spec.method, "--label", spec.label,
                                    "--project", spec.project, "--strict"])
    assert result.exit_code == 0, result.output + str(result.exception)
    result = CliRunner().invoke(cli, ["--manifest", str(manifest), "provenance",
                                    "validate-records", "--strict"])
    assert result.exit_code == 0 and "1 record(s) checked" in result.output, result.output


def test_corpus_consumers_use_the_selected_tree_without_writing_elsewhere(project_tree, monkeypatch):
    import click
    from data_sheets_schema import backfill_checks, runs
    from data_sheets_schema.cli import cli
    from data_sheets_schema.cli.receipts import _run_paths

    root, manifest, bundle = project_tree
    method, label, project = "claudecode_api", "synthetic_rep1", "CLINICAL_X"
    outputs = root / "data/d4d_concatenated"
    full = outputs / method / label / f"{project}_d4d.yaml"
    full.parent.mkdir(parents=True)
    full.write_text("id: https://example.org/test\ntitle: Synthetic\n")
    record = outputs / f"{method}_core" / label / f"{project}_provenance.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(yaml.safe_dump({
        "run": {"project": project, "method": method, "label": label},
        "model": {"agent_runtime": "Claude API (direct)"},
        "canonical": {"criterion": "test fixture"},
    }))
    before = record.read_bytes()
    with click.Context(cli) as context:
        context.params["manifest"] = str(manifest)
        assert _run_paths(method, label, project)["full"] == full
        assert backfill_checks.declared_bundle({"inputs": {"bundle_path":
            "data/preprocessed/concatenated/CLINICAL_X_preprocessed.txt"}}) == bundle
        assert runs.canonical_runs()[project]["provenance"] == str(record)
        assert runs.arm_facts("synthetic")["projects"] == [project]
        archive = runs.archive_runs([label], reason="fixture", projects=[project])
        assert archive["count"] == 2 and archive["dry_run"]
        assert all(Path(dst).is_relative_to(root / "data/ATTIC") for _, dst in archive["moved"])
    assert record.read_bytes() == before
    assert not (Path.cwd() / "data").exists()


def test_environment_selection_roots_corpus_helpers(project_tree, monkeypatch):
    root, manifest, bundle = project_tree
    monkeypatch.setenv("D4D_MANIFEST", str(manifest))
    assert chunking.bundle_path("CLINICAL_X").resolve() == bundle
    from data_sheets_schema.provenance import record_path_for
    assert record_path_for("CLINICAL_X", "external", "run").resolve() == root / "data/d4d_concatenated/external_core/run/CLINICAL_X_provenance.yaml"


def test_no_selected_manifest_keeps_new_outputs_in_the_callers_directory(tmp_path, monkeypatch):
    from data_sheets_schema import corpus, provenance
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("D4D_MANIFEST", raising=False)
    assert corpus.root() == tmp_path.resolve()
    target = provenance.record_path_for("UNDECLARED", "external", "run")
    assert target.resolve() == tmp_path / "data/d4d_concatenated/external_core/run/UNDECLARED_provenance.yaml"
