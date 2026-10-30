#!/usr/bin/env python3
"""Summarize offline E3x x #5096 / #5213 checks, 2026-10-29.

Inputs: pytest evidence directory. Output: JSON to stdout, including
artifact hashes, outcomes, dependency identity and CI coverage counts.
No providers, source mutations, network access or rating runs.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def main():
    evidence = Path(sys.argv[1]).resolve()
    results = {}
    for log in sorted(evidence.glob("*.log")):
        label = log.stem
        text = log.read_text(errors="replace")
        row = {"summaries": [line.strip("= ") for line in text.splitlines()
                             if re.search(r"\d+ (?:passed|failed|tests collected).* in ", line)]}
        exit_file = log.with_suffix(".exit")
        if exit_file.exists():
            row["exit"] = int(exit_file.read_text())
        xml = log.with_suffix(".xml")
        if xml.exists():
            tree = ET.parse(xml)
            cases = tree.findall(".//testcase")
            row["cases"] = len(cases)
            row["failures"] = [{"class": case.get("classname"), "name": case.get("name"),
                                "outcome": child.tag, "message": child.get("message")}
                               for case in cases for child in case
                               if child.tag in {"failure", "error"}]
            row["skipped"] = sum(case.find("skipped") is not None for case in cases)
        row["artifacts"] = {p.name: {"bytes": p.stat().st_size,
                                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                            for p in (log, xml, exit_file, log.with_suffix(".inputs")) if p.exists()}
        results[label] = row
    ci = {k: v for k, v in results.items()
          if k.startswith("ci-ordinary-") or k.startswith("ci-routing-")}
    result = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "interpreter": sys.executable, "python": sys.version, "evidence_directory": str(evidence),
        "dependencies": dict(sorted((dist.metadata["Name"], dist.version)
                                    for dist in importlib.metadata.distributions()
                                    if dist.metadata["Name"])),
        "results": results,
        "ci_partition": {"lanes": len(ci), "executed_cases": sum(v.get("cases", 0) for v in ci.values()),
                         "failed_lanes": [k for k, v in ci.items() if v.get("exit") != 0]},
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
