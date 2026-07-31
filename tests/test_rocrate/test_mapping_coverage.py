"""The RO-Crate mapping must be checkable against the schema it targets.

A row naming a slot that no longer exists is invisible at run time — the
transformation produces an absent field, which is indistinguishable from a crate
that lacked the property, and reports success either way. That is how a row
mapping to `vulnerable_populations` survived its rename for five months.
"""

import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(".claude/agents/scripts/check_mapping_coverage.py")
MAPPING = Path("data/ro-crate_mapping/"
               "D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv")


class TestMappingCoverage(unittest.TestCase):

    def setUp(self):
        if not (SCRIPT.exists() and MAPPING.exists()):
            self.skipTest("mapping or checker not present")

    def _run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              capture_output=True, text=True, timeout=300)

    def test_the_renamed_slot_is_gone_from_the_mapping(self):
        """at_risk_populations replaced vulnerable_populations in the schema."""
        text = MAPPING.read_text(encoding="utf-8")
        self.assertNotIn("vulnerable_populations", text)
        self.assertIn("at_risk_populations", text)

    def test_the_checker_reports_a_measured_figure(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("induced slots", r.stdout)
        self.assertIn("mapped, direct", r.stdout)

    def test_nested_class_slots_are_not_reported_as_broken(self):
        """`md5` and `bytes` belong to File, reached via file_collections.

        Grading against Dataset's induced slots alone called eight valid
        mappings broken and buried the two real ones.
        """
        r = self._run()
        broken = r.stdout.split("resolve to\nnothing", 1)[-1]
        for slot in ("md5", "bytes", "media_type"):
            with self.subTest(slot=slot):
                self.assertNotIn(f"  {slot}\n", broken)
        self.assertIn("mapped, nested classes", r.stdout)

    def test_strict_mode_fails_while_broken_rows_remain(self):
        """Two rows still resolve to nothing; strict must not pass silently."""
        r = self._run("--strict")
        if "in no class" not in r.stdout:
            self.assertEqual(r.returncode, 0)
        else:
            self.assertEqual(r.returncode, 1,
                             "strict mode must fail while rows resolve to nothing")

    def test_the_doc_no_longer_asserts_a_fixed_coverage_number(self):
        """Asserting the figure is the defect; explaining it is not.

        An earlier version of this test forbade the string anywhere, which also
        forbade the paragraph documenting why the number was wrong — the one
        place it belongs.
        """
        doc = Path(".claude/agents/d4d-rocrate.md")
        if not doc.exists():
            self.skipTest("agent doc not present")
        text = doc.read_text()
        for claim in ("95.2% D4D field coverage",
                      "(95.2% coverage)",
                      "| 95.2%"):
            with self.subTest(claim=claim):
                self.assertNotIn(claim, text)
        self.assertIn("check_mapping_coverage.py", text,
                      "the doc must point at the measurement instead")


if __name__ == "__main__":
    unittest.main()
