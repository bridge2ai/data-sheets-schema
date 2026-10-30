"""Summarize sleep-patch measurements and refresh only requested CI weights.

Inputs: local JUnit/measurement files from sleep_patch_checks.py, original CI
weights. Outputs: JSON evidence and optional targeted timing updates. Serves
main's red CI run 41092033720; 2026-10-30. Uses the repository's JUnit aggregator.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.update_ci_shard_timings import build

RESULTS = ROOT / "test-results" / "sleep-patch"
AFFECTED = {
    "tests.test_report_admission", "tests.test_download.test_api_runner",
    "tests.test_source_review", "tests.test_duplicate_keys", "tests.test_backoff_sleep",
}


def cases(path):
    return [{**case.attrib, "outcome": ("failed" if case.find("failure") is not None
             or case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed")}
            for case in ET.fromstring(path.read_bytes()).iter("testcase")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--refresh-from", help="Label with a successful full-file or ordinary-shard run")
    parser.add_argument("--files", nargs="*", default=[])
    args = parser.parse_args()
    evidence = {"red_ci_run": 41092033720, "measurements": {}}
    for label in args.labels:
        directory = RESULTS / label
        measurement = json.loads((directory / "measurement.json").read_text())
        xml = directory / "pytest.xml"
        recorded = cases(xml)
        measurement.update(junit_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),
                           outcomes=dict(Counter(case["outcome"] for case in recorded)),
                           cases=[case for case in recorded if any(
                               case["classname"] == name or case["classname"].startswith(name + ".")
                               for name in AFFECTED)])
        waits = directory / "waits.json"
        if waits.exists():
            traces = json.loads(waits.read_text())
            measurement["timeout_waits"] = {
                "artifact_sha256": hashlib.sha256(waits.read_bytes()).hexdigest(),
                "calls": sum(row["count"] for row in traces.values()),
                "call_chains": sorted({tuple(re.findall(
                    r'/src/(data_sheets_schema/[^"\n]+)", line (\d+), in ([^\n]+)',
                    row["stack"])) for row in traces.values()}),
            }
        evidence["measurements"][label] = measurement
    if {"before-nine", "after-nine"}.issubset(evidence["measurements"]):
        before = evidence["measurements"]["before-nine"]
        after = evidence["measurements"]["after-nine"]
        index = {(row["classname"], row["name"]): row for row in after["cases"]}
        comparison = []
        for old in before["cases"]:
            new = index[(old["classname"], old["name"])]
            comparison.append({"classname": old["classname"], "name": old["name"],
                               "before_seconds": float(old["time"]), "after_seconds": float(new["time"]),
                               "before_outcome": old["outcome"], "after_outcome": new["outcome"]})
        evidence["nine_case_comparison"] = comparison
        for row in comparison:
            print(f"{row['name']}: {row['before_seconds']:.3f}s -> {row['after_seconds']:.3f}s")
    if args.refresh_from:
        if not args.files:
            parser.error("--refresh-from requires explicit --files")
        directory = RESULTS / args.refresh_from
        measurement = json.loads((directory / "measurement.json").read_text())
        if measurement["exit_code"] != 0:
            parser.error("timing source must be a successful run")
        # build() sums every JUnit occurrence and rejects failures/duplicates.
        # A local run is not a GitHub run; retain its actual origin separately.
        generated = build(directory, ROOT, None, measurement["commit"])
        selected = {name: generated["file_seconds"][name] for name in args.files}
        timing_path = ROOT / "utils" / "ci_test_durations.json"
        original = json.loads(timing_path.read_text())
        prior = {name: original["file_seconds"].get(name) for name in selected}
        original["file_seconds"].update(selected)
        original["file_seconds"] = dict(sorted(original["file_seconds"].items()))
        origin = {"kind": "local_offline_partial_refresh", "date": "2026-10-30",
                  "base_commit": measurement["commit"], "red_ci_run": 41092033720,
                  "python": measurement["python"], "packages_sha256": measurement["packages_sha256"],
                  "command": measurement["pytest_args"], "label": args.refresh_from,
                  "artifacts": generated["source"]["artifacts"],
                  "file_seconds_before": prior, "file_seconds": selected}
        original.setdefault("local_updates", []).append(origin)
        timing_path.write_text(json.dumps(original, indent=2) + "\n")
        evidence["timing_update"] = origin
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
