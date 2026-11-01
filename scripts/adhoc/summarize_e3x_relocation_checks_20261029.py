#!/usr/bin/env python3
"""Summarize offline E3x x #5096 / #5213 checks, 2026-10-29.

Inputs: pytest evidence directory. Output: JSON to stdout, including
artifact hashes, outcomes, dependency identity and CI coverage counts.
No providers, source mutations, network access or rating runs.
"""
import hashlib
from collections import Counter
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
    case_keys = {}
    executed_nodes = {}
    for log in sorted(evidence.glob("*.log")):
        label = log.stem
        text = log.read_text(errors="replace")
        executed_nodes[label] = re.findall(r"^(tests/.+) (?:PASSED|SKIPPED|FAILED)\b", text, re.M)
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
            case_keys[label] = {(case.get("classname"), case.get("name")) for case in cases}
            row["unique_cases"] = len(case_keys[label])
            counts = Counter((case.get("classname"), case.get("name")) for case in cases)
            row["junit_name_collisions"] = [{"class": key[0], "name": key[1], "entries": count}
                                             for key, count in counts.items() if count > 1]
            row["duration_seconds"] = sum(float(suite.get("time", "0"))
                                           for suite in tree.findall(".//testsuite"))
            row["failures"] = [{"class": case.get("classname"), "name": case.get("name"),
                                "outcome": child.tag, "message": child.get("message")}
                               for case in cases for child in case
                               if child.tag in {"failure", "error"}]
            row["skipped"] = sum(case.find("skipped") is not None for case in cases)
        inputs = log.with_suffix(".inputs")
        if inputs.exists():
            row["input_head"] = inputs.read_text().splitlines()[0]
        row["artifacts"] = {p.name: {"bytes": p.stat().st_size,
                                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                            for p in (log, xml, exit_file, log.with_suffix(".inputs")) if p.exists()}
        results[label] = row
    ci = {k: v for k, v in results.items()
          if k.startswith("ci-ordinary-") or k.startswith("ci-routing-")}
    ci_keys = set().union(*(case_keys.get(label, set()) for label in ci))
    collection_log = (evidence / "collect-ci-tree.log").read_text()
    collected = re.search(r"(\d+) tests collected", collection_log)
    ci_collected = int(collected[1])
    collected_nodes = Counter(line for line in collection_log.splitlines() if line.startswith("tests/"))
    node_counts = Counter(node for label in ci for node in executed_nodes[label])
    missing_nodes = dict(collected_nodes - node_counts)
    unexpected_nodes = dict(node_counts - collected_nodes)
    duplicate_nodes = {node: count for node, count in node_counts.items() if count > 1}
    supporting = [p for p in evidence.iterdir() if p.suffix in {".json", ".txt", ".md"}
                  and p.name != "progress-summary.json"]
    result = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "interpreter": sys.executable, "python": sys.version, "evidence_directory": str(evidence),
        "dependencies": dict(sorted((dist.metadata["Name"], dist.version)
                                    for dist in importlib.metadata.distributions()
                                    if dist.metadata["Name"])),
        "results": results,
        "ci_partition": {"lanes": len(ci), "collected_tests": ci_collected,
                         "executed_cases": sum(node_counts.values()),
                         "distinct_nodeids": len(node_counts),
                         "unique_junit_names": len(ci_keys),
                         "junit_phase_entries": sum(v.get("cases", 0) for v in ci.values()),
                         "missing_nodeids": missing_nodes, "unexpected_nodeids": unexpected_nodes,
                         "duplicate_nodeids": duplicate_nodes,
                         "collection_duplicate_nodeids": {node: count for node, count in collected_nodes.items() if count > 1},
                         "complete": (len(ci) == 10 and sum(collected_nodes.values()) == ci_collected
                                      and not missing_nodes and not unexpected_nodes),
                         "failed_lanes": [k for k, v in ci.items() if v.get("exit") != 0]},
        "isolated_reruns": json.loads((evidence / "environment-reruns.json").read_text()),
        "ps_sandbox_diagnostic": json.loads((evidence / "ps-sandbox-diagnostic.json").read_text()),
        "supporting_artifacts": {p.name: {"bytes": p.stat().st_size,
                                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                  for p in sorted(supporting)},
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
