"""`d4d runs select` — pick one replicate, keep them all (#176).

Selection rather than merging. Merging splices values across replicates that
disagree on 77-98% of the slots they share, for a coverage gain of 1-5 slots
(#229), and a spliced record can assert a participant count from one referent
and a DOI from another. One replicate is internally coherent because one
generation produced it.

Validity first, coverage second — because coverage alone is nearly arbitrary
here. Across the generic-v2 config the margins are +0, +1, +2 and +1 slots, and
AI-READI is an outright tie that only validity resolves.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from click.testing import CliRunner


def _rec(n):
    d = {"id": "https://example.org/x", "name": "x", "title": "T",
         "description": "d"}
    d.update({f"slot_{i}": [f"v{i}"] for i in range(n)})
    return d


class TestSelect(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli import runs as runs_cli
        self.cli = runs_cli.runs
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "d4d_concatenated"
        self.method = self.root / "claudecode_agent"
        # rep1 smallest, rep2 largest, rep3 middle
        for label, n in (("cfg_rep1", 4), ("cfg_rep2", 9), ("cfg_rep3", 6)):
            d = self.method / label
            d.mkdir(parents=True)
            (d / "P_d4d.yaml").write_text(yaml.safe_dump(_rec(n)),
                                          encoding="utf-8")
            core = self.root / "claudecode_agent_core" / label
            core.mkdir(parents=True, exist_ok=True)
            (core / "P_d4d_core.yaml").write_text("id: x\n", encoding="utf-8")
            (core / "P_reconciliation.md").write_text("# r\n", encoding="utf-8")
            (core / "P_provenance.yaml").write_text(yaml.safe_dump({
                "record_mode": "live",
                "run": {"method": "claudecode_agent", "label": label,
                        "project": "P"}}), encoding="utf-8")
        import data_sheets_schema.runs as runs_mod
        self._orig = runs_mod.CONCAT_DIR
        runs_mod.CONCAT_DIR = self.root

    def tearDown(self):
        import data_sheets_schema.runs as runs_mod
        runs_mod.CONCAT_DIR = self._orig
        self.tmp.cleanup()

    def _run(self, *args, valid=None):
        """`valid` maps label -> bool; default every replicate validates."""
        def fake(record):
            label = Path(record).parent.name
            return True if valid is None else valid.get(label, True)
        with mock.patch("data_sheets_schema.cli.runs._validates", fake):
            return CliRunner().invoke(
                self.cli, ["select", "--project", "P", "--config", "cfg", *args])

    def test_the_largest_valid_replicate_wins(self):
        out = self._run()
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("→ cfg_rep2", out.output)

    def test_validity_outranks_coverage(self):
        """The whole point: the biggest record is not canonical if it is
        broken. On the real corpus this is what resolves AI-READI's tie and
        drops a higher-coverage CM4AI replicate."""
        out = self._run(valid={"cfg_rep2": False})
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("→ cfg_rep3", out.output)

    def test_it_refuses_when_nothing_validates(self):
        """No VOICE replicate validates. Picking the least-bad would ship a
        record known to be broken, so the command declines."""
        out = self._run(valid={"cfg_rep1": False, "cfg_rep2": False,
                               "cfg_rep3": False})
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("Nothing here can be canonical", out.output)

    def test_a_thin_margin_is_reported_as_thin(self):
        out = self._run(valid={"cfg_rep2": False})   # rep3 (6) over rep1 (4)
        self.assertIn("ahead of the runner-up", out.output)

    def test_a_dry_run_records_nothing(self):
        before = (self.root / "claudecode_agent_core" / "cfg_rep2" /
                  "P_provenance.yaml").read_text()
        self._run()
        after = (self.root / "claudecode_agent_core" / "cfg_rep2" /
                 "P_provenance.yaml").read_text()
        self.assertEqual(before, after)

    def test_execute_records_the_choice_and_its_candidates(self):
        out = self._run("--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        prov = yaml.safe_load((self.root / "claudecode_agent_core" /
                               "cfg_rep2" / "P_provenance.yaml").read_text())
        canon = prov.get("canonical")
        self.assertIsNotNone(canon, "no canonical block written")
        self.assertEqual(len(canon["selected_from"]), 3,
                         "the losers must be named, or the choice is not "
                         "auditable")
        self.assertIn("criterion", canon)

    def test_nothing_is_moved_or_deleted(self):
        """Replicates are a measurement device; selection marks one, it does
        not collapse the set."""
        self._run("--execute")
        for label in ("cfg_rep1", "cfg_rep2", "cfg_rep3"):
            self.assertTrue((self.method / label / "P_d4d.yaml").exists(),
                            f"{label} disappeared")

    def test_one_replicate_is_not_a_selection(self):
        import shutil
        for label in ("cfg_rep2", "cfg_rep3"):
            shutil.rmtree(self.method / label)
        out = self._run()
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("at least two", out.output)


if __name__ == "__main__":
    unittest.main()
