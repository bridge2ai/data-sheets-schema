#!/usr/bin/env python3
"""Independent check of where each cpu-monitoring run was refused.

Purpose: AGY4's analysis of the D132 diagnostic says the 382f run passed two
  freshness checks that the 3cc113 and 458887 runs failed, and was refused
  later, at the pre-reservation check. This script re-derives that from the
  saved measurement files without using AGY4's script or JSON: for each run it
  lists the launch-phase call rows whose label mentions freshness, with their
  outcome and the capture age when the row was entered, and the launch
  phase's row range and CPU.
Inputs: the three run directories under scratch-native-u1u3/u3m (arguments).
Outputs: text on stdout only. Reads only.
Serves: owner decision D132 (2026-11-11); native track.
Date: 2026-11-11
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timezone


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> int:
    for run in sys.argv[1:]:
        measurement = json.load(open(glob.glob(os.path.join(run, "phase-metrics", "*-measurement.json"))[0]))
        diagnostic = json.load(open(glob.glob(os.path.join(run, "phase-metrics", "*-diagnostic.json"))[0]))
        capture = parse(diagnostic["capture_timestamp"])
        launch = [p for p in measurement["phases"] if p["name"] == "launch"][0]
        first, last = launch["first_call_row"], launch["last_call_row_exclusive"]
        calls = measurement["calls"]
        print(f"== {os.path.basename(run)}")
        print(f"   outcome {diagnostic['outcome']}; error {diagnostic.get('error')}")
        print(f"   launch rows {first}..{last} ({last - first} rows); process CPU "
              f"{launch['elapsed']['process_cpu']:.2f} s; wall {launch['elapsed']['wall_monotonic']:.2f} s")
        if first == 457 or True:
            sample = calls[first]
            if run == sys.argv[1]:
                print("   row keys:", sorted(sample.keys()) if isinstance(sample, dict) else type(sample).__name__)
        for index in range(first, last):
            row = calls[index]
            label = str(row.get("label") or row.get("name") or "")
            if "fresh" not in label.lower():
                continue
            entered = row.get("entered_utc") or (row.get("before") or {}).get("utc")
            age = (parse(entered) - capture).total_seconds() if entered else None
            outcome = row.get("outcome")
            age_text = "n/a" if age is None else f"{age:.2f}"
            print(f"   row {index:5d}  {label:34s} outcome {str(outcome)[:60]:60s} capture age at entry {age_text} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
