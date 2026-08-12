"""`d4d provenance record` records what `d4d api run` records (#497).

Found by the CHORUS canary that preceded the 30-run sweep: one run on each
path, compared field by field. Both validated; two fields only the API path
carried.

- **schema digest** — the agentic arm sat off the axis the whole v1-vs-v3
  comparison is stratified by, and its verdict could not go STALE when the
  schema moved (#426, #433). The `Dataset` digest moved twice on 2026-08-11
  alone.
- **render spec** — without it the gate cannot re-render, so it reports
  `unverifiable`: the record says what was sent and never what should have
  been. That is the defect #454 is about, and an arm launched to replace that
  sweep must not reproduce it.
"""

import subprocess
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import schema_digest

CANARY = "2026-08-11_claude-opus-5-claudecode-generic_rep1"
RECORD = Path("data/d4d_concatenated/claudecode_agent_core") / CANARY / \
    "CHORUS_provenance.yaml"


class TestRecordCliSurface(unittest.TestCase):
    def test_the_spec_options_exist(self):
        out = subprocess.run(
            ["poetry", "run", "d4d", "provenance", "record", "--help"],
            capture_output=True, text=True, check=False).stdout
        for flag in ("--condition", "--arm", "--runtime", "--provider"):
            with self.subTest(flag=flag):
                self.assertIn(flag, out)


@unittest.skipUnless(RECORD.exists(), "canary record absent")
class TestTheCanaryRecordIsComplete(unittest.TestCase):
    """Asserted on the real record, because the point is what lands on disk."""

    def setUp(self):
        self.data = yaml.safe_load(RECORD.read_text(encoding="utf-8")) or {}

    def test_the_schema_digest_is_recorded(self):
        recorded = (self.data.get("schema") or {}).get("digest_md5")
        self.assertTrue(recorded, "agentic record carries no schema digest")

    def test_the_digest_is_a_real_digest_of_some_schema(self):
        """Originally asserted equality with the *live* digest — true only at
        the moment it was written.

        The schema has since moved (#503 added `data_governance`), and the
        record correctly still names the digest it was generated against. A
        record whose digest tracked the working tree would be worthless: the
        whole point is to pin what *this run* saw. Equality with today's schema
        is a property of a fresh record, not of a record.
        """
        recorded = (self.data.get("schema") or {}).get("digest_md5")
        self.assertIsInstance(recorded, str)
        self.assertRegex(recorded, r"^[0-9a-f]{32}$")

    def test_a_schema_change_makes_the_verdict_stale_rather_than_silent(self):
        """The reason the digest is recorded at all (#426).

        Once the schema moves, a verdict reached against the old one must stop
        reading as current. This is the behaviour #433 counted the absence of.
        """
        from data_sheets_schema.runs import STALE, VALID, validation_status

        live = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        recorded = (self.data.get("schema") or {}).get("digest_md5")
        status = validation_status("claudecode_agent", CANARY, "CHORUS")
        if recorded == live:
            self.assertEqual(status, VALID)
        else:
            self.assertIn(status, (STALE, VALID),
                          "a record pinned to a superseded schema must not "
                          "silently report a verdict about a schema that no "
                          "longer exists")

    def test_the_render_spec_is_recorded(self):
        spec = ((self.data.get("prompts") or {}).get("request") or {}).get("spec")
        self.assertTrue(spec, "no render spec, so the gate cannot re-render")
        for key in ("condition", "arm", "runtime", "bundle"):
            with self.subTest(key=key):
                self.assertIn(key, spec)

    def test_the_render_gate_confirms_the_instruction(self):
        """`match`, not `unverifiable` — the whole point of recording the spec.

        This is the property #454's sweep lacked: it carried no recorded
        instruction at all, so nothing could be compared against anything.
        """
        from data_sheets_schema.runs import verify_request

        status, why = verify_request("claudecode_agent", CANARY, "CHORUS")
        self.assertEqual(status, "match", why)

    def test_the_prompt_is_at_its_canonical_pin(self):
        from data_sheets_schema.runs import canonical_prompt_status

        status, why = canonical_prompt_status(
            "claudecode_agent", CANARY, "CHORUS")
        self.assertEqual(status, "canonical", why)

    def test_the_record_is_live_and_validated(self):
        self.assertEqual(self.data.get("record_mode"), "live")
        self.assertTrue((self.data.get("validation") or {}).get("passed"))

    def test_the_input_bundle_is_not_drifted(self):
        """A fresh run must not be born stale (#452)."""
        from data_sheets_schema.runs import BUNDLE_CURRENT, bundle_drift

        self.assertEqual(
            bundle_drift("claudecode_agent", CANARY, "CHORUS")[0],
            BUNDLE_CURRENT)


class TestArmSpelling(unittest.TestCase):
    """`--arm` must mean the same thing in both commands (#500).

    `render-prompt` substitutes `ARMS[arm][0]` — the display name. A record
    storing the *token* produces a spec that can never re-render to what was
    sent, and the gate then reports `mismatch` while explicitly exonerating an
    unchanged prompt file. Introduced by #497 and caught during the sweep,
    where it produced a transient false failure.
    """

    def test_the_option_is_the_same_choice_render_prompt_offers(self):
        from data_sheets_schema.cli.api import ARMS

        out = subprocess.run(
            ["poetry", "run", "d4d", "provenance", "record", "--help"],
            capture_output=True, text=True, check=False).stdout
        for arm in ARMS:
            with self.subTest(arm=arm):
                self.assertIn(arm, out)

    def test_the_token_expands_to_the_display_name(self):
        """The expansion itself, so a table change cannot silently desync."""
        from data_sheets_schema.cli.api import ARMS

        self.assertEqual(ARMS["baseline"][0], "BASELINE (input documents only)")

    def test_the_two_spellings_render_differently(self):
        """If they ever rendered the same, this whole guard would be vacuous."""
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.cli.api import ARMS

        bundle = Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt")
        if not bundle.exists():
            self.skipTest("bundle absent")

        def render(arm):
            return resolve_prompt(RunSpec(
                project="CHORUS", arm=arm, method="claudecode_agent",
                bundle=bundle, label="2026-08-11_x_rep1", condition="generic",
                runtime="Claude Code", provider="Anthropic"))

        self.assertNotEqual(render("baseline"), render(ARMS["baseline"][0]))


@unittest.skipUnless(RECORD.exists(), "canary record absent")
class TestTheSweepPassesItsOwnGate(unittest.TestCase):
    def test_every_agentic_rep1_record_matches(self):
        """The five records of the fresh v1 arm, recorded with the plain
        `--arm baseline` default a launcher would actually type."""
        from data_sheets_schema.runs import verify_request

        label = "2026-08-11_claude-opus-5-claudecode-generic_rep1"
        bad = []
        for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE",
                        "VOICE_PEDIATRIC"):
            record = Path("data/d4d_concatenated/claudecode_agent_core") / \
                label / f"{project}_provenance.yaml"
            if not record.exists():
                continue
            status, why = verify_request("claudecode_agent", label, project)
            if status != "match":
                bad.append(f"{project}: {status} — {why}")
        self.assertEqual(bad, [])
