#!/usr/bin/env python3
"""#5212 D70 round 3, 2026-10-31: compare the full committed-record census.

Inputs: pinned archive name, unique result prefix. Outputs: before/after
per-record JSON and a compact comparison under scratch-5212fix. No corpus edits.
Run inside d73_offline_20261031.sb with Python -S -P -B.
"""
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
name, prefix = sys.argv[1:]
tree = SCRATCH / name
assert tree.parent == SCRATCH and tree.is_dir()
sys.path.insert(0, str(ROOT / "scripts/adhoc"))
from d41_legacy_controls_20261029 import bootstrap
bootstrap(tree, SCRATCH)
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
results = {}
for label, ref in (("before", "c9567e3c3"), ("after", head)):
    destination = SCRATCH / f"{prefix}-{label}.json"
    assert destination.parent == SCRATCH and not destination.exists()
    sys.argv = ["d70_corpus_eligibility_20261030.py", "--ref", ref, "--output", str(destination)]
    runpy.run_path(str(tree / "scripts/adhoc/d70_corpus_eligibility_20261030.py"), run_name="__main__")
    results[label] = json.loads(destination.read_text())
before, after = results["before"], results["after"]
assert not before["parse_errors"] and not after["parse_errors"]
assert before["records"] == after["records"], "committed record eligibility changed during round 3"
summary = {"before_head": before["ref"], "after_head": head,
           "before": before["counts"], "after": after["counts"],
           "round3_eligibility_changes": 0, "round3_v8_changes": 0}
(SCRATCH / f"{prefix}-comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
