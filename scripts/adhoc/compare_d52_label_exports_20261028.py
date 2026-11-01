#!/usr/bin/env python3
# Purpose: prove D52 publication D1 changes display/identity, not numeric evidence.
# Inputs: original baseline and fixed synthetic canary exports; outputs: fresh JSON proof.
# Refs D52 review D1, #2912/#5121; 2026-10-28. Offline, read-only inputs.
import argparse
import hashlib
import json
from pathlib import Path


def differences(before, after, path=""):
    if type(before) is not type(after):
        return [{"path": path, "before": before, "after": after}]
    if isinstance(before, dict) and before.keys() == after.keys():
        return [row for key in sorted(before) for row in differences(before[key], after[key], path + "/" + key)]
    if isinstance(before, list) and len(before) == len(after):
        return [row for i, (left, right) in enumerate(zip(before, after))
                for row in differences(left, right, path + "/" + str(i))]
    return [] if before == after else [{"path": path, "before": before, "after": after}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = [path.read_bytes() for path in (args.before, args.after)]
    before, after = map(json.loads, raw)
    if len(before) != 1 or len(after) != 1:
        raise ValueError("exactly one synthetic evaluation per canary required")
    positions = [[i for i, question in enumerate(data[0]["rubric20"]["questions"]) if question["id"] == 9]
                 for data in (before, after)]
    if len(positions[0]) != 1 or positions[0] != positions[1]:
        raise ValueError("Q9 identity changed")
    prefix = f"/0/rubric20/questions/{positions[0][0]}"
    labels = {prefix + "/score_label", prefix + "/unit_scores/0/label"}
    identity = {"/0/instrument/sha256", "/0/instrument/inputs/runner"}
    allowed = labels | identity | {"/0/file_path", "/0/timestamp"}
    changes = differences(before, after)
    changed = {row["path"] for row in changes}
    if not labels | identity <= changed or not changed <= allowed:
        raise ValueError("unexpected exported change: " + repr(changes))
    result = {
        "format": "d52_display_only_comparison_v1", "changes": changes,
        "numeric_scores_maxima_and_evidence_unchanged": True,
        "scope": "one synthetic canary; no corpus rescore or scientific acceptance",
        "inputs": [{"path": str(path.resolve()), "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest()}
                   for path, content in zip((args.before, args.after), raw)],
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if json.loads(args.output.read_bytes()) != result:
        raise ValueError("persisted proof differs")
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
