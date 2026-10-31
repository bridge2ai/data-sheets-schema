#!/usr/bin/env python3
# Purpose: run and summarize the R4/R6 follow-up acceptance, 2026-10-29.
# Inputs: original acceptance XML, R4 causal XML, rebuilt inertness ledger, git.
# Outputs: r4_r6 acceptance XML/log and validation.json; no network/provider calls.
# Review: receipts_v5_fixes_claude_rereview_2026-10-29, R4 and R6.
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PRIOR = ROOT / "notes/receipts_v5_merge_validation_2026-10-29"
OUT = PRIOR / "r4_r6"
BASE = "e8e033bf681df97dc25fa761660f8c4c9768afb5"


def cases(path):
    result = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        key = case.attrib["classname"] + "::" + case.attrib["name"]
        assert key not in result
        result[key] = ("failed" if case.find("failure") is not None or case.find("error") is not None
                       else "skipped" if case.find("skipped") is not None else "passed")
    return result


def counts(items):
    return {state: list(items.values()).count(state) for state in ("passed", "failed", "skipped")}


def modules():
    original = ET.parse(PRIOR / "acceptance.xml").getroot()
    paths = sorted({"/".join(case.attrib["classname"].split(".")[:2]) + ".py"
                    for case in original.iter("testcase")})
    assert len(paths) == 18 and all((ROOT / path).is_file() for path in paths)
    return paths + ["tests/test_receipts_v5_merge_r4.py"]


def run_tests():
    xml = Path(os.environ["TMPDIR"]) / "codex-v5r4-acceptance.xml"
    runner = ROOT / "scripts/adhoc/validate_receipts_v5_merge_20261029.py"
    command = [sys.executable, "-S", "-B", str(runner), "--", *modules(),
               f"--basetemp={Path(os.environ['TMPDIR']) / 'codex-v5r4-pt'}", f"--junitxml={xml}"]
    # Open log before pytest inventories notes/. XML is copied only after exit.
    with (OUT / "acceptance.log").open("w") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert xml.stat().st_size > 0
    shutil.copyfile(xml, OUT / "acceptance.xml")
    print(json.dumps(counts(cases(OUT / "acceptance.xml")), sort_keys=True))
    return result.returncode


def summarize():
    before = cases(PRIOR / "r4_causal_before.xml")
    after = cases(PRIOR / "r4_causal_after.xml")
    acceptance = cases(OUT / "acceptance.xml")
    assert counts(before) == {"passed": 2, "failed": 3, "skipped": 0}
    assert before.keys() == after.keys() and counts(after) == {"passed": 5, "failed": 0, "skipped": 0}
    assert counts(acceptance) == {"passed": 899, "failed": 0, "skipped": 19}
    assert all(acceptance[key] == "passed" for key in after)
    inertness = json.loads((OUT / "inertness.json").read_text())
    assert set(inertness["slices"]) == {"corpus", "report", "chorus", "assembly"}
    assert all(row["equal"] for row in inertness["slices"].values())
    assert inertness["base_tree"] == "rebuilt with git archive in TMPDIR at run time"
    changed = subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=ROOT).decode().splitlines()
    protected = [path for path in changed if path.startswith(("data/", "src/download/", ".claude/", ".github/"))
                 or path.endswith(("STATUS.md", "shared_generation.py")) or "decision" in path.lower()]
    assert not protected
    assert not subprocess.check_output(["git", "diff", inertness["head"], "--", "src/", "tests/"], cwd=ROOT)
    artifacts = [PRIOR / f"r4_causal_{phase}.{suffix}"
                 for phase in ("before", "after") for suffix in ("log", "xml")]
    artifacts += [OUT / name for name in ("acceptance.log", "acceptance.xml", "canary.json",
                                         "inertness.json", "inertness_canary.log", "inertness_full.log")]
    source = [ROOT / path for path in changed if path.endswith(".py")]
    source += [Path(__file__).resolve()]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    summary = {"tested_head": head, "inertness_started_head": inertness["head"],
               "causal_base": BASE, "python": sys.version,
               "r4_causal": {"before": counts(before), "after": counts(after)},
               "acceptance": counts(acceptance), "modules": modules(),
               "artifact_sha256": {str(p.relative_to(PRIOR)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in artifacts},
               "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in source},
               "protected_paths_changed": protected, "inertness": inertness["slices"],
               "limits": ["Selected 19-module suite, not the entire repository suite.",
                          "R1-R3 and R5 activation blockers unchanged; no v5 activation.",
                          "R6 routing-worker pin deferred as an offline issue draft."]}
    (OUT / "validation.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    assert (OUT / "validation.json").stat().st_size > 0
    print(json.dumps({"r4_causal": summary["r4_causal"], "acceptance": summary["acceptance"],
                      "inertness": {key: row["equal"] for key, row in inertness["slices"].items()}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("tests", "summarize"))
    options = parser.parse_args()
    if options.phase == "tests":
        raise SystemExit(run_tests())
    summarize()
