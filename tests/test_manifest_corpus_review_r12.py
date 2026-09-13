"""Input selection and backfill must not borrow another corpus's evidence."""
from pathlib import Path
import hashlib

import pytest
import yaml

from data_sheets_schema import api_runner, backfill_checks, provenance
from tests.test_manifest_corpus_root import project_tree
from tests import test_review_pack as review_fixtures


@pytest.mark.parametrize("declares_unused", [False, True])
def test_auto_external_bundle_uses_the_same_output_owner_as_its_spec(project_tree, monkeypatch, declares_unused):
    ancestor, _, _ = project_tree
    caller = ancestor / "analysis"; caller.mkdir()
    monkeypatch.chdir(caller)
    bundle = Path("external.txt"); bundle.write_text("A caller-owned synthetic dataset.\n")
    spec = api_runner.RunSpec(project="CLINICAL_X", arm="BASELINE (input documents only)",
        method="external", label="run", condition="generic", bundle=bundle, profile="neutral")
    assert spec.manifest is None
    header = "# Source manifest: not used (external bundle)\n" if declares_unused else ""
    for owner, identifier in ((caller, "caller"), (ancestor, "ancestor")):
        for path in (spec.full_path, spec.core_path):
            target = owner / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(header + f"id: https://example.org/{identifier}\n")
    result = provenance.build_record(spec.project, spec.method, spec.label, mode="live",
        input_bundle=bundle, input_verified=True)
    for variant, path in (("full", spec.full_path), ("core", spec.core_path)):
        assert Path(result.data["outputs"][variant]["path"]).resolve() == path.resolve()
    assert result.data["inputs"]["source_manifest"]["path"] is None


@pytest.mark.parametrize("known_owner", [False, True])
@pytest.mark.parametrize("caller_copy", [False, True])
def test_backfill_grounding_uses_only_an_established_record_owner(tmp_path, monkeypatch, known_owner, caller_copy):
    owner = tmp_path / "owner"
    record = (owner / "data/d4d_concatenated/external_core/run/P_provenance.yaml" if known_owner
              else owner / "flat/P_provenance.yaml")
    record.parent.mkdir(parents=True)
    record.write_text(yaml.safe_dump({"inputs": {"bundle_path": "evidence.txt"}}))
    paths = backfill_checks.record_paths(record)
    for name in ("full", "core"):
        paths[name].parent.mkdir(parents=True, exist_ok=True)
        paths[name].write_text("id: https://example.org/synthetic\nfunders:\n  - id: ror:04qk2t514\n")
    (owner / "evidence.txt").write_text("The actual owner's evidence contains no organization identifier.\n")
    caller = tmp_path / "caller"
    manifest = caller / "data/preprocessed/source_manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("projects: {}\n")
    if caller_copy:
        (caller / "evidence.txt").write_text("The caller names ror:04qk2t514.\n")
    analysis = caller / "analysis"; analysis.mkdir()
    monkeypatch.chdir(analysis)
    block = backfill_checks.compute(record, only={"grounding"})["grounding"]
    assert block["checked"] is known_owner, block
    if known_owner:
        assert Path(block["artifacts"]["bundle"]["path"]).resolve() == owner / "evidence.txt"
    else:
        assert "base" in block["reason"]


def test_header_only_reconstruction_uses_the_discovered_artifact_owner(project_tree, monkeypatch):
    owner, manifest, bundle = project_tree
    full = owner / "data/d4d_concatenated/external/run/CLINICAL_X_d4d.yaml"
    full.parent.mkdir(parents=True)
    full.write_text(f"# Source bundle: {bundle.relative_to(owner)}\n"
                    f"# Source manifest: {manifest.relative_to(owner)}\n"
                    "id: https://example.org/clinical\n")
    result = provenance.build_record("CLINICAL_X", "external", "run", mode="reconstructed",
        input_verified=True, concat_dir=owner / "data/d4d_concatenated")
    assert Path(result.data["inputs"]["bundle_path"]).resolve() == bundle
    assert result.data["inputs"]["source_manifest"]["md5"] == hashlib.md5(manifest.read_bytes()).hexdigest()


def test_header_only_auto_selection_honors_an_explicit_manifest(project_tree, monkeypatch):
    owner, manifest, bundle = project_tree
    monkeypatch.setenv("D4D_MANIFEST", str(manifest))
    full = owner / "data/d4d_concatenated/external/run/CLINICAL_X_d4d.yaml"
    full.parent.mkdir(parents=True)
    full.write_text(f"# Source bundle: {bundle}\n# Source manifest: {manifest}\n"
                    "id: https://example.org/clinical\n")
    result = provenance.build_record("CLINICAL_X", "external", "run", mode="reconstructed",
                                     input_verified=True)
    assert result.data["outputs"]["full"] is not None
    assert Path(result.data["outputs"]["full"]["path"]).resolve() == full


@pytest.mark.parametrize("recorded_rule", [False, True])
def test_unknown_chunk_base_disables_discovery_but_preserves_verified_recovery(tmp_path, monkeypatch, recorded_rule):
    original = tmp_path / "original"; original.mkdir()
    record, _ = review_fixtures.Pack()._run(original)
    row = yaml.safe_load(record.read_text())
    mapping = Path(row["inputs"]["chunks"]["path"])
    chunk_data = yaml.safe_load(mapping.read_text())
    row["inputs"]["chunks"]["path"] = mapping.name  # Absolute flat record: base unknown.
    if recorded_rule:
        row["inputs"]["chunks"].update(rule=chunk_data["rule"],
            sha256=hashlib.sha256(mapping.read_bytes()).hexdigest())
    record.write_text(yaml.safe_dump(row, sort_keys=False))
    caller = tmp_path / "caller"; caller.mkdir()
    (caller / mapping.name).write_bytes(mapping.read_bytes())
    monkeypatch.chdir(caller)
    block = backfill_checks.compute(record, only={"receipts"})["receipts"]
    assert block["checked"] is recorded_rule, block
    if not recorded_rule:
        assert "base" in block["reason"]
