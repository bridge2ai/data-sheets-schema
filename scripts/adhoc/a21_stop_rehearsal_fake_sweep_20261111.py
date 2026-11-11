#!/usr/bin/env python3
"""Hold a real sweep lock and sleep, so the A21 stop path can be rehearsed.

Purpose: the launch packet's stop command (`d4d api stop --label-prefix …`
  through the launcher) and the lead's watcher have never been exercised
  against a live process. This stands in for a sweep: it claims a label
  prefix with the production `run_lock.acquire`, exactly as `d4d api batch`
  does, and then only sleeps. It makes no provider call, reads no input and
  writes nothing but the lock file.
Inputs: argv[1] the label prefix; argv[2] seconds to live (default 600). Run
  with the working directory at the rehearsal checkout and that checkout's
  `src` on PYTHONPATH, never in the launch base.
Outputs: `data/.run_locks/<prefix>.json` under the working directory, removed
  on a normal exit and left behind (stale) when the process is signalled, as
  a stopped sweep leaves it.
Serves: the A21 launch packet of 2026-11-11 (owner decision D131).
Date: 2026-11-11
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from data_sheets_schema import run_lock


def main() -> int:
    prefix = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 600.0
    if "launch-a21" in str(Path.cwd()):
        raise SystemExit("refusing to hold a rehearsal lock in the launch base")
    path = run_lock.acquire(prefix, ["CHORUS"])
    print(f"fake sweep pid {os.getpid()} holds {path.resolve()}", flush=True)
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        time.sleep(0.5)
    run_lock.release(path)
    print("fake sweep ended by itself", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
