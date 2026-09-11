"""The v7 corpus measurement must reproduce, including snapshot evidence."""
from collections import Counter
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import backfill_checks as bc, report_claims as rc


@pytest.mark.corpus
def test_all_report_measurements_reproduce_with_the_registered_aggregate():
    declared, ranges = rc.declared_slots(), rc.declared_ranges()
    blocks = []
    for path in sorted(Path("data/d4d_concatenated").rglob("*_provenance.yaml")):
        stored = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("report_claims") or {}
        if not stored.get("checked"):
            continue
        fresh = bc.compute(path, only={"report_claims"}, declared=declared, ranges=ranges)["report_claims"]
        assert fresh == stored, str(path)
        blocks.append(fresh)
    assert len(blocks) == 277
    assert Counter(f["kind"] for b in blocks for f in b["findings"]) == {
        "removal_not_performed": 41, "false_schema_claim": 23,
        "change_not_shown": 6, "retention_not_shown": 10, "removal_not_recorded": 3,
    }
    assert sum(b["claims_checked"] for b in blocks) == 1033
    assert sum(b["prose_retention_claims"] for b in blocks) == 164
    assert sum(b.get("removals_unrecorded_count") or 0 for b in blocks) == 41
    assert sum(b["snapshot_checked"] for b in blocks) == 86
