#!/usr/bin/env python
"""Run every figure script in the #2303 set, in order, and list the outputs."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))


def main() -> int:
    failures = []
    for script in sorted(HERE.glob("fig*_*.py")):
        print(f"== {script.name}")
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:  # scripts exit via SystemExit(main())
            if exc.code not in (0, None):
                failures.append((script.name, exc.code))
        except Exception as exc:  # noqa: BLE001
            failures.append((script.name, repr(exc)))
            print(f"   failed: {exc!r}")
    out = HERE.parents[1] / "notes" / "figures" / "set_2303"
    for p in sorted(out.glob("*.svg")):
        print(f"   {p.relative_to(HERE.parents[1])}  {p.stat().st_size // 1024} KB")
    if failures:
        print("FAILED:", failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
