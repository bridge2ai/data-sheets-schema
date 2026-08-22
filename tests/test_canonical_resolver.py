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
        """Which projects are marked is a property of the corpus, not of the
        resolver, so it is not asserted as a literal.

        This used to read `["AI_READI", "CHORUS", "CM4AI"]`. Two sweeps later
        that list was wrong twice over: #292 was fixed so VOICE gained a
        canonical record, and VOICE_PEDIATRIC became a project in its own
        right. A test that has to be edited every time generation improves is
        measuring the calendar.
        """
        self.assertTrue(self.found, "no project has a canonical record")
        self.assertLessEqual(set(self.found), set(PROJECTS))

    def test_a_project_with_no_valid_replicate_is_absent_rather_than_guessed(self):
        """Absent, not least-bad: marking one would ship a record known to be
        broken, which is what `select` refuses to do.

        Constructed rather than read off the corpus. This assertion used to be
        `assertNotIn("VOICE", found)` and rested on #292 keeping every VOICE
        replicate invalid; when that was fixed the test failed, having become a
        statement about VOICE rather than about the resolver.
        """
        import tempfile
        import yaml as _yaml
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "m_core" / "2026-01-01_config_rep1"
            d.mkdir(parents=True)
            # A run with provenance but no `canonical` block: the shape
            # `select` leaves behind when no replicate is fit to mark.
            (d / "CHORUS_provenance.yaml").write_text(_yaml.safe_dump({
                "run": {"project": "CHORUS", "label": "2026-01-01_config_rep1",
                        "method": "m"},
                "outputs": {"full": {"path": "f.yaml"},
                            "core": {"path": "c.yaml"}}}))
            self.assertEqual({}, canonical_runs(concat_dir=Path(tmp)))

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
        """The config is derived from the marks, not hardcoded: it changes with
        every sweep, and pinning it made this test expire on a schedule.

        It used to assert all marks share one config. That became factually
        wrong the day selection moved four projects to the v5 arm while
        VOICE_PEDIATRIC — deliberately excluded from that arm, no v4 baseline
        (#590) — kept its 2026-08-11 canonical. Multiple configs across
        projects is the lawful state whenever a project sits out a sweep; the
        invariant that holds is one mark per project, and that a config
        filter returns exactly the marks carrying it.
        """
        configs = {e["label"].rsplit("_rep", 1)[0] for e in self.found.values()}
        for config in sorted(configs):
            subset = {p: e for p, e in self.found.items()
                      if e["label"].rsplit("_rep", 1)[0] == config}
            with self.subTest(config=config):
                self.assertEqual(canonical_runs(config=config), subset)
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

    def test_the_gap_is_every_project_without_a_mark(self):
        """Derived, not literal. This pair used to assert `"VOICE" in output`;
        #292 was fixed, every project gained a mark, and the gap is now empty —
        so the old assertion tested that generation was still broken."""
        gap = set(PROJECTS) - set(canonical_runs())
        out = self._run("--missing")
        self.assertEqual(out.exit_code, 0, out.output)
        if not gap:
            self.assertIn("Every project has a canonical record", out.output)
            return
        named = {l.strip() for l in out.output.splitlines() if l.strip()}
        self.assertEqual(named, gap)

    def test_one_project_can_be_asked_for(self):
        out = self._run("--project", "CHORUS")
        self.assertEqual(out.exit_code, 0)
        self.assertIn("CHORUS", out.output)
        self.assertNotIn("CM4AI", out.output)

    def test_asking_for_a_project_without_one_fails_rather_than_empties(self):
        """Silence would read as "no canonical needed" rather than "none exists".

        The project is derived. This used to name VOICE, which had no mark only
        because #292 was open; when that was fixed the test asserted that a
        successful lookup should fail. With every project now marked there is
        nothing on the real corpus to exercise, so the case is skipped here and
        the behaviour is held by the library-level test above.
        """
        gap = sorted(set(PROJECTS) - set(canonical_runs()))
        if not gap:
            self.skipTest("every project has a canonical record")
        out = self._run("--project", gap[0])
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
