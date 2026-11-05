"""NF3-7: relative publication must preserve input identity (2026-10-31).

Real symlinks followed by parent traversal distinguish filesystem resolution
from lexical collapse. Decoys make an unintended replacement observable in
both RunSpec inputs and recorded provenance hashes; no generation is invoked.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api, chunking, provenance


@pytest.fixture(params=("ordinary", "inside-parent", "outside-parent"))
def input_paths(request, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "checkout"
    root.mkdir()
    (root / ".git").mkdir()
    monkeypatch.chdir(root)
    monkeypatch.delenv("D4D_MANIFEST", raising=False)
    monkeypatch.delenv("D4D_PROFILE", raising=False)
    preprocessed = root / "data/preprocessed"
    preprocessed.mkdir(parents=True)
    manifest = preprocessed / "source_manifest.yaml"
    manifest.write_bytes(b"projects:\n  CLINICAL_X:\n    sources: []\n")
    location = {
        "ordinary": preprocessed / "inputs",
        "inside-parent": preprocessed,
        "outside-parent": tmp_path / "outside",
    }[request.param]
    location.mkdir(parents=True, exist_ok=True)
    bundle = location / "bundle.txt"
    bundle_bytes = b"FILE: clinical.txt\nPATH: clinical.txt\nOriginal clinical source.\n"
    bundle.write_bytes(bundle_bytes)
    chunks = location / "bundle.chunks.yaml"
    chunks.write_text(chunking.dump_manifest(chunking.manifest_from_bytes(
        bundle_bytes, bundle.name,
    )), encoding="utf-8")
    originals = {"bundle": bundle, "manifest": manifest, "chunk_manifest": chunks}
    selected = dict(originals)
    decoys = []
    if request.param != "ordinary":
        (location / "subdir").mkdir()
        link = root / "link"
        link.symlink_to(location / "subdir", target_is_directory=True)
        selected["bundle"] = link / ".." / bundle.name
        selected["chunk_manifest"] = link / ".." / chunks.name
        if request.param == "inside-parent":
            # The physical manifest is conventional, so the owner remains root
            # and this exercises normalization rather than the frozen branch.
            selected["manifest"] = link / ".." / manifest.name
        for key, path in selected.items():
            if ".." in path.parts:
                decoy = root / path.name
                decoy.write_bytes(b"Decoy for " + key.encode() + b"\n")
                decoys.append(decoy)
    before = {p: p.read_bytes() for p in (*originals.values(), *decoys)}
    expected = {
        key: path if ".." in path.parts else path.relative_to(root)
        for key, path in selected.items()
    }
    return SimpleNamespace(
        root=root, selected=selected, originals=originals,
        expected=expected, before=before,
    )


def test_runspec_preserves_physical_input_identity(input_paths):
    p = input_paths
    spec = api.RunSpec(
        project="CLINICAL_X", arm="BASELINE (input documents only)", method="external",
        label="nf3_path_identity", condition="generic_v9", runtime="Claude Code",
        provider="offline", render_version=5, run_date="2026-10-31", profile="neutral",
        **p.selected,
    )
    assert spec._corpus_root == p.root
    for key, original in p.originals.items():
        actual = getattr(spec, key)
        assert actual == p.expected[key]
        assert actual.resolve() == original.resolve()
        assert actual.read_bytes() == p.before[original]
    assert {path: path.read_bytes() for path in p.before} == p.before


def test_provenance_preserves_input_paths_and_hashes(input_paths):
    p = input_paths
    label = "nf3_path_identity"
    outputs = {
        "full": p.root / "data/d4d_concatenated/claudecode_agent" / label / "CLINICAL_X_d4d.yaml",
        "core": p.root / "data/d4d_concatenated/claudecode_agent_core" / label / "CLINICAL_X_d4d_core.yaml",
    }
    for path in outputs.values():
        path.parent.mkdir(parents=True)
        path.write_text("id: CLINICAL_X\n", encoding="utf-8")
    record = provenance.build_record(
        "CLINICAL_X", "claudecode_agent", label, mode="live", input_verified=True,
        input_bundle=p.selected["bundle"], manifest=p.selected["manifest"],
        chunk_manifest=p.selected["chunk_manifest"], outputs=outputs,
    )
    inputs = record.data["inputs"]
    assert inputs["bundle_path"] == str(p.expected["bundle"])
    assert inputs["source_manifest"]["path"] == str(p.expected["manifest"])
    assert inputs["chunks"] is not None
    assert inputs["chunks"]["path"] == str(p.expected["chunk_manifest"])
    bundle_bytes = p.before[p.originals["bundle"]]
    assert inputs["bundle_md5"] == hashlib.md5(bundle_bytes).hexdigest()
    assert inputs["bundle_bytes"] == len(bundle_bytes)
    assert inputs["hash_basis"] == "verified identical to the bytes consumed"
    assert inputs["source_manifest"]["md5"] == hashlib.md5(
        p.before[p.originals["manifest"]],
    ).hexdigest()
    assert inputs["chunks"]["sha256"] == hashlib.sha256(
        p.before[p.originals["chunk_manifest"]],
    ).hexdigest()
    assert {path: path.read_bytes() for path in p.before} == p.before
