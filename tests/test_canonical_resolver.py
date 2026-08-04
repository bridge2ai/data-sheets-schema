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
from data_sheets_schema.runs import AmbiguousCanonical, canonical_runs

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


class TestAmbiguity(unittest.TestCase):
    """#308: `select --execute` does not clear a prior mark.

    The plan in NEXT_TASKS §9 re-selects canonical after a v3 run, which leaves
    every project carrying two marks. Keeping whichever label sorted last would
    have made the answer a property of the string — and v3 labels sort after v2
    ones, so it would have been right by accident until a label broke the
    pattern.
    """

    def _corpus(self, tmp, labels):
        import yaml
        root = Path(tmp)
        for label in labels:
            d = root / "m_core" / label
            d.mkdir(parents=True)
            (d / "CHORUS_provenance.yaml").write_text(yaml.safe_dump({
                "run": {"project": "CHORUS", "label": label, "method": "m"},
                "canonical": {"criterion": "c", "selected_from": [{}, {}, {}]},
                "outputs": {"full": {"path": f"{label}/f.yaml"},
                            "core": {"path": f"{label}/c.yaml"}}}))
        return root

    def test_two_marks_for_one_project_raise(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = self._corpus(tmp, ["2026-01-01_config-a_rep1",
                                      "2026-09-09_config-b_rep1"])
            with self.assertRaises(AmbiguousCanonical) as ctx:
                canonical_runs(concat_dir=root)
            self.assertIn("CHORUS", str(ctx.exception))
            self.assertIn("config-a", str(ctx.exception))
            self.assertIn("config-b", str(ctx.exception))

    def test_a_config_filter_resolves_the_ambiguity(self):
        """--config already narrows correctly; it just had to be required."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = self._corpus(tmp, ["2026-01-01_config-a_rep1",
                                      "2026-09-09_config-b_rep1"])
            got = canonical_runs(concat_dir=root, config="2026-09-09")
            self.assertEqual(got["CHORUS"]["label"], "2026-09-09_config-b_rep1")

    def test_one_mark_does_not_raise(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = self._corpus(tmp, ["2026-01-01_config-a_rep1"])
            self.assertEqual(list(canonical_runs(concat_dir=root)), ["CHORUS"])

    def test_the_command_names_the_configurations(self):
        """The user cannot pass --config without knowing what to pass."""
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = self._corpus(tmp, ["2026-01-01_config-a_rep1",
                                      "2026-09-09_config-b_rep1"])
            with mock.patch("data_sheets_schema.runs.CONCAT_DIR", root):
                out = CliRunner().invoke(runs, ["canonical"])
        self.assertEqual(out.exit_code, 2)
        self.assertIn("config-a", out.output)


if __name__ == "__main__":
    unittest.main()
