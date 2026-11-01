"""D76 / #5213: never select matching decoys via symlink-parent traversal.

These synthetic records distinguish the file named by the filesystem from a
hash-matching lexical decoy, for live input reads and historical manifest names.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import arm_comparison as ac


def _traversal_case(tmp_path, ownership, spelling, outside, name):
    root = tmp_path / "checkout"
    local = root / "data/preprocessed"
    local.mkdir(parents=True)
    source_root = root if ownership == "owned" else tmp_path / "foreign"
    source = source_root / "data/preprocessed"
    source.mkdir(parents=True, exist_ok=True)
    physical = tmp_path / "outside" if outside else root / "real"
    (physical / "child").mkdir(parents=True)
    (source / "link").symlink_to(physical / "child", target_is_directory=True)
    requested = source / "link" / ".." / name
    # relpath would erase the traversal whose filesystem meaning is under test.
    prefix = (Path("data/preprocessed") if ownership == "owned" else
              Path("../foreign/data/preprocessed"))
    recorded = str(requested if spelling == "absolute" else prefix / "link" / ".." / name)
    assert (root / recorded).resolve() == (physical / name).resolve()
    return root, local / name, physical / name, recorded


@pytest.mark.parametrize("ownership", ["owned", "foreign"])
@pytest.mark.parametrize("spelling", ["absolute", "relative"])
@pytest.mark.parametrize("outside", [False, True], ids=["inside-target", "outside-target"])
def test_bundle_traversal_cannot_select_hash_matching_decoy(
    tmp_path, monkeypatch, ownership, spelling, outside,
):
    root, decoy, actual, recorded = _traversal_case(
        tmp_path, ownership, spelling, outside, "bundle.txt")
    historical = b"historical input retained only by the decoy\n"
    decoy.write_bytes(historical)
    actual.write_bytes(b"actual input changed\n")
    requested = root / recorded
    assert requested.read_bytes() != historical
    assert requested.resolve() == actual.resolve()
    reads = []
    read_bytes = Path.read_bytes

    def observed_read(path):
        reads.append(path)
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", observed_read)
    record = {"inputs": {"bundle_path": recorded,
                         "bundle_md5": hashlib.md5(historical).hexdigest()}}
    result = ac.bundle_drift(record, root)
    assert result["disk_status"] == "unknown", result
    assert result["disk_md5"] is None
    assert decoy not in reads, "ambiguous spelling must not read the lexical replacement"


@pytest.mark.parametrize("ownership", ["owned", "foreign"])
@pytest.mark.parametrize("spelling", ["absolute", "relative"])
@pytest.mark.parametrize("outside", [False, True], ids=["inside-target", "outside-target"])
def test_chunk_traversal_cannot_select_pinned_decoy_or_invent_git_name(
    tmp_path, monkeypatch, ownership, spelling, outside,
):
    root, decoy, actual, recorded = _traversal_case(
        tmp_path, ownership, spelling, outside, "bundle.chunks.yaml")
    bundle = root / "bundle.txt"
    bundle.write_bytes(b"unchanged bundle\n")
    md5 = hashlib.md5(bundle.read_bytes()).hexdigest()
    historical = yaml.safe_dump({"bundle": bundle.name, "bundle_md5": md5, "chunks": []}).encode()
    decoy.write_bytes(historical)
    actual.write_bytes(b"different physical manifest\n")
    assert (root / recorded).read_bytes() != historical
    reads = []
    read_bytes = Path.read_bytes

    def observed_read(path):
        reads.append(path)
        return read_bytes(path)

    def no_recovery(*args, **kwargs):
        pytest.fail("ambiguous spelling must not become a historical Git name")

    monkeypatch.setattr(Path, "read_bytes", observed_read)
    record = {"inputs": {"bundle_path": str(bundle), "bundle_md5": md5,
                         "chunks": {"path": recorded,
                                    "sha256": hashlib.sha256(historical).hexdigest()}}}
    result = ac.bundle_drift(record, root, recover=no_recovery)
    assert result["disk_status"] == "match", "the independently named bundle still matches"
    assert result["manifest_status"] == "unknown", result
    assert result["manifest_md5"] is result["manifest_basis"] is None
    assert decoy not in reads

    # A mismatching decoy must not open a second route through Git recovery.
    decoy.write_bytes(b"changed decoy too\n")
    reads.clear()
    result = ac.bundle_drift(record, root, recover=no_recovery)
    assert result["manifest_status"] == "unknown"
    assert result["manifest_md5"] is result["manifest_basis"] is None
    assert decoy not in reads


@pytest.mark.parametrize("value", [
    "data/preprocessed/child/../bundle.txt",
    "/old/child/../checkout/data/preprocessed/bundle.txt",
])
def test_even_ordinary_parent_traversal_does_not_claim_a_historical_name(tmp_path, value):
    """No filesystem lookup can establish which Git name a historical path used."""
    root = tmp_path / "checkout"
    (root / "data/preprocessed/child").mkdir(parents=True)
    (root / "data/preprocessed/bundle.txt").write_bytes(b"historical\n")
    record = {"inputs": {"bundle_path": value,
                         "bundle_md5": hashlib.md5(b"historical\n").hexdigest()}}
    result = ac.bundle_drift(record, root)
    assert result["disk_status"] == "unknown"
    assert result["disk_md5"] is None
