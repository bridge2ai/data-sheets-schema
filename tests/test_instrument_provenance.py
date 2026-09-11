"""Every semantic rubric evaluation resolves to the instrument that scored it.

Why this exists (#1077): an evaluation records `metadata.rubric_hash`, and
until this change the agents' output contract asked for "the sha256 of
rubric10.txt". That file is the rubric *text*. The rules that decide a score
live in the agent definition, and the text did not change across #1059,
#1060 or #1082 — the three revisions that moved scores. So a rubric-text hash
cannot tell two instruments apart, and the 29 rubric10 evaluations that
followed the contract **exactly** are the ones whose instrument their own
artifact cannot name, while the 24 that deviated can be identified. Obeying
the rule was the failure mode.

Nothing is lost, because both files are in git. `scripts/instrument_provenance.py`
resolves every evaluation to an agent version by one of two bases, and the
manifest it writes is what this checks:

- `recorded` — the artifact names its own instrument;
- `recovered_from_commit` — the hash is a rubric-text version, so the agent
  file as it stood in the commit that last wrote this evaluation's bytes is
  named instead. Weaker than a recorded claim, and labelled as one.

Not by timestamp (#1100): the workflow is revise, re-adjudicate, commit
together, so an evaluation's timestamp precedes the commit of the version
that produced it and a time lookup returns the version being replaced. It was
wrong on 19 of 43. The timestamp is also model-written and stale in places.

The test is that **no evaluation is unresolved**. A new evaluation whose
instrument cannot be placed either way fails here rather than joining the
corpus unidentifiable.
"""
import pytest
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "data" / "evaluation_instruments.json"
SCRIPT = ROOT / "scripts" / "instrument_provenance.py"
RUBRICS = ("rubric10_semantic", "rubric20_semantic")
AGENT_PATHS = {
    "rubric10_semantic": ".claude/agents/d4d-rubric10-semantic.md",
    "rubric20_semantic": ".claude/agents/d4d-rubric20-semantic.md",
}


def _shallow():
    """CI checks out at depth 1 (#1100), where `git log --all` sees one
    commit and every evaluation resolves to nothing. Tests that need history
    skip; the ones that check the checked-in manifest against the artifacts
    do not need it and still run."""
    out = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                         capture_output=True, text=True, cwd=ROOT).stdout
    return out.strip() == "true"


class InstrumentManifest(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest("no manifest in this checkout")
        self.doc = json.loads(MANIFEST.read_text())

    def _live(self, rubric):
        base = ROOT / "data" / "evaluation_llm" / rubric
        return sorted(str(p.relative_to(base))
                      for p in base.rglob("*_evaluation.json")) \
            if base.exists() else []


class TestEveryEvaluationNamesItsInstrument(InstrumentManifest):
    def test_no_evaluation_is_unresolved(self):
        """The property the manifest exists for."""
        unresolved = [(rubric, name)
                      for rubric in RUBRICS
                      for name, entry in self.doc["rubrics"][rubric]["evaluations"].items()
                      if entry["basis"] == "unresolved"
                      or not entry.get("instrument_sha256")]
        self.assertEqual(unresolved, [])

    def test_the_manifest_covers_exactly_the_live_evaluations(self):
        for rubric in RUBRICS:
            with self.subTest(rubric=rubric):
                self.assertEqual(
                    sorted(self.doc["rubrics"][rubric]["evaluations"]),
                    self._live(rubric),
                    "run scripts/instrument_provenance.py --write")

    def test_a_recovered_basis_says_what_it_recovered_from(self):
        """A recovered claim must not read like a recorded one (#399)."""
        for rubric in RUBRICS:
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                if entry["basis"] != "recovered_from_commit":
                    continue
                with self.subTest(rubric=rubric, evaluation=name):
                    self.assertIn("recorded_hash_is", entry)
                    self.assertTrue(entry.get("recovered_from"),
                                    "a recovered instrument must name the "
                                    "commit it was recovered from")

    def test_an_uncommitted_evaluation_resolves_to_the_agent_on_disk(self):
        """#1100: `d4d evaluate llm` leaves an untracked evaluation, and
        resolving it from the previous commit would name an instrument that
        did not produce it — so the state immediately after producing a score
        failed the suite, saying the corpus was unidentifiable when the honest
        answer is "not committed yet; the instrument is the file on disk"."""
        if not SCRIPT.exists():
            self.skipTest("resolver not in this checkout")
        source = SCRIPT.read_text()
        self.assertIn('"basis": "working_tree"', source)
        self.assertIn("def _dirty(", source)

    def test_the_archived_scorings_are_in_scope(self):
        """The `superseded_*` directories hold the scorings #1059, #1060 and
        #1082 displaced — the direct evidence of the instrument changes this
        exists to make legible, and the first thing the glob left out."""
        names = set(self.doc["rubrics"]["rubric10_semantic"]["evaluations"])
        self.assertTrue(any(n.startswith("label_aware/superseded_") for n in names),
                        "no archived scoring is covered")
        for marker in ("superseded_software_threshold", "superseded_gate_v1",
                       "superseded_fable5"):
            with self.subTest(archive=marker):
                self.assertTrue(any(marker in n for n in names))

    def test_no_entry_is_resolved_by_timestamp(self):
        """#1100. A time lookup returns the version the run's own commit
        replaced — off by one towards the instrument the revision corrected,
        wrong on 19 of 43 — because the agent and its rescores are committed
        together. `evaluation_timestamp` is model-written besides, and three
        CM4AI files record a time hours before the commit of the text they
        hash. The basis must be the commit that carries the bytes."""
        for rubric in RUBRICS:
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                with self.subTest(rubric=rubric, evaluation=name):
                    self.assertNotEqual(entry["basis"], "recovered_by_time")
                    self.assertNotIn("evaluated_at", entry)

    def test_recovered_commit_contains_the_evaluation_and_named_agent(self):
        """Verify both artifacts in git, including scores archived later."""
        if _shallow():
            self.skipTest("shallow clone: no history to resolve against")
        for rubric, agent in AGENT_PATHS.items():
            base = ROOT / "data" / "evaluation_llm" / rubric
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                if entry["basis"] != "recovered_from_commit":
                    continue
                with self.subTest(rubric=rubric, evaluation=name):
                    commit = entry["recovered_from"]
                    history = subprocess.run(
                        ["git", "log", "--follow", "--find-renames=100%",
                         "--format=%H", "--", str(base / name)],
                        capture_output=True, text=True, cwd=ROOT, check=True).stdout
                    self.assertTrue(any(c.startswith(commit) for c in history.split()))
                    # Its historic path may differ. Match the actual JSON
                    # blob against the rubric tree at the recovered commit.
                    evaluation_blob = subprocess.run(
                        ["git", "hash-object", str(base / name)],
                        capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
                    tree_blobs = subprocess.run(
                        ["git", "ls-tree", "-r", "--format=%(objectname)", commit,
                         "--", str(base.relative_to(ROOT))],
                        capture_output=True, text=True, cwd=ROOT, check=True).stdout.split()
                    self.assertIn(evaluation_blob, tree_blobs)
                    blob = subprocess.run(["git", "show", f"{commit}:{agent}"],
                                          capture_output=True, cwd=ROOT, check=True)
                    self.assertEqual(
                        hashlib.sha256(blob.stdout).hexdigest(),
                        entry["instrument_sha256"])

    def test_every_named_instrument_is_a_real_agent_version(self):
        """Against git, not against the manifest's own list (#1100).

        Checking `instrument_sha256` against the manifest's `agent_versions`
        was an internal-consistency check: a fabricated hash passed as long as
        it was also appended to that block. These are hashes of real blobs or
        they are nothing.
        """
        if _shallow():
            self.skipTest("shallow clone: no history to hash against")
        for rubric, agent in AGENT_PATHS.items():
            real = set()
            for commit in subprocess.run(
                    ["git", "log", "--all", "--format=%H", "--", agent],
                    capture_output=True, text=True, cwd=ROOT).stdout.split():
                blob = subprocess.run(["git", "show", f"{commit}:{agent}"],
                                      capture_output=True, cwd=ROOT)
                if not blob.returncode:
                    real.add(hashlib.sha256(blob.stdout).hexdigest())
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                with self.subTest(rubric=rubric, evaluation=name):
                    self.assertIn(entry["instrument_sha256"], real)

    def test_a_recorded_instrument_is_read_from_the_new_key_when_present(self):
        """#1100: the resolver read only `rubric_hash`, so an evaluation that
        obeyed the revised contract and recorded its instrument outright was
        still resolved from its writing commit. Following the fix downgraded
        the evidence it produced."""
        if not SCRIPT.exists():
            self.skipTest("resolver not in this checkout")
        source = SCRIPT.read_text()
        self.assertIn('meta.get("instrument_sha256") or meta.get("rubric_hash")',
                      source)


class TestTheContractAsksForTheScoringRules(unittest.TestCase):
    """The fix itself: the contract now names the file whose bytes decide a
    score, not only the text it reads."""

    def test_both_agents_ask_for_their_own_hash(self):
        for name in ("d4d-rubric10-semantic", "d4d-rubric20-semantic"):
            with self.subTest(agent=name):
                text = (ROOT / ".claude" / "agents" / f"{name}.md").read_text()
                self.assertIn(f'"instrument_sha256": "<sha256 of '
                              f'.claude/agents/{name}.md, this file>"', text)
                self.assertIn("Why two hashes (#1077)", text)

    def test_the_rubric_hash_names_its_path(self):
        """`<sha256 of rubric10.txt>` named no path, which is part of why
        three different sources ended up in the field."""
        for name, rubric in (("d4d-rubric10-semantic", "rubric10"),
                             ("d4d-rubric20-semantic", "rubric20")):
            with self.subTest(agent=name):
                text = (ROOT / ".claude" / "agents" / f"{name}.md").read_text()
                self.assertIn(f'"rubric_hash": "<sha256 of data/rubric/'
                              f'{rubric}.txt>"', text)


@pytest.mark.corpus   # walks the committed corpus; the main-branch lane (#1203)
class TestTheResolverIsReproducible(InstrumentManifest):
    def test_regenerating_the_manifest_changes_nothing(self):
        """Content, not counts (#1100).

        The first version compared the summary line, so a manifest whose
        entries had all moved to different — but equally distributed —
        instruments would have passed. It rebuilds and compares the mapping.
        """
        if not SCRIPT.exists():
            self.skipTest("resolver not in this checkout")
        if _shallow():
            self.skipTest("shallow clone: git history is not available")
        import importlib.util
        spec = importlib.util.spec_from_file_location("_ip", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for rubric in RUBRICS:
            with self.subTest(rubric=rubric):
                #: The whole block, not only the attributions (#1100). Every
                #: agent revision adds a version the committed manifest lacks
                #: while attributions and counts stay identical — which is how
                #: the first manifest shipped stale — so `agent_versions` has
                #: to be compared too.
                self.assertEqual(module.resolve(rubric),
                                 self.doc["rubrics"][rubric],
                                 "the manifest disagrees with a fresh resolve; "
                                 "run scripts/instrument_provenance.py --write")


if __name__ == "__main__":
    unittest.main()
