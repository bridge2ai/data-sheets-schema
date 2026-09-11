#!/usr/bin/env python3
"""Compare removal suppression before/after a parser change (#1196).

Use a saved report_claims.py as --baseline-source. Each report is tested
against a synthetic snapshot containing every slot it names, followed by
empty records. Thus a name that suppresses a hypothetical removal is visible
even when the real corpus has not dropped that slot. This calls the actual
checker on both sides; it does not reimplement its clause parsing.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import yaml

from data_sheets_schema import backfill_checks as bc, report_claims as current


def compare(baseline_source: Path) -> dict:
    spec = importlib.util.spec_from_file_location("report_claims_baseline", baseline_source)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    declared, ranges = current.declared_slots(), current.declared_ranges()
    totals = {"reports": 0, "before": 0, "after": 0, "gained": 0, "lost": 0}
    changes = {}
    for provenance in sorted(Path("data/d4d_concatenated").rglob("*_provenance.yaml")):
        record = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}
        if not (record.get("report_claims") or {}).get("checked"):
            continue
        report = bc.record_paths(provenance)["report"]
        raw = report.read_bytes()
        names = {n for n in current._TICKED.findall(raw.decode("utf-8"))
                 if current._SLOT_PATH.fullmatch(n) and n not in current._SNAPSHOT_EXEMPT}
        snapshot = dict.fromkeys(names, 1)
        suppressed = []
        for checker in (baseline, current):
            result = checker.check_report(report, {}, {}, declared, snapshot=snapshot,
                                          ranges=ranges)
            suppressed.append(names - set(result["removals_unrecorded"]))
        before, after = suppressed
        gained, lost = sorted(after - before), sorted(before - after)
        totals["reports"] += 1
        totals["before"] += len(before)
        totals["after"] += len(after)
        totals["gained"] += len(gained)
        totals["lost"] += len(lost)
        if gained or lost:
            changes[str(report)] = {"sha256": hashlib.sha256(raw).hexdigest(),
                                    "gained": gained, "lost": lost}
    return {"basis": __doc__.strip(),
            "baseline_source_sha256": hashlib.sha256(baseline_source.read_bytes()).hexdigest(),
            "before_instrument": baseline.REPORT_CLAIMS_INSTRUMENT,
            "after_instrument": current.REPORT_CLAIMS_INSTRUMENT,
            "totals": totals, "changes": changes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.baseline_source)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["totals"]))


if __name__ == "__main__":
    main()
