"""The `data/_wcrate` copies are the bytes `index.yaml` recorded (#5060 F6).

The copies were made byte-identical to their originals on 2026-10-14
(#5042). An original may since be rewritten (a provenance record is
re-recorded, a check block recomputed), so what stays checkable is the copy
against the sha256 and size recorded beside it, not against today's original.
`.gitattributes` marks the folder `-text`, so no line-ending conversion on
checkout can change those bytes (#5083 N3).
"""
import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "_wcrate" / "index.yaml"


def _entries():
    if not INDEX.exists():
        return []
    index = yaml.safe_load(INDEX.read_text(encoding="utf-8"))
    return [f for record in index["records"] for f in record["files"]]


def test_the_index_counts_what_it_lists():
    if not INDEX.exists():
        pytest.skip("data/_wcrate is not in this checkout")
    index = yaml.safe_load(INDEX.read_text(encoding="utf-8"))
    assert len(index["records"]) == index["record_count"]
    assert len(_entries()) == index["file_count"]
    # The tracked files, so an untracked .DS_Store a Finder window leaves is
    # not a copy (#5083 M1).
    try:
        out = subprocess.run(["git", "ls-files", "-z", "data/_wcrate/AI_READI"], cwd=ROOT,
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"the tracked copies need git: {exc}")
    tracked = {p for p in out.decode().split("\0") if p}
    listed = {f["copy"] for f in _entries()}
    assert sorted(tracked - listed) == [], "tracked copies index.yaml does not list"
    assert sorted(listed - tracked) == [], "copies index.yaml lists that are not tracked"


@pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["copy"].removeprefix("data/_wcrate/"))
def test_each_copy_is_the_recorded_bytes(entry):
    raw = (ROOT / entry["copy"]).read_bytes()
    assert len(raw) == entry["bytes"]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
