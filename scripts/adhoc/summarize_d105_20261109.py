#!/usr/bin/env python3
# Purpose: retain exact D105 test/corpus counts and SHA-256 artifact identities.
# Inputs: completed validate_d105_20261109 runs; output: scratch-d105 summary.
# Serves D105 offline secondary transformation receipts, 2026-11-09.
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-d105"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-label", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if Path(args.final_label).name != args.final_label or Path(args.output).name != args.output:
        parser.error("labels/output must be basenames within scratch-d105")
    runs = []
    for path in sorted(SCRATCH.glob("*/result.json")):
        result = json.loads(path.read_text())
        junit = path.parent / "junit.xml"
        suite = ET.parse(junit).getroot().find("testsuite") if junit.exists() else None
        runs.append({"label": path.parent.name, "result_sha256": digest(path),
                     "junit_sha256": digest(junit) if junit.exists() else None,
                     "exit_code": result["exit_code"],
                     "elapsed_seconds": result["elapsed_seconds"],
                     "counts": dict(suite.attrib) if suite is not None else None})
    corpus = []
    final = SCRATCH / args.final_label
    for path in sorted((final / "pytest").rglob("*_transformation_measure.json")):
        result = json.loads(path.read_text())
        corpus.append({"project": path.name.removesuffix("_transformation_measure.json"),
                       "receipt_path": str(path), "receipt_sha256": digest(path),
                       "counts": result["counts"],
                       "matches_derived_core": result["matches_derived_core"],
                       "input_digests": result["input_digests"],
                       "instrument": result["instrument"]})
    assert len(corpus) == 3 and {r["project"] for r in corpus} == {"CHORUS", "VOICE", "CM4AI"}
    final_result = json.loads((final / "result.json").read_text())
    assert final_result["exit_code"] == 0
    result = {"runs": runs, "final_label": args.final_label, "corpus": corpus}
    output = SCRATCH / args.output
    with output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"path": str(output), "sha256": digest(output),
                      "corpus": [{"project": r["project"], **r["counts"],
                                  "matches_derived_core": r["matches_derived_core"]} for r in corpus]}))


if __name__ == "__main__":
    main()
