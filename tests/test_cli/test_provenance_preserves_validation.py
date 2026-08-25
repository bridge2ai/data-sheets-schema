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
        # The recorder refuses any cwd that is not shaped like the repo root
        # (#672): it needs both marker directories. The tests run in a scratch
        # root by design — they test verdict preservation, not cwd policy —
        # so the scratch root carries the markers.
        (self.root / 'src' / 'data_sheets_schema').mkdir(parents=True)

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


class TestTheVerdictDoesNotOutliveItsSchema(unittest.TestCase):
    """Raised reviewing #396. "Validates" is a claim about a record *against a
    schema*, and `validation.artifacts` pins only the record.

    Before the carry-forward existed the gap was bounded: a re-record dropped
    the verdict and forced re-validation. Carrying it would let a verdict
    outlive the schema it was reached against, so the record's own `schema`
    block is compared too. The underlying blind spot in `validation_status` is
    #426.
    """

    def setUp(self):
        from data_sheets_schema.provenance import preservable_validation
        self.fn = preservable_validation
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "prov.yaml"
        self.artifact = Path(self.tmp.name) / "rec.yaml"
        self.artifact.write_text("id: x\n")
        self.md5 = hashlib.md5(self.artifact.read_bytes()).hexdigest()
        self.prior = {
            "schema": {"full_sha256": "aaa", "core_sha256": "bbb"},
            "validation": {
                "passed": True,
                "artifacts": {"full": {"path": str(self.artifact),
                                       "md5": self.md5}},
            },
        }
        self.path.write_text(yaml.safe_dump(self.prior, sort_keys=False))

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_schema_carries(self):
        new = {"schema": {"full_sha256": "aaa", "core_sha256": "bbb"}}
        self.assertIsNotNone(self.fn(self.path, new))

    def test_a_changed_full_schema_drops_it(self):
        new = {"schema": {"full_sha256": "CHANGED", "core_sha256": "bbb"}}
        self.assertIsNone(self.fn(self.path, new))

    def test_a_changed_core_schema_drops_it(self):
        new = {"schema": {"full_sha256": "aaa", "core_sha256": "CHANGED"}}
        self.assertIsNone(self.fn(self.path, new))


class PhaseVocabulary(unittest.TestCase):
    """--phase names must be phases the pipeline has (#642).

    The agentic arm's phase_log is its only phase attestation (#400), so a
    typo used to enter the record as an accomplished phase with nothing able
    to tell it from a real one.
    """

    def test_known_names_pass_in_both_forms(self):
        from data_sheets_schema.cli.provenance import _parse_phases
        parsed = _parse_phases(["full", '{"name": "audit", "completed": false}'])
        self.assertEqual([p["name"] for p in parsed], ["full", "audit"])

    def test_a_typo_is_refused_with_the_vocabulary_named(self):
        import click

        from data_sheets_schema.cli.provenance import _parse_phases
        for bad in ("recncile_full", '{"name": "phase_7"}'):
            with self.subTest(value=bad):
                with self.assertRaises(click.BadParameter) as caught:
                    _parse_phases([bad])
                self.assertIn("full", str(caught.exception),
                              "the refusal must name the known phases")

    def test_the_vocabulary_derives_from_the_pipeline(self):
        """Derived, not restated: a phase added to PHASES is known here."""
        from data_sheets_schema.api_runner import PHASES
        from data_sheets_schema.cli.provenance import _known_phases
        self.assertTrue(set(PHASES) <= _known_phases())
        self.assertIn("report_after_repair", _known_phases())

    def test_the_playbook_instructed_names_are_accepted(self):
        """The agentic playbook (d4d-full-core.md) instructs these exact
        names in its record template; a vocabulary that refuses the only
        names the agentic path is told to use validates nothing (#672 F1).
        `repair` and `report_after_repair` joined when the playbook gained
        the API pipeline's closing loop."""
        from data_sheets_schema.cli.provenance import _parse_phases
        names = ["generate_full", "generate_core", "source_audit",
                 "reconcile", "repair", "report_after_repair"]
        self.assertEqual([p["name"] for p in _parse_phases(names)], names)

    def test_observed_totals_are_kept_and_api_fields_are_refused(self):
        """The orchestrator may record aggregate totals it observed; the
        phase agent's own estimates in api_usage shape are refused, because
        a phase log that looks comparable to api_usage and is not would be
        worse than the gap it fills (#400)."""
        import click

        from data_sheets_schema.cli.provenance import _parse_phases
        from data_sheets_schema.provenance import phase_facts

        ok = _parse_phases(['{"name": "generate_full", "completed": true, '
                            '"observed": {"total_tokens": 48211, '
                            '"tool_uses": 31, "duration_ms": 812000}}'])
        block = phase_facts(ok)
        self.assertEqual(block["phases"][0]["observed"]["total_tokens"], 48211)
        self.assertIn("observed_basis", block)
        self.assertIn("not billing-grade", block["observed_basis"])

        for bad in ('{"name": "generate_full", "input_tokens": 5}',
                    '{"name": "generate_full", "seconds": 3.2}',
                    '{"name": "repair", "observed": {"cost_usd": 3}}',
                    '{"name": "repair", "observed": {}}'):
            with self.subTest(value=bad):
                with self.assertRaises(click.BadParameter):
                    _parse_phases([bad])

    def test_a_log_with_no_observed_block_claims_no_observation(self):
        """A phase log whose phases carry no observed block must not carry
        the basis either — a basis with nothing under it reads as data."""
        from data_sheets_schema.cli.provenance import _parse_phases
        from data_sheets_schema.provenance import phase_facts
        block = phase_facts(_parse_phases(["generate_full", "reconcile"]))
        self.assertNotIn("observed_basis", block)

    def test_the_playbook_template_itself_parses(self):
        """Read the names out of the playbook rather than restating them, so
        an edited template cannot silently diverge from this vocabulary.
        The template is not literal JSON (it carries {FILL-IN} placeholders),
        so only the names are extracted and checked."""
        import re

        from data_sheets_schema.cli.provenance import _known_phases
        playbook = Path(".claude/commands/d4d-full-core.md").read_text(
            encoding="utf-8")
        names = re.findall(r"--phase '\{\"name\":\"([a-z_]+)\"", playbook)
        self.assertTrue(names, "the playbook no longer shows --phase examples")
        unknown = set(names) - _known_phases()
        self.assertFalse(
            unknown,
            f"the playbook instructs phase names the recorder refuses: "
            f"{sorted(unknown)}")


class SchemaResolutionAwayFromRepoRoot(unittest.TestCase):
    """The #659 class: cwd-relative constants on paths that run anywhere.

    `d4d provenance record` is the agentic arm's recorder; launched outside
    the repo root it died on FileNotFoundError with no record written.
    """

    def test_digest_and_schema_facts_work_from_a_temp_cwd(self):
        import os
        import tempfile

        from data_sheets_schema import schema_digest as sd
        from data_sheets_schema.provenance import schema_facts
        cwd = os.getcwd()
        # Clear the digest caches first: they are process-global and keyed on
        # (class, ""), so a warm cache from any earlier test would satisfy the
        # assertion without resolve_schema ever running (#672 review).
        sd._BUILD_CACHE.clear()
        sd._TEXT_CACHE.clear()
        try:
            with tempfile.TemporaryDirectory() as d:
                os.chdir(d)
                self.assertTrue(
                    sd.fingerprint(sd.digest_text("Dataset")))
                facts = schema_facts()
                self.assertTrue(facts["full_sha256"])
                self.assertTrue(facts["core_sha256"])
        finally:
            os.chdir(cwd)
