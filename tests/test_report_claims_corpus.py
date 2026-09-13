"""Recorded report measurements must reproduce, including snapshot evidence."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import backfill_checks as bc, report_claims as rc


def assert_measurement_matches(stored, fresh, context, expected_origin):
    """Compare measurements without recasting original-run checks as backfills.

    The runner omits recorded_by; compute() necessarily adds its own origin.
    Only this documented difference is allowed. The stored origin must match
    the frozen path inventory, and every other value and key must reproduce.
    Work on a copy so even an in-memory comparison preserves the attestation.
    """
    assert fresh.get("recorded_by") == bc.RECORDED_BY, context
    assert expected_origin in (None, bc.RECORDED_BY), context
    if expected_origin is None:
        assert "recorded_by" not in stored, context
    else:
        assert stored.get("recorded_by") == expected_origin, context
    expected = {**stored, "recorded_by": bc.RECORDED_BY}
    assert fresh == expected, context


@pytest.mark.parametrize("backfilled", [False, True])
def test_original_run_and_backfill_measurements_reproduce_without_mutation(backfilled):
    stored = {"checked": True, "claims_checked": 25, "findings": [],
              "artifacts": {"phase1_snapshot": {"sha256": "a" * 64}}}
    if backfilled:
        stored["recorded_by"] = bc.RECORDED_BY
    original = deepcopy(stored)
    fresh = {**deepcopy(stored), "recorded_by": bc.RECORDED_BY}
    assert_measurement_matches(stored, fresh, "synthetic report",
                               bc.RECORDED_BY if backfilled else None)
    assert stored == original


@pytest.mark.parametrize("origin", [None, "", "unknown", "api_runner.execute"])
@pytest.mark.parametrize("side", ["stored", "fresh"])
def test_unknown_report_origins_are_rejected(origin, side):
    stored = {"checked": True}
    fresh = {"checked": True, "recorded_by": bc.RECORDED_BY}
    (stored if side == "stored" else fresh)["recorded_by"] = origin
    with pytest.raises(AssertionError):
        assert_measurement_matches(stored, fresh, "synthetic report", None)


@pytest.mark.parametrize("expected_origin", [None, bc.RECORDED_BY])
def test_swapping_native_and_historical_origins_is_rejected(expected_origin):
    # This also exercises deletion of a historical marker. Both blocks have
    # exactly the same measurements; only the recorded origin changes.
    stored = {"checked": True, "claims_checked": 25, "findings": []}
    if expected_origin is None:
        stored["recorded_by"] = bc.RECORDED_BY
    fresh = {**stored, "recorded_by": bc.RECORDED_BY}
    with pytest.raises(AssertionError):
        assert_measurement_matches(stored, fresh, "synthetic report", expected_origin)


@pytest.mark.parametrize("changed", [
    {"claims_checked": 26},
    {"findings": [{"kind": "false_schema_claim"}]},
    {"artifacts": {"phase1_snapshot": {"sha256": "b" * 64}}},
    {"schema": {"core_sha256": "b" * 64}},
    {"instrument": "different instrument"},
    {"unexpected": "field"},
])
def test_authorship_handling_does_not_hide_measurement_or_pin_changes(changed):
    stored = {"checked": True, "claims_checked": 25, "findings": [],
              "artifacts": {"phase1_snapshot": {"sha256": "a" * 64}},
              "schema": {"core_sha256": "a" * 64},
              "instrument": "registered instrument"}
    fresh = {**deepcopy(stored), "recorded_by": bc.RECORDED_BY, **changed}
    with pytest.raises(AssertionError):
        assert_measurement_matches(stored, fresh, "synthetic report", None)


@pytest.mark.corpus
def test_all_report_measurements_reproduce_with_the_registered_aggregate():
    declared, ranges = rc.declared_slots(), rc.declared_ranges()
    # #1363: do not infer an origin from a block whose origin is being checked.
    # Null means the marker was absent in the registered original-run block;
    # it never means a null-valued recorded_by field is allowed.
    origins = json.loads(Path("tests/data/report_claims_origins.json").read_text())["origins"]
    blocks = []
    seen = set()
    for path in sorted(Path("data/d4d_concatenated").rglob("*_provenance.yaml")):
        stored = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("report_claims") or {}
        if not stored.get("checked"):
            continue
        assert str(path) in origins, f"unregistered checked report: {path}"
        fresh = bc.compute(path, only={"report_claims"}, declared=declared, ranges=ranges)["report_claims"]
        assert_measurement_matches(stored, fresh, str(path), origins[str(path)])
        blocks.append(fresh)
        seen.add(str(path))
    assert seen == set(origins), "registered report measurements are missing or unchecked"
    # #1361: the September 12 v9 canary adds one original-run block to the
    # historical 277 backfilled blocks, with 25 claims, one prose-retention
    # claim and one checked snapshot. The historical measurements and all
    # findings remain unchanged; no provenance file is rewritten.
    assert len(blocks) == 278
    assert Counter(f["kind"] for b in blocks for f in b["findings"]) == {
        "removal_not_performed": 41, "false_schema_claim": 23,
        "change_not_shown": 6, "retention_not_shown": 10, "removal_not_recorded": 3,
    }
    assert sum(b["claims_checked"] for b in blocks) == 1058
    assert sum(b["prose_retention_claims"] for b in blocks) == 165
    assert sum(b.get("removals_unrecorded_count") or 0 for b in blocks) == 41
    assert sum(b["snapshot_checked"] for b in blocks) == 87
