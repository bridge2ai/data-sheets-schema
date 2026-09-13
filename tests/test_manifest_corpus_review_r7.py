"""A run selecting no manifest must not inherit an ancestor's chunk namespace."""
from pathlib import Path

from click.testing import CliRunner

from data_sheets_schema import api_runner as api, chunking, provenance
from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import _spec
from tests.test_agentic_selected_playbook import commands
from tests.test_manifest_corpus_root import project_tree


def test_automatic_no_manifest_selection_keeps_a_symlinks_caller_namespace(project_tree, monkeypatch):
    root, _, bundle = project_tree
    monkeypatch.chdir(root)
    ancestor_mapping, _ = chunking.write_manifest_for(bundle)
    ancestor_mapping = ancestor_mapping.absolute()
    caller = root / "analysis"
    caller.mkdir()
    monkeypatch.chdir(caller)
    alias = Path("alias.txt")
    alias.symlink_to(bundle)
    local_mapping = Path("alias_chunks.yaml")
    local_mapping.write_text(chunking.dump_manifest(
        chunking.manifest_from_bytes(alias.read_bytes(), alias.name, chunking.DEFAULT_RULE)))
    spec = _spec("UNDECLARED", "baseline", "run", "generic_v9", bundle=alias,
        runtime="Claude Code")
    assert spec.manifest is None
    command = next(row for row in commands(spec) if row[:2] == ["bundle", "chunk"])
    result = CliRunner().invoke(cli, command)
    assert result.exit_code == 0, result.output
    assert spec.chunk_manifest.resolve() == local_mapping.resolve()
    assert chunking.manifest_for(alias).resolve() == ancestor_mapping
    assert chunking.manifest_for(alias, source_manifest=None).resolve() == local_mapping.resolve()
    assert api.build_phase(spec, "full", carry={}) is not None
    recorded = provenance.build_record(spec.project, spec.method, spec.label, mode="live",
        input_bundle=alias, input_verified=True, manifest=None, selected_manifest=None,
        chunk_manifest=spec.chunk_manifest)
    assert recorded.data["inputs"]["chunks"]["bundle_name"] == alias.name
    assert recorded.data["inputs"]["source_manifest"]["path"] is None
