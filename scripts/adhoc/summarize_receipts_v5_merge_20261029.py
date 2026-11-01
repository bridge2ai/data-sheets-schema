#!/usr/bin/env python3
# Purpose: verify and summarize N1/N3/N4 causal/acceptance/inertness evidence, 2026-10-29.
# Inputs: saved JUnit XML and inertness.json; outputs: validation.json with artifact hashes.
# Review: receipts_v5_562ca36b2_claude_review_2026-10-29; local files/git only.
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes/receipts_v5_merge_validation_2026-10-29"


def cases(path):
    result = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        key = case.attrib["classname"] + "::" + case.attrib["name"]
        assert key not in result
        result[key] = ("failed" if case.find("failure") is not None or case.find("error") is not None
                       else "skipped" if case.find("skipped") is not None else "passed")
    return result


def counts(items):
    return {state: sum(value == state for value in items.values()) for state in ("passed", "failed", "skipped")}


def main():
    before = cases(OUT / "causal_before.xml")
    after = cases(OUT / "acceptance.xml")
    assert counts(before) == {"passed": 14, "failed": 38, "skipped": 0}
    assert counts(after) == {"passed": 894, "failed": 0, "skipped": 19}
    transitions = {}
    for finding, failures, total in (("n1", 28, 34), ("n3", 4, 9), ("n4", 6, 9)):
        module = "test_receipts_v5_merge_" + finding
        old = {key.split("::", 1)[1]: value for key, value in before.items() if module in key}
        new = {key.split("::", 1)[1]: value for key, value in after.items() if module in key}
        assert len(old) == len(new) == total and old.keys() == new.keys()
        assert counts(old)["failed"] == failures and counts(new)["passed"] == total
        transitions[finding.upper()] = {"before": counts(old), "after": counts(new),
                                        "failed_before_passed_after": [key for key in old if old[key] == "failed"]}
    inertness = json.loads((OUT / "inertness.json").read_text())
    assert len(inertness["slices"]) == 4 and all(s["equal"] for s in inertness["slices"].values())
    assert not subprocess.check_output(["git", "diff", inertness["head"], "HEAD", "--", "src/"], cwd=ROOT)
    changed = subprocess.check_output(["git", "diff", "--name-only", "562ca36b2", "HEAD"], cwd=ROOT).decode().splitlines()
    protected = [path for path in changed if path.startswith(("data/", "src/download/", ".claude/", ".github/"))
                 or path.endswith(("STATUS.md", "shared_generation.py")) or "decision" in path.lower()]
    assert not protected
    artifacts = ["causal_before.xml", "causal_before.log", "acceptance.xml", "acceptance.log",
                 "canary.json", "inertness.json", "inertness_canary.log", "inertness_full.log"]
    hashes = {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in artifacts}
    source = [ROOT / path for path in changed if path.endswith(".py")]
    source += list((ROOT / "scripts/adhoc/receipts_v5_merge_probes_20261029").glob("*.py"))
    source += [ROOT / "scripts/adhoc/prove_receipts_v5_inertness_20261029.py", Path(__file__).resolve()]
    summary = {"tested_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
               "causal_base": "562ca36b29c907bd64f1a2ac63c70baf24d8e2cf", "python": sys.version,
               "causal": transitions, "acceptance": counts(after), "artifact_sha256": hashes,
               "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source},
               "protected_paths_changed": protected, "inertness": inertness["slices"],
               "limits": ["Offline selected 18-module suite, not the entire repository suite.",
                          "19 existing native-runtime-only skips; no new causal test skips.",
                          "N11 shared-generation v2 identity changes; generic_v10/A21 remains identical."]}
    (OUT / "validation.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"causal_before": counts(before), "acceptance": counts(after),
                      "inertness": {key: value["equal"] for key, value in inertness["slices"].items()}}, indent=2))


if __name__ == "__main__":
    main()
