"""The `data/_wcrate` copies are the bytes `index.yaml` recorded (#5060 F6).

The copies were made byte-identical to their originals on 2026-10-14
(#5042). An original may since be rewritten (a provenance record is
re-recorded, a check block recomputed), so what stays checkable is the copy
against the sha256 and size recorded beside it, not against today's original.
"""
import hashlib
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
    on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "data" / "_wcrate" / "AI_READI").rglob("*")
               if p.is_file()}
    assert on_disk == {f["copy"] for f in _entries()}


@pytest.mark.parametrize("entry", _entries(), ids=lambda e: e["copy"].removeprefix("data/_wcrate/"))
def test_each_copy_is_the_recorded_bytes(entry):
    raw = (ROOT / entry["copy"]).read_bytes()
    assert len(raw) == entry["bytes"]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
