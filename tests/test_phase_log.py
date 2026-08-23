"""What a run says about its own phases (#562).

The API path records eight `api_usage` entries per run — phase, attempt,
seconds, tokens, stop reason. The agentic path recorded nothing, so its phase
structure existed only as prose in the reconciliation report, and #546 showed a
report is not a reliable account of what happened.

That made every arm comparison one-sided in a way easy to miss: #544's finding
was about a phase, and the same question could not be asked of the other arm
from the record at all.
"""

import unittest

from data_sheets_schema.provenance import (
    PHASE_FIELDS_UNAVAILABLE_TO_AGENTS,
    phase_facts,
)


class PhaseFactsTest(unittest.TestCase):

    def test_order_is_kept_and_numbered(self):
        block = phase_facts([{"name": "a"}, {"name": "b"}, {"name": "c"}])
        self.assertEqual([p["phase"] for p in block["phases"]], ["a", "b", "c"])
        self.assertEqual([p["ordinal"] for p in block["phases"]], [1, 2, 3])

    def test_nothing_recorded_is_none_not_an_empty_log(self):
        """An empty phase log reads as a run that performed no phases."""
        self.assertIsNone(phase_facts([]))

    def test_iterations_only_appear_when_given(self):
        """`iterations: 1` on a phase that cannot loop implies it was measured."""
        block = phase_facts([{"name": "a"}, {"name": "b", "iterations": 3}])
        self.assertNotIn("iterations", block["phases"][0])
        self.assertEqual(block["phases"][1]["iterations"], 3)

    def test_an_incomplete_phase_says_so(self):
        block = phase_facts([{"name": "a", "completed": False}])
        self.assertFalse(block["phases"][0]["completed"])

    def test_timing_and_tokens_are_named_unavailable_not_omitted(self):
        """#400 is a runtime limit, and a named limit reads differently from
        an absent field: one is a fact about the instrument, the other looks
        like an oversight."""
        block = phase_facts([{"name": "a"}])
        self.assertEqual(set(block["unavailable"]),
                         set(PHASE_FIELDS_UNAVAILABLE_TO_AGENTS))
        self.assertIn("#400", block["unavailable_basis"])
        for field in PHASE_FIELDS_UNAVAILABLE_TO_AGENTS:
            with self.subTest(field=field):
                self.assertNotIn(field, block["phases"][0])


class ParseTest(unittest.TestCase):

    def _parse(self, *specs):
        from data_sheets_schema.cli.provenance import _parse_phases
        return _parse_phases(specs)

    def test_a_bare_name_is_a_completed_phase(self):
        self.assertEqual(self._parse("audit"),
                         [{"name": "audit", "completed": True}])

    def test_json_carries_the_detail(self):
        # `reconcile_full` rather than the pre-#642 arbitrary "reconcile":
        # names are now validated against the pipeline's vocabulary, and this
        # test is about the JSON detail carrying, not the name.
        got = self._parse(
            '{"name":"reconcile_full","completed":true,"iterations":3}')
        self.assertEqual(got[0]["iterations"], 3)

    def test_malformed_json_raises_rather_than_being_dropped(self):
        """A log missing one phase is worse than no log: it reads as a run
        that skipped a step."""
        import click
        with self.assertRaises(click.BadParameter):
            self._parse('{"name": "broken"')
        with self.assertRaises(click.BadParameter):
            self._parse('{"completed": true}')


class StatusTest(unittest.TestCase):
    """Three answers, because two would misdescribe one of the arms."""

    def test_the_three_statuses_are_distinct(self):
        from data_sheets_schema.runs import (
            PHASES_ABSENT, PHASES_API, PHASES_RECORDED,
        )
        self.assertEqual(len({PHASES_ABSENT, PHASES_API, PHASES_RECORDED}), 3)

    def test_an_api_record_reports_its_api_usage(self):
        from pathlib import Path

        from data_sheets_schema.runs import PHASES_API, phase_log_status
        label = "2026-08-13_claude-opus-5-api-generic-v4_rep1"
        if not (Path("data/d4d_concatenated/claudecode_agent_core") / label
                / "CHORUS_provenance.yaml").exists():
            self.skipTest("v4 arm not present in this checkout")
        status, n = phase_log_status("claudecode_agent", label, "CHORUS")
        self.assertEqual(status, PHASES_API)
        self.assertGreaterEqual(n, 6, "six phases plus repair")


if __name__ == "__main__":
    unittest.main()
