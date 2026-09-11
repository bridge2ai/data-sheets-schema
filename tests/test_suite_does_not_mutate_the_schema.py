"""Schema-generation tests must leave their repository artifacts untouched.

The old test ran `make full-schema` in the checkout. Its non-atomic write
could expose a partial schema to a parallel reader even though the final
bytes were identical (#1208). Run that test in a disposable repository with
older merged artifacts so Make cannot hide the regression with a no-op
(#1215). The real checkout remains safe even when this guard fails.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = Path("src/data_sheets_schema/schema")
MERGED = ("data_sheets_schema_all.yaml", "data_sheets_schema_core_all.yaml")


def _state(root):
    """Mtime detects rewrites that reproduce the original content."""
    return {
        name: (hashlib.sha256((root / SCHEMA_DIR / name).read_bytes()).hexdigest(),
               (root / SCHEMA_DIR / name).stat().st_mtime_ns)
        for name in MERGED
    }


class TheSuiteLeavesTheMergedSchemasAlone(unittest.TestCase):
    def test_the_full_schema_tests_do_not_rewrite_the_committed_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp)
            # Include the real build rules and inputs: restoring the old
            # `make` invocation must successfully build, then fail our
            # mutation assertion, rather than fail on a missing Makefile.
            for name in ("Makefile", "project.Makefile", "config.env", "about.yaml",
                         "pyproject.toml", "utils/get-value.sh",
                         "tests/test_d4d_full_schema.py"):
                target = checkout / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            shutil.copytree(ROOT / SCHEMA_DIR, checkout / SCHEMA_DIR)
            # Deterministically force Make to rebuild if the regression
            # returns, regardless of checkout order or prior test runs.
            oldest_source = min(p.stat().st_mtime_ns
                                for p in (checkout / SCHEMA_DIR).glob("*.yaml")
                                if p.name not in MERGED)
            for name in MERGED:
                older = oldest_source - 2_000_000_000
                os.utime(checkout / SCHEMA_DIR / name, ns=(older, older))
            before = _state(checkout)
            # The module's unittest entrypoint runs its tests independently
            # of the outer pytest selection. Reuse this interpreter's
            # environment for its `poetry run gen-linkml` subprocess.
            env = {**os.environ, "VIRTUAL_ENV": sys.prefix}
            # Poetry ignores VIRTUAL_ENV when an inherited Conda base
            # environment is still named, even inside a Python virtualenv.
            env.pop("CONDA_DEFAULT_ENV", None)
            result = subprocess.run(
                [sys.executable, "tests/test_d4d_full_schema.py"],
                cwd=checkout, env=env,
                capture_output=True, text=True, timeout=900)
            self.assertEqual(result.returncode, 0,
                             (result.stdout + result.stderr)[-2000:])
            self.assertEqual(
                _state(checkout), before,
                "the full-schema tests rewrote a repository artifact; "
                "generate into a temporary directory instead (#1208)")
