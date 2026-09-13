"""Corpus R4 review: flat layout evidence and selected symlink identity."""
import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, provenance as pv, runs
from data_sheets_schema.cli.api import _spec
from tests.test_manifest_corpus_root import project_tree


@pytest.mark.parametrize("damage", ["modified", "missing"])
@pytest.mark.parametrize("out_dir", ["out", "out_core/run"])
def test_nested_legacy_flat_record_never_adopts_a_corpus_root(project_tree, monkeypatch, damage, out_dir):
    root, _, _ = project_tree
    launch = root / "data/d4d_concatenated"
    launch.mkdir(parents=True)
    original = b"id: https://example.org/original\n"
    pin = Path(out_dir) / "CLINICAL_X_d4d.yaml"
    for owner in (root, launch):
        target = owner / pin
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original)
    record = Path(out_dir) / "CLINICAL_X_provenance.yaml"
    data = {"run": {"project": "CLINICAL_X", "method": "external", "label": "run"},
        "record_mode": "live", "validation": {"passed": True, "artifacts": {"full": {
            "path": str(pin), "sha256": hashlib.sha256(original).hexdigest()}}}}
    (launch / record).write_text(yaml.safe_dump(data))
    if damage == "modified":
        (launch / pin).write_text("id: https://example.org/modified\n")
    else:
        (launch / pin).unlink()
    monkeypatch.chdir(launch)
    for address in (record, record.absolute()):
        result = runs.check_provenance("external", "run", "CLINICAL_X", record=address)
        assert not result["ok"], result
        assert pv.preservable_validation(address, {}) is None


@pytest.fixture
def selected_alias(project_tree):
    root, manifest, bundle = project_tree
    mapping = root / "data/preprocessed/chunks/CLINICAL_X_chunks.yaml"
    mapping.parent.mkdir()
    mapping.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    alias = Path("alias.txt")
    alias.symlink_to(bundle)
    ambient = Path("data/preprocessed/source_manifest.yaml")
    ambient.parent.mkdir(parents=True)
    ambient.write_text(yaml.safe_dump({"projects": {"OTHER": {"sources": []}}}))
    return root, manifest, bundle, mapping, alias


@pytest.mark.parametrize("arm", ["baseline", "crate_only"])
def test_explicit_symlink_namespace_reaches_phase_assembly(selected_alias, arm):
    root, manifest, bundle, mapping, alias = selected_alias
    spec = _spec("CLINICAL_X", arm, "run", "generic_v9", bundle=alias, manifest=manifest)
    assert spec.chunk_manifest.resolve() == mapping
    phase = api.build_phase(spec, "full", carry={})
    assert phase is not None


@pytest.mark.parametrize("consumed", [True, False])
def test_explicit_symlink_namespace_reaches_recorded_chunk_identity(selected_alias, consumed):
    root, manifest, bundle, mapping, alias = selected_alias
    record = pv.build_record("CLINICAL_X", "external", "run", mode="live",
        input_bundle=alias, input_verified=True, manifest=manifest if consumed else None,
        selected_manifest=manifest, chunk_manifest=mapping)
    assert record.data["inputs"]["chunks"] is not None
    assert record.data["inputs"]["chunks"]["bundle_name"] == bundle.name
    assert record.data["inputs"]["source_manifest"]["path"] == (str(manifest) if consumed else None)
