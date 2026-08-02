#!/usr/bin/env python
"""How many generated records validate, and why the rest do not.

Written because #215 has no "fix": the records are what the generator produced,
so editing them would falsify the experiment and break the artifact hashes their
provenance pins. The failures are evidence about generation quality, and the
useful response is to measure them rather than repair them.

Forward fixes exist for two of the three causes — `normalise_temporal()` on
write, and the DataCite-aligned enum plus its exposure in the schema digest —
so a rerun should show a different profile. This script is how that gets
checked.

    python scripts/validation_profile.py                 # the 2026-07-31 sweep
    python scripts/validation_profile.py --label 2026-08 # any label prefix
"""

from __future__ import annotations

import argparse
import collections
import glob
import os
import re
import subprocess
import sys

SCHEMA = {
    "Dataset": "src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
    "CoreDataset": "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml",
}


def classify(error: str) -> str:
    """The shape of the failure, not its wording."""
    if "is not a 'date-time'" in error or "is not a 'date'" in error:
        return "temporal format"
    if (m := re.search(r"'([^']+)' is not one of", error)):
        return f"enum value not permitted: {m.group(1)[:40]}"
    if "is not valid under any of the given schemas" in error:
        return "union: no matching shape"
    if (m := re.search(r"is not of type '(\w+)'", error)):
        return f"wrong type (expected {m.group(1)})"
    if "is a required property" in error:
        return "missing required property"
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="2026-07-31",
                    help="label prefix to profile (default: the sweep)")
    args = ap.parse_args()

    records = sorted(glob.glob(
        f"data/d4d_concatenated/*/{args.label}*/*_d4d*.yaml"))
    if not records:
        print(f"no records under label prefix {args.label!r}", file=sys.stderr)
        return 1

    by_arm = collections.Counter()
    failures = collections.Counter()
    invalid_by_arm = collections.Counter()
    causes_per_record: dict[str, set[str]] = {}
    valid = 0

    for path in records:
        cls = "CoreDataset" if path.endswith("_core.yaml") else "Dataset"
        arm = path.split("/")[2]
        by_arm[arm] += 1
        r = subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", SCHEMA[cls],
             "-C", cls, path],
            capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            valid += 1
            continue
        invalid_by_arm[arm] += 1
        seen = set()
        for line in (r.stdout + r.stderr).splitlines():
            if "ERROR" not in line:
                continue
            kind = classify(line)
            if kind not in seen:            # one vote per record per kind
                seen.add(kind)
                failures[kind] += 1
        causes_per_record[path] = seen

    total = len(records)
    print(f"label prefix: {args.label}")
    print(f"{valid}/{total} records validate "
          f"({valid / total:.0%}), {total - valid} do not\n")

    print("by arm (invalid / total)")
    for arm in sorted(by_arm):
        print(f"  {arm:34s} {invalid_by_arm[arm]:3d} / {by_arm[arm]:3d}")

    print("\nfailure kinds (records affected; a record may have several, so "
          "these sum to more than the record count)")
    for kind, n in failures.most_common():
        print(f"  {n:3d}  {kind}")

    spread = collections.Counter(len(v) for v in causes_per_record.values())
    print("\ncauses per failing record")
    for k in sorted(spread):
        print(f"  {spread[k]:3d} record(s) with {k} distinct cause(s)")

    # The number that matters is records whose *every* cause has a forward fix.
    # Summing the cause counts instead overstates it — that error put the
    # prediction in the first draft of the profile note at 3 when it is 7.
    fixed_forward = {"temporal format"}
    clearable = [p for p, kinds in causes_per_record.items()
                 if kinds and all(k in fixed_forward or k.startswith("enum value")
                                  for k in kinds)]
    print(f"\n{len(clearable)} of {len(causes_per_record)} failing records have "
          f"*every* cause fixed forward (temporal or enum).")
    print(f"A rerun under the current schema and digest should leave "
          f"{len(causes_per_record) - len(clearable)}, not zero: the rest carry "
          f"at least one cause with no forward fix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
