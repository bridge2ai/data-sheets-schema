"""A canonical mark nobody can read answers nothing (#306).

`d4d runs select` wrote a `canonical` block and the only reader in the tree was
the test for the writer. #176 called selection the answer to "which record *is*
the CHORUS datasheet"; until something could enumerate the marks, that was an
answer only for someone who already knew to open provenance.

#287's scoping needs the enumeration before it can size an evaluation: "one
canonical record per project" is a number only if the set can be listed.
"""

import unittest
from pathlib import Path

from click.testing import CliRunner

from data_sheets_schema.cli.runs import runs
from data_sheets_schema.constants import PROJECTS
from data_sheets_schema.runs import canonical_runs

REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless((REPO / "data" / "d4d_concatenated").exists(),
                     "corpus not present")
class TestCanonicalRuns(unittest.TestCase):

    def setUp(self):
        self.found = canonical_runs()

    def test_it_finds_the_marked_records(self):
        self.assertEqual(sorted(self.found), ["AI_READI", "CHORUS", "CM4AI"])

    def test_voice_is_absent_rather_than_guessed(self):
        """No VOICE replicate validates (#292), so it has no canonical record.

        Absent, not least-bad: picking one would ship a record known to be
        broken, which is what `select` refuses to do.
        """
        self.assertNotIn("VOICE", self.found)

    def test_every_entry_resolves_to_records_that_exist(self):
        for project, entry in self.found.items():
            for variant in ("full", "core"):
                with self.subTest(project=project, variant=variant):
                    self.assertTrue((REPO / entry[variant]).is_file(),
                                    entry[variant])

    def test_each_entry_carries_its_criterion_and_candidates(self):
        """A mark that does not say why is not auditable."""
        for project, entry in self.found.items():
            with self.subTest(project=project):
                self.assertTrue(entry["criterion"])
                self.assertEqual(entry["candidates"], 3)

    def test_a_config_filter_narrows_it(self):
        self.assertEqual(
            canonical_runs(config="2026-07-31_claude-opus-5-generic-v2"),
            self.found)
        self.assertEqual(canonical_runs(config="no-such-config"), {})


@unittest.skipUnless((REPO / "data" / "d4d_concatenated").exists(),
                     "corpus not present")
class TestTheCommand(unittest.TestCase):

    def _run(self, *args):
        return CliRunner().invoke(runs, ["canonical", *args])

    def test_paths_only_is_pipeable(self):
        """What an evaluation sweep consumes."""
        out = self._run("--paths-only")
        self.assertEqual(out.exit_code, 0, out.output)
        lines = [l for l in out.output.splitlines() if l.strip()]
        self.assertEqual(len(lines), 2 * len(canonical_runs()),
                         "one full and one core per canonical project")
        for line in lines:
            self.assertTrue((REPO / line).is_file(), line)

    def test_missing_names_the_gap(self):
        out = self._run("--missing")
        self.assertIn("VOICE", out.output)

    def test_the_gap_is_every_project_without_a_mark(self):
        out = self._run("--missing")
        named = {l.strip() for l in out.output.splitlines() if l.strip()}
        self.assertEqual(named, set(PROJECTS) - set(canonical_runs()))

    def test_one_project_can_be_asked_for(self):
        out = self._run("--project", "CHORUS")
        self.assertEqual(out.exit_code, 0)
        self.assertIn("CHORUS", out.output)
        self.assertNotIn("CM4AI", out.output)

    def test_asking_for_a_project_without_one_fails_rather_than_empties(self):
        """Silence would read as "no canonical needed" rather than "none exists"."""
        out = self._run("--project", "VOICE")
        self.assertNotEqual(out.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
