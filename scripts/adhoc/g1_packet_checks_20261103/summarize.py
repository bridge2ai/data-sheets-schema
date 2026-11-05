#!/usr/bin/env python3
# Purpose: summarize persisted pytest evidence and changed shared-generation pins.
# Inputs: scratch directory containing checks and packet/final-identity.json.
# Outputs: JSON summary on stdout; G1V-1/G1V-2, 2026-11-03. Read only.
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

scratch = Path(sys.argv[1])
checks = {}
for path in sorted(scratch.glob("*/pytest.xml")):
    root = ET.parse(path).getroot()
    suites = list(root) if root.tag == "testsuites" else [root]
    checks[path.parent.name] = {
        **{key: sum(int(suite.get(key, 0)) for suite in suites)
           for key in ("tests", "failures", "errors", "skipped")},
        "seconds": sum(float(suite.get("time", 0)) for suite in suites),
        "failed": [{"class": case.get("classname"), "name": case.get("name"),
                    "message": problem.get("message")}
                   for case in root.iter("testcase") for problem in case
                   if problem.tag in {"failure", "error"}],
        "exit_status": (path.parent / "exit-status.txt").read_text().strip(),
    }


def differences(before, after, path=()):
    if isinstance(before, dict) and isinstance(after, dict):
        return [item for key in sorted(before.keys() | after.keys())
                for item in differences(before.get(key), after.get(key), (*path, key))]
    return [] if before == after else [{"path": list(path), "before": before, "after": after}]


pins = []
if (scratch / "final-identity.json").exists():
    pins = differences(json.loads((scratch / "packet-identity.json").read_bytes()),
                       json.loads((scratch / "final-identity.json").read_bytes()))
print(json.dumps({"checks": checks, "changed_pins": pins}, indent=2, sort_keys=True))
