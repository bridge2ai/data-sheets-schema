"""`d4d review disposition` (#903): a curator's answer to a review finding is
recorded, and an amendment is proven to change exactly one leaf."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from click.testing import CliRunner

RECORD = """# D4D Datasheet for P Dataset
id: https://x/ds
name: p
source_caveats: The nine sizes sum to 100 bytes, which exceeds the total
  of 90 bytes by 10 bytes; both figures are recorded as stated.
funders:
- name: NIH
  notes: unrelated text
"""


class TestDisposition(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli import review as review_cli
        self.cli = review_cli.review
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name) / "d4d_concatenated"
        self.full_dir = root / "claudecode_agent" / "L"; self.core = root / "claudecode_agent_core" / "L"
        self.full_dir.mkdir(parents=True); self.core.mkdir(parents=True)
        (self.full_dir / "VOICE_d4d.yaml").write_text(RECORD, encoding="utf-8")
        (self.core / "VOICE_d4d_core.yaml").write_text(RECORD.replace("Datasheet", "Core Datasheet"), encoding="utf-8")
        (self.core / "VOICE_reconciliation.md").write_text("# r\n", encoding="utf-8")
        (self.core / "VOICE_review.yaml").write_text(yaml.safe_dump({"items": [
            {"id": "rule-01", "verdict": "violated", "evidence": "arithmetic"},
            {"id": "slot-002", "verdict": "misread", "evidence": "x"}]}), encoding="utf-8")
        self.prov = self.core / "VOICE_provenance.yaml"
        self.prov.write_text("# header\n" + yaml.safe_dump({
            "run": {"label": "L", "project": "VOICE", "method": "claudecode_agent"}}), encoding="utf-8")
        import data_sheets_schema.provenance as pv
        self._orig = pv.CONCAT_DIR; pv.CONCAT_DIR = root
        self.patches = [mock.patch("data_sheets_schema.api_runner.validate_outputs", lambda spec: []),
                        mock.patch("data_sheets_schema.api_runner.validation_block",
                                   lambda spec, problems, recorded_by: {"valid": True, "recorded_by": recorded_by}),
                        mock.patch("data_sheets_schema.backfill_checks.compute", lambda p: {})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        import data_sheets_schema.provenance as pv
        pv.CONCAT_DIR = self._orig
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _run(self, *args):
        return CliRunner().invoke(self.cli, ["disposition", "--label", "L", "--project", "VOICE", *args])

    def test_retain_records_the_finding_and_touches_no_record(self):
        before = (self.full_dir / "VOICE_d4d.yaml").read_bytes()
        out = self._run("--item", "slot-002", "--disposition", "retain", "--note", "left as generated", "--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        rec = yaml.safe_load(self.prov.read_text())
        self.assertEqual(rec["dispositions"][0]["item"], "slot-002")
        self.assertEqual(rec["dispositions"][0]["verdict"], "misread")
        self.assertEqual(rec["dispositions"][0]["disposition"], "retain")
        self.assertEqual((self.full_dir / "VOICE_d4d.yaml").read_bytes(), before)
        self.assertTrue(self.prov.read_text().startswith("#"))          # written through ProvenanceRecord, header kept

    def test_an_unknown_item_is_refused(self):
        out = self._run("--item", "slot-099", "--disposition", "retain", "--note", "n", "--execute")
        self.assertNotEqual(out.exit_code, 0); self.assertIn("no item", out.output)

    def test_amend_matches_across_line_wrapping_and_proves_one_leaf_changed(self):
        args = ["--item", "rule-01", "--disposition", "amend", "--note", "sum re-verified",
                "--path", "source_caveats",
                "--replace", "sum to 100 bytes, which exceeds the total of 90 bytes by 10 bytes",
                "--with", "sum to 80 bytes, which falls 10 bytes short of the total of 90 bytes"]
        dry = self._run(*args)
        self.assertEqual(dry.exit_code, 0, dry.output); self.assertIn("dry run", dry.output)
        self.assertIn("sum to 100 bytes", (self.full_dir / "VOICE_d4d.yaml").read_text())
        out = self._run(*args, "--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        for p in (self.full_dir / "VOICE_d4d.yaml", self.core / "VOICE_d4d_core.yaml"):
            text = p.read_text()
            self.assertIn("sum to 80 bytes, which falls 10 bytes short", text)
            self.assertNotIn("exceeds", text)
            self.assertTrue(text.startswith("# D4D"))                      # the header survives
            self.assertEqual(yaml.safe_load(text)["funders"][0]["notes"], "unrelated text")
        rec = yaml.safe_load(self.prov.read_text())
        d = rec["dispositions"][0]
        self.assertEqual(d["path"], "source_caveats")
        self.assertEqual(set(d["files"]), {"full", "core"})
        self.assertEqual(d["files"]["full"]["sha256_after"],
                         hashlib.sha256((self.full_dir / "VOICE_d4d.yaml").read_bytes()).hexdigest())
        self.assertNotEqual(d["files"]["full"]["sha256_before"], d["files"]["full"]["sha256_after"])
        self.assertEqual(rec["validation"]["recorded_by"], "d4d review disposition")

    def test_an_edit_that_crosses_a_value_boundary_or_names_the_wrong_path_is_refused(self):
        out = self._run("--item", "rule-01", "--disposition", "amend", "--note", "n", "--path", "name",
                        "--replace", "sum to 100 bytes", "--with", "sum to 80 bytes", "--execute")
        self.assertNotEqual(out.exit_code, 0); self.assertIn("not exactly 'name'", out.output)
        self.assertIn("sum to 100 bytes", (self.full_dir / "VOICE_d4d.yaml").read_text())
        out = self._run("--item", "rule-01", "--disposition", "amend", "--note", "n", "--path", "source_caveats",
                        "--replace", "bytes", "--with", "octets", "--execute")
        self.assertNotEqual(out.exit_code, 0); self.assertIn("occurs", out.output)


if __name__ == "__main__":
    unittest.main()
