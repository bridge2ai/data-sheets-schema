"""Exact-bound checks for K1's offline planner study (2026-10-25)."""
import pytest

from data_sheets_schema import audit_batches as batches
from scripts.adhoc.k1_size_requests_20261025 import planning_bounds


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
