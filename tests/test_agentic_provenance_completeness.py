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

    def test_the_digest_is_the_one_on_disk(self):
        """Observed, not asserted: the run validated against this schema."""
        self.assertEqual(
            (self.data.get("schema") or {}).get("digest_md5"),
            schema_digest.fingerprint(schema_digest.digest_text("Dataset")))

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
