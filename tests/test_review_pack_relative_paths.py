"""A review pack states its bundle paths relative to the resource root (#6379).

The pack is pinned by sha256 in its review and in the provenance record. Two
absolute paths (`bundle.manifest`, `bundle.resolved_path`) made the same pack
differ between two checkouts of one commit and put the generating machine's
directory layout into a committed file.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from data_sheets_schema import resources, review_pack


def test_a_path_under_the_resource_root_is_stated_relative_to_it(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    target = root / "data" / "preprocessed" / "chunks" / "x_chunks.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("chunks: []\n")
    monkeypatch.setattr(resources, "resource_root", lambda: (root, "checkout"))

    assert review_pack._pack_path(target) == "data/preprocessed/chunks/x_chunks.yaml"


def test_two_checkouts_at_different_locations_state_the_same_path(tmp_path, monkeypatch):
    stated = []
    for name in ("first", "second/nested"):
        root = tmp_path / name
        target = root / "data" / "bundle.txt"
        target.parent.mkdir(parents=True)
        target.write_text("text\n")
        monkeypatch.setattr(resources, "resource_root", lambda root=root: (root, "checkout"))
        stated.append(review_pack._pack_path(target))

    assert stated == ["data/bundle.txt", "data/bundle.txt"]


def test_a_path_under_no_root_is_stated_as_given(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    root.mkdir()
    elsewhere = tmp_path / "another_corpus" / "bundle.txt"
    elsewhere.parent.mkdir()
    elsewhere.write_text("text\n")
    monkeypatch.setattr(resources, "resource_root", lambda: (root, "checkout"))

    assert review_pack._pack_path(elsewhere) == str(elsewhere)


def test_a_symlinked_root_does_not_make_the_path_absolute(tmp_path, monkeypatch):
    real = tmp_path / "real"
    (real / "data").mkdir(parents=True)
    (real / "data" / "bundle.txt").write_text("text\n")
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr(resources, "resource_root", lambda: (link, "checkout"))

    assert review_pack._pack_path(real / "data" / "bundle.txt") == "data/bundle.txt"


@pytest.mark.corpus
def test_a_pack_built_from_a_committed_record_carries_no_absolute_bundle_path():
    root, kind = resources.resource_root()
    if kind != "checkout":
        pytest.skip("needs a checkout with the corpus")
    core = Path(root) / "data" / "d4d_concatenated"
    records = sorted(core.glob("*_core/*/*_provenance.yaml"))
    built = None
    for provenance in reversed(records):          # newest labels first: they carry a chunk manifest
        pack = review_pack.build_pack(provenance, None, None, write_instruction=False, instruction_out=[])
        if pack["bundle"].get("manifest") and pack["bundle"].get("resolved_path"):
            built = pack
            break
    assert built is not None, "no committed record resolves both a bundle and a chunk manifest"

    assert not Path(built["bundle"]["manifest"]).is_absolute()
    assert not Path(built["bundle"]["resolved_path"]).is_absolute()
    assert built["bundle"]["resolved_path"] == built["bundle"]["path"]
