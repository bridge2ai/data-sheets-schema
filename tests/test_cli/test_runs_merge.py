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
        self.assertIn(str(self.root / "claudecode_agent_merged" /
                          "2026-08-01_cfg_merged" / "P_d4d.yaml"), out.output)
        self.assertFalse(
            (self.root / "claudecode_agent_merged" / "2026-08-01_cfg_merged" / "P_d4d.yaml").exists(),
            "a dry run wrote a record")

    def test_the_union_covers_slots_no_single_replicate_had(self):
        out = self._run("--project", "P", "--config", "2026-08-01_cfg",
                        "--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        merged = yaml.safe_load(
            (self.root / "claudecode_agent_merged" / "2026-08-01_cfg_merged" / "P_d4d.yaml").read_text())
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
        # The merged label's own record, named explicitly. `rglob` order is
        # directory order — sorted on APFS, unsorted on ext4 — and `prov[0]`
        # was a replicate's live provenance on every Linux CI run (#941).
        merged = [p for p in self.method.parent.rglob("P_provenance.yaml")
                  if p.parent.name == "2026-08-01_cfg_merged"]
        self.assertEqual(len(merged), 1, "the merged label must write one "
                         "provenance record: found "
                         f"{sorted(str(p) for p in merged)}")
        data = yaml.safe_load(merged[0].read_text())
        self.assertEqual(data.get("record_mode"), "derived",
                         "a merged record must never claim to be live")
        self.assertEqual(data["run"]["method"], "claudecode_agent_merged")
        self.assertEqual({row["method"] for row in data["sources"]}, {"claudecode_agent"})

    def test_explicit_output_method_does_not_change_source_selection(self):
        out = self._run("--method", "claudecode_agent", "--project", "P",
                        "--config", "2026-08-01_cfg", "--out-method", "reviewed_union",
                        "--out-label", "chosen_label", "--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        output = self.root / "reviewed_union" / "chosen_label" / "P_d4d.yaml"
        record = yaml.safe_load(output.read_text())
        self.assertIn("only_in_a", record)
        self.assertIn("only_in_b", record)
        provenance = yaml.safe_load((self.root / "reviewed_union_core" / "chosen_label" /
                                     "P_provenance.yaml").read_text())
        self.assertEqual(provenance["run"]["method"], "reviewed_union")
        self.assertEqual(provenance["run"]["label"], "chosen_label")
        self.assertEqual({row["method"] for row in provenance["sources"]}, {"claudecode_agent"})

    def test_invalid_destination_refuses_in_dry_run_and_execute(self):
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        for method in ("claudecode_agent", "claudecode_agent_core", "", "../outside"):
            for execute in (False, True):
                with self.subTest(method=method, execute=execute):
                    args = ["--project", "P", "--config", "2026-08-01_cfg",
                            "--out-method", method]
                    result = self._run(*args, *(["--execute"] if execute else []))
                    self.assertEqual(result.exit_code, 1, result.output)
                    self.assertIn("Error:", result.output)
                    self.assertEqual({p.relative_to(self.root): p.read_bytes()
                                      for p in self.root.rglob("*") if p.is_file()}, before)
        self.assertFalse((self.root / "claudecode_agent_merged").exists())

    def test_destination_refusal_precedes_optional_scorer_construction(self):
        from unittest.mock import patch
        context = Path(self.tmp.name) / "context.json"
        cache = Path(self.tmp.name) / "cache.jsonl"
        context.write_text("{}", encoding="utf-8")
        cache.write_text("", encoding="utf-8")
        with patch("data_sheets_schema.cli.runs._merge_fitness_scorer",
                   side_effect=AssertionError("must refuse destination first")) as scorer:
            result = self._run("--project", "P", "--config", "2026-08-01_cfg",
                               "--out-method", "claudecode_agent", "--fitness-context",
                               str(context), "--fitness-cache", str(cache), "--execute")
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("distinct", result.output)
        scorer.assert_not_called()

    def test_publication_refusal_uses_the_cli_error_surface(self):
        from unittest.mock import patch
        with patch("data_sheets_schema.merge.write_merge", side_effect=ValueError("destination changed")):
            result = self._run("--project", "P", "--config", "2026-08-01_cfg", "--execute")
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("Error: destination changed", result.output)
        self.assertFalse((self.root / "claudecode_agent_merged").exists())


class TestADerivedRecordIsExcludedAsDerived(unittest.TestCase):
    """Not as "incomplete". A merged record has no core and no reconciliation
    report by construction — it is a union of full records, not a run — so
    testing completeness first sent the reader looking for a run that would
    never arrive, and made the exclusion an accident of its artifact set."""

    def test_derived_is_checked_before_completeness(self):
        import inspect
        from data_sheets_schema import runs as r
        src = inspect.getsource(r.compare)
        body = src[src.index("for label in labels:"):]
        self.assertLess(
            body.index("== DERIVED"), body.index("is_complete("),
            "completeness is tested before derivedness, so a merged record "
            "reports as incomplete")

    def test_the_cli_reports_the_exclusion_rather_than_hiding_it(self):
        import inspect
        from data_sheets_schema.cli import runs as cli
        src = inspect.getsource(cli)
        self.assertIn("excluded_derived", src,
                      "compare() reports excluded_derived but the CLI never "
                      "prints it, so the record vanishes without explanation")


if __name__ == "__main__":
    unittest.main()
