#!/usr/bin/env python3
"""D68-D70/#5212 review item 7: identical offline baseline, 2026-10-30.

Inputs: local d9b69d84d and FAIRSCAPE object store, current validation helpers.
Output: nested baseline checkout, with only untracked harness helpers added.
Git populates historical tracked bytes; no protected file is edited by hand.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("submodule_git")
args = parser.parse_args()
destination = ROOT / ".d68-validation/base"
assert not destination.exists()
subprocess.run(["git", "worktree", "add", "-b", "codex/d68-d70-base-d9-20261030",
                str(destination), "d9b69d84d"], cwd=ROOT, check=True)
pin = subprocess.check_output(["git", "ls-tree", "HEAD", "fairscape_models"], cwd=destination, text=True).split()[2]
archive = subprocess.check_output(["git", f"--git-dir={args.submodule_git}", "archive", pin])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall(destination / "fairscape_models", filter="data")
helpers = {}
for name in ("d41_legacy_controls_20261029.py", "run_d68_offline_20261030.py",
             "d68_offline_20261030.sb", "d68_local_git_20261030.sh"):
    source = ROOT / "scripts/adhoc" / name
    target = destination / "scripts/adhoc" / name
    assert not target.exists()
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(source, target)
    helpers[str(target.relative_to(destination))] = hashlib.sha256(source.read_bytes()).hexdigest()
result = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=destination, text=True).strip(),
          "fairscape_commit": pin, "untracked_helpers": helpers, "scratch": str(destination)}
(ROOT / ".d68-validation/base-preparation.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
