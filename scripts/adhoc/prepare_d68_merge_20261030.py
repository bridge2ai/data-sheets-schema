#!/usr/bin/env python3
"""D68-D70/#5212 offline integration checkout, 2026-10-30.

Inputs: current committed packet, local 50bc50af6, local FAIRSCAPE Git store.
Outputs: a scratch branch/check-out nested under this authorized worktree and
a merge-evidence JSON. No edit to the packet's protected files or run trees;
protected bytes in scratch are populated by Git from the merge, never by hand.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("submodule_git", type=Path)
args = parser.parse_args()
destination = ROOT / ".d68-validation/merge"
assert not destination.exists()
branch = "codex/d68-d70-merge-50bc50af6-20261030"
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
subprocess.run(["git", "worktree", "add", "-b", branch, str(destination), head], cwd=ROOT, check=True)
subprocess.run(["git", "merge", "--no-ff", "50bc50af6", "-m",
                "Scratch integration of D68-D70 with 50bc50af6 for review item 7 validation"],
               cwd=destination, check=True)
pin = subprocess.check_output(["git", "ls-tree", "HEAD", "fairscape_models"], cwd=destination, text=True).split()[2]
archive = subprocess.check_output(["git", f"--git-dir={args.submodule_git}", "archive", pin])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall(destination / "fairscape_models", filter="data")
merge = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=destination, text=True).strip()
result = {"packet_head": head, "merge_head": merge, "target": "50bc50af6", "branch": branch,
          "scratch": str(destination), "fairscape_commit": pin, "submodule_source": str(args.submodule_git)}
(ROOT / ".d68-validation/merge-preparation.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
