#!/usr/bin/env python3
"""D4D API Launcher script (Step A4b / #4345, #777).

Enforces worktree code isolation, environment variable hygiene, and launch safeguards.
Can be executed from within the repository or copied standalone into a sibling inputs
directory under d4d-executions/.

Usage examples:
    # Check worktree environment and import isolation:
    python scripts/api_launcher.py --check-only

    # Dry-run a batch command in a worktree:
    python scripts/api_launcher.py --worktree /path/to/worktree --dry-run d4d api batch --manifest ...

    # Launch a long-running batch job in background with caffeinate and external logging:
    python scripts/api_launcher.py --worktree /path/to/worktree --launch --log /path/to/logs/batch.log d4d api batch ...
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repository src to sys.path if running from within the repository
ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "src").is_dir() and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# If copied outside to a sibling inputs directory, inspect --worktree / -w argument
for idx, arg in enumerate(sys.argv):
    if arg in ("--worktree", "-w") and idx + 1 < len(sys.argv):
        candidate_src = Path(sys.argv[idx + 1]).resolve() / "src"
        if candidate_src.is_dir() and str(candidate_src) not in sys.path:
            sys.path.insert(0, str(candidate_src))

try:
    from data_sheets_schema.api_launcher import main
except ImportError as exc:
    sys.stderr.write(
        f"api_launcher: fatal error: unable to import data_sheets_schema.api_launcher ({exc}).\n"
        "Ensure the worktree contains src/data_sheets_schema or specify --worktree <path>.\n"
    )
    sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
