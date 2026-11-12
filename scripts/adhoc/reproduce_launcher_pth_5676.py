#!/usr/bin/env python3
"""Reproduce #5676: outer venv whose dependencies arrive via a .pth file (2026-11-10).

Purpose: Build a minimal outer venv in a temporary directory whose site-packages
exposes the dependency venv's site-packages only through a .pth file (matching
the U3-A / U3-H test harness u3a_paths.pth layout), then run pytest on
tests/test_api_launcher.py inside that outer venv and report the exit status.
Inputs: Invoking dependency Python interpreter and tests/test_api_launcher.py.
Outputs: Standard output/error and exit code from pytest tests/test_api_launcher.py.
Serves: Issue #5676.
"""

from __future__ import annotations

import os
from pathlib import Path
import site
import subprocess
import sys
import tempfile
import venv

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    dep_sites = [Path(p).resolve() for p in site.getsitepackages() if Path(p).is_dir()]
    if not dep_sites:
        raise RuntimeError("No site-packages directories found on invoking interpreter")

    with tempfile.TemporaryDirectory(prefix="d4d_5676_outer_") as tmp:
        outer_venv = Path(tmp) / "outer_venv"
        venv.EnvBuilder(with_pip=False, symlinks=True).create(outer_venv)
        outer_sites = list(outer_venv.glob("lib/python*/site-packages"))
        if not outer_sites:
            raise RuntimeError(f"No site-packages in {outer_venv}")
        outer_site = outer_sites[0]

        pth_paths = [REPO_ROOT / "src", REPO_ROOT, *dep_sites]
        (outer_site / "u3a_paths.pth").write_text(
            "".join(f"{p}\n" for p in pth_paths),
            encoding="utf-8",
        )
        (outer_site / "sitecustomize.py").write_text(
            "# Minimal isolated outer test venv for #5676 reproduction.\n",
            encoding="utf-8",
        )

        outer_python = outer_venv / "bin" / "python"
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{REPO_ROOT}"
        env["PYTHONNOUSERSITE"] = "1"

        cmd = [
            str(outer_python),
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "tests/test_api_launcher.py",
            *sys.argv[1:],
        ]
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=False)
        print(f"PYTEST_EXIT_CODE={proc.returncode}")
        return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
