#!/usr/bin/env python3
# Purpose: compare complete specificity finding identities for assistant repair #2088.
# Inputs: baseline and candidate scanner JSON reports; outputs: comparison JSON/stdout.
# Date: 2026-10-16. Offline only; preserves duplicate findings and does not edit reports.
"""Compare validated scan reports without treating unchanged violations as a clean scan."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read_report(path):
    raw = path.read_bytes()
    report = json.loads(raw)
    if report.get("self_test", {}).get("passed") is not True or report.get("exit") not in (0, 1):
        raise ValueError("both reports must have completed with a passing self-test")
    findings = report["violations"]
    if type(findings) is not list or len(findings) != report["totals"]["violations"]:
        raise ValueError("report findings differ from the reported total")
    for finding in findings:
        if finding.get("violation") is not True or not finding.get("path") or not finding.get("gates_in"):
            raise ValueError("malformed violation identity")
    # Compare every recorded field, including location, matched text, governing
    # approaches and classification. Counter preserves same-line duplicate hits.
    identities = Counter(json.dumps(item, sort_keys=True, ensure_ascii=False) for item in findings)
    pin = {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
           "bytes": len(raw), "commit": report.get("commit"), "root": report["root"]}
    return report, identities, pin


def rows(counts):
    return [{"count": count, "finding": json.loads(identity)}
            for identity, count in sorted(counts.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline, old, baseline_pin = read_report(args.baseline)
    candidate, new, candidate_pin = read_report(args.candidate)
    added, removed = new - old, old - new
    report = {"format": "assistant_specificity_comparison_v1", "issue": 2088,
        "baseline": baseline_pin, "candidate": candidate_pin,
        "baseline_violations": sum(old.values()), "candidate_violations": sum(new.values()),
        "identical_violations": sum((old & new).values()),
        "added": rows(added), "removed": rows(removed),
        "baseline_by_approach": baseline["totals"]["violations_by_approach"],
        "candidate_by_approach": candidate["totals"]["violations_by_approach"],
        "meaning": "Unchanged findings remain unresolved; equality does not establish a globally clean scan."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
    print(f"Baseline violations: {sum(old.values())}; candidate: {sum(new.values())}; "
          f"identical: {report['identical_violations']}; added: {sum(added.values())}; "
          f"removed: {sum(removed.values())}")
    print(f"Comparison: {args.output}")
    return 1 if added else 0


if __name__ == "__main__":
    raise SystemExit(main())
