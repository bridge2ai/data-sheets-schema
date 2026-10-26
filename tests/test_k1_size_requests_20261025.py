"""Exact-bound checks for K1's historical whole-root instrument (2026-10-25).

2026-10-26: isolate the exact A16 source fixture after A17 changed both the
inventory interface and indivisible-unit semantics. Assertions stay unchanged.
"""
import hashlib
from pathlib import Path
import types
import pytest

from scripts.adhoc.k1_size_requests_20261025 import planning_bounds


_fixture = Path(__file__).parent / "fixtures/k1/audit_batches_56c41163f.py.txt"
_raw = _fixture.read_bytes()
assert hashlib.sha256(_raw).hexdigest() == "c95ec83f2f730df8c9766173f4d71367dfe705b08ec4acc4a17f8ef002da4414"
batches = types.ModuleType("data_sheets_schema._k1_historical_audit_batches_56c41163f")
batches.__package__ = "data_sheets_schema"
batches.__file__ = str(_fixture)
exec(compile(_raw, str(_fixture), "exec"), batches.__dict__)


def test_root_minima_refuse_one_less_and_actual_worker_bound():
    raw = "a:\n- alpha\n- beta\nb:\n- gamma\n- delta\nc: " + "x" * 300 + "\n"
    result = planning_bounds(batches, raw)
    limits = result["componentwise_minimum"]
    plan = batches.make_plan(raw, **limits, version=2)
    assert len(plan["workers"]) == limits["max_workers"]
    for key in ("max_paths", "max_inventory_bytes", "max_workers"):
        if limits[key] > 1:
            with pytest.raises(batches.AuditBatchError):
                batches.make_plan(raw, **{**limits, key: limits[key] - 1}, version=2)
    assert result["inventory_path_count"] == 5
    assert len(result["indivisible_roots"]) == 3


def test_four_worker_lexicographic_point_is_tight():
    raw = "\n".join(f"field{i}: value{i}" for i in range(11)) + "\n"
    result = planning_bounds(batches, raw)
    limits = result["four_worker_lexicographic_point"]["limits"]
    assert len(batches.make_plan(raw, **limits, version=2)["workers"]) <= 4
    with pytest.raises(batches.AuditBatchError):
        batches.make_plan(raw, **{**limits, "max_paths": limits["max_paths"] - 1,
                                 "max_inventory_bytes": 1_000_000}, version=2)
    with pytest.raises(batches.AuditBatchError):
        batches.make_plan(raw, **{**limits, "max_inventory_bytes": limits["max_inventory_bytes"] - 1}, version=2)


def test_empty_and_escaped_roots_are_preserved():
    assert planning_bounds(batches, "{}\n")["minimum_plan"]["workers"][0]["paths"] == []
    result = planning_bounds(batches, "'a/b':\n  '~x': 0\nempty: []\nflag: false\n")
    assert [row["root"] for row in result["indivisible_roots"]] == ["/a~1b", "/empty", "/flag"]
    assert result["inventory_path_count"] == 2


def test_measure_refuses_scratch_outside_source_tree(tmp_path):
    from types import SimpleNamespace
    from scripts.adhoc.k1_size_requests_20261025 import measure
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    with pytest.raises(ValueError, match="within the selected root"):
        measure(None, SimpleNamespace(root=root), "CHORUS", "label", {}, outside)
    assert not outside.exists()
