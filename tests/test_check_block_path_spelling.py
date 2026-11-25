"""Check blocks name the bundle and chunk manifest as the record declares them (#6314, 2026-11-24).

The 16 records of 2026-11-22 carry the operator's absolute worktree path at
`grounding.artifacts.bundle.path`, `receipts.bundle_basis.path` and, where
`d4d provenance record` computed the block, `receipts.artifacts.manifest.path`,
beside a repository-relative `inputs.bundle_path`. `declared_bundle` anchors
the relative declaration to the record's tree for reading; the blocks persisted
the anchored result.

Offline; synthetic corpus only. Inputs: generated fixture; outputs: temporary records.
"""
from pathlib import Path

import yaml

from data_sheets_schema import backfill_checks as bc
from data_sheets_schema import chunking, receipts


def _corpus(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    bundle = root / "data/preprocessed/concatenated/EXAMPLE_preprocessed.txt"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("=" * 80 + "\nFILE: one.txt\n" + "=" * 80 + "\nThe Example dataset has 12 participants.\n")
    monkeypatch.chdir(root)
    manifest, _ = chunking.write_manifest_for(Path("data/preprocessed/concatenated/EXAMPLE_preprocessed.txt"))
    full_dir = root / "data/d4d_concatenated/external/run1"
    core_dir = root / "data/d4d_concatenated/external_core/run1"
    full_dir.mkdir(parents=True)
    core_dir.mkdir(parents=True)
    body = "id: https://example.org/example\ntitle: Example\n"
    (full_dir / "EXAMPLE_d4d.yaml").write_text(body)
    (core_dir / "EXAMPLE_d4d_core.yaml").write_text(body)
    chunk_id = yaml.safe_load(Path(manifest).read_text())["chunks"][-1]["id"]
    (core_dir / "EXAMPLE_coverage_receipt.yaml").write_text(yaml.safe_dump({
        "chunks": [{"id": c["id"], "status": "nothing_relevant", "reason": "header"} if c["id"] != chunk_id else
                   {"id": c["id"], "status": "extracted",
                    "extracted": [{"slot": "title", "snippet": "The Example dataset has 12 participants."}]}
                   for c in yaml.safe_load(Path(manifest).read_text())["chunks"]]}))
    import hashlib
    record = {"run": {"project": "EXAMPLE", "method": "external", "label": "run1"},
              "record_mode": "live",
              "inputs": {"bundle_path": "data/preprocessed/concatenated/EXAMPLE_preprocessed.txt",
                         "bundle_md5": hashlib.md5(bundle.read_bytes()).hexdigest(),
                         "receipt_expected": True,
                         "chunks": {"path": str(Path(manifest)),
                                    "sha256": hashlib.sha256(Path(manifest).read_bytes()).hexdigest()}}}
    provenance = core_dir / "EXAMPLE_provenance.yaml"
    provenance.write_text(yaml.safe_dump(record))
    return root, provenance, record, Path(manifest)


def test_the_blocks_use_the_records_spelling_not_the_resolved_path(tmp_path, monkeypatch):
    root, provenance, record, manifest = _corpus(tmp_path, monkeypatch)
    assert not manifest.is_absolute()
    resolved = bc.declared_bundle(record, provenance)
    assert resolved.is_absolute()                       # what the blocks used to persist
    # As the recorder calls it: from the checkout root, by the record's relative path.
    blocks = bc.compute(provenance.relative_to(root), only={"grounding", "receipts"})
    text = yaml.safe_dump(blocks)
    assert str(root) not in text, text
    assert blocks["grounding"]["artifacts"]["bundle"]["path"] == record["inputs"]["bundle_path"]
    assert blocks["receipts"]["bundle_basis"] == {"source": "bundle on disk", "path": record["inputs"]["bundle_path"]}
    assert blocks["receipts"]["artifacts"]["manifest"]["path"] == record["inputs"]["chunks"]["path"]


def test_without_a_spelling_the_block_names_the_path_it_was_given(tmp_path, monkeypatch):
    """Callers that do not resolve from a record are unchanged."""
    root, provenance, record, manifest = _corpus(tmp_path, monkeypatch)
    bundle = bc.declared_bundle(record, provenance)
    full = root / "data/d4d_concatenated/external/run1/EXAMPLE_d4d.yaml"
    receipt = provenance.parent / "EXAMPLE_coverage_receipt.yaml"
    block = receipts.block_for(full, receipt, bundle, record["inputs"]["bundle_md5"], True,
                               manifest=manifest.absolute())
    assert block["bundle_basis"]["path"] == str(bundle)
    assert block["artifacts"]["manifest"]["path"] == str(manifest.absolute())


def test_an_absolute_declaration_stays_absolute(tmp_path, monkeypatch):
    """An external bundle is named as the record names it; nothing is relativised."""
    root, provenance, record, manifest = _corpus(tmp_path, monkeypatch)
    record["inputs"]["bundle_path"] = str(root / record["inputs"]["bundle_path"])
    record["inputs"]["chunks"]["path"] = str(manifest.absolute())
    provenance.write_text(yaml.safe_dump(record))
    blocks = bc.compute(provenance, only={"grounding", "receipts"})
    assert blocks["grounding"]["artifacts"]["bundle"]["path"] == record["inputs"]["bundle_path"]
    assert blocks["receipts"]["bundle_basis"]["path"] == record["inputs"]["bundle_path"]
    assert blocks["receipts"]["artifacts"]["manifest"]["path"] == record["inputs"]["chunks"]["path"]
