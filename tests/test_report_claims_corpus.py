"""Recorded report measurements must reproduce, including snapshot evidence."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import backfill_checks as bc, report_claims as rc


RELEASE_HISTORY = Path("src/data_sheets_schema/schema/release_history.yaml")


def registered_schema_pairs() -> list[dict]:
    """The merged-schema hash pairs a checked block may attest (#1874).

    A block records the hashes of the schema files its check ran under. A
    schema release moves them, and the historical blocks are never rewritten
    (#1362, #1363), so a block may attest any registered release and a fresh
    recompute must attest the newest one.
    """
    releases = yaml.safe_load(RELEASE_HISTORY.read_text(encoding="utf-8"))["releases"]
    return [{"full_sha256": r["full_merged_sha256"], "core_sha256": r["core_merged_sha256"]}
            for r in releases]


def assert_measurement_matches(stored, fresh, context, expected_origin, *, schemas=None):
    """Compare measurements without recasting original-run checks as backfills.

    The runner omits recorded_by; compute() necessarily adds its own origin.
    Only this documented difference is allowed. The stored origin must match
    the frozen path inventory, and every other value and key must reproduce.
    Work on a copy so even an in-memory comparison preserves the attestation.

    With `schemas` (the registered release pairs, newest last) the `schema`
    block is compared against the registry instead of byte-for-byte: the
    stored pair must be a registered release and the fresh pair the newest
    one, so a registered schema release does not read as a measurement
    change and an unregistered schema still does. Without it the block is
    compared exactly, like every other field.
    """
    assert fresh.get("recorded_by") == bc.RECORDED_BY, context
    assert expected_origin in (None, bc.RECORDED_BY), context
    if expected_origin is None:
        assert "recorded_by" not in stored, context
    else:
        assert stored.get("recorded_by") == expected_origin, context
    expected = {**stored, "recorded_by": bc.RECORDED_BY}
    if schemas is None:
        assert fresh == expected, context
        return
    assert ("schema" in stored) == ("schema" in fresh), context
    if "schema" in stored:
        assert stored["schema"] in schemas, f"{context}: unregistered schema attested"
        assert fresh["schema"] == schemas[-1], f"{context}: recompute is not under the newest release"
    expected = {k: v for k, v in expected.items() if k != "schema"}
    assert {k: v for k, v in fresh.items() if k != "schema"} == expected, context


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


@pytest.mark.parametrize("stored_pair,fresh_pair,ok", [
    ("prior", "newest", True),      # a block checked before the 3.0.0 boundary
    ("newest", "newest", True),     # a block checked after it
    ("prior", "prior", False),      # a recompute that is not under the newest release
    ("other", "newest", False),     # a block attesting no registered release
    ("newest", "other", False),     # a recompute under an unregistered schema
])
def test_a_registered_schema_release_is_not_a_measurement_change(stored_pair, fresh_pair, ok):
    """#1874: the blocks attest the schema hashes they were checked under and
    are never rewritten; the release history says which pairs are releases."""
    pairs = {"prior": {"full_sha256": "a" * 64, "core_sha256": "b" * 64},
             "newest": {"full_sha256": "c" * 64, "core_sha256": "d" * 64},
             "other": {"full_sha256": "e" * 64, "core_sha256": "f" * 64}}
    schemas = [pairs["prior"], pairs["newest"]]
    stored = {"checked": True, "claims_checked": 25, "findings": [], "schema": pairs[stored_pair]}
    fresh = {**deepcopy(stored), "schema": pairs[fresh_pair], "recorded_by": bc.RECORDED_BY}
    if ok:
        assert_measurement_matches(stored, fresh, "synthetic report", None, schemas=schemas)
    else:
        with pytest.raises(AssertionError):
            assert_measurement_matches(stored, fresh, "synthetic report", None, schemas=schemas)
    # A measurement change is still a failure under the registry comparison.
    with pytest.raises(AssertionError):
        assert_measurement_matches(stored, {**fresh, "claims_checked": 26}, "synthetic report", None,
                                   schemas=schemas)


def test_the_release_history_ends_at_the_schema_on_disk():
    from data_sheets_schema.provenance import (CORE_SCHEMA, CORE_SOURCE_SCHEMA, FULL_SCHEMA,
                                               declared_schema_version)
    pairs = registered_schema_pairs()
    assert len(pairs) >= 2
    assert pairs[-1] == {"full_sha256": bc._schema_sha(FULL_SCHEMA),
                         "core_sha256": bc._schema_sha(CORE_SCHEMA)}
    assert len({json.dumps(p, sort_keys=True) for p in pairs}) == len(pairs)
    # #1890: a moved schema re-registered under the same label is the #1874
    # drift with a registry entry blessing it. Labels are unique, strictly
    # increasing, and the newest is what both entry points declare.
    releases = yaml.safe_load(RELEASE_HISTORY.read_text(encoding="utf-8"))["releases"]
    versions = [str(r["version"]) for r in releases]
    keys = [tuple(int(x) for x in v.split(".")) for v in versions]
    assert keys == sorted(set(keys)), versions
    assert versions[-1] == declared_schema_version() == declared_schema_version(CORE_SOURCE_SCHEMA)


@pytest.mark.parametrize("side", ["stored", "fresh"])
def test_a_schema_block_present_on_one_side_only_is_a_mismatch(side):
    """#1895: the registry comparison never reaches the lookup when one side
    lacks the block; it fails as any other missing key would."""
    schemas = [{"full_sha256": "a" * 64, "core_sha256": "b" * 64}]
    stored = {"checked": True, "claims_checked": 25, "findings": []}
    fresh = {**stored, "recorded_by": bc.RECORDED_BY}
    (stored if side == "stored" else fresh)["schema"] = schemas[0]
    with pytest.raises(AssertionError):
        assert_measurement_matches(stored, fresh, "synthetic report", None, schemas=schemas)


@pytest.mark.corpus
def test_all_report_measurements_reproduce_with_the_registered_aggregate():
    declared, ranges = rc.declared_slots(), rc.declared_ranges()
    schemas = registered_schema_pairs()
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
        # These are frozen v7 measurements, not a request to replace them
        # with the current v8 reading (#1808). Keep every field comparable.
        assert stored["instrument"] == rc.REPORT_CLAIMS_INSTRUMENT_V7
        fresh = bc.compute(path, only={"report_claims"}, declared=declared, ranges=ranges,
                           report_claims_version=7)["report_claims"]
        # #1874: a schema release moves the hashes every checked block attests;
        # the blocks stay as written and the release history says which pairs
        # a block may attest. Every measurement must still reproduce exactly.
        assert_measurement_matches(stored, fresh, str(path), origins[str(path)], schemas=schemas)
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
