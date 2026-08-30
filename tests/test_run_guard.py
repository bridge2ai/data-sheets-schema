"""A run tracked on another ref but absent from disk is refused (#795)."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from data_sheets_schema import run_guard


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


class RunGuard(unittest.TestCase):
    def test_a_branch_committed_run_missing_from_disk_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            _git(tmp, "init", "-q", "-b", "main"); _git(tmp, "config", "user.email", "t@t"); _git(tmp, "config", "user.name", "t")
            (Path(tmp) / "README").write_text("x"); _git(tmp, "add", "README"); _git(tmp, "commit", "-qm", "init")
            _git(tmp, "checkout", "-qb", "data")
            d = Path(tmp) / "data/d4d_concatenated/claudecode_agent_core/L_rep1"; d.mkdir(parents=True)
            (d / "P_provenance.yaml").write_text("run: {label: L_rep1}\n"); _git(tmp, "add", "data"); _git(tmp, "commit", "-qm", "run")
            _git(tmp, "checkout", "-q", "main")                      # the directory is now gone from disk
            self.assertFalse(d.exists())
            cwd = os.getcwd(); os.chdir(tmp)
            try:
                found = run_guard.runs_on_other_refs(["L_rep1", "L_rep2"])
                self.assertEqual(found, [("L_rep1", "data")])
                self.assertIn("tracked on data", run_guard.message(found))
                # present on disk → not a finding, whatever the refs say
                d.mkdir(parents=True); (d / "P_provenance.yaml").write_text("x")
                self.assertEqual(run_guard.runs_on_other_refs(["L_rep1"]), [])
            finally:
                os.chdir(cwd)

    def test_outside_a_repository_the_guard_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd(); os.chdir(tmp)
            try:
                self.assertEqual(run_guard.runs_on_other_refs(["L_rep1"]), [])
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
