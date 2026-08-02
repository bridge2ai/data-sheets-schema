"""`d4d runs merge` — the production output #176 says the pipeline lacks."""

import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner


REC_A = {"id": "https://example.org/x", "name": "x", "title": "T",
         "description": "d", "keywords": ["a"], "only_in_a": ["p"]}
REC_B = {"id": "https://example.org/x", "name": "x", "title": "T",
         "description": "different", "keywords": ["b"], "only_in_b": ["q"]}


class TestMergeCommand(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli import runs as runs_cli
        self.cli = runs_cli.runs
        self.tmp = tempfile.TemporaryDirectory()
        # Must contain a `d4d_concatenated` component: the merge helpers
        # read a source's corpus root and method off its own path, so a
        # fixture without one resolves to method "unknown" and no
        # provenance.
        self.root = Path(self.tmp.name) / "d4d_concatenated"
        self.root.mkdir(parents=True)
        self.method = self.root / "claudecode_agent"
        for lab, rec in (("2026-08-01_cfg_rep1", REC_A),
                         ("2026-08-01_cfg_rep2", REC_B)):
            d = self.method / lab
            d.mkdir(parents=True)
            (d / "P_d4d.yaml").write_text(yaml.safe_dump(rec), encoding="utf-8")
            # Contributors must be attested: a derived record inherits its
            # sources' standing, so merging an unestablished run would launder
            # it. `check_sources` enforces this, hence the fixtures need it.
            core = self.root / "claudecode_agent_core" / lab
            core.mkdir(parents=True, exist_ok=True)
            (core / "P_d4d_core.yaml").write_text(yaml.safe_dump(rec),
                                                  encoding="utf-8")
            (core / "P_reconciliation.md").write_text("# r\n", encoding="utf-8")
            (core / "P_provenance.yaml").write_text(yaml.safe_dump({
                "record_mode": "live",
                "run": {"method": "claudecode_agent", "label": lab,
                        "project": "P"},
            }), encoding="utf-8")
        import data_sheets_schema.runs as runs_mod
        self._orig = runs_mod.CONCAT_DIR
        runs_mod.CONCAT_DIR = self.root

    def tearDown(self):
        import data_sheets_schema.runs as runs_mod
        runs_mod.CONCAT_DIR = self._orig
        self.tmp.cleanup()

    def _run(self, *args):
        return CliRunner().invoke(self.cli, ["merge", *args])

    def test_a_dry_run_writes_nothing(self):
        out = self._run("--project", "P", "--config", "2026-08-01_cfg")
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("Dry run", out.output)
        self.assertFalse(
            (self.method / "2026-08-01_cfg_merged" / "P_d4d.yaml").exists(),
            "a dry run wrote a record")

    def test_the_union_covers_slots_no_single_replicate_had(self):
        out = self._run("--project", "P", "--config", "2026-08-01_cfg",
                        "--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        merged = yaml.safe_load(
            (self.method / "2026-08-01_cfg_merged" / "P_d4d.yaml").read_text())
        self.assertIn("only_in_a", merged)
        self.assertIn("only_in_b", merged)

    def test_merging_one_replicate_is_refused(self):
        """A single record is not a merge, and calling it one would let a
        derived record stand in for a generated one."""
        out = self._run("--project", "P", "--label", "2026-08-01_cfg_rep1")
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("at least two", out.output)

    def test_a_missing_record_is_named_not_skipped(self):
        out = self._run("--project", "MISSING", "--config", "2026-08-01_cfg")
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("no record at", out.output)

    def test_the_output_states_that_the_base_wins_contested_slots(self):
        """The count alone reads as "unresolved disagreement". It is not: the
        base's value is used, and the report has to say so."""
        out = self._run("--project", "P", "--config", "2026-08-01_cfg")
        self.assertIn("base's value is used", out.output)

    def test_the_merged_record_is_derived_not_live(self):
        out = self._run("--project", "P", "--config", "2026-08-01_cfg",
                        "--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        prov = list((self.method.parent).rglob("P_provenance.yaml"))
        if prov:
            data = yaml.safe_load(prov[0].read_text())
            self.assertEqual(data.get("record_mode"), "derived",
                             "a merged record must never claim to be live")


if __name__ == "__main__":
    unittest.main()
