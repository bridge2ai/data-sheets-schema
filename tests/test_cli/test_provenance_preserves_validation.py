"""Re-recording provenance must not silently discard the validation verdict.

`d4d provenance record` rewrites the record from scratch, while the
`validation:` block is written separately by `d4d runs validate`. So any
re-record deleted the verdict and the run failed `d4d runs check --strict`
immediately with "nothing to verify" — while `record` printed a tick and exited
0 (#396).

That was easy to hit, because re-recording is the *correct* response to several
situations: a header field was added, Phase 3 corrected an artifact, provenance
was recorded before the last edit. The playbook worked around it with a
five-step "the order is load-bearing" sequence that had to be executed by hand.

A verdict is a claim about specific bytes, and it is still true if those bytes
have not changed. So it is carried forward when every artifact it names still
hashes to what it recorded, and dropped — loudly — when one does not.
"""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner


HEADER = """\
# D4D Datasheet for TESTPROJ Dataset
# Agent runtime: Claude Code
# Provider: Anthropic
# Model: claude-opus-5
# Reasoning effort: high
# Temperature: 0.0
"""


class TestReRecordPreservesTheVerdict(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli import provenance as prov_cli

        self.cli = prov_cli.provenance
        self.runner = CliRunner()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.label = "2026-08-07_test_rep1"
        self.method = "claudecode_agent"

        concat = self.root / "data" / "d4d_concatenated"
        self.full_dir = concat / self.method / self.label
        self.core_dir = concat / f"{self.method}_core" / self.label
        self.full_dir.mkdir(parents=True)
        self.core_dir.mkdir(parents=True)

        body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
        self.full = self.full_dir / "TESTPROJ_d4d.yaml"
        self.core = self.core_dir / "TESTPROJ_d4d_core.yaml"
        self.full.write_text(HEADER + body)
        self.core.write_text(HEADER + body)
        (self.core_dir / "TESTPROJ_reconciliation.md").write_text("# report\n")

        self.bundle = self.root / "bundle.txt"
        self.bundle.write_text("source documents\n")
        self.record_path = self.core_dir / "TESTPROJ_provenance.yaml"
        self.concat = concat

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self):
        args = ["record", "--project", "TESTPROJ", "--method", self.method,
                "--label", self.label, "--input-bundle", str(self.bundle)]
        cwd = os.getcwd()
        os.chdir(self.root)
        try:
            return self.runner.invoke(self.cli, args)
        finally:
            os.chdir(cwd)

    def _md5(self, p: Path) -> str:
        return hashlib.md5(p.read_bytes()).hexdigest()

    def _add_verdict(self):
        """What `d4d runs validate` writes, in the shape it writes it."""
        data = yaml.safe_load(self.record_path.read_text())
        data["validation"] = {
            "passed": True,
            "artifacts": {
                "full": {"path": str(self.full), "md5": self._md5(self.full)},
                "core": {"path": str(self.core), "md5": self._md5(self.core)},
            },
            "recorded_by": "d4d runs validate",
        }
        self.record_path.write_text(yaml.safe_dump(data, sort_keys=False))

    def test_an_unchanged_verdict_survives_a_re_record(self):
        self._record()
        self._add_verdict()

        result = self._record()
        self.assertEqual(result.exit_code, 0, result.output)

        v = yaml.safe_load(self.record_path.read_text()).get("validation")
        self.assertIsInstance(v, dict, "the verdict was discarded (#396)")
        self.assertTrue(v["passed"])
        self.assertEqual({"full", "core"}, set(v["artifacts"]))
        self.assertIn("carried forward", result.output)

    def test_a_stale_verdict_is_dropped_and_the_drop_is_announced(self):
        self._record()
        self._add_verdict()
        self.full.write_text(self.full.read_text() + "\n# edited after validating\n")

        result = self._record()
        self.assertEqual(result.exit_code, 0, result.output)

        data = yaml.safe_load(self.record_path.read_text())
        self.assertIsNone(data.get("validation"),
                          "a verdict about bytes that changed must not survive")
        self.assertIn("dropped", result.output)
        self.assertIn("d4d runs validate", result.output,
                      "the warning must name the command that fixes it")

    def test_a_record_with_no_prior_verdict_says_nothing_about_one(self):
        result = self._record()
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("carried forward", result.output)
        self.assertNotIn("dropped", result.output)

    def test_a_verdict_naming_a_deleted_artifact_is_dropped(self):
        """`verify_entry` returns None, not False, when the file is gone — the
        distinction that made an early version of this carry it forward."""
        self._record()
        self._add_verdict()
        self.full.unlink()

        self._record()
        data = yaml.safe_load(self.record_path.read_text())
        self.assertIsNone(data.get("validation"))

    def test_a_verdict_with_no_artifacts_is_not_carried(self):
        """Nothing to re-hash means nothing can be shown still true."""
        self._record()
        data = yaml.safe_load(self.record_path.read_text())
        data["validation"] = {"passed": True, "recorded_by": "hand"}
        self.record_path.write_text(yaml.safe_dump(data, sort_keys=False))

        self._record()
        self.assertIsNone(
            yaml.safe_load(self.record_path.read_text()).get("validation"))


if __name__ == "__main__":
    unittest.main()
