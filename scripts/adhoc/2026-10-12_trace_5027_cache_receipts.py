#!/usr/bin/env python3
"""Create a portable summary of the confirmed #5027 pre-fix reproduction.

Purpose: retain exact outcomes and hashes without hostnames, private paths or
    large logs; this reads completed receipts only and executes no project code.
Inputs: --receipt-dir with identifier-alone.{xml,log} and
    identifier-ordered.{xml,log}; --repo at the reviewed PR head.
Outputs: --output JSON (refuses overwrite). Python versions are reported from
    the root-runner/CI record, not inferred from XML or the metadata interpreter.
Issue: #5027, follow-up to timing PR #5022 / #5016.
Date: 2026-10-12.
"""

import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


HEAD = "363714122048ef40b567229158d4995afb7735bb"
TARGET = (
    "tests/test_identifier_form.py::TestOnTheRunner::"
    "test_the_written_full_and_core_carry_the_curie_and_the_grounding_check_sees_none"
)
PREDECESSOR = (
    "tests/test_schema/test_datacite_relationships.py::"
    "TestTheDigestShowsNestedVocabularies::"
    "test_truncation_still_announces_itself_if_it_ever_happens"
)


def pin(path):
    data = path.read_bytes()
    return {"name": path.name, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def receipt(directory, stem):
    xml_path = directory / (stem + ".xml")
    root = ET.fromstring(xml_path.read_bytes())
    suites = list(root.iter("testsuite"))
    if len(suites) != 1:
        raise ValueError("expected one pytest suite")
    suite = suites[0]
    cases = []
    for case in suite.findall("testcase"):
        failures = case.findall("failure")
        cases.append({
            "classname": case.attrib["classname"], "name": case.attrib["name"],
            "time_seconds": case.attrib["time"],
            "outcome": "failed" if failures else "passed",
            "failure_messages": [failure.attrib.get("message", "") for failure in failures],
        })
    return {
        "counts": {key: int(suite.attrib[key])
                   for key in ("tests", "failures", "errors", "skipped")},
        "xml_suite_seconds": suite.attrib["time"],
        "cases": cases,
        "receipts": [pin(xml_path), pin(directory / (stem + ".log"))],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    head = subprocess.check_output(
        ["git", "-C", str(args.repo), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != HEAD:
        raise ValueError("expected the exact pre-fix timing PR head")
    alone = receipt(args.receipt_dir, "identifier-alone")
    ordered = receipt(args.receipt_dir, "identifier-ordered")
    if alone["counts"] != {"tests": 1, "failures": 0, "errors": 0, "skipped": 0}:
        raise ValueError("standalone positive does not match the reported evidence")
    if ordered["counts"] != {"tests": 2, "failures": 1, "errors": 0, "skipped": 0}:
        raise ValueError("ordered reproduction does not match the reported evidence")
    target_name = TARGET.rsplit("::", 1)[1]
    predecessor_name = PREDECESSOR.rsplit("::", 1)[1]
    if [case["name"] for case in ordered["cases"]] != [predecessor_name, target_name]:
        raise ValueError("the ordered receipt has a different case roster/order")
    if alone["cases"][0]["name"] != target_name:
        raise ValueError("the standalone receipt has a different target")
    failed = ordered["cases"][1]
    if (ordered["cases"][0]["outcome"] != "passed"
            or failed["outcome"] != "failed"
            or not any("merged schema matches but its digest does not" in message
                       for message in failed["failure_messages"])):
        raise ValueError("the failure is not the expected digest-consistency guard")
    source = "tests/test_schema/test_datacite_relationships.py"
    before = subprocess.check_output(
        ["git", "-C", str(args.repo), "show", HEAD + ":" + source]
    )
    result = {
        "issue": "https://github.com/bridge2ai/data-sheets-schema/issues/5027",
        "pre_fix_commit": HEAD,
        "source_before": {"path": source, "sha256": hashlib.sha256(before).hexdigest()},
        "ci_job": "https://github.com/bridge2ai/data-sheets-schema/actions/runs/38342496007/job/115116774404",
        "reported_python_versions": {"ci": "3.12.15", "local_root_runner": "3.12.11"},
        "commands": {
            "standalone_nodes": [TARGET], "ordered_nodes": [PREDECESSOR, TARGET],
            "scope": "fresh serial pytest process per receipt; real schema-sync guard retained",
        },
        "standalone": alone, "ordered": ordered,
        "conclusion": "The same target passes alone and fails after the truncation fixture; production was unchanged.",
        "fix_validation": "pending root execution; this summary contains pre-fix evidence only",
        "helper": pin(Path(__file__)),
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
