"""Prompt paths are recorded as this repository names them (#398).

Every other path-like field in a record is repo-relative by construction —
`inputs.bundle_path`, `schema.full_path`, `outputs.*.path` — because they are
built from module constants. Prompt paths came from the command line and were
recorded verbatim, so one prompt could appear under two strings. The sha256
still matched, so integrity was never at risk; what broke is any analysis that
groups runs *by prompt path*, which then sees two conditions where there is one.
"""

import tempfile
import unittest
from pathlib import Path

from data_sheets_schema.provenance import (
    playbook_facts,
    prompt_facts,
    repo_relative,
)

REPO = Path(__file__).resolve().parents[1]
A_PROMPT = "src/download/prompts/d4d_generic_arm_prompt.md"


class TestRepoRelative(unittest.TestCase):
    def test_a_relative_path_is_unchanged(self):
        self.assertEqual(repo_relative(A_PROMPT), A_PROMPT)

    def test_an_absolute_path_inside_the_repo_is_shortened(self):
        """The defect itself: the same file under two strings."""
        self.assertEqual(repo_relative(REPO / A_PROMPT), A_PROMPT)

    def test_both_spellings_agree(self):
        self.assertEqual(repo_relative(A_PROMPT), repo_relative(REPO / A_PROMPT))

    def test_a_path_outside_the_repo_keeps_its_absolute_form(self):
        """Rewriting it would assert a location that does not exist here.

        A long string is better than a wrong one, and the caller can still tell
        the cases apart because only this one comes back absolute.
        """
        with tempfile.TemporaryDirectory() as d:
            outside = Path(d) / "elsewhere.md"
            self.assertEqual(repo_relative(outside), str(outside.resolve()))
            self.assertTrue(Path(repo_relative(outside)).is_absolute())

    def test_an_outside_path_is_resolved_too(self):
        """Both branches resolve, or the same defect survives outside the repo.

        On macOS `/var` is a symlink to `/private/var`, so an unresolved
        outside path reproduces exactly the two-strings-one-file problem this
        function exists to remove — just beyond the repo boundary. Caught by
        the test above failing on that difference.
        """
        with tempfile.TemporaryDirectory() as d:
            a = repo_relative(Path(d) / "x.md")
            b = repo_relative(Path(d).resolve() / "x.md")
            self.assertEqual(a, b)

    def test_a_nonexistent_path_inside_the_repo_still_normalises(self):
        """Recording is not gated on the file existing — `exists` is its own
        field, and a missing prompt should still be named consistently."""
        self.assertEqual(repo_relative(REPO / "src/download/prompts/nope.md"),
                         "src/download/prompts/nope.md")

    def test_a_traversal_is_resolved_not_preserved(self):
        self.assertEqual(
            repo_relative(REPO / "src/download/../download/prompts" /
                          "d4d_generic_arm_prompt.md"),
            A_PROMPT)


class TestRecordedFacts(unittest.TestCase):
    def test_prompt_facts_records_the_repo_relative_path(self):
        facts = prompt_facts([REPO / A_PROMPT])
        self.assertEqual([f["path"] for f in facts["files"]], [A_PROMPT])

    def test_prompt_facts_agrees_across_spellings(self):
        """Two records of one run must not describe two conditions."""
        absolute = prompt_facts([REPO / A_PROMPT])
        relative = prompt_facts([Path(A_PROMPT)])
        self.assertEqual([f["path"] for f in absolute["files"]],
                         [f["path"] for f in relative["files"]])
        self.assertEqual([f["sha256"] for f in absolute["files"]],
                         [f["sha256"] for f in relative["files"]])

    def test_playbook_facts_are_normalised_too(self):
        """Same writer, same defect — and playbooks are hashed for every run."""
        for entry in playbook_facts()["files"]:
            with self.subTest(path=entry["path"]):
                self.assertFalse(Path(entry["path"]).is_absolute())

    def test_no_recorded_path_leaks_a_home_directory(self):
        facts = prompt_facts([REPO / A_PROMPT])
        for entry in facts["files"]:
            self.assertNotIn("/Users/", entry["path"])
            self.assertNotIn("/home/", entry["path"])


class TestPlanFacts(unittest.TestCase):
    def test_the_plan_records_repo_relative_prompt_files(self):
        """`api_runner.plan` is the third writer and was not normalised either."""
        from data_sheets_schema.api_runner import RunSpec, plan

        bundle = Path("data/preprocessed/concatenated/CHORUS_preprocessed.txt")
        if not bundle.exists():
            self.skipTest("bundle not present")
        spec = RunSpec(project="CHORUS", arm="BASELINE (input documents only)",
                       method="claudecode_agent", bundle=bundle, label="L",
                       condition="generic", runtime="Claude API (direct)",
                       provider="Anthropic")
        for recorded in plan(spec)["prompt_files"]:
            with self.subTest(path=recorded):
                self.assertFalse(Path(recorded).is_absolute())
