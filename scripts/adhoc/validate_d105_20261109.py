#!/usr/bin/env python3
# Purpose: bounded offline D105 validation with one-unit canary before a batch.
# Inputs: existing Python environment, pytest nodes and a fresh evidence label.
# Outputs: logs, JUnit, pytest-owned scratch, hashes and result.json; 2026-11-09.
"""Keep validation reproducible, credential-free and outside every worktree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = ROOT.parent
SCRATCH = EXECUTIONS / "scratch-d105"
LOCK = EXECUTIONS / "plans/native_quiet_window.lock"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("nodes", nargs="+")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.label):
        parser.error("label must be a simple lowercase name")
    if LOCK.exists() or LOCK.is_symlink():
        parser.error("quiet-window lock is present; do not launch tests")
    out = SCRATCH / args.label
    out.mkdir(parents=True, exist_ok=False)
    for name in ("home", "tmp"):
        (out / name).mkdir()
    # No inherited provider/OAuth credentials or SDK endpoints, including
    # collection-time imports. Paths are local; no dependency installation.
    env = {
        "HOME": str(out / "home"), "TMPDIR": str(out / "tmp"),
        "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
        "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "LC_ALL": "en_US.UTF-8",
    }
    profile = out / "offline.sb"
    profile.write_text("(version 1)\n(allow default)\n(deny network*)\n")
    command = ["/usr/bin/sandbox-exec", "-f", str(profile), sys.executable,
               "-m", "pytest", "-p", "xdist.plugin", "-p", "no:cacheprovider",
               "-n", "2", "--basetemp", str(out / "pytest"),
               "--junitxml", str(out / "junit.xml"), "-q", *args.nodes]
    result = {"command": command, "cwd": str(ROOT), "network": "OS deny network*",
              "environment_keys": sorted(env), "timeout_seconds": 3000,
              "quiet_lock_absent_at_start": True}
    started = time.monotonic()
    with (out / "pytest.log").open("wb") as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            result["exit_code"] = child.wait(timeout=3000)
        except subprocess.TimeoutExpired:
            result["timeout"] = True
            os.killpg(child.pid, signal.SIGKILL)
            result["exit_code"] = child.wait()
        finally:
            # These are only our process-group descendants, never other jobs.
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result["artifacts"] = {
        str(path.relative_to(out)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(out.rglob("*"))
        if path.is_file() and (path.suffix in {".json", ".xml"} or path.name == "pytest.log")
    }
    (out / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"evidence": str(out), "exit_code": result["exit_code"],
                      "elapsed_seconds": result["elapsed_seconds"]}))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
