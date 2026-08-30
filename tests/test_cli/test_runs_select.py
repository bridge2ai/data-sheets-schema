"""`d4d runs select` — pick one replicate, keep them all (#176).

Selection rather than merging. Replicates state different facts on 47-63% of
the slots they share (generic-v2, judged equivalence), for a coverage gain from
merging of 1-5 slots (#229), and a spliced record can assert a participant count
from one referent and a DOI from another. One replicate is internally coherent
because one generation produced it.

That figure said 77-98% until #169 was settled — byte equality over nested free
text, which counts two wordings of one fact as two facts. The decision is
unchanged: splicing mixes referents at either rate, and the coverage bought is
1-5 slots either way. The old number only made the case look better supported
than it was.

Validity first, coverage second — because coverage alone is nearly arbitrary
here. Across the generic-v2 config the margins are +0, +1, +2 and +1 slots, and
AI-READI is an outright tie that only validity resolves.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from click.testing import CliRunner


def _rec(n):
    d = {"id": "https://example.org/x", "name": "x", "title": "T",
         "description": "d"}
    d.update({f"slot_{i}": [f"v{i}"] for i in range(n)})
    return d


class TestSelect(unittest.TestCase):
    def setUp(self):
        from data_sheets_schema.cli import runs as runs_cli
        self.cli = runs_cli.runs
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "d4d_concatenated"
        self.method = self.root / "claudecode_agent"
        # rep1 smallest, rep2 largest, rep3 middle
        for label, n in (("cfg_rep1", 4), ("cfg_rep2", 9), ("cfg_rep3", 6)):
            d = self.method / label
            d.mkdir(parents=True)
            (d / "P_d4d.yaml").write_text(yaml.safe_dump(_rec(n)),
                                          encoding="utf-8")
            core = self.root / "claudecode_agent_core" / label
            core.mkdir(parents=True, exist_ok=True)
            (core / "P_d4d_core.yaml").write_text("id: x\n", encoding="utf-8")
            (core / "P_reconciliation.md").write_text("# r\n", encoding="utf-8")
            (core / "P_provenance.yaml").write_text(yaml.safe_dump({
                "record_mode": "live",
                "run": {"method": "claudecode_agent", "label": label,
                        "project": "P"}}), encoding="utf-8")
        import data_sheets_schema.runs as runs_mod
        self._orig = runs_mod.CONCAT_DIR
        runs_mod.CONCAT_DIR = self.root

    def tearDown(self):
        import data_sheets_schema.runs as runs_mod
        runs_mod.CONCAT_DIR = self._orig
        self.tmp.cleanup()

    def _run(self, *args, valid=None):
        """`valid` maps label -> bool, or label -> (bool, detail).

        `_validates` returns (ok, detail) so the report can name *which* of the
        two records a run ships failed; "invalid" alone sends the reader to the
        wrong file (#237).
        """
        def fake(record):
            label = Path(record).parent.name
            v = True if valid is None else valid.get(label, True)
            return v if isinstance(v, tuple) else (v, "valid" if v else "invalid")
        with mock.patch("data_sheets_schema.cli.runs._validates", fake):
            return CliRunner().invoke(
                self.cli, ["select", "--project", "P", "--config", "cfg", *args])

    def test_the_largest_valid_replicate_wins(self):
        out = self._run()
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("→ cfg_rep2", out.output)

    def test_validity_outranks_coverage(self):
        """The whole point: the biggest record is not canonical if it is
        broken. On the real corpus this is what resolves AI-READI's tie and
        drops a higher-coverage CM4AI replicate."""
        out = self._run(valid={"cfg_rep2": False})
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("→ cfg_rep3", out.output)

    def test_an_invalid_core_disqualifies_a_run(self):
        """A run ships two records and selection marks both. Judging it on the
        full record alone can bless a run that cannot ship half of itself —
        CM4AI rep1 in the real corpus is exactly that, and is excluded today
        only because it loses on coverage (#237)."""
        out = self._run(valid={"cfg_rep2": (False, "invalid (core)")})
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn("invalid (core)", out.output)
        self.assertIn("→ cfg_rep3", out.output)

    def test_it_refuses_when_nothing_validates(self):
        """No VOICE replicate validates. Picking the least-bad would ship a
        record known to be broken, so the command declines."""
        out = self._run(valid={"cfg_rep1": False, "cfg_rep2": False,
                               "cfg_rep3": False})
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("Nothing here can be canonical", out.output)

    def test_a_thin_margin_is_reported_as_thin(self):
        out = self._run(valid={"cfg_rep2": False})   # rep3 (6) over rep1 (4)
        self.assertIn("ahead of the runner-up", out.output)

    def test_a_dry_run_records_nothing(self):
        before = (self.root / "claudecode_agent_core" / "cfg_rep2" /
                  "P_provenance.yaml").read_text()
        self._run()
        after = (self.root / "claudecode_agent_core" / "cfg_rep2" /
                 "P_provenance.yaml").read_text()
        self.assertEqual(before, after)

    def test_execute_records_the_choice_and_its_candidates(self):
        out = self._run("--execute")
        self.assertEqual(out.exit_code, 0, out.output)
        prov = yaml.safe_load((self.root / "claudecode_agent_core" /
                               "cfg_rep2" / "P_provenance.yaml").read_text())
        canon = prov.get("canonical")
        self.assertIsNotNone(canon, "no canonical block written")
        self.assertEqual(len(canon["selected_from"]), 3,
                         "the losers must be named, or the choice is not "
                         "auditable")
        self.assertIn("criterion", canon)

    def test_nothing_is_moved_or_deleted(self):
        """Replicates are a measurement device; selection marks one, it does
        not collapse the set."""
        self._run("--execute")
        for label in ("cfg_rep1", "cfg_rep2", "cfg_rep3"):
            self.assertTrue((self.method / label / "P_d4d.yaml").exists(),
                            f"{label} disappeared")

    def test_reselecting_clears_the_prior_mark(self):
        """One canonical record per project, enforced rather than hoped for.

        `select` used to leave a previous mark in place, so re-selecting under
        a new config left the project with two and the resolver had to refuse
        (#308). The v3 run re-selects, so this is the next step rather than a
        hypothetical.
        """
        self._run("--execute")                     # cfg_rep2 wins
        first = yaml.safe_load((self.root / "claudecode_agent_core" /
                                "cfg_rep2" / "P_provenance.yaml").read_text())
        self.assertIn("canonical", first)

        # rep2 now invalid, so a different replicate wins the re-selection
        self._run("--execute", valid={"cfg_rep2": False})
        second = yaml.safe_load((self.root / "claudecode_agent_core" /
                                 "cfg_rep3" / "P_provenance.yaml").read_text())
        self.assertIn("canonical", second)

        cleared = yaml.safe_load((self.root / "claudecode_agent_core" /
                                  "cfg_rep2" / "P_provenance.yaml").read_text())
        self.assertNotIn("canonical", cleared,
                         "the prior mark must not survive a re-selection")

    def test_both_records_state_the_relationship(self):
        """Named, not merely removed.

        A mark that vanishes leaves no trace of what the project used to ship,
        and "this replaced that" is the fact a reader of either record wants.
        """
        self._run("--execute")
        self._run("--execute", valid={"cfg_rep2": False})

        winner = yaml.safe_load((self.root / "claudecode_agent_core" /
                                 "cfg_rep3" / "P_provenance.yaml").read_text())
        self.assertEqual(winner["canonical"].get("supersedes"), ["cfg_rep2"])

        loser = yaml.safe_load((self.root / "claudecode_agent_core" /
                                "cfg_rep2" / "P_provenance.yaml").read_text())
        self.assertEqual(loser["canonical_superseded_by"]["label"], "cfg_rep3")
        self.assertIn("at", loser["canonical_superseded_by"])

    def test_the_displaced_mark_is_demoted_and_the_chain_is_transitive(self):
        """#677: the displaced selection's evidence stays in the live corpus
        under canonical_history, and the winner's `supersedes` walks back to
        the first mark ever made, not one hop."""
        self._run("--execute")                                   # rep2
        self._run("--execute", valid={"cfg_rep2": False})        # rep3 supersedes rep2
        self._run("--execute", valid={"cfg_rep2": False, "cfg_rep3": False})   # rep1 supersedes rep3 (and rep2)
        core = self.root / "claudecode_agent_core"
        rep3 = yaml.safe_load((core / "cfg_rep3" / "P_provenance.yaml").read_text())
        self.assertNotIn("canonical", rep3)
        self.assertEqual(len(rep3["canonical_history"]), 1)
        h = rep3["canonical_history"][0]
        self.assertEqual(h["supersedes"], ["cfg_rep2"])           # its own evidence, intact
        self.assertIn("selected_from", h); self.assertIn("margin_over_runner_up", h)
        self.assertEqual(h["superseded_by"]["label"], "cfg_rep1")
        self.assertEqual(rep3["canonical_superseded_by"]["label"], "cfg_rep1")
        rep1 = yaml.safe_load((core / "cfg_rep1" / "P_provenance.yaml").read_text())
        self.assertEqual(rep1["canonical"]["supersedes"], ["cfg_rep3", "cfg_rep2"])
        rep2 = yaml.safe_load((core / "cfg_rep2" / "P_provenance.yaml").read_text())
        self.assertEqual(rep2["canonical_superseded_by"]["label"], "cfg_rep3")   # its own displacer, unchanged

    def test_the_demotion_pointer_is_written_as_a_value_not_an_alias(self):
        """The displaced record names its displacer twice — at the top and inside
        its history entry. Written as one shared object, PyYAML emits the second
        as `*id001`, a reference a reader of the file has to chase."""
        self._run("--execute")
        self._run("--execute", valid={"cfg_rep2": False})
        text = (self.root / "claudecode_agent_core" / "cfg_rep2" / "P_provenance.yaml").read_text()
        self.assertNotIn("&id", text); self.assertNotIn("*id", text)

    def test_a_same_winner_rerun_keeps_the_chain_and_re_promotion_is_clean(self):
        """#748: re-selecting the current canonical must not drop its chain;
        a record promoted again after a displacement must not name itself
        and must shed the pointer that said it was displaced."""
        core = self.root / "claudecode_agent_core"
        rd = lambda l: yaml.safe_load((core / l / "P_provenance.yaml").read_text())  # noqa: E731
        self._run("--execute")                                   # rep2
        self._run("--execute", valid={"cfg_rep2": False})        # rep3 supersedes rep2
        self._run("--execute")                                   # rep2 again: re-promotion
        rep2 = rd("cfg_rep2")
        self.assertEqual(rep2["canonical"]["supersedes"], ["cfg_rep3"])
        self.assertNotIn("canonical_superseded_by", rep2)
        self.assertEqual(len(rep2["canonical_history"]), 1)     # its first mark, displaced by rep3
        self.assertEqual(rep2["canonical_history"][0]["superseded_by"]["label"], "cfg_rep3")
        self._run("--execute")                                   # idempotent re-run, same winner
        rep2 = rd("cfg_rep2")
        self.assertEqual(rep2["canonical"]["supersedes"], ["cfg_rep3"])
        self.assertEqual(len(rep2["canonical_history"]), 2)
        self.assertEqual(rep2["canonical_history"][0]["superseded_by"]["reason"], "re-selected")
        rep3 = rd("cfg_rep3")
        self.assertEqual(rep3["canonical_superseded_by"]["label"], "cfg_rep2")

    def test_a_first_selection_supersedes_nothing(self):
        self._run("--execute")
        first = yaml.safe_load((self.root / "claudecode_agent_core" /
                                "cfg_rep2" / "P_provenance.yaml").read_text())
        self.assertNotIn("supersedes", first["canonical"])

    def test_an_unreadable_prior_record_fails_the_selection(self):
        """#310: a clear that can silently fail to clear guarantees nothing.

        The contract is one canonical record per project. Skipping an
        unreadable file leaves the ambiguity to surface later in
        `canonical_runs`, in a different command, with nothing connecting it
        back to the selection that was meant to resolve it.
        """
        self._run("--execute")                       # cfg_rep2 becomes canonical
        corrupt = (self.root / "claudecode_agent_core" / "cfg_rep2" /
                   "P_provenance.yaml")
        corrupt.write_text(corrupt.read_text() + "\nbroken: [unclosed\n",
                           encoding="utf-8")
        out = self._run("--execute", valid={"cfg_rep2": False})
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("could not be read", out.output)
        self.assertIn("two", out.output, "the message should say what goes wrong")

    def test_a_prior_record_that_is_not_a_mapping_also_fails(self):
        self._run("--execute")
        bad = (self.root / "claudecode_agent_core" / "cfg_rep2" /
               "P_provenance.yaml")
        bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
        out = self._run("--execute", valid={"cfg_rep2": False})
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("not a mapping", out.output)

    def test_one_replicate_is_not_a_selection(self):
        import shutil
        for label in ("cfg_rep2", "cfg_rep3"):
            shutil.rmtree(self.method / label)
        out = self._run()
        self.assertNotEqual(out.exit_code, 0)
        self.assertIn("at least two", out.output)



class TestTheRationaleMatchesTheMeasurement(unittest.TestCase):
    """The figure in the help text must be the one that was measured (#176).

    `select` justified itself with "replicates disagree on 77-98% of the slots
    they share" for months. That was byte equality over nested free text — the
    measure #169 showed returns the same answer regardless of input. A command
    whose stated reason rests on a disproved number is worse than one that
    states no reason, because the number invites belief.
    """

    CACHE = Path("data/evaluation_llm/agreement_cache/matrix.json")

    def _help(self, command):
        from click.testing import CliRunner
        from data_sheets_schema.cli.runs import runs
        return CliRunner().invoke(runs, [command, "--help"]).output

    def test_the_disproved_figure_is_not_offered_as_the_reason(self):
        for command in ("select", "merge"):
            with self.subTest(command=command):
                text = self._help(command)
                claim = re.search(r"disagree on 77-98%", text)
                self.assertIsNone(
                    claim, "77-98% is byte equality; it cannot be the stated "
                           "disagreement rate")

    @unittest.skipUnless(CACHE.exists(), "agreement matrix not present")
    def test_the_quoted_range_is_the_measured_one(self):
        import math
        published = json.loads(self.CACHE.read_text())
        differ = sorted(100 * (1 - c["rate"])
                        for k, c in published.items() if k.startswith("v2"))
        # Floor the low end and ceil the high end so the quoted range provably
        # contains every project. `round()` put CHORUS's exact 62.5 outside the
        # range that claimed to span it, because Python rounds half to even
        # (#283) — no rounding rule should be load-bearing in a figure whose
        # whole point is that the previous one was wrong.
        expected = f"{math.floor(differ[0])}-{math.ceil(differ[-1])}%"
        for command in ("select", "merge"):
            with self.subTest(command=command):
                self.assertIn(
                    expected, self._help(command),
                    f"`d4d runs {command} --help` must quote {expected}, the "
                    f"measured range (per-project: "
                    f"{[f'{d:.1f}' for d in differ]}). If the corpus changed, "
                    f"update the prose in cli/runs.py to match.")

    def test_each_command_names_the_other(self):
        """Two commands recommending opposite things must acknowledge it.

        Otherwise a reader believes whichever help text they happened to open.
        """
        self.assertIn("merging", self._help("select"))
        self.assertIn("select", self._help("merge"))


if __name__ == "__main__":
    unittest.main()
