"""A label's condition and its hashed prompt must name the same thing (#420).

The 2026-08-07 sweep is labelled `generic-v3` and hashes
`d4d_generic_arm_prompt.md`, which is v1. v3 adds seven decision rules over v1,
so they are different conditions and the label was the only place the v3 claim
existed — an assertion by whoever typed it, checkable by nothing.
"""

import unittest
from pathlib import Path

from data_sheets_schema.runs import (condition_from_label,
                                     prompt_condition_mismatch)


class TestReadingTheConditionOffALabel(unittest.TestCase):

    def test_versioned_conditions_win_over_their_prefix(self):
        """`generic` is a prefix of `generic-v3`, so a shortest-first scan
        answers `generic` for every versioned label — reporting the exact
        mismatch this exists to detect as agreement."""
        self.assertEqual(
            "generic_v3",
            condition_from_label("2026-08-07_claude-opus-5-claudecode-generic-v3_rep2"))
        self.assertEqual(
            "generic_v2",
            condition_from_label("2026-07-31_claude-opus-5-generic-v2_rep1"))

    def test_hyphens_and_underscores_are_the_same_spelling(self):
        self.assertEqual("generic_v4",
                         condition_from_label("2026-09-01_x-generic-v4_rep1"))
        self.assertEqual("generic_v4",
                         condition_from_label("2026-09-01_x_generic_v4_rep1"))

    def test_a_label_naming_no_condition_returns_none(self):
        """Labels predating the convention name none; that is not a defect."""
        self.assertIsNone(condition_from_label("2026-07-27_claude-opus-5_rep1"))

    def test_plain_generic_is_still_recognised(self):
        self.assertEqual("generic",
                         condition_from_label("2026-07-28_claude-opus-5-generic_rep1"))


class TestTheMismatchIsSilentWhenItCannotTell(unittest.TestCase):
    """Absence of evidence must not read as a mismatch: a run whose label names
    no condition, or which has no record, is not thereby inconsistent."""

    def test_an_unknown_run_reports_nothing(self):
        self.assertIsNone(
            prompt_condition_mismatch("claudecode_agent",
                                      "2099-01-01_no-such-label_rep1", "VOICE"))

    def test_a_label_with_no_condition_reports_nothing(self):
        self.assertIsNone(
            prompt_condition_mismatch("claudecode_agent",
                                      "2026-07-27_claude-opus-5_rep1", "VOICE"))


class TestTheKnownMismatchIsDetected(unittest.TestCase):

    LABEL = "2026-08-07_claude-opus-5-claudecode-generic-v3_rep2"

    def test_the_2026_08_07_sweep_is_flagged(self):
        m = prompt_condition_mismatch("claudecode_agent", self.LABEL, "VOICE")
        if m is None:
            self.skipTest("corpus not present")
        self.assertIn("generic_v3", m)
        self.assertIn("d4d_generic_arm_prompt.md", m)


class TestPlaybooksAreHashed(unittest.TestCase):
    """`.claude/commands/d4d-agent.md` carries the slot-filling contract that
    produces v3 behaviour on the agentic path, mirrored there by #394. It was
    hashed nowhere, so two runs following different playbook content were
    indistinguishable afterwards."""

    def test_the_playbooks_a_run_follows_are_recorded(self):
        from data_sheets_schema.provenance import playbook_facts
        facts = playbook_facts()
        named = {f["path"] for f in facts["files"]}
        self.assertIn(".claude/commands/d4d-agent.md", named)
        self.assertIn(".claude/commands/d4d-full-core.md", named)
        self.assertIn(".claude/agents/d4d-provenance-guard.md", named)

    def test_each_carries_a_hash_and_a_length(self):
        from data_sheets_schema.provenance import playbook_facts
        for f in playbook_facts()["files"]:
            with self.subTest(path=f["path"]):
                if f["exists"]:
                    self.assertEqual(64, len(f["sha256"]))
                    self.assertGreater(f["bytes"], 0)

    def test_a_missing_playbook_is_recorded_as_missing_not_omitted(self):
        from pathlib import Path
        from data_sheets_schema.provenance import playbook_facts
        facts = playbook_facts((Path(".claude/commands/no-such-file.md"),))
        self.assertFalse(facts["files"][0]["exists"])
        self.assertIsNone(facts["files"][0]["sha256"])


if __name__ == "__main__":
    unittest.main()


class TestPlaybooksAreNotFabricatedForOldRuns(unittest.TestCase):
    """Raised reviewing #420, against my own change.

    `playbook_facts()` was called unconditionally in `build_record`, so
    `d4d provenance backfill` — which builds `mode="reconstructed"` records —
    would have hashed *today's* `.claude/` content and recorded it as what a
    historical run followed.

    That is exactly the claim this module's docstring forbids: "hashing them
    today and recording that against an April run would be a fabricated
    provenance claim. Such fields are listed under `unrecoverable` with the
    reason, never silently filled."
    """

    LABEL = "2026-08-07_claude-opus-5-claudecode-generic-v3_rep2"
    BUNDLE = Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")

    def _record(self, mode, **kw):
        from data_sheets_schema.provenance import build_record
        return build_record("VOICE", "claudecode_agent", self.LABEL,
                            mode=mode, **kw).data

    def test_a_live_record_hashes_them(self):
        if not self.BUNDLE.exists():
            self.skipTest("bundles not present")
        d = self._record("live", input_bundle=self.BUNDLE, input_verified=True)
        self.assertEqual(3, len(d["playbooks"]["files"]))

    def test_a_reconstructed_record_does_not(self):
        d = self._record("reconstructed")
        self.assertIsNone(d["playbooks"])

    def test_and_says_why_rather_than_omitting_the_field(self):
        """Absent with no reason reads as "this run had none", which is a
        different and false claim."""
        d = self._record("reconstructed")
        fields = {u["field"] for u in d["unrecoverable"]}
        self.assertIn("playbooks", fields)
        reason = next(u["reason"] for u in d["unrecoverable"]
                      if u["field"] == "playbooks")
        self.assertIn("cannot be recovered", reason)
