"""A subagent's reply proves which definition it was given (#1077).

The incident: the Element 8 software threshold was written into
`d4d-rubric10-semantic.md`, verified on disk, and a subagent spawned
afterwards reported the pre-edit criteria verbatim. Intermittent, so worse
than consistent — a rescore can silently measure the old instrument and
nothing in its output says so.

`instrument_sha256` (#1099) does not detect this. The agent computes that by
reading the file from disk, which is current, while the definition it was
handed may be stale; the two agree even when the run is wrong. Only a
challenge the stale text cannot answer discriminates.

The decisive test here replays the actual incident from git — `8813c8e6`
against `119e3171` — because the first version of this module failed exactly
that replay: it drew the challenge from the longest line, which both versions
shared.
"""
import subprocess
import unittest
from pathlib import Path

from data_sheets_schema.agent_pin import (MIN_CHALLENGE, StaleAgentDefinition,
                                          _normalise, _usable, agent_digest,
                                          challenge, challenge_is_from_a_change,
                                          echoed, spawn_preamble, verify_echo)

REPO = Path(__file__).resolve().parents[1]
AGENT = "d4d-rubric10-semantic"
AGENT_REL = f".claude/agents/{AGENT}.md"


class TestTheChallengeDiscriminates(unittest.TestCase):
    def test_it_catches_the_incident_that_filed_the_issue(self):
        """The one that matters. `8813c8e6` is the text the stale subagent
        held; `119e3171` added the #1059 threshold. A challenge drawn from
        the addition is absent from the old text; one drawn from the longest
        line is not, which is how the first version of this passed review and
        would still have missed the defect."""
        pre = subprocess.run(["git", "show", f"8813c8e6:{AGENT_REL}"],
                             capture_output=True, cwd=REPO)
        diff = subprocess.run(
            ["git", "diff", "--unified=0", "8813c8e6", "119e3171", "--",
             AGENT_REL], capture_output=True, text=True, cwd=REPO)
        if pre.returncode or not diff.stdout:
            self.skipTest("that history is not in this checkout")
        old = pre.stdout.decode("utf-8", "replace")
        added = _usable([ln[1:] for ln in diff.stdout.splitlines()
                         if ln.startswith("+") and not ln.startswith("+++")])
        self.assertTrue(added, "the #1059 change added no usable line")
        self.assertNotIn(_normalise(max(added, key=len)), _normalise(old),
                         "a challenge from the change is in the stale text")

        #: And the rule the first version used would have failed here.
        longest_overall = max(_usable(old.split("---", 2)[2].splitlines()),
                              key=len)
        self.assertIn(_normalise(longest_overall), _normalise(old),
                      "the longest-line rule echoes from the stale text, "
                      "which is why it is not the rule")

    def test_the_challenge_comes_from_a_change_where_there_is_one(self):
        self.assertTrue(challenge_is_from_a_change(AGENT))

    def test_a_challenge_is_long_enough_that_echoing_it_is_not_luck(self):
        self.assertGreaterEqual(len(challenge(AGENT)), MIN_CHALLENGE)

    def test_a_challenge_is_prose_not_a_marker(self):
        """A heading or list bullet recurs across versions and discriminates
        nothing."""
        first = challenge(AGENT).lstrip()[:2]
        self.assertNotIn(first[0], "#|>")
        self.assertFalse(first.startswith(("- ", "* ", "+ ")))


class TestVerification(unittest.TestCase):
    def test_a_reply_without_the_challenge_is_refused(self):
        with self.assertRaises(StaleAgentDefinition):
            verify_echo(AGENT, "I applied the rubric as given.")

    def test_a_reply_quoting_it_is_accepted(self):
        self.assertTrue(echoed(AGENT, f"Quoting: {challenge(AGENT)}"))

    def test_whitespace_and_case_do_not_decide_it(self):
        noisy = "  ".join(challenge(AGENT).upper().split())
        self.assertTrue(echoed(AGENT, f"> {noisy}\n"))

    def test_the_refusal_says_what_it_means(self):
        with self.assertRaises(StaleAgentDefinition) as caught:
            verify_echo(AGENT, "nothing relevant")
        message = str(caught.exception)
        self.assertIn("#1077", message)
        self.assertIn("stale", message)


class TestThePreamble(unittest.TestCase):
    def test_it_carries_the_digest_the_agent_must_record(self):
        text = spawn_preamble(AGENT)
        self.assertIn(agent_digest(AGENT), text)
        self.assertIn("instrument_sha256", text)

    def test_it_tells_the_agent_to_stop_rather_than_proceed(self):
        """A stale agent that answers anyway produces a number that looks
        like a rescore and is not one."""
        text = spawn_preamble(AGENT)
        self.assertIn("stop rather than proceeding", text)

    def test_it_quotes_the_challenge(self):
        self.assertIn(challenge(AGENT), spawn_preamble(AGENT))


if __name__ == "__main__":
    unittest.main()
