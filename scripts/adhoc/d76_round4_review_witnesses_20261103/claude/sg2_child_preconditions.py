#!/usr/bin/env python3
# Purpose: show the preconditions the round-3 SG2 test wrapper inherits from its child
#   (scripts/adhoc/run_d76_sg2_case_20261102.py -> d76_suite_common_20261031.source):
#   the child refuses unless the tree is a git checkout whose EVERY tracked file equals
#   HEAD. Checks (1) a non-git pinned copy, (2) a temporary git repo with one dirty
#   tracked file, (3) the same repo clean. Imports the helper read-only from the checkout.
# Inputs: argv[1] = review checkout, argv[2] = a non-git pinned copy, argv[3] = fresh tmp dir.
# Outputs: printed observations. Date: 2026-11-02. Claude round-3 re-check of PR #5213.
import importlib.util
import subprocess
import sys
from pathlib import Path

# -I ignores PYTHONDONTWRITEBYTECODE; the first run left one .pyc in the checkout's
# scripts/adhoc/ (removed by hand at 13:53:56). Never write bytecode beside the helper.
sys.dont_write_bytecode = True

checkout, archive, tmp = (Path(p) for p in sys.argv[1:4])
spec = importlib.util.spec_from_file_location(
    "common", checkout / "scripts/adhoc/d76_suite_common_20261031.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)

try:
    common.source(archive)
    print("non-git copy: source() returned")
except Exception as exc:  # noqa: BLE001
    print("non-git copy: source() raised", type(exc).__name__, str(exc)[:120])

repo = tmp / "repo"
repo.mkdir(parents=True)
run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
(repo / "tracked.txt").write_text("committed\n")
run("init", "-q")
run("-c", "user.name=r", "-c", "user.email=r@example.invalid", "add", "tracked.txt")
run("-c", "user.name=r", "-c", "user.email=r@example.invalid", "commit", "-qm", "c")
print("clean repo: tracked_exact =", common.source(repo)["tracked_exact"])
(repo / "tracked.txt").write_text("an uncommitted developer edit\n")
print("dirty repo: tracked_exact =", common.source(repo)["tracked_exact"],
      "-> the SG2 child raises 'SG2 child source must match its recorded commit'")
