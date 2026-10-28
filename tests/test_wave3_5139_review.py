"""Independent #5139 review, 2026-10-26.

Inputs: synthetic local bundles and historical chunk-manifest pins. Outputs:
offline pytest results for lexical path identity and containment; no providers.
"""
import hashlib
from pathlib import Path

import pytest
import yaml

from data_sheets_schema.evaluation import arm_comparison


@pytest.mark.parametrize("prefix", ["", "archive-copy"])
def test_absolute_owned_manifest_keeps_its_exact_git_path(tmp_path, prefix):
    folder = tmp_path / prefix / "data/preprocessed/individual/CHORUS"
    folder.mkdir(parents=True)
    bundle = folder / "CHORUS_preprocessed.txt"
    bundle.write_bytes(b"synthetic source\n")
    manifest = folder / "CHORUS_chunks.yaml"
    original = yaml.safe_dump({"bundle": bundle.name,
        "bundle_md5": hashlib.md5(bundle.read_bytes()).hexdigest(), "chunks": []}).encode()
    manifest.write_bytes(b"changed current manifest\n")
    record = {"inputs": {"bundle_path": str(bundle),
        "bundle_md5": hashlib.md5(bundle.read_bytes()).hexdigest(),
        "chunks": {"path": str(manifest), "sha256": hashlib.sha256(original).hexdigest()}}}
    requested = []
    exact = manifest.relative_to(tmp_path).as_posix()
    def recover(path, **pins):
        requested.append(path)
        return (original, {}) if path == exact else None
    result = arm_comparison.bundle_drift(record, tmp_path, recover=recover)
    assert requested == [exact], "historical recovery must use the recorded lexical path"
    assert result["manifest_status"] == "match"


def test_foreign_tail_does_not_follow_an_escape_symlink(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    (target / "bundle.txt").write_text("outside source")
    (root / "data").mkdir()
    (root / "data/preprocessed").symlink_to(target, target_is_directory=True)
    assert arm_comparison._path(root, "/old/checkout/data/preprocessed/bundle.txt") is None


@pytest.mark.parametrize("value", ["../outside.txt", "/old/checkout/data/preprocessed/../../../../outside.txt", "x\x00y"])
def test_unowned_or_malformed_paths_remain_unknown(tmp_path, value):
    assert arm_comparison._path(tmp_path, value) is None
