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
- `recovered_by_time` — the hash is a rubric-text version, so the agent
  version current at `evaluation_timestamp` is named instead. That is a
  weaker claim and is labelled as one, the way #399's prompt hashes recovered
  from git are.

The test is that **no evaluation is unresolved**. A new evaluation whose
instrument cannot be placed either way fails here rather than joining the
corpus unidentifiable.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "data" / "evaluation_instruments.json"
SCRIPT = ROOT / "scripts" / "instrument_provenance.py"
RUBRICS = ("rubric10_semantic", "rubric20_semantic")


class InstrumentManifest(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest("no manifest in this checkout")
        self.doc = json.loads(MANIFEST.read_text())

    def _live(self, rubric):
        base = ROOT / "data" / "evaluation_llm" / rubric / "label_aware"
        return sorted(p.name for p in base.glob("*_evaluation.json")) \
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
                if entry["basis"] != "recovered_by_time":
                    continue
                with self.subTest(rubric=rubric, evaluation=name):
                    self.assertIn("recorded_hash_is", entry)
                    self.assertTrue(entry.get("evaluated_at"),
                                    "a time-recovered instrument needs the "
                                    "time it was recovered from")

    def test_every_named_instrument_is_a_real_agent_version(self):
        for rubric in RUBRICS:
            known = {v["sha256"] for v in self.doc["rubrics"][rubric]["agent_versions"]}
            for name, entry in self.doc["rubrics"][rubric]["evaluations"].items():
                with self.subTest(rubric=rubric, evaluation=name):
                    self.assertIn(entry["instrument_sha256"], known)


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


class TestTheResolverIsReproducible(InstrumentManifest):
    def test_regenerating_the_manifest_changes_nothing(self):
        """The manifest is a pure function of git history and the artifacts,
        so a stale one is a defect rather than a matter of taste."""
        if not SCRIPT.exists():
            self.skipTest("resolver not in this checkout")
        proc = subprocess.run([sys.executable, str(SCRIPT)],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for rubric in RUBRICS:
            counts = {}
            for entry in self.doc["rubrics"][rubric]["evaluations"].values():
                counts[entry["basis"]] = counts.get(entry["basis"], 0) + 1
            summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
            with self.subTest(rubric=rubric):
                self.assertIn(summary, proc.stdout,
                              "the manifest disagrees with a fresh resolve; "
                              "run scripts/instrument_provenance.py --write")


if __name__ == "__main__":
    unittest.main()
