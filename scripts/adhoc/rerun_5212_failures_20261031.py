#!/usr/bin/env python3
"""#5212, 2026-10-31: rerun recorded failures on an unmodified pinned archive.

Inputs: archive directory, prior phase name, new phase name under scratch-5212fix.
Outputs: exact failed-node selection plus the ordinary offline pytest evidence.
Launch under d73_offline_20261031.sb; provider/network restrictions stay intact.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / "scratch-5212fix"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("tree")
parser.add_argument("source_phase")
parser.add_argument("name")
args = parser.parse_args()
tree = (SCRATCH / args.tree).resolve()
base = SCRATCH / args.name
assert tree.parent == SCRATCH and base.parent == SCRATCH and not base.exists()
prior = json.loads((SCRATCH / args.source_phase / "d73-result.json").read_text())
nodes = sorted({row["nodeid"] for row in prior["reports"] if row["outcome"] == "failed"})
assert nodes
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tree, text=True).strip()
assert not subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=tree, text=True)
selected = [*nodes, "-q", "--tb=short", "--basetemp", str(base), "--junitxml", str(base) + ".xml"]
(SCRATCH / (args.name + "-selection.json")).write_text(json.dumps({
    "head": head, "tree": tree.name, "source_phase": args.source_phase,
    "source_head": prior["environment"]["head"], "arguments": selected}, indent=2) + "\n")
command = [sys.executable, "-S", "-P", "-B", str(ROOT / "scripts/adhoc/run_d73_offline_20261031.py"),
           "--tree", str(tree), *selected]
os.execv(sys.executable, command)
